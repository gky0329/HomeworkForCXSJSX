import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.theme.styles import GLOBAL_STYLESHEET
from app.core.engine import Engine


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("C++ Memory Visualizer")
    app.setStyleSheet(GLOBAL_STYLESHEET)

    config_path = Path(__file__).parent / "config.yaml"
    window = MainWindow(config_path)
    Engine(window, config_path)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
