"""Репозиторий: данные для отчёта Т-12"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

from backend.db import MSSQLClient
from backend.models import T12Record, T12GroupedRow
from utils.format import format_hours, is_hours_code

logger = logging.getLogger(__name__)


class T12Repository:

    def __init__(self, db: MSSQLClient):
        self.db = db

    def load_data(self, restaurant_id: str, start_date: date, end_date: date,
                  position_filters: List[str] = None) -> List[T12Record]:
        sql_start = start_date.strftime("%Y-%m-%d")
        sql_end = end_date.strftime("%Y-%m-%d")

        query = """
        WITH RankedRecords AS (
            SELECT 
                т.[date],
                т.[employee_id],
                т.[position_id],
                т.[target_position_id],
                т.[work_type],
                т.[hours],
                т.[is_vacation],
                т.[is_sick],
                т.[is_without_pay],
                т.[is_correction],
                т.[created_at],
                т.[id],
                т.[restaurant_id],
                ROW_NUMBER() OVER (
                    PARTITION BY 
                        т.[employee_id],
                        т.[date],
                        ISNULL(т.[work_type], 'Основной'),
                        CASE 
                            WHEN LOWER(т.[work_type]) IN ('замещение', 'совмещение') THEN т.[target_position_id]
                            ELSE т.[position_id]
                        END
                    ORDER BY 
                        т.[created_at] DESC,
                        т.[is_correction] DESC,
                        т.[id] DESC
                ) as rn
            FROM [dbo].[ТабельОрганизаций] т
            WHERE т.[date] BETWEEN CONVERT(date, ?) AND CONVERT(date, ?)
                AND т.[restaurant_id] = ?
        )
        SELECT 
            р.[date],
            р.[employee_id],
            ISNULL(с.[Наименование], 'Неизвестно') as employee_name,
            р.[position_id],
            ISNULL(п.[Наименование], 'Неизвестно') as position_name,
            р.[target_position_id],
            ISNULL(теп.[Наименование], '') as target_position_name,
            р.[work_type],
            р.[hours],
            р.[is_vacation],
            р.[is_sick],
            р.[is_without_pay],
            р.[is_correction],
            р.[created_at],
            ISNULL(подр.[Наименование], '') as employee_department
        FROM RankedRecords р
        LEFT JOIN [dbo].[СотрудникиОрганизаций_Перевод] с 
            ON р.[employee_id] = с.[Ссылка]
        LEFT JOIN [dbo].[ДолжностиОрганизаций] п 
            ON р.[position_id] = п.[Ссылка]
        LEFT JOIN [dbo].[ДолжностиОрганизаций] теп 
            ON р.[target_position_id] = теп.[Ссылка]
        LEFT JOIN [dbo].[ПодразделенияОрганизаций] подр
            ON с.[ТекущееПодразделениеОрганизации] = подр.[Ссылка]
        WHERE р.rn = 1
        """

        params: list = [sql_start, sql_end, restaurant_id]

        if position_filters:
            placeholders = ','.join(['?'] * len(position_filters))
            filter_condition = f"""
                AND (
                    р.[position_id] IN ({placeholders})
                    OR 
                    р.[target_position_id] IN ({placeholders})
                )
            """
            query += filter_condition
            params.extend(position_filters)
            params.extend(position_filters)

        query += " ORDER BY р.[date], с.[Наименование]"

        result = self.db.execute_query(query, tuple(params)) or []
        records = []

        for row in result:
            work_type_raw = row['work_type'] or 'Основной'
            if work_type_raw.lower() in ('замещение', 'совмещение'):
                target_position = row['target_position_name'] or ''
                work_type_display = 'Замещение' if work_type_raw.lower() == 'замещение' else 'Совмещение'
            else:
                target_position = ''
                work_type_display = 'Основной'

            hours_value = float(row['hours']) if row['hours'] is not None else 0.0

            if row['is_vacation']:
                code = 'ОТ'
            elif row['is_sick']:
                code = 'Б'
            elif row['is_without_pay']:
                code = 'бс'
            elif hours_value > 0:
                code = format_hours(hours_value)
            else:
                code = ''

            records.append(T12Record(
                date=row['date'],
                employee_id=row['employee_id'],
                employee_name=row['employee_name'],
                position_id=row['position_id'],
                position_name=row['position_name'],
                target_position_id=row['target_position_id'],
                target_position_name=target_position,
                work_type=work_type_display,
                code=code,
                hours=hours_value,
                is_correction=bool(row['is_correction']),
                created_at=row['created_at'],
                employee_department=row['employee_department'] or '',
            ))

        logger.info("Т-12: загружено %d записей", len(records))
        return records

    @staticmethod
    def group_data(records: List[T12Record], start_date: date) -> List[T12GroupedRow]:
        """Группировка записей Т-12 по сотрудникам"""
        grouped: Dict[tuple, T12GroupedRow] = {}

        for rec in records:
            if rec.work_type in ('Замещение', 'Совмещение'):
                pos_key = rec.target_position_id or rec.position_id
            else:
                pos_key = rec.position_id

            key = (rec.employee_id, rec.work_type, pos_key)

            day_date = rec.date
            if isinstance(day_date, datetime):
                day_date = day_date.date()
            elif isinstance(day_date, str):
                day_date = datetime.strptime(day_date[:10], "%Y-%m-%d").date()
            if not isinstance(day_date, date):
                day_date = start_date

            is_hours = is_hours_code(rec.code)

            if key not in grouped:
                grouped[key] = T12GroupedRow(
                    employee_id=rec.employee_id,
                    employee_name=rec.employee_name,
                    main_position=rec.position_name,
                    work_type=rec.work_type,
                    employee_department=rec.employee_department,
                    days={day_date: {'code': rec.code, 'hours': rec.hours}},
                    total_days=1 if is_hours else 0,
                    total_hours=rec.hours if is_hours else 0,
                    vacation_days=1 if rec.code == 'ОТ' else 0,
                    sick_days=1 if rec.code == 'Б' else 0,
                    without_pay_days=1 if rec.code == 'бс' else 0,
                )
                grouped[key].target_position = rec.target_position_name if rec.work_type in ('Замещение', 'Совмещение') else ''
            else:
                grp = grouped[key]
                if rec.target_position_name and rec.work_type in ('Замещение', 'Совмещение'):
                    grp.target_position = rec.target_position_name

                if day_date in grp.days:
                    existing_code = grp.days[day_date]['code']
                    if rec.is_correction or (is_hours and not existing_code):
                        grp.days[day_date] = {'code': rec.code, 'hours': rec.hours}
                else:
                    grp.days[day_date] = {'code': rec.code, 'hours': rec.hours}

                if is_hours:
                    grp.total_days += 1
                    grp.total_hours += rec.hours
                elif rec.code == 'ОТ':
                    grp.vacation_days += 1
                elif rec.code == 'Б':
                    grp.sick_days += 1
                elif rec.code == 'бс':
                    grp.without_pay_days += 1

        result = list(grouped.values())
        work_type_order = {'Основной': 0, 'Замещение': 1, 'Совмещение': 2}
        result.sort(key=lambda x: (x.employee_name, work_type_order.get(x.work_type, 3), x.target_position))
        return result
