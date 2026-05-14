from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMainWindow, QStackedWidget

from app.core.challenge_loader import ChallengeLoader
from app.core.engine import Engine
from app.services.audio_manager import AudioManager
from app.ui.pages.challenge_page import ChallengePage
from app.ui.pages.level_select_page import LevelSelectPage
from app.ui.pages.main_menu_page import MainMenuPage
from app.ui.pages.splash_screen import SplashScreen

TEACHING_URL = "http://cxsjsx.openjudge.cn/"


class MainWindow(QMainWindow):

    def __init__(
        self,
        audio: AudioManager,
        loader: ChallengeLoader,
        engine: Engine,
    ) -> None:
        super().__init__()
        self.audio = audio
        self.loader = loader
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.splash = SplashScreen()
        self.main_menu = MainMenuPage(audio)
        self.level_select = LevelSelectPage(loader)
        self.challenge = ChallengePage(loader, engine)

        for page in (self.splash, self.main_menu, self.level_select, self.challenge):
            self.stack.addWidget(page)

        self._wire()
        self.stack.setCurrentWidget(self.splash)
        self.audio.play_startup_music()
        QTimer.singleShot(900, lambda: self.stack.setCurrentWidget(self.main_menu))

    def _wire(self) -> None:
        m = self.main_menu
        m.single_player_requested.connect(self._show_level_select)
        m.multiplayer_requested.connect(lambda: QDesktopServices.openUrl(QUrl(TEACHING_URL)))
        m.exit_requested.connect(self.close)

        ls = self.level_select
        ls.back_requested.connect(lambda: self.stack.setCurrentWidget(self.main_menu))
        ls.level_selected.connect(self._start_challenge)

        ch = self.challenge
        ch.back_requested.connect(self._show_level_select)

    def _show_level_select(self) -> None:
        self.level_select.refresh()
        self.stack.setCurrentWidget(self.level_select)

    def _start_challenge(self, level_id: str) -> None:
        self.challenge.load_level(level_id)
        self.stack.setCurrentWidget(self.challenge)
