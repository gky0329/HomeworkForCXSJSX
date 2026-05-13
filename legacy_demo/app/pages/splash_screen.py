from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout

from app.pages.widgets import APP_STYLE
from app.theme.config import Assets, Colors
from app.widgets.panorama_background import PanoramaBackground


class SplashScreen(PanoramaBackground):
    def __init__(self) -> None:
        super().__init__(dim=55)
        self.setStyleSheet(APP_STYLE)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        logo = QLabel("MINECRAFT\nCXSJSX")
        logo.setAlignment(Qt.AlignCenter)
        logo.setObjectName("mcTitle")
        if Assets.TITLE_LOGO.exists():
            pixmap = QPixmap(str(Assets.TITLE_LOGO))
            if not pixmap.isNull():
                logo.setPixmap(pixmap.scaledToWidth(560, Qt.FastTransformation))
        logo.setStyleSheet(
            f"font-size: 52px; font-weight: 900; color: {Colors.CREAM}; "
            "background: transparent; border: none; padding: 20px;"
        )
        loading = QLabel("正在加载方块世界...")
        loading.setAlignment(Qt.AlignCenter)
        loading.setObjectName("mcSubtitle")

        layout.addWidget(logo)
        layout.addSpacing(18)
        layout.addWidget(loading)
