"""Репозиторий: CRUD табеля"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from backend.db import MSSQLClient
from backend.models import TimesheetRecord

logger = logging.getLogger(__name__)


class TimesheetRepository:

    def __init__(self, db: MSSQLClient):
        self.db = db

    def check_fact_table_empty(self) -> bool:
        try:
            query = "SELECT COUNT(*) as record_count FROM [dbo].[ТабельОрганизаций]"
            result = self.db.execute_query(query)
            if result and result[0]['record_count'] is not None:
                count = result[0]['record_count']
                logger.info("Таблица фактов содержит %d записей", count)
                return count > 0
            return False
        except Exception as e:
            logger.error("Ошибка при проверке таблицы фактов: %s", e)
            return False

    def get_next_id(self, prefix: str) -> str:
        try:
            query = """
            SELECT [id] FROM [dbo].[ТабельОрганизаций]
            WHERE [id] LIKE ? + '%'
            """
            result = self.db.execute_query(query, (prefix,))
            max_number = 0
            if result:
                for row in result:
                    id_str = row['id']
                    if isinstance(id_str, str) and id_str.startswith(prefix):
                        try:
                            num_part = id_str[len(prefix):]
                            if num_part.isdigit():
                                max_number = max(max_number, int(num_part))
                        except Exception:
                            pass
            new_number = max_number + 1
            new_id = f"{prefix}{new_number:09d}"
            logger.info("Сгенерирован ID %s (префикс %s, номер %d)", new_id, prefix, new_number)
            return new_id
        except Exception as e:
            logger.error("Ошибка при генерации ID: %s", e)
            return f"tmp{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def load_existing_records(self, date_str: str, restaurant_id: str) -> Dict[str, List[TimesheetRecord]]:
        try:
            date_obj = datetime.strptime(date_str, "%d.%m.%Y")
            sql_date = date_obj.strftime("%Y-%m-%d")

            query = """
            SELECT 
                [id],
                [employee_id],
                [position_id],
                [target_position_id],
                [hours],
                [work_type],
                [is_correction],
                [comment],
                [is_vacation],
                [is_sick],
                [is_without_pay]
            FROM [dbo].[ТабельОрганизаций]
            WHERE [date] = CONVERT(date, ?)
                AND [restaurant_id] = ?
            ORDER BY [id]
            """
            result = self.db.execute_query(query, (sql_date, restaurant_id)) or []
            records: Dict[str, List[TimesheetRecord]] = {}

            for row in result:
                emp_id = row['employee_id']
                if emp_id not in records:
                    records[emp_id] = []
                records[emp_id].append(TimesheetRecord(
                    id=row['id'],
                    employee_id=row['employee_id'],
                    position_id=row['position_id'],
                    target_position_id=row['target_position_id'],
                    hours=float(row['hours']) if row['hours'] else 0,
                    work_type=row['work_type'] or 'основной',
                    is_correction=bool(row['is_correction']),
                    comment=row['comment'] or '',
                    is_vacation=bool(row['is_vacation']),
                    is_sick=bool(row['is_sick']),
                    is_without_pay=bool(row['is_without_pay']),
                    has_record=True,
                ))

            logger.info("Загружено %d записей для ресторана %s на %s", len(result), restaurant_id, date_str)
            return records
        except Exception as e:
            logger.error("Ошибка при загрузке существующих записей: %s", e)
            return {}

    def save_record(self, record: TimesheetRecord, date_str: str, restaurant_id: str,
                    prefix: str) -> Optional[str]:
        try:
            date_obj = datetime.strptime(date_str, "%d.%m.%Y")
            sql_date = date_obj.strftime("%Y-%m-%d")

            new_id = self.get_next_id(prefix)

            insert_query = """
            INSERT INTO [dbo].[ТабельОрганизаций]
                ([id], [date], [restaurant_id], [employee_id], [position_id], [target_position_id], 
                 [hours], [work_type], [is_correction], [comment], [created_at],
                 [is_vacation], [is_sick], [is_without_pay])
            VALUES
                (?, CONVERT(date, ?), ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?, ?, ?)
            """
            params = (
                str(new_id), str(sql_date), str(restaurant_id),
                str(record.employee_id),
                str(record.position_id) if record.position_id else None,
                str(record.target_position_id) if record.target_position_id else None,
                float(record.hours) if record.hours else 0,
                str(record.work_type),
                1 if record.is_correction else 0,
                str(record.comment) if record.comment else None,
                1 if record.is_vacation else 0,
                1 if record.is_sick else 0,
                1 if record.is_without_pay else 0,
            )

            success = self.db.execute_non_query(insert_query, params)
            if success:
                logger.info("Сохранена запись ID %s: сотрудник %s, часы %s, тип %s",
                            new_id, record.employee_id, record.hours, record.work_type)
                return new_id
            return None
        except Exception as e:
            logger.error("Ошибка при сохранении в таблицу фактов: %s", e)
            import traceback
            traceback.print_exc()
            return None
