"""Утилиты форматирования"""


def format_hours(hours) -> str:
    """Форматирование часов: целые без дробной части, дробные с запятой"""
    if hours is None:
        return ''
    try:
        h = float(hours)
    except (ValueError, TypeError):
        return ''
    if h == int(h):
        return str(int(h))
    s = f"{h:.2f}".rstrip('0').rstrip('.')
    return s.replace('.', ',')


def is_hours_code(code: str) -> bool:
    """Проверка, является ли код числом часов"""
    if not code:
        return False
    try:
        float(str(code).replace(',', '.'))
        return True
    except (ValueError, TypeError):
        return False
