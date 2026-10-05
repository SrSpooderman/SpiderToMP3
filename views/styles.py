import re


APP_STYLESHEET = """
QWidget {
    background: #f7f7f4;
    color: #20242a;
    font-family: Segoe UI, Inter, Arial, sans-serif;
    font-size: 13px;
}
QLabel#Title {
    font-size: 30px;
    font-weight: 800;
}
QLabel#Subtitle {
    color: #59606b;
    font-size: 14px;
}
QLabel#Hint {
    color: #6c4e17;
    background: #fff3cf;
    border: 1px solid #efd27d;
    border-radius: 6px;
    padding: 8px;
}
QLabel#Error {
    color: #a32424;
    font-weight: 600;
}
QLineEdit, QTextEdit, QPlainTextEdit, QListWidget, QComboBox {
    background: #ffffff;
    border: 1px solid #d5d8df;
    border-radius: 6px;
    padding: 8px;
    selection-background-color: #216e77;
}
QPushButton {
    background: #216e77;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 9px 14px;
    font-weight: 700;
}
QPushButton:hover {
    background: #175d65;
}
QPushButton:disabled {
    background: #b7bdc4;
    color: #eef0f2;
}
QPushButton:focus, QLineEdit:focus, QTextEdit:focus, QListWidget:focus,
QComboBox:focus, QSpinBox:focus, QCheckBox:focus {
    border: 2px solid #d85f45;
}
QProgressBar {
    background: #ffffff;
    border: 1px solid #d5d8df;
    border-radius: 6px;
    height: 18px;
    text-align: center;
}
QProgressBar::chunk {
    background: #d85f45;
    border-radius: 5px;
}
QSplitter::handle {
    background: #e2e4e8;
    width: 2px;
}
"""

DARK_COLORS = {
    "#f7f7f4": "#20242a", "#20242a": "#f0f2f4",
    "#59606b": "#b8c0c8", "#6c4e17": "#ffe09a",
    "#fff3cf": "#443815", "#efd27d": "#8a7136",
    "#a32424": "#ff9b9b", "#ffffff": "#2a3038",
    "#d5d8df": "#68727e", "#216e77": "#277d8a",
    "#175d65": "#348e9b", "#b7bdc4": "#505963",
    "#eef0f2": "#d1d7dc", "#e2e4e8": "#4f5862",
}
DARK_STYLESHEET = re.sub(r"#[0-9a-fA-F]{6}", lambda match: DARK_COLORS.get(match.group(), match.group()), APP_STYLESHEET)

HIGH_CONTRAST_STYLESHEET = """
QWidget { background: #000000; color: #ffffff; font-size: 14px; }
QLineEdit, QTextEdit, QPlainTextEdit, QListWidget, QComboBox, QSpinBox {
    background: #000000; color: #ffffff; border: 2px solid #ffffff; padding: 6px;
}
QPushButton { background: #000000; color: #ffffff; border: 2px solid #ffffff; padding: 7px; }
QPushButton:focus, QLineEdit:focus, QTextEdit:focus, QListWidget:focus,
QComboBox:focus, QSpinBox:focus { border: 3px solid #ffff00; }
QProgressBar { background: #000000; color: #ffffff; border: 2px solid #ffffff; }
QProgressBar::chunk { background: #ffff00; }
"""
