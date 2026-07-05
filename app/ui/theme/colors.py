"""Theme color tokens used by QSS and page-level inline styles.

Most pages import these constants at module import time, so the palette is
selected once during startup from config.yaml. Restart the app after changing
the UI theme in Settings.
"""

from __future__ import annotations

from pathlib import Path

import yaml


_MINECRAFT = {
    "CANVAS_BG": "#111611",
    "CANVAS_BG_LIGHTER": "#1B201A",
    "SURFACE": "#242820",
    "SURFACE_HOVER": "#31382B",
    "BORDER": "#626A59",
    "BORDER_FOCUS": "#8CB45D",
    "TEXT_PRIMARY": "#F5F0DC",
    "TEXT_SECONDARY": "#C9BEA8",
    "TEXT_MUTED": "#AFA58F",
    "TEXT_INVERSE": "#1A260E",
    "TEXT_TITLE": "#FFFFFF",
    "TEXT_TITLE_WARM": "#F6E6B8",
    "TEXT_DISABLED": "#8F8A7A",
    "TEXT_PLACEHOLDER": "#9A927F",
    "TEXT_BUTTON_PRIMARY": "#FFFFFF",
    "TEXT_BUTTON_WOOD": "#FFF2D0",
    "PARCHMENT_TEXT": "#2C2115",
    "PARCHMENT_MUTED": "#5F4B33",
    "STACK_BORDER": "#7E9FBE",
    "STACK_BG": "#233242",
    "STACK_TITLE": "#B9D3E6",
    "STACK_VAR_TEXT": "#E0DED2",
    "STACK_AREA_BG": "#172330",
    "HEAP_BORDER": "#B58A5A",
    "HEAP_BG": "#332719",
    "HEAP_TEXT": "#D1B184",
    "HEAP_AREA_BG": "#211A12",
    "ACCENT": "#78A84A",
    "ACCENT_TEXT": "#9BE35A",
    "ACCENT_HOVER": "#8BBC57",
    "ACCENT_PRESSED": "#557B34",
    "SECONDARY": "#3A3D35",
    "SECONDARY_HOVER": "#4A5042",
    "ERROR": "#B86A5E",
    "ERROR_BG": "#3A211E",
    "SUCCESS": "#93B77E",
    "SUCCESS_BG": "#24351F",
    "WARN": "#D1B66A",
    "WARN_BG": "#342C17",
    "INFO": "#86A6BD",
    "INFO_BG": "#1E2B34",
    "EDGE_SOLID": "#A0A695",
    "EDGE_DANGLING": "#B86A5E",
    "EDGE_REF": "#93B77E",
    "HIGHLIGHT": "#D8C56B",
    "HIGHLIGHT_BG": "#30351D",
    "EDITOR_BG": "#141713",
    "EDITOR_TEXT": "#F2E8D0",
    "EDITOR_LINE_NUM": "#AFA58F",
    "EDITOR_CURSOR": "#D8C56B",
    "EDITOR_SELECTION": "#33412C",
}


_DARK = {
    "CANVAS_BG": "#000000",
    "CANVAS_BG_LIGHTER": "#080808",
    "SURFACE": "#0D0D0D",
    "SURFACE_HOVER": "#171717",
    "BORDER": "#3A3A3A",
    "BORDER_FOCUS": "#FFFFFF",
    "TEXT_PRIMARY": "#F7F7F7",
    "TEXT_SECONDARY": "#B8B8B8",
    "TEXT_MUTED": "#8A8A8A",
    "TEXT_INVERSE": "#000000",
    "TEXT_TITLE": "#FFFFFF",
    "TEXT_TITLE_WARM": "#FFFFFF",
    "TEXT_DISABLED": "#666666",
    "TEXT_PLACEHOLDER": "#767676",
    "TEXT_BUTTON_PRIMARY": "#000000",
    "TEXT_BUTTON_WOOD": "#F7F7F7",
    "PARCHMENT_TEXT": "#F7F7F7",
    "PARCHMENT_MUTED": "#B8B8B8",
    "STACK_BORDER": "#FFFFFF",
    "STACK_BG": "#080808",
    "STACK_TITLE": "#FFFFFF",
    "STACK_VAR_TEXT": "#EDEDED",
    "STACK_AREA_BG": "#050505",
    "HEAP_BORDER": "#D0D0D0",
    "HEAP_BG": "#101010",
    "HEAP_TEXT": "#D8D8D8",
    "HEAP_AREA_BG": "#080808",
    "ACCENT": "#FFFFFF",
    "ACCENT_TEXT": "#FFFFFF",
    "ACCENT_HOVER": "#E5E5E5",
    "ACCENT_PRESSED": "#BDBDBD",
    "SECONDARY": "#151515",
    "SECONDARY_HOVER": "#222222",
    "ERROR": "#FFFFFF",
    "ERROR_BG": "#1A1A1A",
    "SUCCESS": "#FFFFFF",
    "SUCCESS_BG": "#1A1A1A",
    "WARN": "#E6E6E6",
    "WARN_BG": "#1A1A1A",
    "INFO": "#DADADA",
    "INFO_BG": "#1A1A1A",
    "EDGE_SOLID": "#D0D0D0",
    "EDGE_DANGLING": "#FFFFFF",
    "EDGE_REF": "#E6E6E6",
    "HIGHLIGHT": "#FFFFFF",
    "HIGHLIGHT_BG": "#181818",
    "EDITOR_BG": "#030303",
    "EDITOR_TEXT": "#F5F5F5",
    "EDITOR_LINE_NUM": "#8A8A8A",
    "EDITOR_CURSOR": "#FFFFFF",
    "EDITOR_SELECTION": "#2A2A2A",
}


