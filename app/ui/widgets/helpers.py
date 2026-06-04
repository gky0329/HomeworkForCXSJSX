from PySide6.QtWidgets import QLabel, QFrame, QVBoxLayout, QBoxLayout
from PySide6.QtGui import QFont, QFontMetricsF


def mlabel(text: str, color: str, size: int = 12, bold: bool = False) -> QLabel:
    weight = "bold" if bold else "normal"
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(
        f"color: {color}; font-size: {size}px; font-weight: {weight}; "
        f"background: transparent; border: none;"
    )
    return lbl


def clear_layout(layout: QBoxLayout):
    while layout.count():
        item = layout.takeAt(0)
        child_layout = item.layout()
        if child_layout is not None:
            clear_layout(child_layout)
            child_layout.deleteLater()
            continue

        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


def text_width(text: str, font: QFont) -> float:
    metrics = QFontMetricsF(font)
    lines = text.splitlines() or [text]
    return max(metrics.horizontalAdvance(line) for line in lines)


def build_code_block(code: str, text_color: str = "#D4D4D4",
                     bg_color: str = "#1E1E1E", border_color: str = "#3C3C3C") -> QFrame:
    frame = QFrame()
    frame.setObjectName("codeBlock")
    frame.setStyleSheet(
        f"QFrame#codeBlock {{ background-color: {bg_color}; border: 1px solid {border_color}; "
        f"padding: 6px; margin: 4px 0; }}"
        f"QFrame#codeBlock QLabel {{ border: none; background: transparent; outline: none; }}"
    )
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(6, 4, 6, 4)
    label = QLabel(code)
    label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 11))
    label.setStyleSheet(f"color: {text_color}; background: transparent; border: none;")
    label.setWordWrap(True)
    layout.addWidget(label)
    return frame
