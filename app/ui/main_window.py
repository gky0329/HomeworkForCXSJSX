from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMainWindow, QStackedWidget

from app.core.session import AppSession, GameMode, WorldMeta, WorldType
from app.nav import NavigationManager
from app.services.audio_manager import AudioManager
from app.services.lesson_service import LessonService
from app.services.storage_service import StorageService
from app.ui.pages.create_world_page import CreateWorldPage
from app.ui.pages.creating_world_page import CreatingWorldPage
from app.ui.pages.lesson_intro_page import LessonIntroPage
from app.ui.pages.main_menu_page import MainMenuPage
from app.ui.pages.quiz_page import QuizPage
from app.ui.pages.result_page import ResultPage
from app.ui.pages.splash_screen import SplashScreen
from app.ui.pages.world_select_page import WorldSelectPage

TEACHING_URL = "http://cxsjsx.openjudge.cn/"
MINECRAFT_WEB_URL = "https://classic.minecraft.net/"


class MainWindow(QMainWindow):

    def __init__(
        self,
        nav: NavigationManager,
        storage: StorageService,
        lesson_service: LessonService,
        audio: AudioManager,
    ) -> None:
        super().__init__()
        self.nav = nav
        self.storage = storage
        self.lesson_service = lesson_service
        self.audio = audio
        self.session = AppSession()

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.splash = SplashScreen()
        self.main_menu = MainMenuPage(audio)
        self.world_select = WorldSelectPage(audio, storage)
        self.create_world = CreateWorldPage(audio)
        self.creating_world = CreatingWorldPage()
        self.lesson_intro = LessonIntroPage(audio)
        self.quiz = QuizPage(audio)
        self.result = ResultPage(audio)

        for page in (
            self.splash, self.main_menu, self.world_select,
            self.create_world, self.creating_world,
            self.lesson_intro, self.quiz, self.result,
        ):
            self.stack.addWidget(page)

        self._wire()
        self.stack.setCurrentWidget(self.splash)
        self.audio.play_startup_music()
        QTimer.singleShot(900, lambda: self.stack.setCurrentWidget(self.main_menu))

    def _wire(self) -> None:
        m = self.main_menu
        m.single_player_requested.connect(self._show_world_select)
        m.multiplayer_requested.connect(
            lambda: QDesktopServices.openUrl(QUrl(TEACHING_URL))
        )
        m.exit_requested.connect(self.close)

        ws = self.world_select
        ws.back_requested.connect(lambda: self.stack.setCurrentWidget(self.main_menu))
        ws.create_requested.connect(lambda: self.stack.setCurrentWidget(self.create_world))
        ws.enter_requested.connect(self._enter_world)

        cw = self.create_world
        cw.back_requested.connect(self._show_world_select)
        cw.world_created.connect(self._create_and_enter)

        cr = self.creating_world
        cr.finished.connect(self._after_creating)

        li = self.lesson_intro
        li.start_requested.connect(self._start_quiz)
        li.back_requested.connect(self._show_world_select)

        qz = self.quiz
        qz.finished.connect(self._show_result)

        re = self.result
        re.back_to_worlds_requested.connect(self._show_world_select)
        re.retry_requested.connect(self._start_quiz)

    def _show_world_select(self) -> None:
        self.world_select.refresh()
        self.stack.setCurrentWidget(self.world_select)

    def _create_and_enter(self, world: WorldMeta) -> None:
        self.storage.save_world(world)
        self._enter_world(world)

    def _enter_world(self, world: WorldMeta) -> None:
        self.session.start_world(world)
        if world.world_type == WorldType.MINECRAFT:
            QDesktopServices.openUrl(QUrl(MINECRAFT_WEB_URL))
            return
        self.creating_world.start()
        self.stack.setCurrentWidget(self.creating_world)

    def _after_creating(self) -> None:
        w = self.session.current_world
        if not w:
            self._show_world_select()
            return
        if w.world_type == WorldType.CPP:
            lesson = self.lesson_service.load("cpp_oop_001")
            if lesson:
                self.session.start_lesson(lesson)
                self.lesson_intro.set_lesson(lesson)
                self.stack.setCurrentWidget(self.lesson_intro)
                return
        self._show_world_select()

    def _start_quiz(self) -> None:
        if not self.session.current_lesson:
            return
        self.session.reset_quiz()
        self.quiz.set_session(self.session)
        self.stack.setCurrentWidget(self.quiz)

    def _show_result(self, success: bool) -> None:
        if self.session.current_world:
            self.storage.update_progress(
                self.session.current_world.id,
                self.session.current_lesson.id if self.session.current_lesson else "",
                success,
            )
        if success:
            self.audio.play_challenge_complete()
        self.result.set_result(self.session, success)
        self.stack.setCurrentWidget(self.result)
