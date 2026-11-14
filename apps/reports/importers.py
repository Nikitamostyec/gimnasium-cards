import io
from dataclasses import dataclass

import docx
import openpyxl
from django.db import transaction

from cards.models import CardAssignment, Student, Trimester
from core.utils import normalize_class_str, normalize_text, parse_grade_class


@dataclass
class ParsedRow:
    """Структура одной распарсенной строки из файла импорта."""

    row_num: int
    full_name: str
    grade_num: int
    grade_letter: str
    card_type: str
    card_type_display: str


def _parse_card_type(raw_value: str) -> str:
    """Определяет тип карты по текстовому описанию из ячейки файла."""
    cleaned = normalize_text(raw_value)
    if 'золот' in cleaned or 'gold' in cleaned:
        return CardAssignment.CardType.GOLD
    if 'серебр' in cleaned or 'silver' in cleaned:
        return CardAssignment.CardType.SILVER
    raise ValueError(f'Неизвестный тип карты: "{raw_value}"')


def _extract_raw_rows_from_xlsx(file_bytes: bytes) -> list[tuple[int, list[str]]]:
    """Извлекает непустые строки из первого листа Excel-книги."""
    workbook = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    sheet = workbook.active
    rows = []
    for idx, row in enumerate(sheet.iter_rows(values_only=True), start=1):
        cells = [str(cell).strip() if cell is not None else '' for cell in row[:3]]
        if any(cells):
            rows.append((idx, cells))
    return rows


def _extract_raw_rows_from_docx(file_bytes: bytes) -> list[tuple[int, list[str]]]:
    """Извлекает непустые строки из всех таблиц документа Word."""
    document = docx.Document(io.BytesIO(file_bytes))
    rows = []
    row_counter = 0
    for table in document.tables:
        for row in table.rows:
            row_counter += 1
            cells = [cell.text.strip() for cell in row.cells[:3]]
            if any(cells):
                rows.append((row_counter, cells))
    return rows


def parse_students_file(
    filename: str, file_bytes: bytes
) -> tuple[list[ParsedRow], list[str]]:
    """Разбирает файл .xlsx или .docx и возвращает список валидных записей и ошибок."""
    lower_name = filename.lower()
    if lower_name.endswith('.xlsx'):
        raw_rows = _extract_raw_rows_from_xlsx(file_bytes)
    elif lower_name.endswith('.docx'):
        raw_rows = _extract_raw_rows_from_docx(file_bytes)
    else:
        return [], ['Неподдерживаемый формат файла. Загрузите .xlsx или .docx.']

    valid_rows: list[ParsedRow] = []
    errors: list[str] = []
    seen_students: set[tuple[str, str]] = set()

    for row_num, cells in raw_rows:
        if len(cells) < 3:
            errors.append(f'Строка {row_num}: недостаточно столбцов (ожидается 3).')
            continue

        raw_name, raw_class, raw_card = cells[0], cells[1], cells[2]

        if row_num == 1 and ('фио' in raw_name.lower() or 'ученик' in raw_name.lower()):
            continue

        norm_name = normalize_text(raw_name)
        if len(norm_name.split()) < 2:
            errors.append(f'Строка {row_num}: некорректное ФИО "{raw_name}".')
            continue

        try:
            grade_num, grade_letter = parse_grade_class(raw_class)
        except ValueError as exc:
            errors.append(f'Строка {row_num}: {exc}')
            continue

        try:
            card_type = _parse_card_type(raw_card)
        except ValueError as exc:
            errors.append(f'Строка {row_num}: {exc}')
            continue

        student_key = (norm_name, normalize_class_str(raw_class))
        if student_key in seen_students:
            errors.append(
                f'Строка {row_num}: дубликат ученика "{raw_name}" ({grade_num}{grade_letter}) в файле.'
            )
            continue
        seen_students.add(student_key)

        display_type = (
            'Золотая' if card_type == CardAssignment.CardType.GOLD else 'Серебряная'
        )
        valid_rows.append(
            ParsedRow(
                row_num=row_num,
                full_name=' '.join(raw_name.split()),
                grade_num=grade_num,
                grade_letter=grade_letter,
                card_type=card_type,
                card_type_display=display_type,
            )
        )

    return valid_rows, errors


@transaction.atomic
def commit_imported_students(trimester: Trimester, parsed_rows: list[dict]) -> int:
    """Сохраняет проверенный список учеников и назначает им карты в выбранном триместре."""
    created_or_updated = 0
    for item in parsed_rows:
        norm_name = normalize_text(item['full_name'])
        norm_class = normalize_class_str(f"{item['grade_num']}{item['grade_letter']}")

        student, _ = Student.objects.update_or_create(
            normalized_name=norm_name,
            normalized_class=norm_class,
            defaults={
                'full_name': item['full_name'],
                'grade_num': item['grade_num'],
                'grade_letter': item['grade_letter'],
            },
        )

        CardAssignment.objects.get_or_create(
            student=student,
            trimester=trimester,
            defaults={'card_type': item['card_type']},
        )
        created_or_updated += 1

    return created_or_updated
