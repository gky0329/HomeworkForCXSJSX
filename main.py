import sys

from PySide6.QtWidgets import QApplication

from app.config import ConfigLoader
from app.di import Container
from app.log import setup_logging
from app.nav import NavigationManager
from app.core.engine import Engine
from app.core.challenge_loader import ChallengeLoader
from app.services.audio_manager import AudioManager
from app.services.lesson_service import LessonService
from app.services.storage_service import StorageService
from app.ui.main_window import MainWindow


def main() -> int:
    config = ConfigLoader.load("config.yaml")
    logger = setup_logging("INFO")
    logger.info(f"{config.window.title} 启动")

    Container.register(NavigationManager, NavigationManager())
    Container.register(AudioManager, AudioManager())
    Container.register(StorageService, StorageService(config.saves.dir))
    Container.register(LessonService, LessonService(config.levels.dir))
    Container.register(ChallengeLoader, ChallengeLoader(config.levels.dir))
    Container.register(Engine, Engine())

    qapp = QApplication(sys.argv)
    qapp.setApplicationName(config.window.title)

    nav = Container.resolve(NavigationManager)
    storage = Container.resolve(StorageService)
    lesson = Container.resolve(LessonService)
    audio = Container.resolve(AudioManager)
    loader = Container.resolve(ChallengeLoader)
    engine = Container.resolve(Engine)

    window = MainWindow(nav, storage, lesson, audio, loader, engine)
    window.setWindowTitle(config.window.title)
    window.resize(config.window.width, config.window.height)
    window.show()

    logger.info("主窗口已显示")
    return qapp.exec()


if __name__ == "__main__":
    raise SystemExit(main())
