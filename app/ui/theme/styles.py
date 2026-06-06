from app.ui.theme.colors import (
    CANVAS_BG, CANVAS_BG_LIGHTER, SURFACE, SURFACE_HOVER, BORDER, BORDER_FOCUS,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_INVERSE, TEXT_TITLE,
    TEXT_TITLE_WARM, TEXT_DISABLED, TEXT_PLACEHOLDER, TEXT_BUTTON_PRIMARY,
    TEXT_BUTTON_WOOD,
    ACCENT, ACCENT_HOVER, ACCENT_PRESSED, SECONDARY, SECONDARY_HOVER,
    ERROR, SUCCESS, WARN, INFO, EDITOR_BG, EDITOR_TEXT, EDITOR_SELECTION,
    HIGHLIGHT, HIGHLIGHT_BG,
)
from app.ui.theme.fonts import BODY_FONT, CODE_FONT, TITLE_FONT
from app.ui.theme.minecraft_assets import asset_url, bg_image, border_image

CHEVRON_DOWN_ICON = "app/ui/theme/icons/chevron-down.svg"
CHECK_ICON = "app/ui/theme/icons/check.svg"

GLOBAL_STYLESHEET = f"""
/* Minecraft dark stone theme */

QWidget {{
    color: {TEXT_PRIMARY};
    background-color: {CANVAS_BG};
    {bg_image("backgrounds", "dark_stone_tile")}
    font-family: {BODY_FONT};
}}

QMainWindow {{
    background-color: {CANVAS_BG};
    {bg_image("backgrounds", "dark_stone_tile")}
}}

QWidget#appShell {{
    background-color: {CANVAS_BG};
    {bg_image("backgrounds", "dark_stone_tile")}
}}

QFrame, QGroupBox {{
    background-color: transparent;
    border: none;
}}

QFrame[panel="stone"], QFrame#resultCard, QFrame#reviewCard, QFrame#ojCard,
QFrame#trackCard {{
    background-color: {SURFACE};
    {border_image("panels", "stone_panel", 12)}
    padding: 8px;
}}

QFrame#kbDetail {{
    background-color: #c7a875;
    {border_image("panels", "parchment_panel", 16)}
    border-width: 16px;
    padding: 14px;
}}

QFrame#kbDetail QLabel {{
    color: #2c2115;
}}

QFrame[panel="card"], QFrame#quickCard, QFrame#statCard {{
    background-color: {SURFACE};
    {border_image("panels", "card_panel", 10)}
    padding: 8px;
}}

QFrame[panel="empty"] {{
    background-color: {SURFACE};
    {border_image("panels", "empty_state_panel", 14)}
    border-width: 14px;
    padding: 16px;
}}

QLabel {{
    color: {TEXT_PRIMARY};
    background: transparent;
    border: none;
    font-size: 14px;
    font-weight: 500;
    font-family: {BODY_FONT};
}}

QLabel[muted="true"] {{
    color: {TEXT_SECONDARY};
}}

QPushButton {{
    background-color: {ACCENT};
    color: {TEXT_BUTTON_PRIMARY};
    {border_image("buttons", "green_action_normal", 8)}
    border-width: 8px;
    padding: 8px 20px;
    min-height: 34px;
    font-size: 16px;
    font-weight: 700;
    font-family: {TITLE_FONT};
}}

QPushButton:hover {{
    background-color: {ACCENT_HOVER};
    color: {TEXT_BUTTON_PRIMARY};
    {border_image("buttons", "green_action_hover", 8)}
}}

QPushButton:pressed {{
    background-color: {ACCENT_PRESSED};
    color: {TEXT_BUTTON_PRIMARY};
    {border_image("buttons", "green_action_pressed", 8)}
}}

QPushButton:disabled {{
    background-color: {SECONDARY};
    color: {TEXT_DISABLED};
    {border_image("buttons", "green_action_disabled", 8)}
}}

QPushButton[variant="secondary"] {{
    background-color: {SECONDARY};
    color: {TEXT_PRIMARY};
    {border_image("buttons", "dark_button_normal", 8)}
}}

QPushButton[variant="secondary"]:hover {{
    background-color: {SECONDARY_HOVER};
    color: {TEXT_TITLE};
    {border_image("buttons", "dark_button_hover", 8)}
}}

QPushButton[variant="secondary"]:pressed {{
    background-color: {CANVAS_BG_LIGHTER};
    color: {TEXT_TITLE_WARM};
    {border_image("buttons", "dark_button_pressed", 8)}
}}

QPushButton[variant="secondary"]:disabled {{
    color: {TEXT_DISABLED};
    {border_image("buttons", "dark_button_disabled", 8)}
}}

QPushButton[variant="icon"] {{
    min-width: 28px;
    max-width: 40px;
    min-height: 28px;
    color: {TEXT_PRIMARY};
    padding: 2px;
    font-size: 16px;
    font-weight: 900;
    font-family: {TITLE_FONT};
    {border_image("buttons", "icon_button", 6)}
}}

QToolButton {{
    background-color: {SECONDARY};
    color: {TEXT_PRIMARY};
    {border_image("buttons", "dark_button_normal", 8)}
    border-width: 8px;
    padding: 6px 12px;
    min-height: 32px;
    font-size: 15px;
    font-weight: 700;
    font-family: {TITLE_FONT};
}}

QToolButton:hover {{
    background-color: {SECONDARY_HOVER};
    {border_image("buttons", "dark_button_hover", 8)}
}}

QTabWidget::pane {{
    border: none;
    background: transparent;
    top: -1px;
}}

QTabBar::tab {{
    color: {TEXT_BUTTON_WOOD};
    background-color: #5b442b;
    {border_image("buttons", "wood_nav_normal", 8)}
    border-width: 8px;
    padding: 9px 20px;
    margin: 6px 4px 6px 0;
    min-height: 38px;
    min-width: 128px;
    font-size: 17px;
    font-weight: 700;
    font-family: {TITLE_FONT};
}}

QTabBar::tab:hover:!selected {{
    color: {TEXT_TITLE};
    {border_image("buttons", "wood_nav_normal", 8)}
}}

QTabBar::tab:selected {{
    color: {TEXT_TITLE};
    {border_image("buttons", "wood_nav_active", 8)}
}}

QPlainTextEdit, QTextEdit {{
    color: {EDITOR_TEXT};
    background-color: {EDITOR_BG};
    {bg_image("backgrounds", "obsidian_tile")}
    {border_image("inputs", "editor_frame", 12)}
    border-width: 12px;
    padding: 10px 12px;
    selection-background-color: {EDITOR_SELECTION};
    selection-color: {TEXT_PRIMARY};
    font-size: 16px;
    font-family: {CODE_FONT};
}}

QPlainTextEdit {{
    placeholder-text-color: {TEXT_PLACEHOLDER};
}}

QGraphicsView {{
    background-color: {EDITOR_BG};
    {bg_image("backgrounds", "obsidian_tile")}
    {border_image("panels", "stone_panel", 12)}
    border-width: 12px;
    padding: 6px;
}}

QPlainTextEdit:focus, QTextEdit:focus {{
    border-color: {BORDER_FOCUS};
}}

QLineEdit, QSpinBox {{
    color: {TEXT_PRIMARY};
    background-color: {EDITOR_BG};
    {border_image("inputs", "text_input_frame", 8)}
    border-width: 8px;
    padding: 6px 10px;
    min-height: 24px;
    selection-background-color: {EDITOR_SELECTION};
    placeholder-text-color: {TEXT_PLACEHOLDER};
    font-size: 14px;
    font-weight: 500;
    font-family: {BODY_FONT};
}}

QLineEdit:focus, QSpinBox:focus {{
    {border_image("inputs", "text_input_focus", 8)}
}}

QLineEdit:disabled, QSpinBox:disabled {{
    color: {TEXT_DISABLED};
    background-color: {SECONDARY};
}}

QComboBox {{
    color: {TEXT_PRIMARY};
    background-color: {EDITOR_BG};
    {border_image("inputs", "combo_frame", 8)}
    border-width: 8px;
    padding: 5px 34px 5px 10px;
    min-height: 30px;
    font-size: 14px;
    font-weight: 600;
    font-family: {BODY_FONT};
}}

QComboBox:hover, QComboBox:focus {{
    border-color: {BORDER_FOCUS};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 2px solid {BORDER};
    background-color: {SURFACE_HOVER};
}}

QComboBox::down-arrow {{
    image: url({CHEVRON_DOWN_ICON});
    width: 10px;
    height: 6px;
}}

QComboBox QAbstractItemView {{
    background-color: {SURFACE};
    color: {TEXT_PRIMARY};
    {border_image("panels", "side_panel", 12)}
    selection-background-color: {ACCENT_PRESSED};
    outline: none;
    padding: 4px;
    font-size: 14px;
}}

QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 8px;
    background: transparent;
    font-size: 14px;
    font-weight: 600;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    image: {asset_url("inputs", "checkbox_unchecked")};
}}

QCheckBox::indicator:checked {{
    image: {asset_url("inputs", "checkbox_checked")};
}}

QSlider::groove:horizontal {{
    background: {BORDER};
    height: 8px;
    border: 1px solid {CANVAS_BG};
}}

QSlider::handle:horizontal {{
    background: {ACCENT};
    border: 2px solid {ACCENT_PRESSED};
    width: 16px;
    height: 16px;
    margin: -6px 0;
}}

QScrollArea {{
    background: transparent;
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

QScrollBar:vertical {{
    background: {CANVAS_BG_LIGHTER};
    width: 12px;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background: {BORDER};
    min-height: 32px;
    border: 2px solid {CANVAS_BG};
}}

QScrollBar::handle:vertical:hover {{
    background: {BORDER_FOCUS};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background: {CANVAS_BG_LIGHTER};
    height: 12px;
    margin: 2px;
}}

QScrollBar::handle:horizontal {{
    background: {BORDER};
    min-width: 32px;
    border: 2px solid {CANVAS_BG};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QListWidget, QListView, QTreeWidget, QTreeView {{
    background: transparent;
    color: {TEXT_PRIMARY};
    border: none;
    outline: none;
}}

QListWidget::item, QListView::item, QTreeWidget::item, QTreeView::item {{
    color: {TEXT_PRIMARY};
    {border_image("lists", "item_normal", 8)}
    padding: 8px 12px;
    min-height: 34px;
    font-size: 16px;
    font-weight: 600;
}}

QListWidget::item:hover, QListView::item:hover, QTreeWidget::item:hover, QTreeView::item:hover {{
    {border_image("lists", "item_hover", 8)}
}}

QListWidget::item:selected, QListView::item:selected, QTreeWidget::item:selected, QTreeView::item:selected {{
    color: {TEXT_PRIMARY};
    {border_image("lists", "item_selected", 8)}
}}

QStatusBar {{
    background-color: {SURFACE};
    color: {TEXT_SECONDARY};
    border-top: 2px solid {BORDER};
    {bg_image("backgrounds", "secondary_stone_tile")}
    font-size: 13px;
}}

QStatusBar QLabel {{
    color: {TEXT_SECONDARY};
    font-size: 13px;
}}

QDialog, QMessageBox {{
    color: {TEXT_PRIMARY};
    background-color: {CANVAS_BG};
    {bg_image("backgrounds", "dark_stone_tile")}
}}

QDialog > QWidget, QMessageBox > QWidget {{
    background: transparent;
}}

QDialogButtonBox QPushButton {{
    min-width: 86px;
}}

QMenuBar, QMenu {{
    background-color: {SURFACE};
    color: {TEXT_PRIMARY};
    {border_image("panels", "side_panel", 12)}
}}

QMenu::item {{
    padding: 9px 24px;
    font-size: 14px;
}}

QMenu::item:selected {{
    background-color: {ACCENT_PRESSED};
}}

QToolTip {{
    background-color: {SURFACE};
    color: {TEXT_PRIMARY};
    border: 2px solid {BORDER_FOCUS};
    padding: 6px 10px;
}}

QSplitter::handle {{
    background-color: {BORDER};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

QWidget[highlight="step"] {{
    background-color: {HIGHLIGHT_BG};
    border: 2px solid {HIGHLIGHT};
}}

QLabel[state="success"] {{ color: {SUCCESS}; }}
QLabel[state="warning"] {{ color: {WARN}; }}
QLabel[state="error"] {{ color: {ERROR}; }}
QLabel[state="info"] {{ color: {INFO}; }}
"""
