from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QLabel, QLineEdit, QListWidgetItem, QPushButton

from app.ui.theme.colors import use_minecraft_assets
from app.ui.theme.minecraft_assets import asset_path


def theme_uses_icons() -> bool:
    return use_minecraft_assets()


def theme_icon(name: str) -> QIcon:
    return QIcon(asset_path("icons", name))


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
    label.setPixmap(QPixmap(asset_path("icons", name)).scaled(
        icon_size,
        icon_size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.FastTransformation,
    ))
    return label
