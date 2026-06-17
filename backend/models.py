"""Модели данных — dataclass вместо словарей"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Restaurant:
    id: str
    name: str
    prefix: str = ""


@dataclass
class Position:
    id: str
    name: str


@dataclass
class Employee:
    id: str
    fio: str
    position: str
    position_id: str
    department: str
    department_id: str
    hire_date: Optional[str] = None
    dismissal_date: Optional[str] = None
    is_dismissed_on_date: bool = False
    should_show: bool = True


@dataclass
class TimesheetRecord:
    id: Optional[str] = None
    date: Optional[str] = None
    employee_id: str = ""
    restaurant_id: str = ""
    position_id: str = ""
    target_position_id: Optional[str] = None
    hours: float = 0.0
    work_type: str = "основной"
    is_correction: bool = False
    comment: str = ""
    is_vacation: bool = False
    is_sick: bool = False
    is_without_pay: bool = False
    has_record: bool = False
    employee_name: str = ""
    position_name: str = ""
    target_position_name: str = ""
    created_at: Optional[datetime] = None


@dataclass
class T12Record:
    date: Optional[datetime] = None
    employee_id: str = ""
    employee_name: str = ""
    position_id: str = ""
    position_name: str = ""
    target_position_id: str = ""
    target_position_name: str = ""
    work_type: str = "Основной"
    code: str = ""
    hours: float = 0.0
    is_correction: bool = False
    created_at: Optional[datetime] = None
    employee_department: str = ""


@dataclass
class T12GroupedRow:
    employee_id: str = ""
    employee_name: str = ""
    main_position: str = ""
    target_position: str = ""
    work_type: str = ""
    employee_department: str = ""
    days: dict = field(default_factory=dict)
    total_days: int = 0
    total_hours: float = 0.0
    vacation_days: int = 0
    sick_days: int = 0
    without_pay_days: int = 0
