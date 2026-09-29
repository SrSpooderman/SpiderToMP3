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
