"""Главное окно — macOS стиль"""

from PySide6.QtWidgets import QMainWindow, QTabWidget, QStatusBar, QLabel, QWidget, QHBoxLayout
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

from backend.db import MSSQLClient
from frontend.tabs.timesheet_tab import TimesheetTab
from frontend.tabs.combination_tab import CombinationTab
from frontend.tabs.t12_tab import T12Tab
from frontend.widgets.loading_overlay import LoadingOverlay
from frontend.styles.theme import apply_theme


class MainWindow(QMainWindow):
    def __init__(self, db: MSSQLClient):
        super().__init__()
        self.db = db
        self.setWindowTitle("Табель v2.1")
        self.resize(1400, 880)

        self._create_tabs()
        self._create_statusbar()

    def _create_tabs(self):
        self.tabs = QTabWidget()

        self.timesheet_tab = TimesheetTab(self.db)
        self.combination_tab = CombinationTab(self.db)
        self.t12_tab = T12Tab(self.db)
        self.overlay = LoadingOverlay()
        self.t12_tab.overlay = self.overlay

        # Синхронизация: при смене ресторана/даты на табеле — обновляем вкладку совмещения
        self.timesheet_tab.restaurant_changed.connect(self._on_restaurant_date_changed)
        self.timesheet_tab.date_changed.connect(self._on_restaurant_date_changed)
        self.timesheet_tab.position_changed.connect(self._on_position_changed)
        self.combination_tab.date_changed.connect(self.timesheet_tab._apply_date)

        self.tabs.addTab(self.timesheet_tab, "Табель")
        self.tabs.addTab(self.combination_tab, "Совмещение / Замещение")
        self.tabs.addTab(self.t12_tab, "Отчёт Т-12")

        self.setCentralWidget(self.tabs)

    def _on_restaurant_date_changed(self):
        r = self.timesheet_tab.current_restaurant
        d = self.timesheet_tab.current_date
        employees = self.timesheet_tab.all_employees
        self.combination_tab.set_context(restaurant=r, date=d, employees=employees)

    def _on_position_changed(self, name):
        self.combination_tab.set_current_position(name)

    def _create_statusbar(self):
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.status_label = QLabel("БД подключена")
        self.status_label.setStyleSheet("color: #34C759; font-size: 11px;")
        self.statusbar.addPermanentWidget(self.status_label)

    def load_reference_data(self):
        self.timesheet_tab.load_reference_data()
        self.combination_tab.set_positions(self.timesheet_tab.positions)
        self.combination_tab.set_restaurants(self.timesheet_tab.restaurants)

        self.t12_tab.set_restaurants(self.timesheet_tab.restaurants)
        self.t12_tab.set_positions(self.timesheet_tab.positions)

    def closeEvent(self, event):
        self.db.disconnect()
        event.accept()
