"""Конфигурация подключения к БД"""

import sys
import os
from dotenv import load_dotenv

if getattr(sys, 'frozen', False):
    _exe_dir = os.path.dirname(sys.executable)
    if not load_dotenv(os.path.join(_exe_dir, '.env')):
        load_dotenv(os.path.join(sys._MEIPASS, '.env'))
else:
    load_dotenv()


class Config:
    MSSQL_SERVER = os.getenv("MSSQL_SERVER", "localhost")
    MSSQL_DATABASE = os.getenv("MSSQL_DATABASE", "TimesheetDB")
    MSSQL_USER = os.getenv("MSSQL_USER", "")
    MSSQL_PASSWORD = os.getenv("MSSQL_PASSWORD", "")
    USE_WINDOWS_AUTH = os.getenv("USE_WINDOWS_AUTH", "True").lower() == "true"
    APP_PASSWORD = os.getenv("APP_PASSWORD", "")
