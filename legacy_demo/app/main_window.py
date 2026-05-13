from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMainWindow, QStackedWidget

from app.models.session import AppSession, GameMode, WorldMeta, WorldType
from app.pages.create_world_page import CreateWorldPage
from app.pages.creating_world_page import CreatingWorldPage
from app.pages.lesson_intro_page import LessonIntroPage
from app.pages.main_menu_page import MainMenuPage
from app.pages.quiz_page import QuizPage
from app.pages.result_page import ResultPage
from app.pages.splash_screen import SplashScreen
from app.pages.world_select_page import WorldSelectPage
from app.services.audio_manager import AudioManager
from app.services.lesson_service import LessonService
from app.services.storage_service import StorageService


TEACHING_URL = "http://cxsjsx.openjudge.cn/"
MINECRAFT_WEB_URL = "https://classic.minecraft.net/"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("用 Minecraft 风格学习编程")
        self.resize(1100, 720)

        self.audio = AudioManager()
        self.storage = StorageService()
        self.lesson_service = LessonService()
        self.session = AppSession()

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.splash = SplashScreen()
        self.main_menu = MainMenuPage(self.audio)
        self.world_select = WorldSelectPage(self.audio)
        self.create_world = CreateWorldPage(self.audio)
        self.creating_world = CreatingWorldPage()
        self.lesson_intro = LessonIntroPage(self.audio)
        self.quiz = QuizPage(self.audio)
        self.result = ResultPage(self.audio)

        for page in (
            self.splash,
            self.main_menu,
            self.world_select,
            self.create_world,
            self.creating_world,
            self.lesson_intro,
            self.quiz,
            self.result,
        ):
            self.stack.addWidget(page)

        self._wire_signals()
        self.stack.setCurrentWidget(self.splash)
        self.audio.play_startup_music()
        QTimer.singleShot(900, lambda: self.stack.setCurrentWidget(self.main_menu))

    def _wire_signals(self) -> None:
        self.main_menu.single_player_requested.connect(self.show_world_select)
        self.main_menu.multiplayer_requested.connect(lambda: QDesktopServices.openUrl(QUrl(TEACHING_URL)))
        self.main_menu.settings_requested.connect(self.main_menu.show_settings_placeholder)
        self.main_menu.exit_requested.connect(self.close)

        self.world_select.back_requested.connect(lambda: self.stack.setCurrentWidget(self.main_menu))
        self.world_select.create_requested.connect(lambda: self.stack.setCurrentWidget(self.create_world))
        self.world_select.enter_requested.connect(self.enter_world)

        self.create_world.back_requested.connect(self.show_world_select)
        self.create_world.world_created.connect(self.create_and_enter_world)

        self.creating_world.finished.connect(self.after_world_created)
        self.lesson_intro.start_requested.connect(self.start_quiz)
        self.lesson_intro.back_requested.connect(self.show_world_select)

        self.quiz.finished.connect(self.show_result)
        self.result.back_to_worlds_requested.connect(self.show_world_select)
        self.result.retry_requested.connect(self.start_quiz)

    def show_world_select(self) -> None:
        self.world_select.set_worlds(self.storage.load_worlds())
        self.stack.setCurrentWidget(self.world_select)

    def create_and_enter_world(self, world: WorldMeta) -> None:
        self.storage.save_world(world)
        self.enter_world(world)

    def enter_world(self, world: WorldMeta) -> None:
        self.session.start_world(world)
        if world.world_type == WorldType.MINECRAFT:
            QDesktopServices.openUrl(QUrl(MINECRAFT_WEB_URL))
            return
        self.creating_world.start()
        self.stack.setCurrentWidget(self.creating_world)

    def after_world_created(self) -> None:
        if not self.session.current_world:
            self.show_world_select()
            return
        if self.session.current_world.world_type == WorldType.CPP:
            lesson = self.lesson_service.load_level("cpp_oop_001")
            self.session.start_lesson(lesson)
            self.lesson_intro.set_lesson(lesson)
            self.stack.setCurrentWidget(self.lesson_intro)
            return
        self.show_world_select()

    def start_quiz(self) -> None:
        if not self.session.current_lesson:
            return
        self.session.reset_quiz()
        self.quiz.set_session(self.session)
        self.stack.setCurrentWidget(self.quiz)

    def show_result(self, success: bool) -> None:
        if self.session.current_world:
            self.storage.update_world_progress(
                self.session.current_world.id,
                self.session.current_lesson.id if self.session.current_lesson else "",
                success,
            )
        if success:
            self.audio.play_challenge_complete()
        self.result.set_result(self.session, success)
        self.stack.setCurrentWidget(self.result)
