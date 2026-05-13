from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from app.theme.styles import APP_STYLE
from app.widgets.mc_button import McButton


def title_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("mcTitle")
    label.setAlignment(Qt.AlignCenter)
    return label


def subtitle_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("mcSubtitle")
    label.setAlignment(Qt.AlignCenter)
    label.setWordWrap(True)
    return label


def menu_button(text: str) -> McButton:
    return McButton(text)
