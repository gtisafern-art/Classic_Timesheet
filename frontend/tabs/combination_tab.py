"""Вкладка «Совмещение / Замещение»"""

import logging
from datetime import datetime, timedelta
from typing import List

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                                QHeaderView, QLineEdit, QCheckBox, QComboBox,
                                QPushButton, QLabel, QMessageBox, QAbstractItemView)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from backend.models import Employee, TimesheetRecord, Restaurant
from backend.repositories.timesheet_repo import TimesheetRepository

logger = logging.getLogger(__name__)

COLOR_SAVED = QColor(232, 245, 233)
COLOR_CORRECTION = QColor(255, 243, 205)

FROZEN_QSS = "background-color:#F0F0F0;color:#999;border:1px solid #E5E5EA;border-radius:6px;padding:2px 4px;font-size:13px;"
EDITABLE_QSS = "background-color:#FFFFFF;color:#1D1D1F;border:1px solid #E5E5EA;border-radius:6px;padding:2px 4px;font-size:13px;"


class CombinationTab(QWidget):
    date_changed = Signal(str)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.timesheet_repo = TimesheetRepository(db)

        self._all_employees: List[Employee] = []
        self._all_positions = []
        self._restaurant: Restaurant = None
        self._all_restaurants: List[Restaurant] = []
        self._date = datetime.now().strftime("%d.%m.%Y")
        self._target_position_name = ""
        self._target_position_id = ""

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # --- Фильтры ---
        filter_row = QHBoxLayout()
        filter_row.setSpacing(16)

        filter_row.addWidget(QLabel("Дата"))
        self.date_combo = QComboBox()
        self.date_combo.setFixedWidth(130)
        self.date_combo.currentTextChanged.connect(self._on_date_changed)
        filter_row.addWidget(self.date_combo)
        filter_row.addSpacing(16)

        filter_row.addWidget(QLabel("Заведение"))
        self.restaurant_combo = QComboBox()
        self.restaurant_combo.setMinimumWidth(180)
        self.restaurant_combo.currentTextChanged.connect(self._on_restaurant_changed)
        filter_row.addWidget(self.restaurant_combo)
        filter_row.addSpacing(16)

        filter_row.addWidget(QLabel("Замещаемая должность"))
        self.position_combo = QComboBox()
        self.position_combo.setMinimumWidth(220)
        self.position_combo.currentTextChanged.connect(self._on_position_changed)
        filter_row.addWidget(self.position_combo)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        # --- Контекст ---
        self.context_label = QLabel("")
        self.context_label.setStyleSheet("color: #86868B; font-size: 11px; padding: 2px 0;")
        layout.addWidget(self.context_label)

        # --- Кнопки ---
        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Добавить")
        add_btn.clicked.connect(self._add_empty_row)
        btn_row.addWidget(add_btn)

        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self._save_all)
        btn_row.addWidget(self.save_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # --- Таблица ---
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Сотрудник", "Осн. должность", "Откуда (БЕ)",
            "Вид", "Часы", "Корр.", "Комментарий", ""
        ])
        hdr = self.table.horizontalHeader()
        hdr.setSectionsMovable(True)
        for i in range(8):
            hdr.setSectionResizeMode(i, QHeaderView.Interactive)
        self.table.resizeColumnsToContents()
        for i, min_w in enumerate([180, 120, 120, 90, 55, 45, 140, 30]):
            if self.table.columnWidth(i) < min_w:
                self.table.setColumnWidth(i, min_w)
        layout.addWidget(self.table)

        self._update_date_combo()
        self._add_empty_row()

    # ========== Публичные методы ==========

    def set_restaurants(self, restaurants: list):
        self._all_restaurants = restaurants
        self.restaurant_combo.blockSignals(True)
        self.restaurant_combo.clear()
        for r in restaurants:
            self.restaurant_combo.addItem(r.name)
        self.restaurant_combo.blockSignals(False)

    def set_context(self, restaurant=None, date="", employees=None):
        if restaurant and restaurant != self._restaurant:
            self._restaurant = restaurant
            idx = self.restaurant_combo.findText(restaurant.name)
            if idx >= 0:
                self.restaurant_combo.blockSignals(True)
                self.restaurant_combo.setCurrentIndex(idx)
                self.restaurant_combo.blockSignals(False)
        if date and date != self._date:
            self._date = date
            self._update_date_combo()
        if employees is not None:
            self._all_employees = employees
            self._refresh_all_combos()
            self._update_position_combo_for_restaurant()
        self._update_context_label()

    def set_positions(self, positions: list):
        self._all_positions = positions
        self.position_combo.blockSignals(True)
        self.position_combo.clear()
        for p in positions:
            self.position_combo.addItem(p.name)
        self.position_combo.blockSignals(False)

    def set_current_position(self, name: str):
        self._target_position_name = name
        self._target_position_id = ""
        for p in self._all_positions:
            if p.name == name:
                self._target_position_id = p.id
                break
        idx = self.position_combo.findText(name)
        if idx >= 0:
            self.position_combo.blockSignals(True)
            self.position_combo.setCurrentIndex(idx)
        self.position_combo.blockSignals(False)
        # Явно синхронизируем (сигнал был заблокирован)
        txt = self.position_combo.currentText()
        if txt:
            self._target_position_name = txt
            for p in self._all_positions:
                if p.name == txt:
                    self._target_position_id = p.id
                    break
        else:
            self._target_position_name = ""
            self._target_position_id = ""
        self._update_context_label()
        self._reload_from_db()

    # ========== Внутренние методы ==========

    def _update_date_combo(self):
        today = datetime.now()
        values = [
            today.strftime("%d.%m.%Y"),
            (today - timedelta(days=1)).strftime("%d.%m.%Y"),
            (today - timedelta(days=2)).strftime("%d.%m.%Y"),
        ]
        self.date_combo.blockSignals(True)
        self.date_combo.clear()
        self.date_combo.addItems(values)
        if self._date in values:
            self.date_combo.setCurrentText(self._date)
        else:
            self.date_combo.addItem(self._date)
            self.date_combo.setCurrentText(self._date)
        self.date_combo.blockSignals(False)

    def _on_date_changed(self, txt):
        if txt and txt != self._date:
            self._date = txt
            self.date_changed.emit(txt)
            self._reload_from_db()

    def _on_restaurant_changed(self, txt):
        if not txt:
            return
        for r in self._all_restaurants:
            if r.name == txt:
                self._restaurant = r
                break
        self._update_position_combo_for_restaurant()
        self._update_context_label()
        self._reload_from_db()

    def _update_position_combo_for_restaurant(self):
        """Фильтровать должности — только те, что есть в выбранном ресторане"""
        if not self._restaurant:
            return

        # Собираем уникальные должности сотрудников этого ресторана
        positions_in_restaurant = set()
        for e in self._all_employees:
            if e.department_id == self._restaurant.id or e.department == self._restaurant.name:
                positions_in_restaurant.add(e.position)

        # Фильтруем self._all_positions — только те, что есть в ресторане
        filtered = [p for p in self._all_positions if p.name in positions_in_restaurant]

        cur = self.position_combo.currentText()
        self.position_combo.blockSignals(True)
        self.position_combo.clear()
        for p in filtered:
            self.position_combo.addItem(p.name)
        if cur and self.position_combo.findText(cur) >= 0:
            self.position_combo.setCurrentText(cur)
        elif self._target_position_name and self.position_combo.findText(self._target_position_name) >= 0:
            self.position_combo.setCurrentText(self._target_position_name)
        elif filtered:
            self.position_combo.setCurrentIndex(0)
        else:
            self.position_combo.setCurrentIndex(-1)
            self._target_position_name = ""
            self._target_position_id = ""
        self.position_combo.blockSignals(False)

    def _refresh_all_combos(self):
        """Обновить списки сотрудников во всех комбобоксах"""
        names = [e.fio for e in self._all_employees]
        for row in range(self.table.rowCount()):
            cb = self.table.cellWidget(row, 0)
            if isinstance(cb, QComboBox):
                cur = cb.currentText()
                cb.blockSignals(True)
                cb.clear()
                cb.addItems(names)
                if cur and cur in names:
                    cb.setCurrentText(cur)
                else:
                    cb.setCurrentIndex(-1)
                cb.blockSignals(False)

    def _update_context_label(self):
        parts = []
        if self._restaurant:
            parts.append(f"Заведение: {self._restaurant.name}")
        if self._target_position_name:
            parts.append(f"Замещает: {self._target_position_name}")
        self.context_label.setText("    ".join(parts))

    def _on_position_changed(self, txt):
        if not txt:
            self._target_position_name = ""
            self._target_position_id = ""
            self._update_context_label()
            self.table.setRowCount(0)
            self._add_empty_row()
            return
        self._target_position_name = txt
        for p in self._all_positions:
            if p.name == txt:
                self._target_position_id = p.id
                break
        self._update_context_label()
        self._reload_from_db()

    def _reload_from_db(self):
        """Загрузить существующие записи из БД и заполнить таблицу"""
        self.table.setRowCount(0)

        # Определяем target_position_id — из поля или из выпадающего списка
        tid = self._target_position_id
        if not tid:
            txt = self.position_combo.currentText()
            for p in self._all_positions:
                if p.name == txt:
                    tid = p.id
                    self._target_position_id = tid
                    break

        if not self._restaurant or not tid:
            self._add_empty_row()
            return

        existing = self.timesheet_repo.load_existing_records(self._date, self._restaurant.id)
        saved_rows = []

        for emp_id, records in existing.items():
            for rec in records:
                if rec.work_type not in ('замещение', 'совмещение'):
                    continue
                if rec.target_position_id != tid:
                    continue
                saved_rows.append(rec)

        # Для каждого сотрудника — только последняя запись (max ID)
        latest_by_emp = {}
        for rec in saved_rows:
            rid = rec.id or ""
            if rec.employee_id not in latest_by_emp or rid > (latest_by_emp[rec.employee_id].id or ""):
                latest_by_emp[rec.employee_id] = rec

        for emp_id, rec in latest_by_emp.items():
            # Пропускаем записи с 0 часов, кроме корректировок (их можно редактировать)
            if rec.hours == 0 and not rec.is_correction:
                continue
            emp = self._find_employee(emp_id)
            if not emp:
                continue
            self._add_saved_row(emp, rec)

        self._add_empty_row()

    def _find_employee(self, emp_id):
        for e in self._all_employees:
            if e.id == emp_id:
                return e
        return None

    def _add_saved_row(self, emp, rec: TimesheetRecord):
        """Создать строку с сохранёнными данными"""
        row = self.table.rowCount()
        self.table.insertRow(row)

        is_corr = rec.is_correction
        hours_style = EDITABLE_QSS if is_corr else FROZEN_QSS
        comment_style = EDITABLE_QSS if is_corr else FROZEN_QSS

        # Сотрудник
        cb = self._make_employee_combo(row)
        idx = cb.findText(emp.fio)
        if idx >= 0:
            cb.blockSignals(True)
            cb.setCurrentIndex(idx)
            cb.setEnabled(not is_corr)
            cb.blockSignals(False)
        self.table.setCellWidget(row, 0, cb)

        # Осн. должность
        lb = QLabel(emp.position)
        lb.setStyleSheet("background: transparent; padding: 2px 6px; font-size: 12px; color: #1D1D1F;")
        self.table.setCellWidget(row, 1, lb)

        # Откуда
        lb2 = QLabel(emp.department or "")
        lb2.setStyleSheet("background: transparent; padding: 2px 6px; font-size: 12px; color: #1D1D1F;")
        self.table.setCellWidget(row, 2, lb2)

        # Вид
        type_cb = QComboBox()
        type_cb.addItems(["Замещение", "Совмещение"])
        type_cb.setStyleSheet("padding: 2px 6px; font-size: 12px;")
        wtype_disp = "Замещение" if rec.work_type == 'замещение' else "Совмещение"
        type_cb.setCurrentText(wtype_disp)
        self.table.setCellWidget(row, 3, type_cb)

        # Часы
        he = QLineEdit()
        he.setAlignment(Qt.AlignCenter)
        he.setMinimumHeight(28)
        he.setStyleSheet(hours_style)
        he.setText(str(rec.hours) if rec.hours and not rec.is_vacation and not rec.is_sick and not rec.is_without_pay else "")
        he.setEnabled(is_corr)
        self.table.setCellWidget(row, 4, he)

        # Корр.
        corr_cb = QCheckBox()
        corr_cb.setChecked(is_corr)
        self._set_cb(row, 5, corr_cb)

        # Комментарий
        ce = QLineEdit()
        ce.setMinimumHeight(28)
        ce.setStyleSheet(comment_style)
        ce.setText(rec.comment or "")
        ce.setEnabled(is_corr)
        self.table.setCellWidget(row, 6, ce)

        # Удалить
        del_btn = QPushButton("×")
        del_btn.setFixedSize(24, 24)
        del_btn.setProperty("class", "danger")
        del_btn.setStyleSheet("font-size: 14px; font-weight: bold; padding: 0;")
        del_btn.clicked.connect(lambda checked=False, r=row: self._delete_row(r))
        self.table.setCellWidget(row, 7, del_btn)

        # Связка: корректировка
        corr_cb.toggled.connect(lambda checked, h=he, c=ce:
            self._toggle_fields(h, c, checked))

        # Окраска строки
        bg = COLOR_CORRECTION if is_corr else COLOR_SAVED
        for ci in range(8):
            item = self.table.item(row, ci)
            if item:
                item.setBackground(bg)

    def _add_empty_row(self):
        """Пустая строка для новой записи"""
        row = self.table.rowCount()
        self.table.insertRow(row)

        cb = self._make_employee_combo(row)
        self.table.setCellWidget(row, 0, cb)

        pos_label = QLabel("")
        pos_label.setStyleSheet("background: transparent; padding: 2px 6px; font-size: 12px;")
        self.table.setCellWidget(row, 1, pos_label)

        dept_label = QLabel("")
        dept_label.setStyleSheet("background: transparent; padding: 2px 6px; font-size: 12px;")
        self.table.setCellWidget(row, 2, dept_label)

        type_cb = QComboBox()
        type_cb.addItems(["Замещение", "Совмещение"])
        type_cb.setStyleSheet("padding: 2px 6px; font-size: 12px;")
        self.table.setCellWidget(row, 3, type_cb)

        he = QLineEdit()
        he.setAlignment(Qt.AlignCenter)
        he.setMinimumHeight(28)
        he.setStyleSheet(EDITABLE_QSS)
        self.table.setCellWidget(row, 4, he)

        self._set_cb(row, 5, QCheckBox())

        ce = QLineEdit()
        ce.setMinimumHeight(28)
        ce.setStyleSheet(EDITABLE_QSS)
        self.table.setCellWidget(row, 6, ce)

        del_btn = QPushButton("×")
        del_btn.setFixedSize(24, 24)
        del_btn.setProperty("class", "danger")
        del_btn.setStyleSheet("font-size: 14px; font-weight: bold; padding: 0;")
        del_btn.clicked.connect(lambda checked=False, r=row: self._delete_row(r))
        self.table.setCellWidget(row, 7, del_btn)

    def _make_employee_combo(self, row):
        cb = QComboBox()
        cb.setMinimumWidth(270)
        cb.setStyleSheet("padding: 2px 6px; font-size: 12px;")
        cb.setProperty("_row", row)
        names = [e.fio for e in self._all_employees]
        cb.blockSignals(True)
        cb.setPlaceholderText("")
        cb.addItems(names)
        cb.setCurrentIndex(-1)
        cb.blockSignals(False)
        cb.activated.connect(self._on_emp_picked)
        return cb

    def _on_emp_picked(self, idx):
        combo = self.sender()
        if not isinstance(combo, QComboBox) or idx < 0:
            return
        name = combo.itemText(idx)
        if not name:
            return
        emp = None
        for e in self._all_employees:
            if e.fio == name:
                emp = e
                break
        if not emp:
            return
        row = combo.property("_row")
        self._fill_row_info(row, emp)

    def _fill_row_info(self, row, emp):
        pos_label = self.table.cellWidget(row, 1)
        if isinstance(pos_label, QLabel):
            pos_label.setText(emp.position)
            pos_label.setStyleSheet("background: transparent; padding: 2px 6px; font-size: 12px; color: #1D1D1F;")

        dept_label = self.table.cellWidget(row, 2)
        if isinstance(dept_label, QLabel):
            dept_label.setText(emp.department or "")
            dept_label.setStyleSheet("background: transparent; padding: 2px 6px; font-size: 12px; color: #1D1D1F;")

    def _toggle_fields(self, hours_edit, comment_edit, checked):
        if checked:
            hours_edit.setStyleSheet(EDITABLE_QSS)
            hours_edit.setEnabled(True)
            comment_edit.setStyleSheet(EDITABLE_QSS)
            comment_edit.setEnabled(True)
        else:
            hours_edit.setStyleSheet(FROZEN_QSS)
            hours_edit.setEnabled(False)
            comment_edit.setStyleSheet(FROZEN_QSS)
            comment_edit.setEnabled(False)

    def _set_cb(self, row, col, cb):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        l = QHBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setAlignment(Qt.AlignCenter)
        l.addWidget(cb)
        self.table.setCellWidget(row, col, w)

    def _delete_row(self, row):
        self.table.removeRow(row)

    def _save_all(self):
        if not self._restaurant or not self._date:
            QMessageBox.warning(self, "Предупреждение", "Сначала выберите ресторан и дату на вкладке Табель")
            return

        target_pos_name = self.position_combo.currentText()
        target_pos_id = self._target_position_id
        if not target_pos_id:
            for p in self._all_positions:
                if p.name == target_pos_name:
                    target_pos_id = p.id
                    self._target_position_id = p.id
                    break

        records = []
        for row in range(self.table.rowCount()):
            emp_w = self.table.cellWidget(row, 0)
            if not isinstance(emp_w, QComboBox) or emp_w.currentIndex() < 0:
                continue
            name = emp_w.currentText().strip()
            if not name:
                continue

            emp = None
            for e in self._all_employees:
                if e.fio == name:
                    emp = e
                    break
            if not emp:
                continue

            he = self.table.cellWidget(row, 4)
            if not isinstance(he, QLineEdit):
                continue
            hours_text = he.text().strip()
            if not hours_text:
                continue
            try:
                hours = float(hours_text.replace(',', '.'))
            except ValueError:
                continue

            type_w = self.table.cellWidget(row, 3)
            wtype_d = type_w.currentText() if isinstance(type_w, QComboBox) else "Замещение"
            wtype_db = "замещение" if wtype_d == "Замещение" else "совмещение"

            corr = self._cb_checked(row, 5)

            ce = self.table.cellWidget(row, 6)
            comment = ce.text().strip() if isinstance(ce, QLineEdit) else ""

            records.append(TimesheetRecord(
                employee_id=emp.id,
                position_id=emp.position_id,
                target_position_id=target_pos_id or emp.position_id,
                hours=hours,
                work_type=wtype_db,
                is_correction=corr,
                comment=comment,
            ))

        if not records:
            QMessageBox.information(self, "Информация", "Нет данных для сохранения")
            return

        success = 0
        for r in records:
            if self.timesheet_repo.save_record(r, self._date, self._restaurant.id, self._restaurant.prefix):
                success += 1

        QMessageBox.information(self, "Успех", f"Сохранено записей: {success}")
        self._reload_from_db()

    def _cb_checked(self, row, col):
        w = self.table.cellWidget(row, col)
        if w:
            for c in w.findChildren(QCheckBox):
                return c.isChecked()
        return False
