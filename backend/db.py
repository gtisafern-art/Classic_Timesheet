"""Клиент для работы с MSSQL"""

import logging
from decimal import Decimal
from typing import Optional, List, Dict, Any

import pyodbc

from backend.config import Config

logger = logging.getLogger(__name__)


class MSSQLClient:
    def __init__(self):
        self.server = Config.MSSQL_SERVER
        self.database = Config.MSSQL_DATABASE
        self.username = Config.MSSQL_USER
        self.password = Config.MSSQL_PASSWORD
        self.use_windows_auth = Config.USE_WINDOWS_AUTH
        self.connection = None
        self.connected_with_windows = False

    def connect(self) -> bool:
        if self.use_windows_auth:
            return self._connect_with_windows_auth()
        return self._connect_with_sql_auth()

    def _connect_with_sql_auth(self) -> bool:
        connection_strings = [
            f"DRIVER={{SQL Server}};SERVER={self.server};DATABASE={self.database};UID={self.username};PWD={self.password};",
            f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={self.server};DATABASE={self.database};UID={self.username};PWD={self.password};",
            f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={self.server};DATABASE={self.database};UID={self.username};PWD={self.password};Encrypt=no;TrustServerCertificate=yes;",
            f"DRIVER={{ODBC Driver 13 for SQL Server}};SERVER={self.server};DATABASE={self.database};UID={self.username};PWD={self.password};",
            f"DRIVER={{SQL Server Native Client 11.0}};SERVER={self.server};DATABASE={self.database};UID={self.username};PWD={self.password};",
        ]
        logger.info("Подключение к MSSQL с SQL аутентификацией: %s@%s", self.username, self.server)
        for i, conn_str in enumerate(connection_strings, 1):
            try:
                self.connection = pyodbc.connect(conn_str, timeout=10, autocommit=False)
                cursor = self.connection.cursor()
                cursor.execute("SELECT @@SERVERNAME, DB_NAME(), USER_NAME()")
                server, db, user = cursor.fetchone()
                cursor.close()
                logger.info("Успешное подключение (SQL Auth) с вариантом %d: сервер=%s, БД=%s, пользователь=%s", i, server, db, user)
                self.connected_with_windows = False
                return True
            except Exception as e:
                logger.warning("Вариант %d не сработал: %s", i, e)
        logger.error("Не удалось подключиться с SQL аутентификацией")
        return False

    def _connect_with_windows_auth(self) -> bool:
        connection_strings = [
            f"DRIVER={{SQL Server}};SERVER={self.server};DATABASE={self.database};Trusted_Connection=yes;",
            f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={self.server};DATABASE={self.database};Trusted_Connection=yes;",
            f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={self.server};DATABASE={self.database};Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes;",
            f"DRIVER={{SQL Server Native Client 11.0}};SERVER={self.server};DATABASE={self.database};Trusted_Connection=yes;",
        ]
        logger.info("Подключение к MSSQL с Windows аутентификацией: %s", self.server)
        for i, conn_str in enumerate(connection_strings, 1):
            try:
                self.connection = pyodbc.connect(conn_str, timeout=10, autocommit=False)
                cursor = self.connection.cursor()
                cursor.execute("SELECT @@SERVERNAME, DB_NAME(), SYSTEM_USER")
                server, db, user = cursor.fetchone()
                cursor.close()
                logger.info("Успешное подключение (Windows Auth) с вариантом %d", i)
                self.connected_with_windows = True
                return True
            except Exception as e:
                logger.warning("Вариант %d не сработал: %s", i, e)
        logger.error("Не удалось подключиться с Windows аутентификацией")
        return False

    def disconnect(self):
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None
            logger.info("Соединение с MSSQL закрыто")

    def execute_query(self, query: str, params: tuple = None) -> Optional[List[Dict[str, Any]]]:
        if not self.connection:
            logger.error("Нет подключения к БД")
            return None
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            if cursor.description is None:
                cursor.close()
                return []
            columns = [column[0] for column in cursor.description]
            result = []
            for row in cursor.fetchall():
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    if isinstance(value, Decimal):
                        if value % 1 == 0:
                            value = int(value)
                        else:
                            value = float(value)
                    row_dict[col] = value
                result.append(row_dict)
            cursor.close()
            return result
        except Exception as e:
            logger.error("Ошибка выполнения запроса: %s", e)
            return None

    def execute_non_query(self, query: str, params: tuple = None) -> bool:
        if not self.connection:
            logger.error("Нет подключения к БД")
            return False
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error("Ошибка выполнения запроса: %s", e)
            try:
                self.connection.rollback()
            except Exception:
                pass
            return False
