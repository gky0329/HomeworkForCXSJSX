from app.ui.theme.colors import (
    CANVAS_BG, SURFACE, SURFACE_HOVER, BORDER, BORDER_FOCUS,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_INVERSE,
    ACCENT, ACCENT_HOVER, ACCENT_PRESSED,
    SECONDARY, SECONDARY_HOVER,
    ERROR, ERROR_BG, SUCCESS, SUCCESS_BG, WARN, WARN_BG, INFO, INFO_BG,
    EDITOR_BG, EDITOR_TEXT, EDITOR_SELECTION,
    HIGHLIGHT, HIGHLIGHT_BG,
    STACK_BORDER, HEAP_BORDER,
)

GLOBAL_STYLESHEET = f"""
/* ═══════════════════════════════════════════════════════
   VS Code Dark+ — C++ Memory Visualizer
   Hierarchy: ACCENT → action  SECONDARY → subtle
              ERROR  → danger  SUCCESS → positive
   ═══════════════════════════════════════════════════════ */

QMainWindow {{
    background-color: {CANVAS_BG};
}}

/* ── Typography scale ──────────────────────────────────
   24px bold  → page title
   18px bold  → section header
   15px       → card title
   14px       → body / code
   13px       → default label
   12px       → secondary label
   11px       → caption / meta
   ────────────────────────────────────────────────────── */

QLabel {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
    background: transparent;
}}

/* ── Buttons ─────────────────────────────────────────── */
QPushButton {{
    background-color: {ACCENT};
    color: #FFFFFF;
    border: none;
    border-radius: 5px;
    padding: 7px 18px;
    font-size: 13px;
    font-weight: 600;
    min-height: 30px;
}}
QPushButton:hover {{
    background-color: {ACCENT_HOVER};
}}
QPushButton:pressed {{
    background-color: {ACCENT_PRESSED};
}}
QPushButton:disabled {{
    background-color: {BORDER};
    color: {TEXT_MUTED};
    font-weight: normal;
}}

/* ── Card pattern (QFrame) ───────────────────────────── */
QFrame[kb-card="true"] {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 16px;
}}
QFrame[kb-card="true"]:hover {{
    border-color: {STACK_BORDER};
}}

/* ── Code Editor ─────────────────────────────────────── */
QPlainTextEdit {{
    background-color: {EDITOR_BG};
    color: {EDITOR_TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 12px 14px;
    font-size: 14px;
    line-height: 1.6;
    selection-background-color: {EDITOR_SELECTION};
    selection-color: {TEXT_PRIMARY};
}}
QPlainTextEdit:focus {{
    border-color: {BORDER_FOCUS};
}}

/* ── Tab Bar ─────────────────────────────────────────── */
QTabWidget::pane {{
    border: none;
    background: {CANVAS_BG};
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_SECONDARY};
    padding: 10px 28px;
    margin-right: 2px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 13px;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    color: {TEXT_PRIMARY};
    border-bottom: 2px solid {ACCENT};
    background: {SURFACE};
}}
QTabBar::tab:hover:!selected {{
    color: {TEXT_PRIMARY};
    background: {SURFACE_HOVER};
}}

/* ── Toolbar ─────────────────────────────────────────── */
QToolBar {{
    background-color: {SURFACE};
    border-bottom: 1px solid {BORDER};
    padding: 6px 10px;
    spacing: 8px;
}}
QToolBar QPushButton {{
    min-height: 28px;
    padding: 5px 14px;
    font-size: 12px;
}}

/* ── Status Bar ──────────────────────────────────────── */
QStatusBar {{
    background-color: {SURFACE};
    color: {TEXT_MUTED};
    border-top: 1px solid {BORDER};
    padding: 3px 10px;
    font-size: 12px;
}}
QStatusBar QLabel {{
    color: {TEXT_MUTED};
    font-size: 12px;
}}

/* ── Menu Bar ────────────────────────────────────────── */
QMenuBar {{
    background-color: {SURFACE};
    color: {TEXT_PRIMARY};
    padding: 2px 0;
    border-bottom: 1px solid {BORDER};
}}
QMenuBar::item:selected {{
    background-color: {ACCENT};
    border-radius: 3px;
}}
QMenu {{
    background-color: {SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 0;
}}
QMenu::item {{
    padding: 7px 28px 7px 16px;
}}
QMenu::item:selected {{
    background-color: {ACCENT};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 5px 10px;
}}

/* ── Splitter ────────────────────────────────────────── */
QSplitter::handle {{
    background-color: {BORDER};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}
QSplitter::handle:hover {{
    background-color: {ACCENT};
}}

/* ── Scrollbar ───────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px 2px;
}}
QScrollBar::handle:vertical {{
    background-color: {BORDER};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {TEXT_MUTED};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 2px 4px;
}}
QScrollBar::handle:horizontal {{
    background-color: {BORDER};
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {TEXT_MUTED};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── Scroll Area ─────────────────────────────────────── */
QScrollArea {{
    border: none;
    background: transparent;
}}

/* ── ComboBox ────────────────────────────────────────── */
QComboBox {{
    background-color: {EDITOR_BG};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 5px 10px;
    min-height: 26px;
    font-size: 12px;
}}
QComboBox:hover {{
    border-color: {ACCENT};
}}
QComboBox:focus {{
    border-color: {BORDER_FOCUS};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background-color: {SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 4px;
    selection-background-color: {ACCENT};
    padding: 4px;
    outline: none;
}}

/* ── Slider ──────────────────────────────────────────── */
QSlider::groove:horizontal {{
    background: {BORDER};
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{
    background: {ACCENT_HOVER};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}

/* ── Checkbox ────────────────────────────────────────── */
QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 8px;
    font-size: 12px;
}}
QCheckBox::indicator {{
    width: 17px;
    height: 17px;
    border: 1.5px solid {BORDER};
    border-radius: 4px;
    background-color: {EDITOR_BG};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}
QCheckBox::indicator:hover {{
    border-color: {ACCENT};
}}

/* ── Input fields ────────────────────────────────────── */
QLineEdit {{
    background-color: {EDITOR_BG};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 7px 10px;
    font-size: 13px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus {{
    border-color: {BORDER_FOCUS};
}}
QLineEdit:disabled {{
    color: {TEXT_MUTED};
    background-color: {CANVAS_BG};
}}

QTextEdit {{
    background-color: {EDITOR_BG};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 8px 10px;
    font-size: 13px;
    selection-background-color: {ACCENT};
}}
QTextEdit:focus {{
    border-color: {BORDER_FOCUS};
}}

/* ── List Widget ─────────────────────────────────────── */
QListWidget {{
    background-color: {EDITOR_BG};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 4px 0;
    outline: none;
}}
QListWidget::item {{
    padding: 8px 14px;
    border-bottom: 1px solid {CANVAS_BG};
}}
QListWidget::item:selected {{
    background-color: {ACCENT};
    color: #FFFFFF;
}}
QListWidget::item:hover:!selected {{
    background-color: {SURFACE_HOVER};
}}

/* ── Dialog ──────────────────────────────────────────── */
QDialog {{
    background-color: {SURFACE};
}}
QDialog QLabel {{
    color: {TEXT_PRIMARY};
}}
QDialogButtonBox QPushButton {{
    min-width: 80px;
}}

/* ── Tooltip ─────────────────────────────────────────── */
QToolTip {{
    background-color: {SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 5px 10px;
    font-size: 12px;
}}

/* ── Progress-like highlight ─────────────────────────── */
QWidget[highlight="step"] {{
    background-color: {HIGHLIGHT_BG};
    border-radius: 4px;
}}
"""
