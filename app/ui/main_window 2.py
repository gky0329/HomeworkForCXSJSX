import logging
from PySide6.QtWidgets import QMainWindow, QStackedWidget

from app.nav import AppPage, NavigationManager
from app.di import Container
from app.config import Config
from app.core.challenge_loader import ChallengeLoader
from app.ui.pages.main_menu_page import MainMenuPage
from app.ui.pages.level_select_page import LevelSelectPage
from app.ui.pages.challenge_page import ChallengePage

logger = logging.getLogger("cpplab.main_window")


class MainWindow(QMainWindow):
    def __init__(self, nav: NavigationManager, config: Config, parent=None):
        super().__init__(parent)
        self._nav = nav
        self._config = config
        self._challenge_loader = Container.resolve(ChallengeLoader)

        self.setWindowTitle(config.window.title)
        self.resize(config.window.width, config.window.height)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._pages: dict[AppPage, object] = {}
        self._build_pages()
        self._wire_nav()

        self.setStyleSheet("background-color: #14142a;")

    def _build_pages(self):
        pages = self._pages

        menu = MainMenuPage()
        pages[AppPage.MAIN_MENU] = menu
        self._stack.addWidget(menu)

        level_select = LevelSelectPage(self._challenge_loader)
        pages[AppPage.LEVEL_SELECT] = level_select
        self._stack.addWidget(level_select)

        challenge = ChallengePage(self._challenge_loader, config=self._config)
        pages[AppPage.CHALLENGE] = challenge
        self._stack.addWidget(challenge)

    def _wire_nav(self):
        nav = self._nav
        pages = self._pages

        def _on_page_changed(target: AppPage, payload: dict):
            logger.info("Navigation: %s", target.name)

            if target == AppPage.LEVEL_SELECT:
                page = pages[AppPage.LEVEL_SELECT]
                page.load_levels()

            if target == AppPage.CHALLENGE:
                level_id = payload.get("level_id")
                if level_id:
                    page = pages[AppPage.CHALLENGE]
                    page.load_challenge(level_id)

            widget = pages.get(target)
            if widget:
                self._stack.setCurrentWidget(widget)

        nav.page_changed.connect(_on_page_changed)

        # Wire page signals → nav
        menu: MainMenuPage = pages[AppPage.MAIN_MENU]
        menu.start_requested.connect(
            lambda: nav.navigate_to(AppPage.LEVEL_SELECT)
        )
        menu.exit_requested.connect(self.close)

        level_select: LevelSelectPage = pages[AppPage.LEVEL_SELECT]
        level_select.back_requested.connect(
            lambda: nav.navigate_to(AppPage.MAIN_MENU)
        )
        level_select.level_selected.connect(
            lambda level_id: nav.navigate_to(AppPage.CHALLENGE, {"level_id": level_id})
        )

        challenge: ChallengePage = pages[AppPage.CHALLENGE]
        challenge.back_requested.connect(
            lambda: nav.navigate_to(AppPage.LEVEL_SELECT)
        )
        challenge.completed.connect(
            lambda: nav.navigate_to(AppPage.LEVEL_SELECT)
        )

    def showEvent(self, event):
        super().showEvent(event)
        self._nav.navigate_to(AppPage.MAIN_MENU)
