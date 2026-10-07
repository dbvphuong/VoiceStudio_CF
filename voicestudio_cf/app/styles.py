"""Qt stylesheet for VoiceStudio_CF (Light lavender desktop theme).

Kế thừa toàn bộ màu sắc, typography và phong cách giao diện từ Voice_Omni.
"""

APP_STYLESHEET = """
QWidget {
    color: #25213d;
    font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
    font-size: 13px;
}
QMainWindow, QWidget#AppRoot, QStackedWidget#Pages {
    background: #f7f5ff;
}
QFrame#TopBar, QFrame#Sidebar, QFrame[card="true"] {
    background: #ffffff;
    border: 1px solid #ebe7f7;
    border-radius: 12px;
}
QFrame#TopBar {
    border-radius: 0;
    border-left: none;
    border-right: none;
    border-top: none;
}
QLabel#AppTitle {
    color: #43239a;
    font-size: 22px;
    font-weight: 700;
}
QLabel#PageTitle {
    color: #221a43;
    font-size: 20px;
    font-weight: 700;
}
QLabel#CardTitle {
    color: #251a47;
    font-size: 15px;
    font-weight: 700;
}
QLabel[muted="true"] { color: #746e86; }
QLabel#DeviceBadge {
    background: #ede6ff;
    color: #4a21af;
    border: 1px solid #d8c8ff;
    border-radius: 14px;
    padding: 3px 12px;
    font-weight: 600;
    font-size: 12px;
}
QPushButton {
    min-height: 34px;
    padding: 0 14px;
    border: 1px solid #c9b9f6;
    border-radius: 8px;
    background: #ffffff;
    color: #4d2aa4;
    font-weight: 600;
}
QPushButton:hover { background: #f3efff; border-color: #8864e8; }
QPushButton:pressed { background: #e8defe; }
QPushButton:disabled { color: #aaa5b7; border-color: #dedbe5; background: #f3f2f6; }
QPushButton[primary="true"] {
    color: white;
    background: #7143dc;
    border-color: #7143dc;
}
QPushButton[primary="true"]:hover { background: #6032cd; }
QPushButton[danger="true"] { color: #cf2f45; border-color: #ef9aaa; }
QPushButton[danger="true"]:hover { background: #fff0f3; }
QPushButton[nav="true"] {
    min-height: 44px;
    text-align: left;
    border-color: transparent;
    color: #4e4770;
    background: transparent;
    font-size: 14px;
    font-weight: 600;
    padding-left: 16px;
}
QPushButton[nav="true"]:checked {
    color: #4d24aa;
    background: #ebe3ff;
    border-color: #e1d6ff;
    border-left: 4px solid #7143dc;
}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    min-height: 34px;
    background: #ffffff;
    border: 1px solid #dcd6eb;
    border-radius: 7px;
    padding: 0 9px;
    selection-background-color: #bea9f5;
}
QTextEdit, QPlainTextEdit { padding: 8px; }
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid #805ae2; }
QComboBox::drop-down { border: none; width: 24px; }
QTableWidget, QListWidget {
    background: #ffffff;
    alternate-background-color: #faf9fe;
    border: 1px solid #e3deed;
    border-radius: 9px;
    gridline-color: #eeeaf5;
    outline: none;
}
QTableWidget::item, QListWidget::item { padding: 7px; }
QTableWidget::item:selected, QListWidget::item:selected {
    color: #2e1769;
    background: #e8ddff;
}
QHeaderView::section {
    color: #393153;
    background: #f7f5fc;
    border: none;
    border-bottom: 1px solid #ddd7eb;
    padding: 9px;
    font-weight: 700;
}
QProgressBar {
    min-height: 14px;
    max-height: 14px;
    border: none;
    border-radius: 7px;
    background: #e9e5f1;
    text-align: center;
    font-size: 11px;
}
QProgressBar::chunk { border-radius: 7px; background: #7650df; }
QGroupBox {
    font-weight: 700;
    border: 1px solid #e2ddec;
    border-radius: 9px;
    margin-top: 14px;
    padding-top: 12px;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; }
QCheckBox { spacing: 7px; font-weight: 500; }
QScrollBar:vertical { width: 10px; background: transparent; }
QScrollBar::handle:vertical { background: #c8bce3; border-radius: 5px; min-height: 24px; }
QSplitter::handle { background: #eeeaf7; width: 2px; }
QToolTip { background: #2b2441; color: white; border: none; padding: 5px; border-radius: 4px; }
"""
