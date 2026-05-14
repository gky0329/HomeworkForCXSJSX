import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app.config import ConfigLoader
from app.log import setup_logging
from app.core.engine import Engine
from app.core.challenge_loader import ChallengeLoader
from app.services.app_settings import AppSettings
from app.services.audio_manager import AudioManager
from app.ui.main_window import MainWindow


def main() -> int:
    config = ConfigLoader.load("config.yaml")
    logger = setup_logging("INFO")
    logger.info(f"{config.window.title} 启动")

    qapp = QApplication(sys.argv)
    qapp.setApplicationName(config.window.title)
    qapp.setFont(QFont("Microsoft YaHei", 16))

    audio = AudioManager()
    loader = ChallengeLoader(config.levels.dir)
    engine = Engine()
    settings = AppSettings()

    window = MainWindow(audio, loader, engine, settings)
    window.setWindowTitle(config.window.title)
    window.resize(config.window.width, config.window.height)
    window.show()

    logger.info("主窗口已显示")
    return qapp.exec()


if __name__ == "__main__":
    raise SystemExit(main())
