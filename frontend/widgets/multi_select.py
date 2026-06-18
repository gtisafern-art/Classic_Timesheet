"""Выпадающий список с множественным выбором + поиск"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, QPushButton,
                                QListWidget, QListWidgetItem, QHBoxLayout,
                                QLabel, QFrame)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QFont


class MultiSelectWidget(QFrame):
    selection_changed = Signal()

    def __init__(self, parent=None, title="Выберите должности"):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setMaximumHeight(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QHBoxLayout()
        lbl = QLabel(title)
        lbl.setFont(QFont("", 10, QFont.Bold))
        header.addWidget(lbl)
        header.addStretch()

        select_all_btn = QPushButton("Все")
        select_all_btn.setProperty("class", "secondary")
        select_all_btn.setFixedWidth(60)
        select_all_btn.clicked.connect(self._select_all)
        header.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("Снять")
        deselect_all_btn.setProperty("class", "secondary")
        deselect_all_btn.setFixedWidth(60)
        deselect_all_btn.clicked.connect(self._deselect_all)
        header.addWidget(deselect_all_btn)

        layout.addLayout(header)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск...")
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)

        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.NoSelection)
        self.list.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.list)

        self._all_values = []
        self._checked = set()
        self._id_map = {}

    def set_items(self, items: dict):
        """items: {id: name}"""
        self._id_map = items
        self._all_values = list(items.values())
        self._rebuild()

    def select_all(self):
        self._checked = set(self._all_values)
        self._rebuild()

    def get_selected_ids(self) -> list:
        ids = []
        for name in self._checked:
            for pid, pname in self._id_map.items():
                if pname == name:
                    ids.append(pid)
                    break
        return ids

    def _on_item_changed(self, item):
        if item.checkState() == Qt.Checked:
            self._checked.add(item.text())
        else:
            self._checked.discard(item.text())
        self.selection_changed.emit()

    def _rebuild(self):
        self.list.blockSignals(True)
        self.list.clear()
        filter_text = self.search.text().lower()
        for value in self._all_values:
            if filter_text and filter_text not in value.lower():
                continue
            item = QListWidgetItem(value)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if value in self._checked else Qt.Unchecked)
            self.list.addItem(item)
        self.list.blockSignals(False)

    def _filter(self, text: str):
        self._rebuild()

    def _select_all(self):
        self.list.blockSignals(True)
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setCheckState(Qt.Checked)
            self._checked.add(item.text())
        self.list.blockSignals(False)
        self.selection_changed.emit()

    def _deselect_all(self):
        self.list.blockSignals(True)
        self._checked.clear()
        for i in range(self.list.count()):
            self.list.item(i).setCheckState(Qt.Unchecked)
        self.list.blockSignals(False)
        self.selection_changed.emit()
