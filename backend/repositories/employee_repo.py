"""Репозиторий: рестораны, должности, сотрудники"""

import logging
from datetime import datetime
from typing import List, Dict, Optional

from backend.db import MSSQLClient
from backend.models import Restaurant, Position, Employee

logger = logging.getLogger(__name__)

# Карта префиксов ресторанов
PREFIX_MAP = {
    "Ресторан Москва": "msk",
    "Ресторан Петербург": "spb",
    "Ресторан Казань": "kzn",
    "Ресторан Центральный": "cnt",
    "Бар Саратов": "bsar",
    "Бар Воронеж": "bvrn",
    "Ресторан Нижний Новгород": "nn",
    "Администрация": "adm",
    "Ресторан Саратов": "sar",
    "Кафе Центральное": "cf",
    "Ресторан Южный": "yug",
    "Ресторан Пенза": "pen",
    "Ресторан Тверь": "tvr",
    "Ресторан Краснодар": "kr",
    "Ресторан Маяк": "myk",
}


def _get_prefix(name: str) -> str:
    if name in PREFIX_MAP:
        return PREFIX_MAP[name]
    for key, prefix in PREFIX_MAP.items():
        if key in name or name in key:
            logger.info("Частичное совпадение префикса: %s -> %s -> %s", name, key, prefix)
            return prefix
    words = name.split()
    if words:
        return ''.join(w[0].lower() for w in words)[:5]
    return "xx"


class EmployeeRepository:

    def __init__(self, db: MSSQLClient):
        self.db = db

    def load_restaurants(self) -> List[Restaurant]:
        query = """
        SELECT DISTINCT 
            п.[Ссылка] AS ID,
            п.[Наименование] AS Наименование
        FROM [dbo].[СотрудникиОрганизаций_Перевод] с
        INNER JOIN [dbo].[ПодразделенияОрганизаций] п 
            ON с.[ТекущееПодразделениеОрганизации] = п.[Ссылка]
        WHERE с.[ДатаУвольнения] IS NULL
        ORDER BY п.[Наименование]
        """
        result = self.db.execute_query(query) or []
        restaurants = []
        for row in result:
            name = row["Наименование"]
            restaurants.append(Restaurant(
                id=row["ID"],
                name=name,
                prefix=_get_prefix(name),
            ))
        logger.info("Загружено ресторанов: %d", len(restaurants))
        return restaurants

    def load_positions(self) -> List[Position]:
        query = """
        SELECT DISTINCT 
            [Ссылка] AS ID,
            [Наименование] AS Наименование
        FROM [dbo].[ДолжностиОрганизаций]
        ORDER BY [Наименование]
        """
        result = self.db.execute_query(query) or []
        positions = [Position(id=row["ID"], name=row["Наименование"]) for row in result]
        logger.info("Загружено должностей: %d", len(positions))
        return positions

    def load_employees(self, selected_date: str = None) -> List[Employee]:
        if selected_date is None:
            selected_date = datetime.now().strftime("%d.%m.%Y")

        sql_date = _parse_date_sql(selected_date)
        query = """
        SELECT 
            с.[Ссылка] AS ID,
            с.[Наименование] AS Сотрудник,
            п.[Ссылка] AS ПодразделениеID,
            п.[Наименование] AS Подразделение,
            д.[Наименование] AS Должность,
            д.[Ссылка] AS ДолжностьID,
            с.[ДатаПриемаНаРаботу],
            с.[ДатаУвольнения]
        FROM [dbo].[СотрудникиОрганизаций_Перевод] с
        LEFT JOIN [dbo].[ДолжностиОрганизаций] д 
            ON с.[ТекущаяДолжностьОрганизации] = д.[Ссылка]
        LEFT JOIN [dbo].[ПодразделенияОрганизаций] п 
            ON с.[ТекущееПодразделениеОрганизации] = п.[Ссылка]
        WHERE 
            (TRY_CONVERT(date, с.[ДатаПриемаНаРаботу], 104) <= CONVERT(date, ?, 120) OR с.[ДатаПриемаНаРаботу] IS NULL)
        ORDER BY 
            CASE 
                WHEN с.[ДатаУвольнения] IS NULL THEN 0
                WHEN TRY_CONVERT(date, с.[ДатаУвольнения], 104) <= CONVERT(date, ?, 120) THEN 1
                ELSE 0
            END,
            д.[Наименование], 
            с.[Наименование]
        """
        result = self.db.execute_query(query, (sql_date, sql_date)) or []
        employees = []

        for row in result:
            position = row["Должность"]
            if not position:
                continue

            dismissal_date = row["ДатаУвольнения"]
            dismissal_date_str = _format_date(dismissal_date)
            is_dismissed = _is_dismissed(dismissal_date, sql_date)

            should_show = True
            if is_dismissed:
                should_show = _is_dismissed_in_recent_months(dismissal_date_str, sql_date)

            employees.append(Employee(
                id=row["ID"],
                fio=row["Сотрудник"],
                position=position,
                position_id=row["ДолжностьID"],
                department=row["Подразделение"],
                department_id=row["ПодразделениеID"],
                hire_date=_format_date(row["ДатаПриемаНаРаботу"]),
                dismissal_date=dismissal_date_str,
                is_dismissed_on_date=is_dismissed,
                should_show=should_show,
            ))

        dismissed_count = sum(1 for e in employees if e.is_dismissed_on_date)
        logger.info("Загружено сотрудников на дату %s: %d (уволено: %d)", selected_date, len(employees), dismissed_count)
        return employees

    def load_t12_restaurants(self) -> List[Restaurant]:
        query = """
        SELECT DISTINCT 
            [Ссылка] AS ID,
            [Наименование] AS Наименование
        FROM [dbo].[ПодразделенияОрганизаций]
        WHERE [Наименование] LIKE '%Ресторан%' 
           OR [Наименование] LIKE '%Бар%'
           OR [Наименование] LIKE '%Кафе%'
           OR [Наименование] = 'Администрация'
        ORDER BY [Наименование]
        """
        result = self.db.execute_query(query) or []
        restaurants = []
        for row in result:
            restaurants.append(Restaurant(id=row["ID"], name=row["Наименование"], prefix=""))
        logger.info("Т-12: загружено ресторанов: %d", len(restaurants))
        return restaurants


