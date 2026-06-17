"""Вкладка «Табель» — macOS стиль"""

import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Optional

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                                QTableWidgetItem, QHeaderView, QLineEdit,
                                QCheckBox, QComboBox, QPushButton,
                                QLabel, QMessageBox, QAbstractItemView)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent
from PySide6.QtWidgets import QApplication

from backend.config import Config
from backend.models import Employee, TimesheetRecord, Restaurant, Position
from backend.repositories.employee_repo import EmployeeRepository
from backend.repositories.timesheet_repo import TimesheetRepository
from backend.validators import (EmployeeExemption, WorkHoursValidator,
                                 EmployeeHoursValidator)
from frontend.dialogs.confirmation_dialog import ConfirmationDialog

logger = logging.getLogger(__name__)

COLOR_SAVED = QColor(232, 245, 233)
COLOR_CORRECTION = QColor(255, 243, 205)
COLOR_DISMISSED = QColor(240, 240, 240)
COLOR_NORMAL = QColor(255, 255, 255)
COLOR_ERROR = QColor(255, 205, 210)

DATE_FORMAT = "dd.MM.yyyy"


def _install_copy_handler(table):
    """Ctrl+C копирует все выделенные ячейки"""
    orig = table.keyPressEvent
    def handler(event):
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_C:
            selected = table.selectedRanges()
            if selected:
                rows_set, cols_set = set(), set()
                for rng in selected:
                    for r in range(rng.topRow(), rng.bottomRow() + 1):
                        rows_set.add(r)
                    for c in range(rng.leftColumn(), rng.rightColumn() + 1):
                        cols_set.add(c)
                rows, cols = sorted(rows_set), sorted(cols_set)
                lines = []
                for r in rows:
                    cells = []
                    for c in cols:
                        item = table.item(r, c)
                        w = table.cellWidget(r, c)
                        if isinstance(w, QLineEdit):
                            cells.append(w.text())
                        else:
                            cells.append(item.text() if item else "")
                    lines.append("\t".join(cells))
                QApplication.clipboard().setText("\n".join(lines))
                return
        orig(event)
    table.keyPressEvent = handler


