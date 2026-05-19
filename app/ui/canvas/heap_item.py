from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QGraphicsItem
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QFont, QColor, QPen, QBrush, QPainter

from app.core.memory_model import HeapBlock
from app.ui.theme.colors import (
    HEAP_BORDER, HEAP_BG, HEAP_TEXT, EDGE_DANGLING, CANVAS_BG,
)


class HeapItem(QGraphicsRectItem):
    WIDTH = 100
    HEIGHT = 78
    RADIUS = 8

    def __init__(self, block: HeapBlock, on_item_moved=None):
        super().__init__()
        self.block = block
        self.address = block.address
        self._on_item_moved = on_item_moved

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        self.setRect(0, 0, self.WIDTH, self.HEIGHT)

        self._addr_label = QGraphicsTextItem(self)
        self._addr_label.setDefaultTextColor(QColor(HEAP_BORDER))
        self._addr_label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9, QFont.Weight.Bold))

        self._type_label = QGraphicsTextItem(self)
        self._type_label.setDefaultTextColor(QColor(HEAP_TEXT))
        self._type_label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10))

        self._value_label = QGraphicsTextItem(self)
        self._value_label.setDefaultTextColor(QColor(HEAP_TEXT))
        self._value_label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 11, QFont.Weight.Bold))

        self._rebuild_labels()

    def _rebuild_labels(self):
        self._addr_label.setPlainText(f"[{self.block.address}]")
        self._addr_label.setPos(4, 2)
        self._type_label.setPlainText(self.block.type)
        self._type_label.setPos(4, 18)
        self._value_label.setPlainText(self.block.value)
        self._value_label.setPos(4, 38)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.block.is_freed:
            pen = QPen(QColor(EDGE_DANGLING), 2, Qt.PenStyle.DashLine)
            brush = QBrush(QColor(CANVAS_BG))
        else:
            pen = QPen(QColor(HEAP_BORDER), 1.5)
            brush = QBrush(QColor(HEAP_BG))

        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawRoundedRect(self.rect(), self.RADIUS, self.RADIUS)

    def update_value(self, new_value: str):
        self.block.value = new_value
        self._value_label.setPlainText(new_value)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if self._on_item_moved:
                self._on_item_moved(self)
        return super().itemChange(change, value)
