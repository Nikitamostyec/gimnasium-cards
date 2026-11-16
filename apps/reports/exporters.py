import io

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

from cards.models import CardAssignment, PrivilegeRequest, Trimester


def generate_trimester_report_xlsx(trimester: Trimester) -> bytes:
    """Формирует сводный Excel-отчет по картам и заявкам за выбранный триместр."""
    workbook = openpyxl.Workbook()

    ws_summary = workbook.active
    ws_summary.title = 'Сводка по ученикам'

    header_font = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='2B547E', end_color='2B547E', fill_type='solid')

    summary_headers = [
        'ФИ ученика',
        'Код активации',
        'Класс',
        'Тип карты',
        'Общий лимит',
        'Использовано',
        'Остаток',
    ]
    ws_summary.append(summary_headers)
    for cell in ws_summary[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')

    cards = (
        CardAssignment.objects.select_related('student')
        .filter(trimester=trimester)
        .order_by('student__grade_num', 'student__grade_letter', 'student__full_name')
    )

    for card in cards:
        code_value = (
            card.student.activation_code
            if card.student.activation_code
            else 'Активирована'
        )
        ws_summary.append([
            card.student.full_name,
            code_value,
            f'{card.student.grade_num}{card.student.grade_letter}',
            'Золотая' if card.card_type == CardAssignment.CardType.GOLD else 'Серебряная',
            card.limit,
            card.used,
            card.remaining_limit,
        ])

    ws_requests = workbook.create_sheet(title='Детализация заявок')
    req_headers = [
        '№ Заявки',
        'Дата подачи',
        'ФИ ученика',
        'Класс',
        'Привилегия',
        'Предмет / Дата',
        'Статус',
        'Обработал',
        'Причина отклонения',
    ]
    ws_requests.append(req_headers)
    for cell in ws_requests[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')

    requests = (
        PrivilegeRequest.objects.select_related(
            'card__student', 'privilege', 'subject', 'processed_by'
        )
        .filter(card__trimester=trimester)
        .order_by('-created_at')
    )

    for req in requests:
        details = ''
        if req.subject:
            details = req.subject.name
        elif req.target_date:
            details = req.target_date.strftime('%d.%m.%Y')

        staff_name = str(req.processed_by) if req.processed_by else '-'
        ws_requests.append([
            req.id,
            req.created_at.strftime('%d.%m.%Y %H:%M'),
            req.card.student.full_name,
            f'{req.card.student.grade_num}{req.card.student.grade_letter}',
            req.privilege.name,
            details,
            req.get_status_display(),
            staff_name,
            req.rejection_reason or '-',
        ])

    for sheet in (ws_summary, ws_requests):
        for column_cells in sheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in column_cells)
            sheet.column_dimensions[column_cells[0].column_letter].width = min(
                max_len + 4, 45
            )

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def generate_import_template_xlsx() -> bytes:
    """Формирует готовый шаблон Excel для импорта списков награждённых учеников."""
    workbook = openpyxl.Workbook()
    ws = workbook.active
    ws.title = 'Список учеников'

    header_font = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='2B547E', end_color='2B547E', fill_type='solid')

    headers = ['ФИ', 'Класс', 'Карта']
    ws.append(headers)
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')

    ws.append(['Иванов Иван', '10Ф', 'Золотая'])
    ws.append(['Петрова Анна', '8А', 'Серебряная'])

    ws.column_dimensions['A'].width = 28
    ws.column_dimensions['B'].width = 14
    ws.column_dimensions['C'].width = 20

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()

