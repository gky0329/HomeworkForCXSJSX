from app.ui.theme.config import Colors


def _url(path) -> str:
    return path.resolve().as_posix()


def _button_image_rules() -> str:
    if not Colors or not hasattr(Colors, "MENU_BUTTON"):
        return ""
    from app.ui.theme.config import Assets

    if not Assets.BUTTON_NORMAL.exists():
        return ""
    normal = _url(Assets.BUTTON_NORMAL)
    hover = _url(Assets.BUTTON_HOVER if Assets.BUTTON_HOVER.exists() else Assets.BUTTON_NORMAL)
    disabled = _url(Assets.BUTTON_DISABLED if Assets.BUTTON_DISABLED.exists() else Assets.BUTTON_NORMAL)
    return f"""
McButton, QPushButton[mcButton="true"] {{
    border-image: url({normal}) 4 4 4 4 stretch stretch;
}}
McButton:hover, QPushButton[mcButton="true"]:hover {{
    border-image: url({hover}) 4 4 4 4 stretch stretch;
}}
McButton:disabled, QPushButton[mcButton="true"]:disabled {{
    border-image: url({disabled}) 4 4 4 4 stretch stretch;
}}
"""


APP_STYLE = f"""
QMainWindow, QWidget {{
    background: {Colors.BEDROCK};
    color: {Colors.CREAM};
    font-family: Microsoft YaHei, Segoe UI, sans-serif;
    font-size: 16px;
}}

QFrame#mcPanel, QLabel#mcPanel {{
    background: {Colors.PANEL_BG};
    border: 4px solid {Colors.STONE_DARK};
    padding: 14px;
}}

QLabel#mcTitle {{
    color: {Colors.CREAM};
    font-size: 36px;
    font-weight: 900;
}}

QLabel#mcSubtitle {{
    color: {Colors.MUTED};
    font-size: 18px;
}}

McButton, QPushButton[mcButton="true"] {{
    background: {Colors.MENU_BUTTON};
    color: white;
    border-left: 4px solid {Colors.STONE_LIGHT};
    border-top: 4px solid {Colors.STONE_LIGHT};
    border-right: 4px solid {Colors.STONE_DARK};
    border-bottom: 4px solid {Colors.STONE_DARK};
    padding: 10px 18px;
    min-height: 34px;
    font-size: 17px;
    font-weight: 700;
}}

McButton:hover, QPushButton[mcButton="true"]:hover {{
    background: {Colors.MENU_BUTTON_HOVER};
    color: {Colors.GOLD};
}}

McButton:pressed, QPushButton[mcButton="true"]:pressed {{
    background: {Colors.MENU_BUTTON_PRESSED};
    border-left: 4px solid {Colors.BLACK};
    border-top: 4px solid {Colors.BLACK};
    border-right: 4px solid {Colors.STONE_LIGHT};
    border-bottom: 4px solid {Colors.STONE_LIGHT};
    padding-left: 21px;
    padding-top: 13px;
}}

McButton:disabled, QPushButton[mcButton="true"]:disabled {{
    background: {Colors.DISABLED_BG};
    color: {Colors.DISABLED_TEXT};
    border-color: {Colors.DISABLED_BORDER};
}}

McButton[selected="true"], QPushButton[mcButton="true"][selected="true"] {{
    background: {Colors.GRASS};
    color: white;
}}

QLineEdit, QComboBox, QTextEdit {{
    background: rgba(0, 0, 0, 210);
    color: {Colors.CREAM};
    border: 3px solid white;
    padding: 8px;
    selection-background-color: {Colors.GRASS};
}}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
    border-color: {Colors.GOLD};
}}

QListWidget {{
    background: {Colors.BEDROCK};
    border: 3px solid {Colors.STONE_DARK};
    padding: 8px;
}}

QListWidget::item {{
    padding: 10px;
}}

QListWidget::item:selected {{
    background: {Colors.GRASS};
    color: white;
}}

QProgressBar {{
    border: 3px solid {Colors.BLACK};
    background: {Colors.BEDROCK};
    color: white;
    text-align: center;
    min-height: 22px;
}}

QProgressBar::chunk {{
    background: {Colors.GRASS_LIGHT};
}}

QRadioButton {{
    spacing: 10px;
    padding: 7px;
}}

QRadioButton::indicator {{
    width: 18px;
    height: 18px;
}}
""" + _button_image_rules()
