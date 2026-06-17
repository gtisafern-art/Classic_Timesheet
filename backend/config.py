"""Конфигурация подключения к БД"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    MSSQL_SERVER = os.getenv("MSSQL_SERVER", "localhost")
    MSSQL_DATABASE = os.getenv("MSSQL_DATABASE", "TimesheetDB")
    MSSQL_USER = os.getenv("MSSQL_USER", "")
    MSSQL_PASSWORD = os.getenv("MSSQL_PASSWORD", "")
    USE_WINDOWS_AUTH = os.getenv("USE_WINDOWS_AUTH", "True").lower() == "true"
    APP_PASSWORD = os.getenv("APP_PASSWORD", "")
