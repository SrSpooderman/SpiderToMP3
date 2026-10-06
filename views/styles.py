"""Styles for the main window's light, dark and high contrast themes."""


def _theme(
    *,
    background: str,
    surface: str,
    input_bg: str,
    text: str,
    muted: str,
    border: str,
    accent: str,
    accent_hover: str,
    accent_text: str,
    hover: str,
    danger: str,
    hint_bg: str,
    hint_text: str,
    selected: str,
) -> str:
    return f"""
QWidget {{
    color: {text};
    font-family: Inter, Segoe UI, Noto Sans, Arial, sans-serif;
    font-size: 13px;
}}
QMainWindow, QWidget#Central, QWidget#ScrollContent, QScrollArea#PanelScroll,
QScrollArea#PanelScroll > QWidget > QWidget {{ background: {background}; }}
QWidget#Card, QWidget#ActionBar {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 14px;
}}
QLabel {{ background: transparent; border: none; }}
QLabel#Title {{ font-size: 26px; font-weight: 800; }}
QLabel#Subtitle {{ color: {muted}; font-size: 13px; }}
QLabel#VersionBadge {{
    background: {surface}; color: {muted}; border: 1px solid {border};
    border-radius: 11px; padding: 7px 10px; font-size: 10px; font-weight: 700;
}}
QLabel#Eyebrow {{ color: {accent}; font-size: 11px; font-weight: 800; }}
QLabel#SectionTitle {{ font-size: 18px; font-weight: 700; }}
QLabel#FieldLabel, QLabel#Preview {{ color: {muted}; }}
QLabel#Preview {{ font-size: 11px; padding: 2px 0; }}
QLabel#Hint {{
    color: {hint_text}; background: {hint_bg};
    border: 1px solid {border}; border-radius: 8px; padding: 8px;
}}
QLabel#Error {{ color: {danger}; font-weight: 700; }}
QLineEdit, QTextEdit, QPlainTextEdit, QListWidget, QComboBox, QSpinBox {{
    background: {input_bg}; color: {text};
    border: 1px solid {border}; border-radius: 8px;
    padding: 8px; selection-background-color: {selected};
}}
QTextEdit, QPlainTextEdit, QListWidget {{ padding: 10px; }}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QListWidget:focus,
QComboBox:focus, QSpinBox:focus, QCheckBox:focus, QPushButton:focus {{
    border: 2px solid {accent};
}}
QListWidget::item {{ padding: 9px 7px; border-bottom: 1px solid {border}; }}
QListWidget::item:selected {{ background: {selected}; border-radius: 6px; }}
QPushButton {{
    background: {surface}; color: {text};
    border: 1px solid {border}; border-radius: 8px;
    padding: 8px 11px; font-weight: 600;
}}
QPushButton:hover {{ background: {hover}; }}
QPushButton:pressed {{ background: {selected}; }}
QPushButton#PrimaryButton {{
    background: {accent}; color: {accent_text}; border: 1px solid {accent};
    padding: 10px 18px; font-weight: 800;
}}
QPushButton#PrimaryButton:hover {{ background: {accent_hover}; }}
QPushButton#DangerButton {{ color: {danger}; }}
QPushButton:disabled, QPushButton#PrimaryButton:disabled {{
    background: {hover}; color: {muted}; border-color: {border};
}}
QProgressBar {{
    background: {input_bg}; color: {text}; border: 1px solid {border};
    border-radius: 7px; min-height: 13px; text-align: center;
}}
QProgressBar::chunk {{ background: {accent}; border-radius: 6px; }}
QSplitter::handle {{ background: transparent; width: 8px; }}
QTabWidget#WorkspaceTabs::pane {{ border: none; background: transparent; }}
QTabBar::tab {{
    background: {background}; color: {muted};
    border: 1px solid {border}; border-bottom: none;
    border-top-left-radius: 8px; border-top-right-radius: 8px;
    padding: 9px 22px; margin-right: 5px; font-weight: 700;
}}
QTabBar::tab:selected {{ background: {surface}; color: {accent}; }}
QTabBar::tab:hover:!selected {{ background: {hover}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {border}; border-radius: 5px; min-height: 28px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QStatusBar {{ background: {background}; color: {muted}; }}
QMenuBar, QMenu {{ background: {surface}; color: {text}; }}
QMenu::item:selected {{ background: {selected}; }}
"""


APP_STYLESHEET = _theme(
    background="#f4f7f7",
    surface="#ffffff",
    input_bg="#fbfcfc",
    text="#172a31",
    muted="#62757c",
    border="#dbe5e5",
    accent="#087f72",
    accent_hover="#06695e",
    accent_text="#ffffff",
    hover="#edf4f3",
    danger="#ad3b48",
    hint_bg="#eef8f6",
    hint_text="#32635e",
    selected="#d9f1ec",
)

DARK_STYLESHEET = _theme(
    background="#111b20",
    surface="#1b2a30",
    input_bg="#152329",
    text="#edf7f6",
    muted="#b4c5c8",
    border="#3b5157",
    accent="#65d3bd",
    accent_hover="#82e1ce",
    accent_text="#102822",
    hover="#273a40",
    danger="#ff9aa4",
    hint_bg="#173b38",
    hint_text="#c4ede5",
    selected="#285950",
)

HIGH_CONTRAST_STYLESHEET = """
QWidget { background: #000000; color: #ffffff; font-size: 14px; }
QWidget#Card, QWidget#ActionBar { border: 2px solid #ffffff; }
QTabWidget#WorkspaceTabs::pane { border: none; }
QTabBar::tab { border: 2px solid #ffffff; padding: 8px 18px; }
QTabBar::tab:selected { background: #ffff00; color: #000000; }
QLabel#Title { font-size: 26px; font-weight: 800; }
QLabel#SectionTitle { font-size: 18px; font-weight: 700; }
QLabel#Subtitle, QLabel#Preview { color: #ffffff; }
QLabel#VersionBadge { border: 2px solid #ffffff; padding: 6px; }
QLineEdit, QTextEdit, QPlainTextEdit, QListWidget, QComboBox, QSpinBox {
    background: #000000; color: #ffffff; border: 2px solid #ffffff; padding: 7px;
}
QPushButton { background: #000000; color: #ffffff; border: 2px solid #ffffff; padding: 8px; }
QPushButton#PrimaryButton { background: #ffff00; color: #000000; border-color: #ffff00; }
QPushButton:disabled { color: #aaaaaa; border-color: #aaaaaa; }
QPushButton:focus, QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QListWidget:focus, QComboBox:focus, QSpinBox:focus { border: 3px solid #ffff00; }
QProgressBar { background: #000000; color: #ffffff; border: 2px solid #ffffff; }
QProgressBar::chunk { background: #ffff00; }
QLabel#Eyebrow, QLabel#Error { color: #ffff00; }
QListWidget::item:selected, QMenu::item:selected { background: #333333; }
QScrollBar:vertical { background: #000000; width: 12px; }
QScrollBar::handle:vertical { background: #ffffff; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""
