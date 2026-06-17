"""macOS-стиль — светлая тема"""

MAC_QSS = """
/* ===== Global ===== */
* {
    font-family: -apple-system, "Segoe UI", "SF Pro Text", sans-serif;
}

/* ===== Main Window ===== */
QMainWindow {
    background-color: #F5F5F7;
}

/* ===== Tab Widget — macOS segmented control ===== */
QTabWidget::pane {
    border: none;
    background-color: #F5F5F7;
}
QTabBar::tab {
    background-color: transparent;
    color: #86868B;
    padding: 6px 20px;
    margin-right: 0;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 13px;
    font-weight: 500;
}
QTabBar::tab:selected {
    color: #1D1D1F;
    border-bottom: 2px solid #7B8CDE;
}
QTabBar::tab:hover:!selected {
    color: #1D1D1F;
}

/* ===== Table ===== */
QTableWidget {
    background-color: #FFFFFF;
    alternate-background-color: #FAFAFA;
    color: #1D1D1F;
    border: 1px solid #E5E5EA;
    border-radius: 10px;
    gridline-color: #F0F0F0;
    font-size: 12px;
}
QTableWidget::item {
    padding: 6px 10px;
}
QHeaderView::section {
    background-color: #FAFAFA;
    color: #86868B;
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid #E5E5EA;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
}

/* ===== Accent button ===== */
QPushButton {
    background-color: #7B8CDE;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 7px 18px;
    font-size: 12px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #6B7DD6;
}
QPushButton:pressed {
    background-color: #5C6EC7;
}
QPushButton:disabled {
    background-color: #E5E5EA;
    color: #BCBCC0;
}

/* Secondary button */
QPushButton.secondary {
    background-color: #F0F0F0;
    color: #1D1D1F;
}
QPushButton.secondary:hover {
    background-color: #E5E5EA;
}

/* Danger button */
QPushButton.danger {
    background-color: #FF3B30;
    color: #FFFFFF;
}
QPushButton.danger:hover {
    background-color: #E0352B;
}

/* ===== Input ===== */
QLineEdit, QDateEdit, QComboBox {
    background-color: #FFFFFF;
    color: #1D1D1F;
    border: 1px solid #E5E5EA;
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 12px;
}
QLineEdit:focus, QDateEdit:focus, QComboBox:focus {
    border-color: #7B8CDE;
    border-width: 2px;
    padding: 5px 9px;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #1D1D1F;
    selection-background-color: #7B8CDE;
    selection-color: #FFFFFF;
    border: 1px solid #E5E5EA;
    border-radius: 6px;
    padding: 4px;
}
QDateEdit::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 20px;
    border-left: 1px solid #E5E5EA;
}

/* ===== Checkbox ===== */
QCheckBox {
    color: #1D1D1F;
    font-size: 12px;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #D1D1D6;
    border-radius: 4px;
    background-color: #FFFFFF;
}
QCheckBox::indicator:checked {
    background-color: #7B8CDE;
    border-color: #7B8CDE;
}

/* ===== Label ===== */
QLabel {
    color: #1D1D1F;
    font-size: 12px;
}
QLabel.section {
    font-size: 11px;
    font-weight: 600;
    color: #86868B;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ===== Group Box ===== */
QGroupBox {
    color: #1D1D1F;
    border: 1px solid #E5E5EA;
    border-radius: 10px;
    margin-top: 14px;
    padding: 18px 12px 12px 12px;
    font-size: 12px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

/* ===== Toolbar ===== */
QToolBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E5E5EA;
    padding: 6px 12px;
    spacing: 10px;
}

/* ===== Status Bar ===== */
QStatusBar {
    background-color: #FAFAFA;
    color: #86868B;
    border-top: 1px solid #E5E5EA;
    font-size: 11px;
}

/* ===== Scroll ===== */
QScrollBar:vertical {
    background-color: transparent;
    width: 8px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background-color: #D1D1D6;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #BCBCC0;
}
QScrollBar:horizontal {
    background-color: transparent;
    height: 8px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background-color: #D1D1D6;
    border-radius: 4px;
    min-width: 30px;
}

/* ===== Text Edit ===== */
QTextEdit {
    background-color: #FFFFFF;
    color: #1D1D1F;
    border: 1px solid #E5E5EA;
    border-radius: 10px;
    font-family: "SF Mono", "Consolas", "Courier New", monospace;
    font-size: 11px;
    padding: 10px;
}

/* ===== Message Box ===== */
QMessageBox {
    background-color: #FFFFFF;
}
"""


def apply_theme(app):
    app.setStyleSheet(MAC_QSS)
