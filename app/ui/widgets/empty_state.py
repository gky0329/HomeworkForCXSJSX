from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from app.ui.theme.colors import ACCENT, TEXT_SECONDARY
from app.ui.theme.icon_helpers import icon_label


class PixelEmptyState(QFrame):
    def __init__(self, icon_name: str, title: str, message: str = "", parent=None):
        super().__init__(parent)
        self.setProperty("panel", "empty")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = icon_label(icon_name, 112)
        if icon is not None:
            layout.addWidget(icon)

        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet(
            f"color: {ACCENT}; font-size: 20px; font-weight: 800; background: transparent;"
        )
        layout.addWidget(self.title_label)

        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 14px; font-weight: 600; background: transparent;"
        )
        layout.addWidget(self.message_label)