_END_CITY = {
    "CANVAS_BG": "#F4E8C2",
    "CANVAS_BG_LIGHTER": "#FAF0CF",
    "SURFACE": "#F7EBD1",
    "SURFACE_HOVER": "#FFF3DA",
    "BORDER": "#C9B0C9",
    "BORDER_FOCUS": "#E85BFF",
    "TEXT_PRIMARY": "#2A2031",
    "TEXT_SECONDARY": "#5F5262",
    "TEXT_MUTED": "#7C6F7D",
    "TEXT_INVERSE": "#FFFFFF",
    "TEXT_TITLE": "#24172C",
    "TEXT_TITLE_WARM": "#3D2548",
    "TEXT_DISABLED": "#958896",
    "TEXT_PLACEHOLDER": "#867787",
    "TEXT_BUTTON_PRIMARY": "#2A2031",
    "TEXT_BUTTON_WOOD": "#2A2031",
    "PARCHMENT_TEXT": "#2A2031",
    "PARCHMENT_MUTED": "#6A5A65",
    "STACK_BORDER": "#8E3FB0",
    "STACK_BG": "#F8EBD1",
    "STACK_TITLE": "#4A3158",
    "STACK_VAR_TEXT": "#2A2031",
    "STACK_AREA_BG": "#FFF6DA",
    "HEAP_BORDER": "#9E5EAE",
    "HEAP_BG": "#F4E3BE",
    "HEAP_TEXT": "#5A3A62",
    "HEAP_AREA_BG": "#FFF2D6",
    "ACCENT": "#A040BF",
    "ACCENT_TEXT": "#8E3FB0",
    "ACCENT_HOVER": "#C35DDA",
    "ACCENT_PRESSED": "#7B2A98",
    "SECONDARY": "#F1E4CF",
    "SECONDARY_HOVER": "#FFF0D9",
    "ERROR": "#A6384B",
    "ERROR_BG": "#F7D9DF",
    "SUCCESS": "#2E7D45",
    "SUCCESS_BG": "#DDEFD9",
    "WARN": "#8C5B00",
    "WARN_BG": "#F4E5BC",
    "INFO": "#8E3FB0",
    "INFO_BG": "#F0DDF5",
    "EDGE_SOLID": "#6A5A65",
    "EDGE_DANGLING": "#A6384B",
    "EDGE_REF": "#2E7D45",
    "HIGHLIGHT": "#D84CFF",
    "HIGHLIGHT_BG": "#F6DCF9",
    "EDITOR_BG": "#FFF6DA",
    "EDITOR_TEXT": "#211827",
    "EDITOR_LINE_NUM": "#7C6F7D",
    "EDITOR_CURSOR": "#8E3FB0",
    "EDITOR_SELECTION": "#EAC8F3",
}

def _normalize_theme(theme: object) -> str:
    key = str(theme or "").strip().lower().replace("-", "_")
    if key in {"", "dark", "mc", "minecraft", "minecraft_dark"}:
        return "mc"
    if key in {"end", "end_city", "mc_end_city", "minecraft_end_city"}:
        return "mc_end_city"
    if key in {"minimal_dark", "minimal_black", "black"}:
        return "minimal_dark"
    return "mc"


def palette_for_theme(theme: object) -> dict[str, str]:
    key = _normalize_theme(theme)
    if key == "mc":
        return dict(_MINECRAFT)
    if key == "mc_end_city":
        return dict(_END_CITY)
    return dict(_DARK)


def _theme_from_config() -> str:
    path = Path(__file__).resolve().parents[3] / "config.yaml"
    try:
        if not path.exists():
            return "mc"
        cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        ui_cfg = cfg.get("ui", {})
        if not isinstance(ui_cfg, dict):
            return "mc"
        return str(ui_cfg.get("theme") or "mc")
    except Exception:
        return "mc"


ACTIVE_THEME = _normalize_theme(_theme_from_config())


def active_theme() -> str:
    return ACTIVE_THEME


def set_active_theme(theme: object) -> None:
    """Update theme globals for lazily imported pages after runtime switching."""
    global ACTIVE_THEME
    ACTIVE_THEME = _normalize_theme(theme)
    globals().update(palette_for_theme(ACTIVE_THEME))


def use_minecraft_assets() -> bool:
    return ACTIVE_THEME in {"mc", "mc_end_city", "minecraft", "minecraft_dark", "end_city", "minecraft_end_city"}


globals().update(palette_for_theme(ACTIVE_THEME))
