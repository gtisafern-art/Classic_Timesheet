"""QDialog для ввода пароля"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit,
                                QPushButton, QHBoxLayout)
from PySide6.QtCore import Qt


class PasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Проверка доступа")
        self.setFixedSize(360, 200)
        self.password = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Введите пароль для расширенного режима")
        title.setStyleSheet("font-size: 13px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("или закройте окно для базового режима")
        subtitle.setStyleSheet("font-size: 11px; color: #a6adc8;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        self.entry = QLineEdit()
        self.entry.setEchoMode(QLineEdit.Password)
        self.entry.setPlaceholderText("Введите пароль...")
        self.entry.returnPressed.connect(self._on_ok)
        layout.addWidget(self.entry)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._on_ok)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.entry.setFocus()

    def _on_ok(self):
        self.password = self.entry.text()
        self.accept()
