from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGridLayout, QLabel, QMessageBox, QVBoxLayout

from app.pages.widgets import APP_STYLE, menu_button, subtitle_label, title_label
from app.services.audio_manager import AudioManager
from app.theme.config import Assets, Colors
from app.widgets.panorama_background import PanoramaBackground


class MainMenuPage(PanoramaBackground):
    single_player_requested = Signal()
    multiplayer_requested = Signal()
    settings_requested = Signal()
    exit_requested = Signal()

    def __init__(self, audio: AudioManager) -> None:
        super().__init__(dim=18)
        self.audio = audio
        self.setStyleSheet(APP_STYLE)
        primary_width = 960
        secondary_width = 470
        secondary_gap = primary_width - secondary_width * 2

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(34, 70, 34, 24)
        layout.setSpacing(8)

        logo = self._logo_label()
        subtitle = self._edition_label()
        splash = QLabel("C++! Python! Blocks!")
        splash.setAlignment(Qt.AlignCenter)
        splash.setStyleSheet(f"font-size: 26px; font-weight: 900; color: {Colors.GOLD};")

        layout.addWidget(logo)
        layout.addWidget(subtitle)
        layout.addWidget(splash)
        layout.addSpacing(46)

        for text, signal in (("单人游戏", self.single_player_requested), ("多人游戏", self.multiplayer_requested)):
            button = menu_button(text)
            button.setMinimumWidth(primary_width)
            button.clicked.connect(self.audio.play_button)
            button.clicked.connect(signal.emit)
            layout.addWidget(button, alignment=Qt.AlignCenter)

        secondary = QGridLayout()
        secondary.setHorizontalSpacing(secondary_gap)
        mod_button = menu_button("Mod")
        realms_button = menu_button("Minecraft Realms")
        settings_button = menu_button("选项...")
        exit_button = menu_button("退出游戏")
        for button in (mod_button, realms_button, settings_button, exit_button):
            button.setMinimumWidth(secondary_width)
            button.clicked.connect(self.audio.play_button)
        mod_button.setEnabled(False)
        realms_button.setEnabled(False)
        settings_button.clicked.connect(self.settings_requested.emit)
        exit_button.clicked.connect(self.exit_requested.emit)
        secondary.addWidget(mod_button, 0, 0)
        secondary.addWidget(realms_button, 0, 1)
        secondary.addWidget(settings_button, 1, 0)
        secondary.addWidget(exit_button, 1, 1)
        layout.addLayout(secondary)
        layout.addStretch(1)

        footer = QLabel("Forge Beta 68.0.3  |  Minecraft 26.1      © Mojang AB 请勿二次分发！")
        footer.setStyleSheet("font-size: 18px; color: white;")
        layout.addWidget(footer)

    def show_settings_placeholder(self) -> None:
        QMessageBox.information(self, "设置", "设置页面将在后续版本加入。")

    def _logo_label(self) -> QLabel:
        label = title_label("MINECRAFT")
        if Assets.TITLE_LOGO.exists():
            pixmap = QPixmap(str(Assets.TITLE_LOGO))
            if not pixmap.isNull():
                label.setPixmap(pixmap.scaledToWidth(620, Qt.FastTransformation))
        label.setStyleSheet("font-size: 76px; font-weight: 900; color: #D7D1C8; background: transparent;")
        return label

    def _edition_label(self) -> QLabel:
        label = subtitle_label("JAVA EDITION  编程学习")
        if Assets.TITLE_EDITION.exists():
            pixmap = QPixmap(str(Assets.TITLE_EDITION))
            if not pixmap.isNull():
                label.setPixmap(pixmap.scaledToWidth(250, Qt.FastTransformation))
        label.setStyleSheet("background: transparent;")
        return label
