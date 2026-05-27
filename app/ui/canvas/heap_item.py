from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QGraphicsItem
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QFont, QColor, QPen, QBrush, QPainter, QFontMetricsF

from app.core.memory_model import HeapBlock
from app.ui.theme.colors import (
    HEAP_BORDER, HEAP_BG, HEAP_TEXT, EDGE_DANGLING, CANVAS_BG,
    STACK_VAR_TEXT,
)


def _text_width(text: str, font: QFont) -> float:
    metrics = QFontMetricsF(font)
    lines = text.splitlines() or [text]
    return max(metrics.horizontalAdvance(line) for line in lines)


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
        self._clear_children()
        block = self.block

        if block.is_object:
            self._build_object(block)
        elif block.is_array and block.elements:
            self._build_array(block)
        elif block.members:
            self._build_struct(block)
        else:
            self._build_plain(block)

    def _clear_children(self):
        for child in list(self.childItems()):
            child.setParentItem(None)
            if child.scene() is not None:
                child.scene().removeItem(child)

    def update_block(self, block: HeapBlock):
        self.block = block
        self.address = block.address
        self._value_label = None
        # Restore visibility in case a previous "freed" animation faded this item out.
        self.setOpacity(1.0)
        self._rebuild_cells()
        if self._on_item_moved:
            try:
                self._on_item_moved(self, 'resize')
            except TypeError:
                self._on_item_moved(self)

    def _build_plain(self, block: HeapBlock):
        addr_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9, QFont.Weight.Bold)
        type_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10)
        value_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 11, QFont.Weight.Bold)
        width = max(
            _text_width(f"[{block.address}]", addr_font),
            _text_width(block.type, type_font),
            _text_width(block.value, value_font),
        ) + 12
        height = 58
        self.prepareGeometryChange()
        self.setRect(0, 0, max(self.WIDTH, width), max(self.HEIGHT, height))

        self._addr_label = QGraphicsTextItem(self)
        self._addr_label.setDefaultTextColor(QColor(HEAP_BORDER))
        self._addr_label.setFont(addr_font)
        self._addr_label.setPlainText(f"[{block.address}]")
        self._addr_label.setPos(4, 2)

        self._type_label = QGraphicsTextItem(self)
        self._type_label.setDefaultTextColor(QColor(HEAP_TEXT))
        self._type_label.setFont(type_font)
        self._type_label.setPlainText(block.type)
        self._type_label.setPos(4, 18)

        self._value_label = QGraphicsTextItem(self)
        self._value_label.setDefaultTextColor(QColor(HEAP_TEXT))
        self._value_label.setFont(value_font)
        self._value_label.setPlainText(block.value)
        self._value_label.setPos(4, 38)

        self._refresh_geometry()

    def _build_array(self, block: HeapBlock):
        cell_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 8)
        metrics = QFontMetricsF(cell_font)
        gap = 3
        cols = max(1, min(len(block.elements), 4))
        n = len(block.elements)
        extra_label_h = 0.0
        if block.container_size is not None and block.container_capacity is not None:
            extra_label_h = metrics.lineSpacing() + 2
        rows = (n + cols - 1) // cols
        cell_w = self._array_cell_width(block, cell_font)
        cell_h = self._array_cell_height(block, cell_font)
        w = max(80, cols * (cell_w + gap) + 10)
        h = cell_h * rows + 24 + extra_label_h
        self.prepareGeometryChange()
        self.setRect(0, 0, w, h)

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
            sz_label.setFont(cell_font)
            sz_label.setPos(4, y)
            y += metrics.lineSpacing() + 2

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
            label.setFont(cell_font)
            label.setPos(2, 1)

        self._refresh_geometry()

    def _array_cell_width(self, block: HeapBlock, font: QFont) -> float:
        max_width = 0.0
        for elem in block.elements:
            max_width = max(max_width, _text_width(f"[{elem.index}]", font))
            max_width = max(max_width, _text_width(elem.value, font))
        return max(36.0, max_width + 10.0)

    def _array_cell_height(self, block: HeapBlock, font: QFont) -> float:
        metrics = QFontMetricsF(font)
        line_count = 2 if block.elements else 1
        return max(28.0, metrics.lineSpacing() * line_count + 8.0)

    def _build_struct(self, block: HeapBlock):
        member_h = 20
        font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10)
        w = max(
            _text_width(f"[{block.address}] {block.type}", QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9, QFont.Weight.Bold)),
            max((_text_width(f"  .{m.name}: {m.type} = {m.value}", font) for m in block.members), default=0.0),
        ) + 12
        h = 24 + len(block.members) * member_h + 6
        self.prepareGeometryChange()
        self.setRect(0, 0, max(160, w), h)

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

        self._refresh_geometry()

    def _build_object(self, block: HeapBlock):
        body_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9)
        member_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10)
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
        width_candidates = [
            _text_width(f"[{block.address}] {block.class_name or block.type}", QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9, QFont.Weight.Bold)),
        ]
        if block.is_destroyed:
            width_candidates.append(_text_width("  💀 destroyed", body_font))
        elif block.is_constructed:
            width_candidates.append(_text_width("  ⚡ constructed", body_font))
        if block.base_classes:
            width_candidates.append(_text_width(f"  ⬆ extends {', '.join(block.base_classes)}", body_font))
        if block.virtual_methods:
            width_candidates.append(_text_width(f"  [vtable] {' '.join(block.virtual_methods)}", body_font))
        for m in block.members:
            if m.name == "_vptr":
                continue
            width_candidates.append(_text_width(f"  .{m.name}: {m.type} = {m.value}", member_font))
        w = max(width_candidates) + 12
        h = 26 + extra_lines * 16 + max(1, n_members) * member_h + 6
        self.prepareGeometryChange()
        self.setRect(0, 0, max(180, w), h)

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

        self._refresh_geometry()

    def _refresh_geometry(self):
        block = self.block
        if block.is_object:
            self._refresh_object_geometry(block)
        elif block.is_array and block.elements:
            self._refresh_array_geometry(block)
        elif block.members:
            self._refresh_struct_geometry(block)
        else:
            self._refresh_plain_geometry(block)
        self._clamp_within_scene()

    def _clamp_within_scene(self):
        scene = self.scene()
        if scene is None:
            return

        scene_rect = scene.sceneRect()
        item_rect = self.boundingRect()
        current = self.pos()
        max_x = max(scene_rect.left(), scene_rect.right() - item_rect.width())
        max_y = max(scene_rect.top(), scene_rect.bottom() - item_rect.height())
        clamped = QPointF(
            min(max(current.x(), scene_rect.left()), max_x),
            min(max(current.y(), scene_rect.top()), max_y),
        )
        if clamped != current:
            self.setPos(clamped)

    def visual_bounds(self):
        """Return the full visual bounds of this heap block, including child items."""
        bounds = self.mapRectToParent(self.rect())
        for child in self.childItems():
            try:
                child_bounds = child.mapToParent(child.boundingRect()).boundingRect()
                bounds = bounds.united(child_bounds)
            except Exception:
                continue
        return bounds

    def _refresh_plain_geometry(self, block: HeapBlock):
        addr_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9, QFont.Weight.Bold)
        type_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10)
        value_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 11, QFont.Weight.Bold)
        width = max(
            _text_width(f"[{block.address}]", addr_font),
            _text_width(block.type, type_font),
            _text_width(self._value_label.toPlainText() if self._value_label else block.value, value_font),
        ) + 12
        height = 58
        self.prepareGeometryChange()
        self.setRect(0, 0, max(self.WIDTH, width), max(self.HEIGHT, height))

    def _refresh_array_geometry(self, block: HeapBlock):
        font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 8)
        metrics = QFontMetricsF(font)
        cell_w = self._array_cell_width(block, font)
        cell_h = self._array_cell_height(block, font)
        cols = max(1, min(len(block.elements), 4))
        rows = (len(block.elements) + cols - 1) // cols
        extra_label_h = metrics.lineSpacing() + 2 if block.container_size is not None and block.container_capacity is not None else 0.0
        w = max(80, cols * (cell_w + 3) + 10)
        h = cell_h * rows + 24 + extra_label_h
        self.prepareGeometryChange()
        self.setRect(0, 0, w, h)

    def _refresh_struct_geometry(self, block: HeapBlock):
        font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10)
        width = max(
            _text_width(f"[{block.address}] {block.type}", QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9, QFont.Weight.Bold)),
            max((_text_width(f"  .{m.name}: {m.type} = {m.value}", font) for m in block.members), default=0.0),
        ) + 12
        height = 24 + len(block.members) * 20 + 6
        self.prepareGeometryChange()
        self.setRect(0, 0, max(160, width), height)

    def _refresh_object_geometry(self, block: HeapBlock):
        body_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9)
        member_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10)
        width_candidates = [
            _text_width(f"[{block.address}] {block.class_name or block.type}", QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9, QFont.Weight.Bold)),
        ]
        if block.is_destroyed:
            width_candidates.append(_text_width("  💀 destroyed", body_font))
        elif block.is_constructed:
            width_candidates.append(_text_width("  ⚡ constructed", body_font))
        if block.base_classes:
            width_candidates.append(_text_width(f"  ⬆ extends {', '.join(block.base_classes)}", body_font))
        if block.virtual_methods:
            width_candidates.append(_text_width(f"  [vtable] {' '.join(block.virtual_methods)}", body_font))
        for m in block.members:
            if m.name == "_vptr":
                continue
            width_candidates.append(_text_width(f"  .{m.name}: {m.type} = {m.value}", member_font))
        width = max(width_candidates) + 12
        n_members = len([m for m in block.members if m.name != "_vptr"])
        extra_lines = 0
        if block.is_destroyed or block.is_constructed:
            extra_lines += 1
        if block.base_classes:
            extra_lines += 1
        if block.virtual_methods:
            extra_lines += 1
        height = 26 + extra_lines * 16 + max(1, n_members) * 18 + 6
        self.prepareGeometryChange()
        self.setRect(0, 0, max(180, width), height)

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
        self._refresh_geometry()
        if self._on_item_moved:
            try:
                self._on_item_moved(self, 'resize')
            except TypeError:
                self._on_item_moved(self)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            scene = self.scene()
            if scene is not None:
                rect = scene.sceneRect()
                item_rect = self.boundingRect()
                min_x = rect.left()
                min_y = rect.top()
                max_x = max(rect.left(), rect.right() - item_rect.width())
                max_y = max(rect.top(), rect.bottom() - item_rect.height())
                value = QPointF(
                    min(max(value.x(), min_x), max_x),
                    min(max(value.y(), min_y), max_y),
                )
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if self._on_item_moved:
                self._on_item_moved(self)
        return super().itemChange(change, value)
