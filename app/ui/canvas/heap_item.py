from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QGraphicsItem
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QFont, QColor, QPen, QBrush, QPainter, QFontMetricsF

from app.core.memory_model import HeapBlock
from app.ui.theme.colors import (
    HEAP_BORDER, HEAP_BG, HEAP_TEXT, EDGE_DANGLING, CANVAS_BG,
    STACK_VAR_TEXT, STACK_BORDER, EDGE_REF, WARN,
)
from app.ui.canvas.object_layout import (
    base_subobjects,
    derived_object_members,
    vtable_rows,
)
from app.ui.widgets.helpers import text_width


def _text_width(text: str, font: QFont) -> float:
    return text_width(text, font)


class HeapItem(QGraphicsRectItem):
    WIDTH = 100
    HEIGHT = 78
    RADIUS = 8
    OBJECT_SECTION_GAP = 8.0

    def __init__(self, block: HeapBlock, on_item_moved=None):
        super().__init__()
        self.block = block
        self.address = block.address
        self._on_item_moved = on_item_moved
        self._value_label = None
        self._array_cells: list[QGraphicsRectItem] = []
        self._array_value_labels: list[QGraphicsTextItem] = []
        self._array_index_labels: list[QGraphicsTextItem] = []
        self._text_items: list[QGraphicsTextItem] = []
        self._object_sections: list[dict[str, object]] = []
        self.member_items: dict[str, QGraphicsTextItem] = {}
        self.element_items: dict[str, QGraphicsRectItem] = {}

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
        self._array_cells.clear()
        self._array_value_labels.clear()
        self._array_index_labels.clear()
        self._text_items.clear()
        self._object_sections.clear()
        self.member_items.clear()
        self.element_items.clear()
        for child in list(self.childItems()):
            child.setParentItem(None)
            if child.scene() is not None:
                child.scene().removeItem(child)

    def _keep_text(self, item: QGraphicsTextItem) -> QGraphicsTextItem:
        self._text_items.append(item)
        return item

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

        self._addr_label = self._keep_text(QGraphicsTextItem(self))
        self._addr_label.setDefaultTextColor(QColor(HEAP_BORDER))
        self._addr_label.setFont(addr_font)
        self._addr_label.setPlainText(f"[{block.address}]")
        self._addr_label.setPos(4, 2)

        self._type_label = self._keep_text(QGraphicsTextItem(self))
        self._type_label.setDefaultTextColor(QColor(HEAP_TEXT))
        self._type_label.setFont(type_font)
        self._type_label.setPlainText(block.type)
        self._type_label.setPos(4, 18)

        self._value_label = self._keep_text(QGraphicsTextItem(self))
        self._value_label.setDefaultTextColor(QColor(HEAP_TEXT))
        self._value_label.setFont(value_font)
        self._value_label.setPlainText(block.value)
        self._value_label.setPos(4, 38)

        self._refresh_geometry()

    def _build_array(self, block: HeapBlock):
        value_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10, QFont.Weight.Bold)
        index_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 8)
        layout = self._array_layout_metrics(block, value_font, index_font)
        gap = 3
        cols = int(layout["cols"])
        rows = int(layout["rows"])
        cell_w = layout["cell_w"]
        cell_h = layout["cell_h"]
        row_h = layout["row_h"]
        top_y = layout["top_y"]
        w = max(80.0, layout["grid_w"], layout["title_w"])
        h = top_y + rows * row_h
        self.prepareGeometryChange()
        self.setRect(0, 0, w, h)

        self._addr_label = self._keep_text(QGraphicsTextItem(self))
        self._addr_label.setDefaultTextColor(QColor(HEAP_BORDER))
        self._addr_label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9, QFont.Weight.Bold))
        self._addr_label.setPlainText(f"[{block.address}] {block.type}")
        self._addr_label.setPos(4, 2)

        y = 20
        if block.container_size is not None and block.container_capacity is not None:
            sz_label = self._keep_text(QGraphicsTextItem(
                f"  size={block.container_size} cap={block.container_capacity}",
                self
            ))
            sz_label.setDefaultTextColor(QColor(WARN))
            sz_label.setFont(index_font)
            sz_label.setPos(4, y)
            y += QFontMetricsF(index_font).lineSpacing() + 2

        for elem in block.elements:
            row = elem.index // cols
            col = elem.index % cols
            x = 6 + col * (cell_w + gap)
            cy = y + row * row_h
            cell = QGraphicsRectItem(0, 0, cell_w, cell_h, self)
            cell.setPos(x, cy)
            cell.setPen(QPen(QColor(HEAP_BORDER), 1))
            cell.setBrush(QBrush(QColor(HEAP_BG)))
            self._array_cells.append(cell)
            if elem.address:
                self.element_items[elem.address] = cell

            value_label = self._keep_text(QGraphicsTextItem("", cell))
            value_label.setDefaultTextColor(QColor(STACK_VAR_TEXT))
            value_label.setFont(value_font)
            value_label.setPlainText(str(elem.value))
            self._array_value_labels.append(value_label)

            index_label = self._keep_text(QGraphicsTextItem("", cell))
            index_label.setDefaultTextColor(QColor(WARN))
            index_label.setFont(index_font)
            index_label.setPlainText(f"[{elem.index}]")
            self._array_index_labels.append(index_label)

            value_rect = value_label.boundingRect()
            index_rect = index_label.boundingRect()
            value_x = max(2.0, (cell_w - value_rect.width()) / 2.0)
            value_y = max(1.0, (cell_h - value_rect.height()) / 2.0 - 1.0)
            index_x = max(2.0, (cell_w - index_rect.width()) / 2.0)
            index_y = cell_h - index_rect.height() * 0.45
            value_label.setPos(value_x, value_y)
            index_label.setPos(index_x, index_y)
            self._value_label = value_label

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

    def _array_layout_metrics(self, block: HeapBlock, value_font: QFont, index_font: QFont) -> dict[str, int | float]:
        value_metrics = QFontMetricsF(value_font)
        index_metrics = QFontMetricsF(index_font)
        cols = max(1, min(len(block.elements), 4))
        rows = (len(block.elements) + cols - 1) // cols
        gap = 3.0

        max_value_w = 0.0
        max_index_w = 0.0
        for elem in block.elements:
            max_value_w = max(max_value_w, _text_width(str(elem.value), value_font))
            max_index_w = max(max_index_w, _text_width(f"[{elem.index}]", index_font))

        cell_w = max(28.0, max(max_value_w, max_index_w) + 10.0)
        cell_h = max(22.0, value_metrics.height() + 4.0)
        row_h = cell_h + index_metrics.height() + 2.0
        grid_w = cols * cell_w + max(0, cols - 1) * gap + 12.0
        title_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9, QFont.Weight.Bold)
        title_w = _text_width(f"[{block.address}] {block.type}", title_font) + 12.0

        top_y = 20.0
        if block.container_size is not None and block.container_capacity is not None:
            top_y += index_metrics.lineSpacing() + 2.0

        return {
            "cols": cols,
            "rows": rows,
            "cell_w": cell_w,
            "cell_h": cell_h,
            "row_h": row_h,
            "top_y": top_y,
            "grid_w": grid_w,
            "title_w": title_w,
        }

    def _build_struct(self, block: HeapBlock):
        font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10)
        member_h = QFontMetricsF(font).lineSpacing() + 6
        title_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9, QFont.Weight.Bold)
        members = list(block.members)
        w = max(
            _text_width(f"[{block.address}] {block.type}", title_font),
            max((_text_width(f"  .{m.name}: {m.type} = {m.value}", font) for m in members), default=0.0),
        ) + 12
        h = 24 + len(members) * member_h + 6
        self.prepareGeometryChange()
        self.setRect(0, 0, max(160, w), h)

        self._addr_label = self._keep_text(QGraphicsTextItem(self))
        self._addr_label.setDefaultTextColor(QColor(HEAP_BORDER))
        self._addr_label.setFont(title_font)
        self._addr_label.setPlainText(f"[{block.address}] {block.type}")
        self._addr_label.setPos(4, 2)

        title_bottom = 2 + self._addr_label.boundingRect().height() + 4

        for i, m in enumerate(members):
            label = self._keep_text(QGraphicsTextItem(
                f"  .{m.name}: {m.type} = {m.value}", self
            ))
            label.setDefaultTextColor(QColor(STACK_BORDER))
            label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10))
            label.setPos(6, title_bottom + i * member_h)
            if m.address:
                self.member_items[m.address] = label
            self._value_label = label

        self._refresh_geometry()

    def _make_object_section(self, color: str, items: list[QGraphicsTextItem]):
        rect = QGraphicsRectItem(self)
        rect.setPen(QPen(QColor(color), 1, Qt.PenStyle.DashLine))
        fill = QColor(color)
        fill.setAlpha(24)
        rect.setBrush(QBrush(fill))
        rect.setZValue(-0.75)
        self._object_sections.append({"rect": rect, "items": items})

    def _layout_object_sections(self):
        for section in self._object_sections:
            rect = section.get("rect")
            items = section.get("items")
            if not isinstance(rect, QGraphicsRectItem) or not isinstance(items, list) or not items:
                continue
            top = min(item.pos().y() for item in items)
            bottom = max(item.pos().y() + item.boundingRect().height() for item in items)
            left = min(item.pos().x() for item in items) - 4.0
            right = self.rect().width() - 6.0
            rect.setRect(left, top - 2.0, max(36.0, right - left), max(18.0, bottom - top + 4.0))

    def _build_object(self, block: HeapBlock):
        body_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9)
        member_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10)
        title_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9, QFont.Weight.Bold)
        body_line_h = max(QFontMetricsF(body_font).lineSpacing() + 2, 24.0)
        member_h = max(QFontMetricsF(member_font).lineSpacing() + 6, 26.0)
        derived_members = derived_object_members(block.base_classes, block.members)
        vtable = vtable_rows(block.class_name, block.type, block.base_classes, block.virtual_methods)
        base_parts = base_subobjects(block.base_classes, block.members)
        width_candidates = [
            _text_width(f"[{block.address}] {block.class_name or block.type}", title_font),
        ]
        if block.is_destroyed:
            width_candidates.append(_text_width("  💀 destroyed", body_font))
        elif block.is_constructed:
            width_candidates.append(_text_width("  ⚡ constructed", body_font))
        for base, member in base_parts:
            width_candidates.append(_text_width(f"  base subobject: {base}", body_font))
            state = member.value if member is not None and member.value else "<base layout>"
            width_candidates.append(_text_width(f"    contains {base} = {state}", body_font))
        if vtable:
            width_candidates.append(_text_width(f"  vptr -> {(block.class_name or block.type)} vtable", body_font))
            for row in vtable:
                width_candidates.append(_text_width(f"    {row}", body_font))
        if block.base_classes and derived_members:
            width_candidates.append(_text_width(f"  derived fields: {block.class_name or block.type}", body_font))
        for m in derived_members:
            width_candidates.append(_text_width(f"  .{m.name}: {m.type} = {m.value}", member_font))
        w = max(width_candidates) + 12
        extra_height = 0.0
        if block.is_destroyed or block.is_constructed:
            extra_height += body_line_h
        extra_height += len(base_parts) * body_line_h * 2
        if vtable:
            extra_height += body_line_h * (1 + len(vtable))
        if block.base_classes and derived_members:
            extra_height += body_line_h
        section_count = (
            len(base_parts)
            + (1 if vtable else 0)
            + (1 if block.base_classes and derived_members else 0)
        )
        h = 26 + extra_height + max(1, len(derived_members)) * member_h + 6
        h += section_count * self.OBJECT_SECTION_GAP
        self.prepareGeometryChange()
        self.setRect(0, 0, max(180, w), h)

        self._addr_label = self._keep_text(QGraphicsTextItem(self))
        self._addr_label.setDefaultTextColor(QColor(HEAP_BORDER))
        self._addr_label.setFont(title_font)
        self._addr_label.setPlainText(f"[{block.address}] {block.class_name or block.type}")
        self._addr_label.setPos(4, 2)

        y = 2 + self._addr_label.boundingRect().height() + 4
        if block.is_destroyed:
            badge = self._keep_text(QGraphicsTextItem("  💀 destroyed", self))
            badge.setDefaultTextColor(QColor(EDGE_DANGLING))
            badge.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9))
            badge.setPos(6, y)
            y += body_line_h
        elif block.is_constructed:
            badge = self._keep_text(QGraphicsTextItem("  ⚡ constructed", self))
            badge.setDefaultTextColor(QColor(EDGE_REF))
            badge.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9))
            badge.setPos(6, y)
            y += body_line_h

        for base, member in base_parts:
            section_items: list[QGraphicsTextItem] = []
            base_label = self._keep_text(QGraphicsTextItem(f"  base subobject: {base}", self))
            base_label.setDefaultTextColor(QColor(HEAP_TEXT))
            base_label.setFont(body_font)
            base_label.setPos(6, y)
            section_items.append(base_label)
            y += body_line_h

            state = member.value if member is not None and member.value else "<base layout>"
            state_label = self._keep_text(QGraphicsTextItem(f"    contains {base} = {state}", self))
            state_label.setDefaultTextColor(QColor(HEAP_TEXT))
            state_label.setFont(body_font)
            state_label.setPos(14, y)
            section_items.append(state_label)
            if member is not None and member.address:
                self.member_items[member.address] = state_label
            self._value_label = state_label
            y += body_line_h
            self._make_object_section(HEAP_TEXT, section_items)
            y += self.OBJECT_SECTION_GAP

        if vtable:
            section_items = []
            vl = self._keep_text(QGraphicsTextItem(f"  vptr -> {(block.class_name or block.type)} vtable", self))
            vl.setDefaultTextColor(QColor(WARN))
            vl.setFont(body_font)
            vl.setPos(6, y)
            section_items.append(vl)
            y += body_line_h
            for row in vtable:
                slot_label = self._keep_text(QGraphicsTextItem(f"    {row}", self))
                slot_label.setDefaultTextColor(QColor(WARN))
                slot_label.setFont(body_font)
                slot_label.setPos(14, y)
                section_items.append(slot_label)
                self._value_label = slot_label
                y += body_line_h
            self._make_object_section(WARN, section_items)
            y += self.OBJECT_SECTION_GAP

        derived_section_items: list[QGraphicsTextItem] = []
        if block.base_classes and derived_members:
            derived_label = self._keep_text(QGraphicsTextItem(f"  derived fields: {block.class_name or block.type}", self))
            derived_label.setDefaultTextColor(QColor(STACK_BORDER))
            derived_label.setFont(body_font)
            derived_label.setPos(6, y)
            derived_section_items.append(derived_label)
            y += body_line_h
            self._make_object_section(STACK_BORDER, derived_section_items)

        for m in derived_members:
            label = self._keep_text(QGraphicsTextItem(f"  .{m.name}: {m.type} = {m.value}", self))
            label.setDefaultTextColor(QColor(STACK_BORDER))
            label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10))
            label.setPos(6, y)
            if derived_section_items:
                derived_section_items.append(label)
            if m.address:
                self.member_items[m.address] = label
            self._value_label = label
            y += member_h
        if derived_section_items:
            y += self.OBJECT_SECTION_GAP

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
        value_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10, QFont.Weight.Bold)
        index_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 8)
        layout = self._array_layout_metrics(block, value_font, index_font)
        cols = int(layout["cols"])
        rows = int(layout["rows"])
        row_h = layout["row_h"]
        top_y = layout["top_y"]
        w = max(80.0, layout["grid_w"], layout["title_w"])
        h = top_y + rows * row_h
        self.prepareGeometryChange()
        self.setRect(0, 0, w, h)

    def _refresh_struct_geometry(self, block: HeapBlock):
        font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10)
        title_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9, QFont.Weight.Bold)
        members = list(block.members)
        member_h = QFontMetricsF(font).lineSpacing() + 6
        width = max(
            _text_width(f"[{block.address}] {block.type}", title_font),
            max((_text_width(f"  .{m.name}: {m.type} = {m.value}", font) for m in members), default=0.0),
        ) + 12
        height = 24 + len(members) * member_h + 6
        self.prepareGeometryChange()
        self.setRect(0, 0, max(160, width), height)

    def _refresh_object_geometry(self, block: HeapBlock):
        body_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9)
        member_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10)
        title_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9, QFont.Weight.Bold)
        body_line_h = max(QFontMetricsF(body_font).lineSpacing() + 2, 24.0)
        member_h = max(QFontMetricsF(member_font).lineSpacing() + 6, 26.0)
        derived_members = derived_object_members(block.base_classes, block.members)
        vtable = vtable_rows(block.class_name, block.type, block.base_classes, block.virtual_methods)
        base_parts = base_subobjects(block.base_classes, block.members)
        width_candidates = [
            _text_width(f"[{block.address}] {block.class_name or block.type}", title_font),
        ]
        if block.is_destroyed:
            width_candidates.append(_text_width("  💀 destroyed", body_font))
        elif block.is_constructed:
            width_candidates.append(_text_width("  ⚡ constructed", body_font))
        for base, member in base_parts:
            width_candidates.append(_text_width(f"  base subobject: {base}", body_font))
            state = member.value if member is not None and member.value else "<base layout>"
            width_candidates.append(_text_width(f"    contains {base} = {state}", body_font))
        if vtable:
            width_candidates.append(_text_width(f"  vptr -> {(block.class_name or block.type)} vtable", body_font))
            for row in vtable:
                width_candidates.append(_text_width(f"    {row}", body_font))
        if block.base_classes and derived_members:
            width_candidates.append(_text_width(f"  derived fields: {block.class_name or block.type}", body_font))
        for m in derived_members:
            width_candidates.append(_text_width(f"  .{m.name}: {m.type} = {m.value}", member_font))
        width = max(width_candidates) + 12
        extra_height = 0.0
        if block.is_destroyed or block.is_constructed:
            extra_height += body_line_h
        extra_height += len(base_parts) * body_line_h * 2
        if vtable:
            extra_height += body_line_h * (1 + len(vtable))
        if block.base_classes and derived_members:
            extra_height += body_line_h
        section_count = (
            len(base_parts)
            + (1 if vtable else 0)
            + (1 if block.base_classes and derived_members else 0)
        )
        height = 26 + extra_height + max(1, len(derived_members)) * member_h + 6
        height += section_count * self.OBJECT_SECTION_GAP
        self.prepareGeometryChange()
        self.setRect(0, 0, max(180, width), height)
        self._layout_object_sections()

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
        if (
            not self.block.is_array
            and not self.block.members
            and not self.block.is_object
            and hasattr(self, '_value_label')
            and self._value_label is not None
        ):
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
