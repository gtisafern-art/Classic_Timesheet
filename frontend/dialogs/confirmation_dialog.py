"""QDialog подтверждения перед сохранением"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                QTextEdit, QPushButton)
from PySide6.QtCore import Qt


class ConfirmationDialog(QDialog):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Подтверждение данных")
        self.resize(800, 600)
        self.confirmed = False

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Проверьте данные перед сохранением в БД")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlainText(text)
        layout.addWidget(self.text_edit)

        btn_layout = QHBoxLayout()
        confirm_btn = QPushButton("Подтвердить и сохранить в БД")
        confirm_btn.clicked.connect(self._on_confirm)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.clicked.connect(self.reject)

        hint = QLabel("Будут сохранены только новые и измененные записи")
        hint.setStyleSheet("color: #a6adc8; font-size: 11px;")

        btn_layout.addWidget(confirm_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(hint)
        layout.addLayout(btn_layout)

    def _on_confirm(self):
        self.confirmed = True
        self.accept()
