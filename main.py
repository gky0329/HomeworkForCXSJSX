import sys
import os
import yaml
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from app.ui.main_window import MainWindow
from app.ui.theme.styles import GLOBAL_STYLESHEET
from app.core.engine import Engine


def load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def has_api_key(config: dict) -> bool:
    llm_cfg = config.get("llm", {})
    provider = str(llm_cfg.get("provider", "deepseek")).lower()
    provider_cfg = llm_cfg.get("providers", {}).get(provider, {})

    env_name = provider_cfg.get("api_key_env", "")
    if env_name and os.environ.get(env_name):
        return True

    api_key = provider_cfg.get("api_key", "")
    if api_key and str(api_key).strip():
        return True

    if provider == "deepseek" and os.environ.get("DEEPSEEK_API_KEY"):
        return True
    if provider == "deepseek":
        legacy_key = llm_cfg.get("api_key", "")
        return bool(legacy_key and str(legacy_key).strip())
    return False


def main():
    config = load_config()

    app = QApplication(sys.argv)
    app.setApplicationName("C++ Memory Visualizer")
    app.setStyleSheet(GLOBAL_STYLESHEET)

    config_path = Path(__file__).parent / "config.yaml"

    window = MainWindow(config_path)
    engine = Engine(window, config_path)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
