from app.ui.theme.colors import (
    CANVAS_BG, CANVAS_BG_LIGHTER, SURFACE, SURFACE_HOVER, BORDER, BORDER_FOCUS,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_INVERSE, TEXT_TITLE,
    TEXT_TITLE_WARM, TEXT_DISABLED, TEXT_PLACEHOLDER, TEXT_BUTTON_PRIMARY,
    TEXT_BUTTON_WOOD,
    ACCENT, ACCENT_HOVER, ACCENT_PRESSED, SECONDARY, SECONDARY_HOVER,
    ERROR, SUCCESS, WARN, INFO, EDITOR_BG, EDITOR_TEXT, EDITOR_SELECTION,
    HIGHLIGHT, HIGHLIGHT_BG, palette_for_theme,
)
from app.ui.theme.fonts import BODY_FONT, CODE_FONT, TITLE_FONT
from app.ui.theme.minecraft_assets import asset_url, bg_image, border_image

CHEVRON_DOWN_ICON = "app/ui/theme/icons/chevron-down.png"

# The Minecraft stylesheet must be independent from the active startup theme.
# Page-level inline styles still import colors.py directly for the active theme.
_MC_PALETTE = palette_for_theme("mc")
(
    CANVAS_BG, CANVAS_BG_LIGHTER, SURFACE, SURFACE_HOVER, BORDER, BORDER_FOCUS,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_INVERSE, TEXT_TITLE,
    TEXT_TITLE_WARM, TEXT_DISABLED, TEXT_PLACEHOLDER, TEXT_BUTTON_PRIMARY,
    TEXT_BUTTON_WOOD, ACCENT, ACCENT_HOVER, ACCENT_PRESSED, SECONDARY,
    SECONDARY_HOVER, ERROR, SUCCESS, WARN, INFO, EDITOR_BG, EDITOR_TEXT,
    EDITOR_SELECTION, HIGHLIGHT, HIGHLIGHT_BG,
) = (
    _MC_PALETTE["CANVAS_BG"], _MC_PALETTE["CANVAS_BG_LIGHTER"],
    _MC_PALETTE["SURFACE"], _MC_PALETTE["SURFACE_HOVER"],
    _MC_PALETTE["BORDER"], _MC_PALETTE["BORDER_FOCUS"],
    _MC_PALETTE["TEXT_PRIMARY"], _MC_PALETTE["TEXT_SECONDARY"],
    _MC_PALETTE["TEXT_MUTED"], _MC_PALETTE["TEXT_INVERSE"],
    _MC_PALETTE["TEXT_TITLE"], _MC_PALETTE["TEXT_TITLE_WARM"],
    _MC_PALETTE["TEXT_DISABLED"], _MC_PALETTE["TEXT_PLACEHOLDER"],
    _MC_PALETTE["TEXT_BUTTON_PRIMARY"], _MC_PALETTE["TEXT_BUTTON_WOOD"],
    _MC_PALETTE["ACCENT"], _MC_PALETTE["ACCENT_HOVER"],
    _MC_PALETTE["ACCENT_PRESSED"], _MC_PALETTE["SECONDARY"],
    _MC_PALETTE["SECONDARY_HOVER"], _MC_PALETTE["ERROR"],
    _MC_PALETTE["SUCCESS"], _MC_PALETTE["WARN"], _MC_PALETTE["INFO"],
    _MC_PALETTE["EDITOR_BG"], _MC_PALETTE["EDITOR_TEXT"],
    _MC_PALETTE["EDITOR_SELECTION"], _MC_PALETTE["HIGHLIGHT"],
    _MC_PALETTE["HIGHLIGHT_BG"],
)

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


