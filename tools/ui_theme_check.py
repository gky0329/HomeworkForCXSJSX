"""Capture key UI screens for Minecraft theme inspection.

Run from the project root:
    python tools/ui_theme_check.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.theme.manager import ThemeManager
from app.ui.widgets.api_key_dialog import ApiKeyDialog


OUT_DIR = ROOT / "debug_screenshots" / "ui_theme_check"


def _settle(app: QApplication, rounds: int = 4) -> None:
    for _ in range(rounds):
        app.processEvents()


def _grab(widget, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pixmap = widget.grab()
    pixmap.save(str(OUT_DIR / name))


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("C++rafting Table UI Theme Check")
    ThemeManager.apply(app)
    if not QFontDatabase.families():
        print(
            "Warning: Qt did not expose system fonts in this platform mode; "
            "Chinese text may appear as boxes in these screenshots."
        )

    window = MainWindow(ROOT / "config.yaml")
    window.resize(1440, 900)
    window.show()
    _settle(app)

    tabs = getattr(window, "_tabs")
    for index in range(tabs.count()):
        tabs.setCurrentIndex(index)
        _settle(app)
        tab_name = tabs.tabText(index).lower().replace(" ", "_").replace("/", "_")
        _grab(window, f"{index + 1:02d}_{tab_name}.png")

    dialog = ApiKeyDialog(window, ROOT / "config.yaml")
    dialog.resize(520, 560)
    dialog.show()
    _settle(app)
    _grab(dialog, "settings_dialog.png")
    dialog.close()

    QTimer.singleShot(0, app.quit)
    _settle(app)
    print(f"Saved UI theme screenshots to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
