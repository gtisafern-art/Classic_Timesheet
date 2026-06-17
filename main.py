"""Точка входа"""

import sys
import logging

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from backend.db import MSSQLClient
from frontend.main_window import MainWindow
from frontend.styles.theme import apply_theme
from utils.resource import resource_path


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('timesheet_app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    logger.info("Запуск")

    app = QApplication(sys.argv)
    app.setApplicationName("Табель")
    app.setWindowIcon(QIcon(resource_path("лого.ico")))

    db = MSSQLClient()
    if not db.connect():
        logger.error("Нет подключения к БД")
        return 1

    window = MainWindow(db)
    window.load_reference_data()
    window.show()

    apply_theme(app)

    result = app.exec()
    db.disconnect()
    return result


if __name__ == "__main__":
    sys.exit(main())
