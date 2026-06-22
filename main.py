import time
PROCESS_START = time.perf_counter()

import os
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from app.ui.main_window import MainWindow
from app.ui.theme.manager import ThemeManager
from app.utils.startup_profiler import StartupProfiler


IMPORTS_DONE = time.perf_counter()


def main():
    profiler = StartupProfiler(PROCESS_START)
    profiler.checkpoint("imports", IMPORTS_DONE)
    config_path = Path(__file__).parent / "config.yaml"

    with profiler.span("QApplication"):
        app = QApplication(sys.argv)
    app.setApplicationName("C++rafting Table")
    with profiler.span("assets"):
        app.setWindowIcon(QIcon(str(Path(__file__).parent / "assets" / "icons" / "app_icon.png")))
    ThemeManager.apply(app, profiler, config_path=config_path)

    with profiler.span("build main window"):
        window = MainWindow(config_path, startup_profiler=profiler)
    engine_ref = {"engine": None}

    def ensure_engine():
        if engine_ref["engine"] is not None:
            return
        with profiler.span("engine"):
            from app.core.engine import Engine
            engine_ref["engine"] = Engine(window, config_path)

    window.code_page_ready.connect(ensure_engine)
    with profiler.span("first show"):
        window.show()

    def on_first_frame():
        profiler.checkpoint("first frame")
        slowest = ", ".join(f"{name} {ms:.0f} ms" for name, ms in profiler.top())
        print(f"[Startup] slowest: {slowest}")

    QTimer.singleShot(0, on_first_frame)
    auto_exit_ms = int(os.environ.get("CPPRAFTING_STARTUP_EXIT_MS", "0") or "0")
    if auto_exit_ms > 0:
        QTimer.singleShot(auto_exit_ms, app.quit)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
