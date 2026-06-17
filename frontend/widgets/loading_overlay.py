"""Оверлей загрузки с анимацией — позиционируется на главное окно"""

import os

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QMovie

from utils.resource import resource_path


class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._movie = None
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 120);")
        self.hide()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.movie_label = QLabel()
        self.movie_label.setAlignment(Qt.AlignCenter)
        self.movie_label.setStyleSheet("background: transparent;")
        layout.addWidget(self.movie_label)

        self.text_label = QLabel("Загрузка данных...")
        self.text_label.setStyleSheet(
            "font-size: 14px; font-weight: 500; color: #FFFFFF; background: transparent;"
        )
        self.text_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.text_label)

        self._init_gif()

    def _init_gif(self):
        paths = [
            os.path.join(os.getcwd(), "loading.gif"),
            os.path.join(os.path.dirname(__file__), "..", "..", "loading.gif"),
            resource_path("loading.gif"),
        ]
        for p in paths:
            if os.path.exists(p):
                self._movie = QMovie(p)
                if self._movie.isValid():
                    self.movie_label.setMovie(self._movie)
                    return

    def show_overlay(self, parent_widget=None):
        """Показать оверлей поверх переданного виджета или всего окна"""
        if parent_widget:
            win = parent_widget.window()
        else:
            win = QApplication.activeWindow()
        if win:
            self.setParent(win)
            self.setGeometry(win.rect())
        self.show()
        self.raise_()
        if self._movie and self._movie.isValid():
            self._movie.start()

    def hide_overlay(self):
        self.hide()
        if self._movie:
            self._movie.stop()
