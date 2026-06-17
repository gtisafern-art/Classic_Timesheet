"""Валидаторы: лимиты часов, исключения сотрудников"""

import logging
from datetime import datetime
from typing import Optional, Set, List, Dict, Tuple

from backend.db import MSSQLClient

logger = logging.getLogger(__name__)


# ============================================================
# EmployeeExemption
# ============================================================

class EmployeeExemptionLoader:
    """Загрузка списка сотрудников-исключений из БД
    Критерии: Наименование содержит 'ЕЖД' или ' БД '
    """

    @staticmethod
    def load_exempted(db_client: MSSQLClient) -> Set[str]:
        exempted = set()
        if not db_client or not db_client.connection:
            logger.warning("Нет подключения к БД для загрузки исключений")
            return exempted

        try:
            query = """
            SELECT [Ссылка], [Наименование]
            FROM [TimesheetDB].[dbo].[СотрудникиОрганизаций_Перевод]
            WHERE [Наименование] LIKE '%ЕЖД%' 
               OR [Наименование] LIKE '% БД %'
            """
            result = db_client.execute_query(query)
            if result:
                for row in result:
                    exempted.add(row['Ссылка'])
                logger.info("Всего загружено исключений: %d", len(exempted))
        except Exception as e:
            logger.error("Ошибка при загрузке исключений: %s", e)

        return exempted


class EmployeeExemption:
    _exempted: Set[str] = set()

    @classmethod
    def initialize(cls, db_client: MSSQLClient):
        cls._exempted = EmployeeExemptionLoader.load_exempted(db_client)

    @classmethod
    def is_exempted(cls, employee_id: str) -> bool:
        return employee_id in cls._exempted

    @classmethod
    def get_count(cls) -> int:
        return len(cls._exempted)


# ============================================================
# WorkHoursValidator — лимиты по подразделениям и дням недели
# ============================================================

class WorkHoursValidator:
    RESTRICTED_GROUP1 = [
        "A0000000000000000000000000000001",
        "A0000000000000000000000000000002",
        "A0000000000000000000000000000003",
        "A0000000000000000000000000000004",
        "A0000000000000000000000000000005",
        "A0000000000000000000000000000006",
        "A0000000000000000000000000000007",
        "A0000000000000000000000000000008",
        "A0000000000000000000000000000009",
        "A0000000000000000000000000000010",
        "A0000000000000000000000000000011",
        "A0000000000000000000000000000012",
        "A0000000000000000000000000000013",
    ]
    RESTRICTED_GROUP2 = [
        "B0000000000000000000000000000001",
    ]

    @staticmethod
    def get_day_of_week(date_str: str) -> int:
        try:
            return datetime.strptime(date_str, "%d.%m.%Y").weekday()
        except Exception:
            return datetime.now().weekday()

    @staticmethod
    def get_max_hours(department_id: str, date_str: str) -> Optional[float]:
        if not department_id:
            return None
        day = WorkHoursValidator.get_day_of_week(date_str)

        if department_id in WorkHoursValidator.RESTRICTED_GROUP1:
            if day in [6, 0, 1, 2, 3]:
                return 12.0
            elif day in [4, 5]:
                return 14.0

        elif department_id in WorkHoursValidator.RESTRICTED_GROUP2:
            if day in [0, 1, 2, 3]:
                return 12.0
            elif day in [4, 6]:
                return 14.0
            elif day == 5:
                return 16.0

        return None

    @staticmethod
    def validate(hours: float, department_id: str, date_str: str,
                 employee_id: str = None) -> Tuple[bool, Optional[str]]:
        if employee_id and EmployeeExemption.is_exempted(employee_id):
            return True, None

        max_hours = WorkHoursValidator.get_max_hours(department_id, date_str)
        if max_hours is None:
            return True, None

        if hours > max_hours:
            day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
            day_name = day_names[WorkHoursValidator.get_day_of_week(date_str)]
            return False, f"Для данного подразделения в {day_name} максимальное количество часов: {max_hours}"

        return True, None


# ============================================================
# EmployeeHoursValidator — суммарные часы сотрудника
# ============================================================

class EmployeeHoursValidator:

    @staticmethod
    def validate_total(employee_records: List[Dict],
                       department_id: str,
                       date_str: str,
                       employee_id: str = None,
                       employee_name: str = "") -> Tuple[bool, Optional[str]]:
        if not department_id or not employee_records:
            return True, None

        if employee_id and EmployeeExemption.is_exempted(employee_id):
            return True, None

        daily_limit = WorkHoursValidator.get_max_hours(department_id, date_str)
        if daily_limit is None:
            return True, None

        main_hours = 0.0
        substitution_hours = 0.0
        combination_hours = 0.0

        for record in employee_records:
            work_type = record.get('work_type', '').lower()
            hours = float(record.get('hours', 0))

            if record.get('is_vacation') or record.get('is_sick') or record.get('is_without_pay'):
                continue

            if work_type == 'основной':
                main_hours += hours
            elif work_type == 'замещение':
                substitution_hours += hours
            elif work_type == 'совмещение':
                combination_hours += hours

        total_main_and_subst = main_hours + substitution_hours
        if total_main_and_subst > daily_limit:
            return False, (
                f"Сотрудник {employee_name}: сумма основных часов ({main_hours:.2f}) "
                f"и часов замещения ({substitution_hours:.2f}) = {total_main_and_subst:.2f} ч. "
                f"превышает дневной лимит {daily_limit:.2f} ч."
            )

        if combination_hours > daily_limit:
            return False, (
                f"Сотрудник {employee_name}: часы только по совмещению ({combination_hours:.2f} ч.) "
                f"превышают допустимый дневной лимит {daily_limit:.2f} ч."
            )

        return True, None
