from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QListWidgetItem, QPushButton

from app.ui.theme.colors import use_minecraft_assets
from app.ui.theme.minecraft_assets import asset_path

_ICON_CACHE: dict[str, QIcon] = {}
_PIXMAP_CACHE: dict[str, QPixmap] = {}


def _active_theme() -> str:
    app = QApplication.instance()
    if app is None:
        return ""
    theme = app.property("cppraftingTheme")
    return str(theme or "").strip().lower().replace("-", "_")


def theme_uses_icons() -> bool:
    theme = _active_theme()
    if theme:
        return theme in {
            "mc",
            "mc_end_city",
            "minecraft",
            "minecraft_dark",
            "end_city",
            "minecraft_end_city",
        }
    return use_minecraft_assets()


def theme_icon_path(name: str) -> str:
    theme = _active_theme()
    if theme in {"mc_end_city", "end_city", "minecraft_end_city"}:
        themed_path = asset_path("themes/mc_end_city/icons", name)
        if not themed_path.endswith(".svg"):
            return themed_path
    return asset_path("icons", name)


def theme_icon(name: str) -> QIcon:
    if not theme_uses_icons():
        return QIcon()
    path = theme_icon_path(name)
    icon = _ICON_CACHE.get(path)
    if icon is None:
        icon = QIcon(path)
        _ICON_CACHE[path] = icon
    return icon


def clear_theme_icon_cache() -> None:
    _ICON_CACHE.clear()
    _PIXMAP_CACHE.clear()


def set_button_icon(button: QPushButton, name: str, size: int = 18) -> None:
    if not theme_uses_icons():
        return
    button.setIcon(theme_icon(name))
    button.setIconSize(QSize(size, size))


def add_line_edit_icon(line_edit: QLineEdit, name: str) -> None:
    if theme_uses_icons():
        line_edit.addAction(theme_icon(name), QLineEdit.ActionPosition.LeadingPosition)


def set_item_icon(item: QListWidgetItem, name: str) -> None:
    if theme_uses_icons():
        item.setIcon(theme_icon(name))


def icon_label(name: str, icon_size: int, fixed_size: int | None = None) -> QLabel | None:
    if not theme_uses_icons():
        return None
    label = QLabel()
    if fixed_size is not None:
        label.setFixedSize(fixed_size, fixed_size)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    path = theme_icon_path(name)
    pixmap = _PIXMAP_CACHE.get(path)
    if pixmap is None:
        pixmap = QPixmap(path)
        _PIXMAP_CACHE[path] = pixmap
    label.setPixmap(pixmap.scaled(
        icon_size,
        icon_size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.FastTransformation,
    ))
    return label
