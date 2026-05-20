from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QGraphicsItem
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QFont, QColor, QPen, QBrush, QPainter

from app.core.memory_model import HeapBlock
from app.ui.theme.colors import (
    HEAP_BORDER, HEAP_BG, HEAP_TEXT, EDGE_DANGLING, CANVAS_BG,
    STACK_VAR_TEXT,
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
        self._value_label = None

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        self._rebuild_cells()

    def _rebuild_cells(self):
        block = self.block

        if block.is_object:
            self._build_object(block)
        elif block.is_array and block.elements:
            self._build_array(block)
        elif block.members:
            self._build_struct(block)
        else:
            self._build_plain(block)

    def _build_plain(self, block: HeapBlock):
        self.setRect(0, 0, self.WIDTH, self.HEIGHT)

        self._addr_label = QGraphicsTextItem(self)
        self._addr_label.setDefaultTextColor(QColor(HEAP_BORDER))
        self._addr_label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9, QFont.Weight.Bold))
        self._addr_label.setPlainText(f"[{block.address}]")
        self._addr_label.setPos(4, 2)

        self._type_label = QGraphicsTextItem(self)
        self._type_label.setDefaultTextColor(QColor(HEAP_TEXT))
        self._type_label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10))
        self._type_label.setPlainText(block.type)
        self._type_label.setPos(4, 18)

        self._value_label = QGraphicsTextItem(self)
        self._value_label.setDefaultTextColor(QColor(HEAP_TEXT))
        self._value_label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 11, QFont.Weight.Bold))
        self._value_label.setPlainText(block.value)
        self._value_label.setPos(4, 38)

    def _build_array(self, block: HeapBlock):
        cell_w = 36
        cell_h = 28
        gap = 3
        cols = max(1, min(len(block.elements), 4))
        n = len(block.elements)
        extra_label_h = 0
        if block.container_size is not None and block.container_capacity is not None:
            extra_label_h = 14
        rows = (n + cols - 1) // cols
        w = max(80, cols * (cell_w + gap) + 10)
        self.setRect(0, 0, w, cell_h * rows + 24 + extra_label_h)

        self._addr_label = QGraphicsTextItem(self)
        self._addr_label.setDefaultTextColor(QColor(HEAP_BORDER))
        self._addr_label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9, QFont.Weight.Bold))
        self._addr_label.setPlainText(f"[{block.address}] {block.type}")
        self._addr_label.setPos(4, 2)

        y = 20
        if block.container_size is not None and block.container_capacity is not None:
            sz_label = QGraphicsTextItem(
                f"  size={block.container_size} cap={block.container_capacity}",
                self
            )
            sz_label.setDefaultTextColor(QColor("#DCDCAA"))
            sz_label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 8))
            sz_label.setPos(4, y)
            y += 14

        for elem in block.elements:
            row = elem.index // cols
            col = elem.index % cols
            x = 6 + col * (cell_w + gap)
            cy = y + row * cell_h
            cell = QGraphicsRectItem(x, cy, cell_w, cell_h, self)
            cell.setPen(QPen(QColor(HEAP_BORDER), 1))
            cell.setBrush(QBrush(QColor("#4A3626")))
            label = QGraphicsTextItem(f"[{elem.index}]\n{elem.value}", cell)
            label.setDefaultTextColor(QColor(STACK_VAR_TEXT))
            label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 8))
            label.setPos(2, 1)

    def _build_struct(self, block: HeapBlock):
        member_h = 20
        w = 160
        h = 24 + len(block.members) * member_h + 6
        self.setRect(0, 0, w, h)

        self._addr_label = QGraphicsTextItem(self)
        self._addr_label.setDefaultTextColor(QColor(HEAP_BORDER))
        self._addr_label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9, QFont.Weight.Bold))
        self._addr_label.setPlainText(f"[{block.address}] {block.type}")
        self._addr_label.setPos(4, 2)

        for i, m in enumerate(block.members):
            label = QGraphicsTextItem(
                f"  .{m.name}: {m.type} = {m.value}", self
            )
            label.setDefaultTextColor(QColor("#9CDCFE"))
            label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10))
            label.setPos(6, 20 + i * member_h)
            self._value_label = label

    def _build_object(self, block: HeapBlock):
        extra_lines = 0
        if block.is_destroyed:
            extra_lines += 1
        elif block.is_constructed:
            extra_lines += 1
        if block.base_classes:
            extra_lines += 1
        if block.virtual_methods:
            extra_lines += 1
        n_members = len([m for m in block.members if m.name != "_vptr"])
        member_h = 18
        w = 180
        h = 26 + extra_lines * 16 + max(1, n_members) * member_h + 6
        self.setRect(0, 0, w, h)

        self._addr_label = QGraphicsTextItem(self)
        self._addr_label.setDefaultTextColor(QColor(HEAP_BORDER))
        self._addr_label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9, QFont.Weight.Bold))
        self._addr_label.setPlainText(f"[{block.address}] {block.class_name or block.type}")
        self._addr_label.setPos(4, 2)

        y = 20
        if block.is_destroyed:
            badge = QGraphicsTextItem("  💀 destroyed", self)
            badge.setDefaultTextColor(QColor(EDGE_DANGLING))
            badge.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9))
            badge.setPos(6, y)
            y += 16
        elif block.is_constructed:
            badge = QGraphicsTextItem("  ⚡ constructed", self)
            badge.setDefaultTextColor(QColor("#4EC9B0"))
            badge.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9))
            badge.setPos(6, y)
            y += 16
        if block.base_classes:
            bl = QGraphicsTextItem(f"  ⬆ extends {', '.join(block.base_classes)}", self)
            bl.setDefaultTextColor(QColor("#CE9178"))
            bl.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9))
            bl.setPos(6, y)
            y += 16

        if block.virtual_methods:
            vl = QGraphicsTextItem(f"  [vtable] {' '.join(block.virtual_methods)}", self)
            vl.setDefaultTextColor(QColor("#DCDCAA"))
            vl.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9))
            vl.setPos(6, y)
            y += 16

        for m in block.members:
            if m.name == "_vptr":
                continue
            label = QGraphicsTextItem(f"  .{m.name}: {m.type} = {m.value}", self)
            label.setDefaultTextColor(QColor("#9CDCFE"))
            label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10))
            label.setPos(6, y)
            y += member_h

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
        if hasattr(self, '_value_label') and self._value_label is not None:
            self._value_label.setPlainText(new_value)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if self._on_item_moved:
                self._on_item_moved(self)
        return super().itemChange(change, value)