def _parse_date_sql(selected_date: str) -> str:
    date_formats = ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"]
    for fmt in date_formats:
        try:
            return datetime.strptime(selected_date, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return datetime.now().strftime("%Y-%m-%d")


def _format_date(value) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, str):
        return value[:10] if len(value) > 10 else value
    return str(value)


def _is_dismissed(dismissal_date, sql_date: str) -> bool:
    if not dismissal_date:
        return False
    try:
        if isinstance(dismissal_date, datetime):
            dismissal_obj = dismissal_date
        elif isinstance(dismissal_date, str):
            for fmt in ["%Y-%m-%d", "%Y%m%d", "%d.%m.%Y"]:
                try:
                    dismissal_obj = datetime.strptime(dismissal_date[:10], fmt)
                    break
                except Exception:
                    continue
            else:
                return False
        else:
            return False
        selected_obj = datetime.strptime(sql_date, "%Y-%m-%d")
        return dismissal_obj <= selected_obj
    except Exception:
        return False


def _is_dismissed_in_recent_months(dismissal_date_str: str, current_date_str: str) -> bool:
    if not dismissal_date_str:
        return False
    try:
        dismissal_date = datetime.strptime(dismissal_date_str, "%d.%m.%Y")
        current_date = datetime.strptime(current_date_str, "%Y-%m-%d")
        first_day_current = current_date.replace(day=1)
        if first_day_current.month == 1:
            first_day_prev = first_day_current.replace(year=first_day_current.year - 1, month=12)
        else:
            first_day_prev = first_day_current.replace(month=first_day_current.month - 1)
        return first_day_prev <= dismissal_date <= current_date
    except Exception:
        return False
