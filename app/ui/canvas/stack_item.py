from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QGraphicsItem
from PySide6.QtCore import QPointF
from PySide6.QtGui import QFont, QColor, QPen, QBrush

from app.core.memory_model import Variable, StackFrame
from app.ui.theme.colors import (
    STACK_BORDER, STACK_BG, STACK_TITLE, STACK_VAR_TEXT,
)


class VarItem(QGraphicsTextItem):
    def __init__(self, variable: Variable, parent=None):
        super().__init__(parent)
        self.variable = variable
        self.address = variable.address
        self.setDefaultTextColor(QColor(STACK_VAR_TEXT))
        self.setFont(QFont("JetBrains Mono", 11))
        self._update_text()

    def _update_text(self):
        self.setPlainText(
            f"  {self.variable.name}: {self.variable.type} = {self.variable.value}"
        )

    def update_value(self, new_value: str):
        self.variable.value = new_value
        self._update_text()


class StackItem(QGraphicsRectItem):
    TITLE_HEIGHT = 24
    VAR_HEIGHT = 22
    PADDING = 8
    MIN_WIDTH = 160

    def __init__(self, frame: StackFrame, on_item_moved=None):
        super().__init__()
        self.frame = frame
        self.var_items: dict[str, VarItem] = {}
        self._on_item_moved = on_item_moved

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        self.setPen(QPen(QColor(STACK_BORDER), 1.5))
        self.setBrush(QBrush(QColor(STACK_BG)))

        self._title_item = QGraphicsTextItem(self)
        self._title_item.setDefaultTextColor(QColor(STACK_TITLE))
        self._title_item.setFont(QFont("JetBrains Mono", 11, QFont.Weight.Bold))

        self._build(frame)

    def _build(self, frame: StackFrame):
        for var in frame.variables:
            item = VarItem(var, self)
            item.setPos(
                self.PADDING,
                self.TITLE_HEIGHT + len(self.var_items) * self.VAR_HEIGHT,
            )
            self.var_items[var.address] = item

        self._title_item.setPlainText(frame.frame_name)
        self._title_item.setPos(self.PADDING, 2)

        width = self._calc_width(frame)
        height = (
            self.TITLE_HEIGHT + max(1, len(frame.variables)) * self.VAR_HEIGHT + 4
        )
        self.setRect(0, 0, width, height)

    def _calc_width(self, frame: StackFrame) -> float:
        max_text = frame.frame_name
        for var in frame.variables:
            text = f"  {var.name}: {var.type} = {var.value}"
            if len(text) > len(max_text):
                max_text = text
        return max(self.MIN_WIDTH, len(max_text) * 8 + self.PADDING * 2)

    def get_var_item(self, address: str) -> VarItem | None:
        return self.var_items.get(address)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if self._on_item_moved:
                self._on_item_moved(self)
        return super().itemChange(change, value)
