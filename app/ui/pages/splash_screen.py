from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout

from app.ui.widgets.panorama_background import PanoramaBackground
from app.ui.theme.config import Assets, Colors
from app.ui.theme.styles import APP_STYLE


class SplashScreen(PanoramaBackground):
    def __init__(self) -> None:
        super().__init__(dim=10)
        self.setStyleSheet(APP_STYLE)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("MINECRAFT  CXSJSX")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"font-size: 64px; font-weight: 900; color: {Colors.GOLD}; "
            f"background: transparent;"
        )
        layout.addWidget(title)

        sub = QLabel("Loading...")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(
            f"font-size: 24px; color: {Colors.CREAM}; background: transparent;"
        )
        layout.addWidget(sub)
