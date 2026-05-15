import sys
import os
import yaml
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from app.ui.main_window import MainWindow
from app.ui.widgets.api_key_dialog import show_api_key_dialog
from app.ui.theme.styles import GLOBAL_STYLESHEET
from app.core.engine import Engine


def load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def has_api_key(config: dict) -> bool:
    if os.environ.get("DEEPSEEK_API_KEY"):
        return True
    api_key = config.get("llm", {}).get("api_key", "")
    return bool(api_key and api_key.strip())


def main():
    config = load_config()

    app = QApplication(sys.argv)
    app.setApplicationName("C++ Memory Visualizer")
    app.setStyleSheet(GLOBAL_STYLESHEET)

    if not has_api_key(config):
        show_api_key_dialog()

    if os.environ.get("QT_SCALE_FACTOR"):
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    config_path = Path(__file__).parent / "config.yaml"

    window = MainWindow(config_path)
    engine = Engine(window, config_path)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