def _minimal_stylesheet(
    *,
    name: str,
    bg: str,
    surface: str,
    surface_alt: str,
    border: str,
    text: str,
    muted: str,
    accent: str,
    accent_hover: str,
    button_bg: str,
    button_hover: str,
    button_border: str,
    button_text: str,
    editor_bg: str,
    editor_text: str,
    selection: str,
) -> str:
    return f"""
/* {name} */

QWidget {{
    color: {text};
    background-color: {bg};
    font-family: "PingFang SC", "Microsoft YaHei UI", "Segoe UI";
    font-size: 14px;
}}

QMainWindow, QWidget#appShell {{
    background-color: {bg};
}}

QFrame, QGroupBox {{
    background-color: transparent;
    border: none;
}}

QFrame[panel="stone"], QFrame[panel="card"], QFrame[panel="empty"],
QFrame#resultCard, QFrame#reviewCard, QFrame#ojCard, QFrame#trackCard,
QFrame#quickCard, QFrame#statCard, QFrame#kbDetail {{
    background-color: {surface};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 10px;
}}

QLabel {{
    color: {text};
    background: transparent;
    border: none;
    font-size: 14px;
    font-weight: 500;
}}

QLabel[muted="true"] {{
    color: {muted};
}}

QPushButton, QToolButton {{
    background-color: {button_bg};
    color: {button_text};
    border: 1px solid {button_border};
    border-radius: 6px;
    padding: 7px 14px;
    min-height: 30px;
    font-size: 14px;
    font-weight: 700;
}}

QPushButton:hover, QToolButton:hover {{
    background-color: {button_hover};
    border-color: {button_border};
    color: {button_text};
}}

QPushButton:pressed, QToolButton:pressed {{
    background-color: {button_hover};
}}

QPushButton:disabled, QToolButton:disabled {{
    background-color: {surface_alt};
    border-color: {border};
    color: {muted};
}}

QPushButton[variant="secondary"], QToolButton[variant="secondary"] {{
    background-color: {surface};
    color: {text};
    border: 1px solid {border};
}}

QPushButton[variant="secondary"]:hover, QToolButton[variant="secondary"]:hover {{
    background-color: {surface_alt};
    border-color: {accent};
}}

QPushButton[variant="icon"] {{
    min-width: 28px;
    max-width: 40px;
    min-height: 28px;
    padding: 2px;
    font-size: 16px;
}}

QTabWidget::pane {{
    border: none;
    background: transparent;
}}

QTabBar::tab {{
    color: {muted};
    background-color: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 10px 16px;
    margin: 4px 2px 0 2px;
    min-height: 32px;
    min-width: 104px;
    font-size: 14px;
    font-weight: 650;
}}

QTabBar::tab:selected {{
    color: {text};
    border-bottom-color: {accent};
}}

QTabBar::tab:hover:!selected {{
    color: {text};
    border-bottom-color: {border};
}}

QPlainTextEdit, QTextEdit {{
    color: {editor_text};
    background-color: {editor_bg};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 10px 12px;
    selection-background-color: {selection};
    selection-color: {editor_text};
    font-size: 15px;
    font-family: "JetBrains Mono", "Cascadia Code", "Consolas", "Menlo", monospace;
}}

QGraphicsView {{
    background-color: {editor_bg};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 4px;
}}

QLineEdit, QSpinBox, QComboBox {{
    color: {text};
    background-color: {surface};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 28px;
    selection-background-color: {selection};
    font-size: 14px;
}}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {accent};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 26px;
    border-left: 1px solid {border};
    background-color: {surface_alt};
}}

QComboBox::down-arrow {{
    width: 0;
    height: 0;
}}

QComboBox QAbstractItemView {{
    background-color: {surface};
    color: {text};
    border: 1px solid {border};
    selection-background-color: {accent};
    outline: none;
}}

QCheckBox {{
    color: {text};
    spacing: 8px;
    background: transparent;
    font-weight: 600;
}}

QSlider::groove:horizontal {{
    background: {border};
    height: 6px;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: {accent};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}

QScrollArea {{
    background: transparent;
    border: none;
}}

QScrollBar:vertical {{
    background: {bg};
    width: 12px;
}}

QScrollBar::handle:vertical {{
    background: {border};
    min-height: 32px;
    border-radius: 6px;
}}

QScrollBar:horizontal {{
    background: {bg};
    height: 12px;
}}

QScrollBar::handle:horizontal {{
    background: {border};
    min-width: 32px;
    border-radius: 6px;
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0;
    height: 0;
}}

QListWidget, QListView, QTreeWidget, QTreeView {{
    background: transparent;
    color: {text};
    border: none;
    outline: none;
}}

QListWidget::item, QListView::item, QTreeWidget::item, QTreeView::item {{
    color: {text};
    padding: 8px 10px;
    min-height: 30px;
    border-radius: 6px;
}}

QListWidget::item:hover, QListView::item:hover, QTreeWidget::item:hover,
QTreeView::item:hover {{
    background: {surface_alt};
}}

QListWidget::item:selected, QListView::item:selected, QTreeWidget::item:selected,
QTreeView::item:selected {{
    background: {selection};
    color: {editor_text};
}}

QStatusBar {{
    background-color: {surface};
    color: {muted};
    border-top: 1px solid {border};
    font-size: 13px;
}}

QDialog, QMessageBox {{
    color: {text};
    background-color: {bg};
}}

QMenuBar, QMenu {{
    background-color: {surface};
    color: {text};
    border: 1px solid {border};
}}

QMenu::item {{
    padding: 8px 22px;
}}

QMenu::item:selected {{
    background-color: {selection};
}}

QToolTip {{
    background-color: {surface};
    color: {text};
    border: 1px solid {accent};
    padding: 6px 8px;
}}

QSplitter::handle {{
    background-color: {border};
}}

QLabel[state="success"] {{ color: {text}; }}
QLabel[state="warning"] {{ color: {muted}; }}
QLabel[state="error"] {{ color: {text}; }}
QLabel[state="info"] {{ color: {accent}; }}
"""


