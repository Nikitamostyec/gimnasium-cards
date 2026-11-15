import re

HOMOGLYPHS = str.maketrans({
    'a': 'а', 'b': 'в', 'c': 'с', 'e': 'е', 'h': 'н', 'k': 'к',
    'm': 'м', 'o': 'о', 'p': 'р', 't': 'т', 'x': 'х', 'y': 'у',
    'ё': 'е',
})

CLASS_PATTERN = re.compile(r'^(?P<num>1[0-1]|[1-9])(?P<letter>[а-я]{1,2})$')


def normalize_text(text: str) -> str:
    """Нормализует ФИО: убирает лишние пробелы, дефисы с пробелами и заменяет омоглифы."""
    if not text:
        return ''
    cleaned = text.strip().lower().translate(HOMOGLYPHS)
    cleaned = re.sub(r'\s*-\s*', '-', cleaned)
    cleaned = re.sub(r'[^а-я\- ]+', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def normalize_class_str(class_str: str) -> str:
    """Приводит строку класса к единому формату вида '9а' или '11б' без спецсимволов."""
    if not class_str:
        return ''
    cleaned = class_str.strip().lower().translate(HOMOGLYPHS)
    cleaned = re.sub(r'[^0-9а-я]+', '', cleaned)
    return cleaned


def parse_grade_class(class_str: str) -> tuple[int, str]:
    """Извлекает номер класса (1–11) и заглавную букву из произвольной строки."""
    normalized = normalize_class_str(class_str)
    match = CLASS_PATTERN.match(normalized)
    if not match:
        raise ValueError(f'Некорректный формат класса: "{class_str}"')
    return int(match.group('num')), match.group('letter').upper()
