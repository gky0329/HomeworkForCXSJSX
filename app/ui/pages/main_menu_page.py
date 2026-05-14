from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout

from app.services.audio_manager import AudioManager
from app.ui.theme.config import Assets, Colors
from app.ui.theme.styles import APP_STYLE
from app.ui.widgets.mc_button import McButton
from app.ui.widgets.panorama_background import PanoramaBackground


def _menu_button(text: str) -> McButton:
    return McButton(text)


class MainMenuPage(PanoramaBackground):
    single_player_requested = Signal()
    multiplayer_requested = Signal()
    settings_requested = Signal()
    exit_requested = Signal()

    def __init__(self, audio: AudioManager) -> None:
        super().__init__(dim=18)
        self.setStyleSheet(APP_STYLE)
        pw = 960
        sw = 470
        gap = pw - sw * 2

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(34, 70, 34, 24)
        layout.setSpacing(8)

        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if Assets.TITLE_LOGO.exists():
            p = QPixmap(str(Assets.TITLE_LOGO))
            if not p.isNull():
                logo.setPixmap(p.scaledToWidth(620, Qt.TransformationMode.FastTransformation))
        logo.setStyleSheet("background: transparent;")

        edition = QLabel("JAVA EDITION  编程学习")
        edition.setAlignment(Qt.AlignmentFlag.AlignCenter)
        edition.setStyleSheet(f"font-size: 18px; color: {Colors.MUTED}; background: transparent;")
        if Assets.TITLE_EDITION.exists():
            pe = QPixmap(str(Assets.TITLE_EDITION))
            if not pe.isNull():
                edition.setPixmap(pe.scaledToWidth(250, Qt.TransformationMode.FastTransformation))

        splash = QLabel("C++! Python! Blocks!")
        splash.setAlignment(Qt.AlignmentFlag.AlignCenter)
        splash.setStyleSheet(f"font-size: 26px; font-weight: 900; color: {Colors.GOLD};")

        layout.addWidget(logo)
        layout.addWidget(edition)
        layout.addWidget(splash)
        layout.addSpacing(46)

        for label, sig in [
            ("单人游戏", self.single_player_requested),
            ("多人游戏", self.multiplayer_requested),
        ]:
            btn = _menu_button(label)
            btn.setMinimumWidth(pw)
            btn.clicked.connect(audio.play_button)
            btn.clicked.connect(sig.emit)
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        sec = QGridLayout()
        sec.setHorizontalSpacing(gap)

        exit_btn = _menu_button("退出游戏")
        exit_btn.setMinimumWidth(sw)
        exit_btn.clicked.connect(audio.play_button)
        exit_btn.clicked.connect(self.exit_requested.emit)

        mod_btn = _menu_button("Mod")
        mod_btn.setMinimumWidth(sw)
        mod_btn.setEnabled(False)
        settings_btn = _menu_button("设置")
        settings_btn.setMinimumWidth(sw)
        settings_btn.clicked.connect(audio.play_button)
        settings_btn.clicked.connect(self.settings_requested.emit)

        sec.addWidget(mod_btn, 0, 0)
        sec.addWidget(settings_btn, 0, 1)
        sec.addWidget(exit_btn, 1, 0, 1, 2)

        layout.addLayout(sec)
        layout.addStretch(1)

        footer = QLabel("Forge Beta 68.0.3  |  Minecraft 26.1      © Mojang AB")
        footer.setStyleSheet("font-size: 18px; color: white;")
        layout.addWidget(footer)