MINIMAL_DARK_STYLESHEET = _minimal_stylesheet(
    name="Minimal black theme",
    bg="#000000",
    surface="#0d0d0d",
    surface_alt="#171717",
    border="#3a3a3a",
    text="#f7f7f7",
    muted="#a3a3a3",
    accent="#ffffff",
    accent_hover="#e5e5e5",
    button_bg="#ffffff",
    button_hover="#e5e5e5",
    button_border="#ffffff",
    button_text="#000000",
    editor_bg="#030303",
    editor_text="#f5f5f5",
    selection="#2a2a2a",
)

END_CITY_OVERRIDES = f"""
/* Minecraft End City light theme */

QWidget {{
    color: #2f2836;
    background-color: #ebe5ba;
    {bg_image("themes/mc_end_city/backgrounds", "end_stone_tile")}
}}

QMainWindow, QWidget#appShell {{
    background-color: #ebe5ba;
    {bg_image("themes/mc_end_city/backgrounds", "end_stone_tile")}
}}

QLabel {{
    color: #302737;
    font-size: 15px;
    font-weight: 600;
}}

QLabel[muted="true"] {{
    color: #6f6372;
}}

QFrame[panel="stone"], QFrame[panel="card"], QFrame[panel="empty"],
QFrame#resultCard, QFrame#reviewCard, QFrame#ojCard, QFrame#trackCard,
QFrame#quickCard, QFrame#statCard {{
    background-color: #32293a;
    color: #fff4df;
    {border_image("themes/mc_end_city/panels", "purpur_panel", 28)}
    border-width: 28px;
    padding: 10px;
}}

QFrame[panel="stone"] QLabel, QFrame[panel="card"] QLabel, QFrame[panel="empty"] QLabel,
QFrame#resultCard QLabel, QFrame#reviewCard QLabel, QFrame#ojCard QLabel,
QFrame#trackCard QLabel, QFrame#quickCard QLabel, QFrame#statCard QLabel {{
    color: #fff4df;
}}

QFrame#kbDetail {{
    background-color: #efe0b8;
    {border_image("panels", "parchment_panel", 16)}
    border-width: 16px;
    padding: 16px;
}}

QFrame#kbDetail QLabel {{
    color: #302416;
}}

QPushButton {{
    background-color: #17765f;
    color: #ffffff;
    {border_image("themes/mc_end_city/buttons", "ender_action_button", 28)}
    border-width: 28px;
    padding: 5px 18px;
    min-height: 36px;
    font-size: 16px;
    font-weight: 800;
}}

QPushButton:hover {{
    background-color: #1f9878;
    color: #ffffff;
    {border_image("themes/mc_end_city/buttons", "ender_action_button", 28)}
}}

QPushButton:pressed {{
    background-color: #105642;
    color: #e9fff6;
    {border_image("themes/mc_end_city/buttons", "ender_action_button", 28)}
}}

QPushButton:disabled {{
    background-color: #7d7582;
    color: #dbd4df;
    {border_image("buttons", "dark_button_disabled", 8)}
}}

QPushButton[variant="secondary"], QToolButton {{
    background-color: #473b4f;
    color: #fff1d6;
    {border_image("themes/mc_end_city/panels", "purpur_panel", 24)}
    border-width: 24px;
    padding: 4px 14px;
    min-height: 32px;
    font-size: 15px;
    font-weight: 700;
}}

QPushButton[variant="secondary"]:hover, QToolButton:hover {{
    background-color: #5b4866;
    color: #ffffff;
}}

QPushButton[variant="secondary"]:pressed, QToolButton:pressed {{
    background-color: #33283c;
    color: #efe5ff;
}}

QPushButton[variant="secondary"]:disabled, QToolButton:disabled {{
    color: #a89cab;
    background-color: #6f6772;
}}

QPushButton[variant="icon"] {{
    min-width: 30px;
    max-width: 44px;
    min-height: 30px;
    padding: 2px;
    color: #ffffff;
}}

QTabBar::tab {{
    color: #fff1d6;
    background-color: #4a3a50;
    {border_image("themes/mc_end_city/panels", "purpur_panel", 24)}
    border-width: 24px;
    padding: 6px 18px;
    min-height: 38px;
    min-width: 128px;
    font-size: 17px;
    font-weight: 800;
}}

QTabBar::tab:hover:!selected {{
    color: #ffffff;
    background-color: #5a4861;
}}

QTabBar::tab:selected {{
    color: #ffffff;
    background-color: #0f7f65;
    {border_image("themes/mc_end_city/buttons", "ender_action_button", 28)}
    border-width: 28px;
}}

QLineEdit, QSpinBox, QComboBox {{
    color: #2e2633;
    background-color: #fbf4cf;
    border: 2px solid #7f6f85;
    padding: 7px 10px;
    min-height: 28px;
    selection-background-color: #38b990;
    selection-color: #10231c;
    placeholder-text-color: #7f7380;
    font-size: 15px;
    font-weight: 600;
}}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 2px solid #159b75;
    background-color: #fff9dc;
}}

QComboBox::drop-down {{
    width: 28px;
    border-left: 1px solid #9e8da4;
    background-color: #d9cfaa;
}}

QComboBox QAbstractItemView {{
    background-color: #fbf4cf;
    color: #2e2633;
    border: 2px solid #7f6f85;
    selection-background-color: #2a9f7b;
    selection-color: #ffffff;
}}

QPlainTextEdit, QTextEdit, QGraphicsView {{
    color: #f7f1dc;
    background-color: #1d1525;
    {bg_image("backgrounds", "obsidian_tile")}
    {border_image("themes/mc_end_city/panels", "purpur_panel", 28)}
    border-width: 28px;
    padding: 10px 12px;
    selection-background-color: #2f9f86;
    selection-color: #ffffff;
    font-size: 16px;
}}

QPlainTextEdit {{
    placeholder-text-color: #a79bb0;
}}

QListWidget, QListView, QTreeWidget, QTreeView {{
    background-color: transparent;
    color: #2f2836;
    border: none;
}}

QListWidget::item, QListView::item, QTreeWidget::item, QTreeView::item {{
    color: #2f2836;
    background-color: rgba(255, 249, 220, 170);
    border: 1px solid rgba(103, 87, 111, 120);
    padding: 8px 12px;
    min-height: 34px;
    font-size: 16px;
    font-weight: 600;
}}

QListWidget::item:hover, QListView::item:hover, QTreeWidget::item:hover,
QTreeView::item:hover {{
    background-color: rgba(226, 215, 173, 220);
    color: #211a26;
}}

QListWidget::item:selected, QListView::item:selected, QTreeWidget::item:selected,
QTreeView::item:selected {{
    background-color: #159b75;
    color: #ffffff;
}}

QCheckBox {{
    color: #302737;
    font-size: 15px;
    font-weight: 600;
}}

QSlider::groove:horizontal {{
    background: #b8aa85;
    height: 8px;
    border: 1px solid #7f6f85;
}}

QSlider::handle:horizontal {{
    background: #18a984;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border: 2px solid #0f4f43;
}}

QScrollBar:vertical, QScrollBar:horizontal {{
    background: #d9cfaa;
}}

QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: #7f6f85;
    border: 1px solid #3b3142;
}}

QStatusBar {{
    background-color: #d7cda7;
    color: #5a5060;
    border-top: 2px solid #8b7c87;
    font-size: 13px;
    font-weight: 600;
}}

QDialog, QMessageBox {{
    color: #2f2836;
    background-color: #ebe5ba;
    {bg_image("themes/mc_end_city/backgrounds", "end_stone_tile")}
}}

QMenuBar, QMenu {{
    background-color: #fbf4cf;
    color: #2f2836;
    border: 2px solid #7f6f85;
}}

QMenu::item:selected {{
    background-color: #159b75;
    color: #ffffff;
}}

QToolTip {{
    background-color: #fbf4cf;
    color: #2f2836;
    border: 2px solid #159b75;
    padding: 6px 8px;
}}

QSplitter::handle {{
    background-color: #9a8da0;
}}

QLabel[state="success"] {{ color: #147b5f; }}
QLabel[state="warning"] {{ color: #8b5b0e; }}
QLabel[state="error"] {{ color: #a63d4c; }}
QLabel[state="info"] {{ color: #0d7b78; }}
"""

END_CITY_STYLESHEET = GLOBAL_STYLESHEET + END_CITY_OVERRIDES


def stylesheet_for_theme(theme: str) -> str:
    if theme == "mc_end_city":
        return END_CITY_STYLESHEET
    if theme == "minimal_dark":
        return MINIMAL_DARK_STYLESHEET
    return GLOBAL_STYLESHEET
