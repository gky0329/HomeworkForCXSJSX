from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFontDatabase


ROOT = Path(__file__).resolve().parents[3]
PROJECT_FONT_DIR = ROOT / "font"
ASSET_FONT_DIR = ROOT / "assets" / "fonts"

TITLE_FONT = '"Mojangles", "Unifont", "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", sans-serif'
BODY_FONT = '"Unifont", "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "Segoe UI", sans-serif'
CODE_FONT = '"JetBrains Mono", "Cascadia Code", "Consolas", "Menlo", monospace'

_LOADED_FONTS: list[str] | None = None


def load_theme_fonts() -> list[str]:
    """Load bundled fonts and return the registered family names."""
    global _LOADED_FONTS
    if _LOADED_FONTS is not None:
        return list(_LOADED_FONTS)
    loaded: list[str] = []
    for folder in (PROJECT_FONT_DIR, ASSET_FONT_DIR):
        if not folder.exists():
            continue
        for path in sorted(folder.rglob("*")):
            if path.suffix.lower() not in {".ttf", ".otf"}:
                continue
            font_id = QFontDatabase.addApplicationFont(str(path))
            if font_id < 0:
                continue
            loaded.extend(QFontDatabase.applicationFontFamilies(font_id))
    _LOADED_FONTS = loaded
    return list(loaded)
