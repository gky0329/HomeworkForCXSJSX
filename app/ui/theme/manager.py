from __future__ import annotations

from pathlib import Path

import yaml
from PySide6.QtWidgets import QApplication

from app.ui.theme.fonts import load_theme_fonts
from app.ui.theme.minecraft_assets import asset_path, asset_url, bg_image, border_image
from app.ui.theme.styles import stylesheet_for_theme
from app.utils.startup_profiler import StartupProfiler

THEME_MINECRAFT = "mc"
THEME_END_CITY = "mc_end_city"
THEME_MINIMAL_DARK = "minimal_dark"

THEME_LABELS = {
    THEME_MINECRAFT: "Minecraft",
    THEME_END_CITY: "Minecraft End City",
    THEME_MINIMAL_DARK: "Minimal Black",
}

_THEME_ALIASES = {
    "": THEME_MINECRAFT,
    "dark": THEME_MINECRAFT,
    "minecraft": THEME_MINECRAFT,
    "mc": THEME_MINECRAFT,
    "end": THEME_END_CITY,
    "end-city": THEME_END_CITY,
    "end_city": THEME_END_CITY,
    "mc-end-city": THEME_END_CITY,
    "mc_end_city": THEME_END_CITY,
    "minecraft-end-city": THEME_END_CITY,
    "minecraft_end_city": THEME_END_CITY,
    "minimal-dark": THEME_MINIMAL_DARK,
    "minimal_dark": THEME_MINIMAL_DARK,
    "minimal-black": THEME_MINIMAL_DARK,
    "minimal_black": THEME_MINIMAL_DARK,
    "black": THEME_MINIMAL_DARK,
}


def normalize_theme(value: object) -> str:
    key = str(value or "").strip().lower()
    return _THEME_ALIASES.get(key, THEME_MINECRAFT)


def theme_from_config(config_path: Path | None = None) -> str:
    path = config_path or Path(__file__).resolve().parents[3] / "config.yaml"
    try:
        if not path.exists():
            return THEME_MINECRAFT
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:
        return THEME_MINECRAFT
    ui_cfg = cfg.get("ui", {})
    if not isinstance(ui_cfg, dict):
        return THEME_MINECRAFT
    return normalize_theme(ui_cfg.get("theme"))


class ThemeManager:
    """Single entry point for app-wide UI theme selection."""

    @staticmethod
    def apply(
        app: QApplication,
        profiler: StartupProfiler | None = None,
        *,
        config_path: Path | None = None,
        theme: str | None = None,
    ) -> list[str]:
        active_theme = normalize_theme(theme) if theme is not None else theme_from_config(config_path)
        if profiler is not None:
            with profiler.span("fonts"):
                loaded_fonts = load_theme_fonts()
            with profiler.span("qss"):
                app.setProperty("cppraftingTheme", active_theme)
                app.setStyleSheet(stylesheet_for_theme(active_theme))
            return loaded_fonts
        loaded_fonts = load_theme_fonts()
        app.setProperty("cppraftingTheme", active_theme)
        app.setStyleSheet(stylesheet_for_theme(active_theme))
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