class TimesheetTab(QWidget):
    restaurant_changed = Signal()
    date_changed = Signal()
    position_changed = Signal(str)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.employee_repo = EmployeeRepository(db)
        self.timesheet_repo = TimesheetRepository(db)

        self.expanded_mode = False
        self.all_employees: List[Employee] = []
        self.restaurants: List[Restaurant] = []
        self.positions: List[Position] = []
        self.current_restaurant: Optional[Restaurant] = None
        self.current_position: Optional[Position] = None
        self.current_date = datetime.now().strftime("%d.%m.%Y")
        self.has_records = False
        self.show_dismissed = False

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # --- Верхняя панель ---
        top = QHBoxLayout()
        top.setSpacing(10)
        font = QFont()
        font.setPointSize(11)

        top.addWidget(QLabel("Ресторан"))
        self.restaurant_combo = QComboBox()
        self.restaurant_combo.setMinimumWidth(240)
        self.restaurant_combo.currentIndexChanged.connect(self._on_restaurant_changed)
        top.addWidget(self.restaurant_combo)

        top.addWidget(QLabel("Дата"))

        # Контейнер для даты (переключается между комбобоксом и полем ввода)
        self.date_container = QHBoxLayout()

        today = datetime.now()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)

        # Базовый режим: выпадающий список
        self.date_combo = QComboBox()
        self.date_combo.addItems([
            today.strftime("%d.%m.%Y"),
            yesterday.strftime("%d.%m.%Y"),
            two_days_ago.strftime("%d.%m.%Y"),
        ])
        self.date_combo.setFixedWidth(120)
        self.date_combo.currentTextChanged.connect(self._on_date_combo_changed)

        # Расширенный режим: свободный ввод
        self.date_edit = QLineEdit()
        self.date_edit.setPlaceholderText("ДД.ММ.ГГГГ")
        self.date_edit.setFixedWidth(110)
        self.date_edit.setText(today.strftime("%d.%m.%Y"))
        self.date_edit.editingFinished.connect(self._on_date_edit_changed)
        self.date_edit.hide()

        top.addWidget(self.date_combo)
        top.addWidget(self.date_edit)

        top.addWidget(QLabel("Должность"))
        self.position_combo = QComboBox()
        self.position_combo.setMinimumWidth(200)
        self.position_combo.currentIndexChanged.connect(self._on_position_changed)
        top.addWidget(self.position_combo)

        self.dismissed_cb = QCheckBox("Уволенные")
        self.dismissed_cb.toggled.connect(self._on_dismissed_toggled)
        top.addWidget(self.dismissed_cb)

        self.load_btn = QPushButton("Загрузить из БД")
        self.load_btn.setProperty("class", "secondary")
        self.load_btn.clicked.connect(self.load_from_db)
        top.addWidget(self.load_btn)

        self.expand_btn = QPushButton("Расширенный")
        self.expand_btn.setProperty("class", "secondary")
        self.expand_btn.clicked.connect(self._toggle_expanded)
        top.addWidget(self.expand_btn)

        top.addStretch()
        layout.addLayout(top)

        # --- Инфо ---
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("font-size: 11px; color: #86868B;")
        layout.addWidget(self.info_label)

        # --- Таблица ---
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "№", "ФИО", "Должность", "Подразделение",
            "Часы", "Отпуск", "Больн.", "Б/с", "Корр.", "Комментарий"
        ])
        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(True)
        hdr.setSectionsMovable(True)
        for i in range(10):
            hdr.setSectionResizeMode(i, QHeaderView.Interactive)
        self.table.resizeColumnsToContents()
        for i, min_w in enumerate([30, 160, 100, 120, 55, 50, 50, 50, 50]):
            if self.table.columnWidth(i) < min_w:
                self.table.setColumnWidth(i, min_w)
        layout.addWidget(self.table)
        _install_copy_handler(self.table)

        # --- Нижняя панель ---
        bottom = QHBoxLayout()
        bottom.setSpacing(8)

        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.save_all_data)
        bottom.addWidget(self.save_btn)

        summary_btn = QPushButton("Сводка")
        summary_btn.setProperty("class", "secondary")
        summary_btn.clicked.connect(self._show_summary)
        bottom.addWidget(summary_btn)

        self.turv_btn = QPushButton("ТУРВ за дату")
        self.turv_btn.setProperty("class", "secondary")
        self.turv_btn.clicked.connect(self._show_turv)
        bottom.addWidget(self.turv_btn)

        clear_btn = QPushButton("Очистить")
        clear_btn.setProperty("class", "secondary")
        clear_btn.clicked.connect(self._clear_unsaved)
        bottom.addWidget(clear_btn)

        bottom.addStretch()
        layout.addLayout(bottom)

    # ========== Публичные методы ==========

    def load_reference_data(self):
        self.restaurants = self.employee_repo.load_restaurants()
        self.positions = self.employee_repo.load_positions()
        self.all_employees = self.employee_repo.load_employees(self.current_date)
        self.has_records = self.timesheet_repo.check_fact_table_empty()

        self.restaurant_combo.blockSignals(True)
        self.restaurant_combo.clear()
        for r in self.restaurants:
            self.restaurant_combo.addItem(r.name)
        self.restaurant_combo.blockSignals(False)
        if self.restaurants:
            self.current_restaurant = self.restaurants[0]

        self.position_combo.blockSignals(True)
        self.position_combo.clear()
        for p in self.positions:
            self.position_combo.addItem(p.name)
        self.position_combo.blockSignals(False)

    def load_main_employees(self):
        if not self.current_restaurant or not self.current_position:
            return

        self.table.setRowCount(0)
        existing = self.timesheet_repo.load_existing_records(self.current_date, self.current_restaurant.id)

        employees = []
        for e in self.all_employees:
            if e.position != self.current_position.name:
                continue
            if e.department != self.current_restaurant.name:
                continue
            if not self.show_dismissed and e.is_dismissed_on_date:
                continue
            if self.show_dismissed and e.is_dismissed_on_date and not e.should_show:
                continue
            employees.append(e)
        employees.sort(key=lambda x: (x.is_dismissed_on_date, x.fio))

        active = sum(1 for e in employees if not e.is_dismissed_on_date)
        dismissed = sum(1 for e in employees if e.is_dismissed_on_date)
        recs = sum(len(v) for v in existing.values())
        info = f"Сотрудников: {active} активных"
        if dismissed:
            info += f", {dismissed} уволенных"
        info += f"  |  Записей в БД: {recs}" if recs else "  |  БД пуста"
        self.info_label.setText(info)

        for idx, emp in enumerate(employees):
            emp_recs = existing.get(emp.id, [])
            main = [r for r in emp_recs if r.work_type == 'основной']
            main.sort(key=lambda x: str(x.id or ''), reverse=True)
            latest = main[0] if main else None

            row = idx
            self.table.insertRow(row)

            # №
            self.table.setItem(row, 0, self._item(str(idx + 1)))

            # ФИО
            fio = emp.fio
            if emp.is_dismissed_on_date and emp.dismissal_date:
                fio += f"  (уволен {emp.dismissal_date})"
            item = QTableWidgetItem(fio)
            item.setForeground(QColor("#86868B") if emp.is_dismissed_on_date else QColor("#1D1D1F"))
            self.table.setItem(row, 1, item)

            # Должность / Подразделение
            self._set_item(row, 2, emp.position, emp.is_dismissed_on_date)
            self._set_item(row, 3, emp.department or "", emp.is_dismissed_on_date)

            # Часы
            he = QLineEdit()
            he.setAlignment(Qt.AlignCenter)
            he.setMinimumHeight(28)
            he.setProperty("emp_id", emp.id)
            he.setProperty("department_id", emp.department_id)
            self.table.setCellWidget(row, 4, he)

            # Статусы + Корректировка
            has_latest = latest and self.has_records
            vac_cb = self._make_cb(latest.is_vacation if has_latest else False)
            sick_cb = self._make_cb(latest.is_sick if has_latest else False)
            wo_cb = self._make_cb(latest.is_without_pay if has_latest else False)
            corr_cb = self._make_cb(latest.is_correction if has_latest else False)

            self._set_cb(row, 5, vac_cb)
            self._set_cb(row, 6, sick_cb)
            self._set_cb(row, 7, wo_cb)
            self._set_cb(row, 8, corr_cb)

            # Комментарий
            ce = QLineEdit()
            ce.setMinimumHeight(28)
            if has_latest:
                ce.setText(latest.comment or "")
            self.table.setCellWidget(row, 9, ce)

            # Начальное состояние полей: текст + стиль
            if has_latest:
                if latest.is_vacation:
                    he.setText("ОТ")
                elif latest.is_sick:
                    he.setText("Б")
                elif latest.is_without_pay:
                    he.setText("б/с")
                else:
                    he.setText(str(latest.hours) if latest.hours else "")

            if has_latest and not latest.is_correction and not emp.is_dismissed_on_date:
                self._set_frozen_style(he)
                self._set_frozen_style(ce)
            else:
                self._set_editable_style(he)
                self._set_editable_style(ce)

            # Связка: чекбоксы статусов
            for cb, code in [(vac_cb, "ОТ"), (sick_cb, "Б"), (wo_cb, "б/с")]:
                cb.toggled.connect(lambda checked, w=he, c=code, cb2=corr_cb, ce2=ce:
                    self._on_status_toggle(w, checked, c, cb2, ce2))

            # Связка: корректировка включает часы + комментарий
            corr_cb.toggled.connect(lambda checked, w=he, c=corr_cb, ce2=ce:
                self._on_correction_toggle(w, checked, c, ce2))

            # Окраска
            bg = COLOR_NORMAL
            if emp.is_dismissed_on_date:
                bg = COLOR_DISMISSED
            elif latest and latest.is_correction:
                bg = COLOR_CORRECTION
            elif latest and self.has_records:
                bg = COLOR_SAVED
            for ci in range(10):
                item = self.table.item(row, ci)
                if item:
                    item.setBackground(bg)

    def load_from_db(self):
        self.all_employees = self.employee_repo.load_employees(self.current_date)
        self.has_records = self.timesheet_repo.check_fact_table_empty()
        self.load_main_employees()

    def save_all_data(self):
        if not self.current_restaurant or not self.current_position:
            QMessageBox.warning(self, "Предупреждение", "Выберите ресторан и должность")
            return

        main_data = self._collect_main_data()
        if not main_data:
            QMessageBox.information(self, "Информация", "Нет данных для сохранения")
            return

        # Валидация (базовый режим)
        if not self.expanded_mode:
            errors = self._validate(main_data)
            if errors:
                QMessageBox.critical(self, "Ошибка валидации", "Обнаружены ошибки:\n\n" + "\n\n".join(errors))
                return

        # Подтверждение
        summary_text = self._format_summary(main_data)
        dlg = ConfirmationDialog(summary_text, self)
        dlg.setStyleSheet(self.styleSheet())
        if dlg.exec() != ConfirmationDialog.Accepted or not dlg.confirmed:
            return

        # Сохранение
        prefix = self.current_restaurant.prefix
        success = 0
        for d in main_data:
            record = TimesheetRecord(
                employee_id=d['emp_id'],
                position_id=d['position_id'],
                hours=d['hours'],
                work_type="основной",
                is_correction=d['is_correction'],
                comment=d['comment'],
                is_vacation=d['is_vacation'],
                is_sick=d['is_sick'],
                is_without_pay=d['is_without_pay'],
            )
            if self.timesheet_repo.save_record(record, self.current_date,
                                                self.current_restaurant.id, prefix):
                success += 1

        self.load_from_db()
        QMessageBox.information(self, "Успех", f"Сохранено записей: {success}")

    # ========== Внутренние методы ==========

    def _item(self, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        return item

    def _set_item(self, row, col, text, dim=False):
        item = QTableWidgetItem(text)
        if dim:
            item.setForeground(QColor("#86868B"))
        self.table.setItem(row, col, item)

    def _make_cb(self, checked=False):
        cb = QCheckBox()
        cb.setChecked(checked)
        return cb

    def _set_cb(self, row, col, cb):
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setAlignment(Qt.AlignCenter)
        l.addWidget(cb)
        self.table.setCellWidget(row, col, w)

    def _set_frozen_style(self, edit):
        edit.setEnabled(False)
        edit.setStyleSheet(
            "background-color: #F0F0F0; color: #999; border: 1px solid #E5E5EA;"
            "border-radius: 6px; padding: 2px 4px; font-size: 13px;"
        )

    def _set_editable_style(self, edit):
        edit.setEnabled(True)
        edit.setStyleSheet(
            "background-color: #FFFFFF; color: #1D1D1F; border: 1px solid #E5E5EA;"
            "border-radius: 6px; padding: 2px 4px; font-size: 13px;"
        )

    def _on_status_toggle(self, hours_edit, checked, code, corr_cb, comment_edit):
        if checked:
            hours_edit.setText(code)
            self._set_frozen_style(hours_edit)
            corr_cb.setChecked(False)
        else:
            hours_edit.clear()
            self._set_editable_style(hours_edit)
        self._mark_changed()

    def _on_correction_toggle(self, hours_edit, checked, corr_cb, comment_edit):
        if checked:
            self._set_editable_style(hours_edit)
            self._set_editable_style(comment_edit)
        else:
            self._set_frozen_style(hours_edit)
            self._set_frozen_style(comment_edit)
        self._mark_changed()

    def _mark_changed(self):
        pass

    def _collect_main_data(self):
        data = []
        for row in range(self.table.rowCount()):
            fio_item = self.table.item(row, 1)
            if not fio_item:
                continue
            fio = fio_item.text().split("  (")[0]

            he = self.table.cellWidget(row, 4)
            if not isinstance(he, QLineEdit):
                continue
            hours_text = he.text().strip()

            emp = self._find_employee(fio)
            if not emp:
                continue

            vac = self._cb_checked(row, 5)
            sick = self._cb_checked(row, 6)
            wo = self._cb_checked(row, 7)
            corr = self._cb_checked(row, 8)

            has_status = vac or sick or wo
            if not hours_text and not has_status:
                continue

            hours = 0.0
            if not has_status:
                try:
                    hours = float(hours_text.replace(',', '.'))
                except ValueError:
                    continue

            ce = self.table.cellWidget(row, 9)
            comment = ce.text().strip() if isinstance(ce, QLineEdit) else ""

            data.append({
                'emp_id': emp.id,
                'fio': fio,
                'position_id': emp.position_id,
                'hours': hours,
                'is_vacation': vac,
                'is_sick': sick,
                'is_without_pay': wo,
                'is_correction': corr,
                'comment': comment,
            })
        return data

    def _find_employee(self, fio):
        for e in self.all_employees:
            if e.fio == fio:
                return e
        return None

    def _cb_checked(self, row, col):
        w = self.table.cellWidget(row, col)
        if w:
            cbs = w.findChildren(QCheckBox)
            if cbs:
                return cbs[0].isChecked()
        return False

    def _validate(self, data):
        errors = []
        rid = self.current_restaurant.id

        all_records = defaultdict(list)
        existing = self.timesheet_repo.load_existing_records(self.current_date, rid)

        for emp_id, recs in existing.items():
            for r in recs:
                if r.work_type == 'основной' and not (r.is_vacation or r.is_sick or r.is_without_pay):
                    all_records[emp_id].append({'work_type': 'основной', 'hours': r.hours, 'is_vacation': False, 'is_sick': False, 'is_without_pay': False})

        for d in data:
            emp_id = d['emp_id']
            all_records[emp_id] = [r for r in all_records[emp_id] if r['work_type'] != 'основной']
            if not d['is_vacation'] and not d['is_sick'] and not d['is_without_pay']:
                all_records[emp_id].append({'work_type': 'основной', 'hours': d['hours'], 'is_vacation': False, 'is_sick': False, 'is_without_pay': False})

        for emp_id, recs in all_records.items():
            if not recs:
                continue
            ename = ""
            did = None
            for e in self.all_employees:
                if e.id == emp_id:
                    ename = e.fio
                    did = e.department_id
                    break
            if not did:
                did = rid

            valid, msg = EmployeeHoursValidator.validate_total(recs, did, self.current_date, emp_id, ename)
            if not valid:
                errors.append(msg)

            for d in data:
                if d['emp_id'] == emp_id and not (d['is_vacation'] or d['is_sick'] or d['is_without_pay']):
                    v, m = WorkHoursValidator.validate(d['hours'], did, self.current_date, emp_id)
                    if not v:
                        errors.append(f"Сотрудник {ename}: {m}")

        return errors

    def _format_summary(self, data):
        lines = []
        lines.append("ТАБЕЛЬ ЗА " + self.current_date)
        lines.append(f"Ресторан: {self.current_restaurant.name}")
        lines.append(f"Должность: {self.current_position.name}")
        if not self.expanded_mode:
            lines.append(f"Исключений: {EmployeeExemption.get_count()}")
        lines.append("=" * 80)
        lines.append("")
        total = 0.0
        for d in data:
            fio = d['fio']
            if d['is_vacation']:
                h = "ОТ (отпуск)"
            elif d['is_sick']:
                h = "Б (больничный)"
            elif d['is_without_pay']:
                h = "б/с"
            else:
                h = f"{d['hours']:.2f} ч"
                total += d['hours']
            corr = " [КОРР]" if d['is_correction'] else ""
            cmt = f" ({d['comment']})" if d['comment'] else ""
            lines.append(f"  {fio}: {h}{corr}{cmt}")
        lines.append("")
        lines.append(f"ВСЕГО ЧАСОВ: {total:.2f}")
        lines.append("=" * 80)
        return "\n".join(lines)

    # ========== Обработчики ==========

    def _on_restaurant_changed(self, idx):
        if idx >= 0 and self.restaurants:
            self.current_restaurant = self.restaurants[idx]
            self._update_position_combo_for_restaurant()
            self.load_main_employees()
            self.restaurant_changed.emit()

    def _update_position_combo_for_restaurant(self):
        """Показывать только должности, которые есть в выбранном ресторане"""
        if not self.current_restaurant:
            return
        positions_in_rest = set()
        for e in self.all_employees:
            if e.department_id == self.current_restaurant.id or e.department == self.current_restaurant.name:
                positions_in_rest.add(e.position)
        filtered = [p for p in self.positions if p.name in positions_in_rest]
        cur = self.position_combo.currentText()
        self.position_combo.blockSignals(True)
        self.position_combo.clear()
        for p in filtered:
            self.position_combo.addItem(p.name)
        if cur and self.position_combo.findText(cur) >= 0:
            self.position_combo.setCurrentText(cur)
        elif filtered:
            self.position_combo.setCurrentIndex(0)
        else:
            self.position_combo.setCurrentIndex(-1)
            self.current_position = None
        self.position_combo.blockSignals(False)
        # Явно синхронизируем current_position (сигнал был заблокирован)
        txt = self.position_combo.currentText()
        if txt:
            for p in self.positions:
                if p.name == txt:
                    self.current_position = p
                    break
        else:
            self.current_position = None

    def _on_position_changed(self, idx):
        txt = self.position_combo.currentText()
        if not txt:
            self.current_position = None
            self.table.setRowCount(0)
            return
        for p in self.positions:
            if p.name == txt:
                self.current_position = p
                break
        else:
            self.current_position = None
            self.table.setRowCount(0)
            return
        self.load_main_employees()
        self.position_changed.emit(self.current_position.name)

    def _on_date_combo_changed(self, txt):
        if txt:
            self._apply_date(txt)

    def _on_date_edit_changed(self):
        txt = self.date_edit.text().strip()
        try:
            dt = datetime.strptime(txt, "%d.%m.%Y")
            txt = dt.strftime("%d.%m.%Y")
            self.date_edit.setText(txt)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Неверный формат даты. Используйте ДД.ММ.ГГГГ")
            self.date_edit.setText(self.current_date)
            return
        self._apply_date(txt)

    def _apply_date(self, txt):
        if txt == self.current_date:
            return
        self.current_date = txt
        self.load_from_db()
        self.date_changed.emit()

    def _on_dismissed_toggled(self, checked):
        self.show_dismissed = checked
        self.load_main_employees()

    def _toggle_expanded(self):
        from frontend.dialogs.password_dialog import PasswordDialog
        if self.expanded_mode:
            self.expanded_mode = False
            self.date_edit.hide()
            self.date_combo.show()
            self.expand_btn.setText("Расширенный")
            self.expand_btn.setProperty("class", "secondary")
            self.expand_btn.setStyleSheet("")
            self._set_status_expanded(False)
        else:
            dlg = PasswordDialog(self)
            dlg.setStyleSheet(self.styleSheet())
            if dlg.exec() != PasswordDialog.Accepted or not dlg.password:
                return
            if dlg.password != Config.APP_PASSWORD:
                QMessageBox.critical(self, "Ошибка", "Неверный пароль!")
                return
            self.expanded_mode = True
            self.date_combo.hide()
            self.date_edit.setText(self.current_date)
            self.date_edit.show()
            self.expand_btn.setText("Базовый")
            self.expand_btn.setProperty("class", "")
            self.expand_btn.setStyleSheet(
                "background-color: #DF8C2E; color: #fff;"
                "border: none; border-radius: 8px; padding: 7px 18px;"
                "font-size: 12px; font-weight: 500;"
            )
            self._set_status_expanded(True)

    def _set_status_expanded(self, active: bool):
        sb = self.window().statusBar() if self.window() else None
        if sb:
            if active:
                sb.setStyleSheet("background-color: #DF8C2E; color: #fff;")
                sb.showMessage("Расширенный режим активен — ограничения сняты")
            else:
                sb.setStyleSheet("")
                sb.showMessage("")

    def _show_summary(self):
        data = self._collect_main_data()
        if not data:
            QMessageBox.information(self, "Сводка", "Нет данных")
            return
        text = self._format_summary(data)
        dlg = ConfirmationDialog(text, self)
        dlg.setWindowTitle("Сводка")
        dlg.setStyleSheet(self.styleSheet())
        dlg.exec()

    def _show_turv(self):
        if not self.current_restaurant:
            return
        existing = self.timesheet_repo.load_existing_records(self.current_date, self.current_restaurant.id)
        if not existing:
            QMessageBox.information(self, "ТУРВ", f"Нет данных за {self.current_date}")
            return

        lines = [f"ТУРВ — {self.current_restaurant.name} — {self.current_date}", "=" * 60]
        total = 0.0
        for emp_id, recs in existing.items():
            for r in recs:
                ename = ""
                for e in self.all_employees:
                    if e.id == emp_id:
                        ename = e.fio
                        break
                if r.is_vacation:
                    h = "ОТ"
                elif r.is_sick:
                    h = "Б"
                elif r.is_without_pay:
                    h = "б/с"
                else:
                    h = f"{r.hours:.1f}"
                    total += r.hours
                lines.append(f"  {ename}  |  {r.work_type}  |  {h}")
        lines.append(f"\nВСЕГО ЧАСОВ: {total:.1f}")
        QMessageBox.information(self, "ТУРВ", "\n".join(lines))

    def _clear_unsaved(self):
        if QMessageBox.question(self, "Очистка", "Сбросить все несохранённые изменения?") == QMessageBox.Yes:
            self.load_main_employees()
