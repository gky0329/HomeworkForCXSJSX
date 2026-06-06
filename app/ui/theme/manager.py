from __future__ import annotations

from PySide6.QtWidgets import QApplication

from app.ui.theme.fonts import load_theme_fonts
from app.ui.theme.minecraft_assets import asset_path, asset_url, bg_image, border_image
from app.ui.theme.styles import GLOBAL_STYLESHEET
from app.utils.startup_profiler import StartupProfiler


class ThemeManager:
    """Single entry point for the Minecraft dark stone theme."""

    @staticmethod
    def apply(app: QApplication, profiler: StartupProfiler | None = None) -> list[str]:
        if profiler is not None:
            with profiler.span("fonts"):
                loaded_fonts = load_theme_fonts()
            with profiler.span("qss"):
                app.setStyleSheet(GLOBAL_STYLESHEET)
            return loaded_fonts
        loaded_fonts = load_theme_fonts()
        app.setStyleSheet(GLOBAL_STYLESHEET)
        return loaded_fonts

    @staticmethod
    def asset_path(category: str, name: str) -> str:
        return asset_path(category, name)

    @staticmethod
    def asset_url(category: str, name: str) -> str:
        return asset_url(category, name)

    @staticmethod
    def bg_image(category: str, name: str) -> str:
        return bg_image(category, name)

    @staticmethod
    def border_image(category: str, name: str, inset: int = 8) -> str:
        return border_image(category, name, inset)
