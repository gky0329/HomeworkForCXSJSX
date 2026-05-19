from PySide6.QtWidgets import QLabel, QBoxLayout


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
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
