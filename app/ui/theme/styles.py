from app.ui.theme.colors import (
    CANVAS_BG, SURFACE, BORDER,
    TEXT_PRIMARY, TEXT_SECONDARY,
    ACCENT, EDITOR_BG, EDITOR_TEXT,
)

GLOBAL_STYLESHEET = f"""
QMainWindow {{
    background-color: {CANVAS_BG};
}}

QPlainTextEdit {{
    background-color: {EDITOR_BG};
    color: {EDITOR_TEXT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 8px;
    selection-background-color: {ACCENT};
    font-size: 14px;
}}

QPushButton {{
    background-color: {ACCENT};
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    font-size: 13px;
    min-height: 28px;
}}

QPushButton:hover {{
    background-color: #1A8CD8;
}}

QPushButton:pressed {{
    background-color: #005A9E;
}}

QPushButton:disabled {{
    background-color: {BORDER};
    color: {TEXT_SECONDARY};
}}

QLabel {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}

QMenuBar {{
    background-color: {SURFACE};
    color: {TEXT_PRIMARY};
}}

QMenuBar::item:selected {{
    background-color: {ACCENT};
}}

QMenu {{
    background-color: {SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
}}

QMenu::item:selected {{
    background-color: {ACCENT};
}}

QStatusBar {{
    background-color: {SURFACE};
    color: {TEXT_SECONDARY};
}}

QSplitter::handle {{
    background-color: {BORDER};
    width: 2px;
}}

QScrollBar:vertical {{
    background-color: {EDITOR_BG};
    width: 12px;
}}

QScrollBar::handle:vertical {{
    background-color: {BORDER};
    border-radius: 4px;
    min-height: 20px;
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QToolBar {{
    background-color: {SURFACE};
    border-bottom: 1px solid {BORDER};
    padding: 4px;
    spacing: 8px;
}}
"""
