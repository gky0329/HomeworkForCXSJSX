from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QGraphicsItem
from PySide6.QtCore import QPointF
from PySide6.QtGui import QFont, QColor, QPen, QBrush

from app.core.memory_model import Variable, StackFrame
from app.ui.theme.colors import (
    STACK_BORDER, STACK_BG, STACK_TITLE, STACK_VAR_TEXT,
    HEAP_BORDER, HEAP_BG,
)


class VarItem(QGraphicsTextItem):
    def __init__(self, variable: Variable, parent=None):
        super().__init__(parent)
        self.variable = variable
        self.address = variable.address
        self.setDefaultTextColor(QColor(STACK_VAR_TEXT))
        self.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 11))
        self._update_text()

    def _update_text(self):
        v = self.variable
        if v.is_array and v.elements:
            items = [e.value for e in v.elements]
            self.setPlainText(
                f"  {v.name}: {v.type} = [{', '.join(items)}]"
            )
        elif v.members:
            items = [f"{m.name}={m.value}" for m in v.members]
            self.setPlainText(
                f"  {v.name}: {v.type} = {{{', '.join(items)}}}"
            )
        else:
            self.setPlainText(
                f"  {v.name}: {v.type} = {v.value}"
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
        self._array_cells: list[QGraphicsRectItem] = []

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        self.setPen(QPen(QColor(STACK_BORDER), 1.5))
        self.setBrush(QBrush(QColor(STACK_BG)))

        self._title_item = QGraphicsTextItem(self)
        self._title_item.setDefaultTextColor(QColor(STACK_TITLE))
        self._title_item.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 11, QFont.Weight.Bold))

        self._build(frame)

    def _build(self, frame: StackFrame):
        y_offset = self.TITLE_HEIGHT
        for var in frame.variables:
            item = VarItem(var, self)
            item.setPos(self.PADDING, y_offset)
            self.var_items[var.address] = item
            y_offset += self.VAR_HEIGHT

            if var.is_array and var.elements:
                y_offset = self._draw_array_cells(var, y_offset)
            elif var.members:
                y_offset = self._draw_struct_members(var, y_offset)

        self._title_item.setPlainText(frame.frame_name)
        self._title_item.setPos(self.PADDING, 2)

        width = self._calc_width(frame)
        height = y_offset + 4
        self.setRect(0, 0, width, height)

    def _draw_array_cells(self, var: Variable, start_y: float) -> float:
        cell_w = 32
        cell_h = 20
        gap = 2
        x = self.PADDING + 16
        y = start_y
        self._array_cells.clear()
        for elem in var.elements:
            cell = QGraphicsRectItem(x, y, cell_w, cell_h, self)
            cell.setPen(QPen(QColor(HEAP_BORDER), 1))
            cell.setBrush(QBrush(QColor(HEAP_BG)))
            label = QGraphicsTextItem(f"[{elem.index}] {elem.value}", cell)
            label.setDefaultTextColor(QColor(STACK_VAR_TEXT))
            label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9))
            label.setPos(2, 1)
            self._array_cells.append(cell)
            x += cell_w + gap
        return y + cell_h + 4

    def _draw_struct_members(self, var: Variable, start_y: float) -> float:
        y = start_y
        for m in var.members:
            label = QGraphicsTextItem(
                f"    .{m.name}: {m.type} = {m.value}", self
            )
            label.setDefaultTextColor(QColor("#9CDCFE"))
            label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10))
            label.setPos(self.PADDING + 16, y)
            y += 18
        return y

    def _calc_width(self, frame: StackFrame) -> float:
        max_text = frame.frame_name
        for var in frame.variables:
            if var.is_array and var.elements:
                w = (len(var.elements) * 34) + self.PADDING * 2 + 16
                if w > max_text:
                    max_text = "x" * int(w / 8)
            elif var.members:
                for m in var.members:
                    text = f"    .{m.name}: {m.type} = {m.value}"
                    if len(text) > len(max_text):
                        max_text = text
            else:
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
