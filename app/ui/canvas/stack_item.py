from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QGraphicsItem
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QFont, QColor, QPen, QBrush, QFontMetricsF

from app.core.memory_model import Variable, StackFrame
from app.ui.theme.colors import (
    STACK_BORDER, STACK_BG, STACK_TITLE, STACK_VAR_TEXT,
    HEAP_BORDER, HEAP_BG, EDGE_DANGLING,
)


def _text_width(text: str, font: QFont) -> float:
    metrics = QFontMetricsF(font)
    lines = text.splitlines() or [text]
    return max(metrics.horizontalAdvance(line) for line in lines)


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
        badges = []
        if v.is_destroyed:
            badges.append("💀 destroyed")
        elif v.is_constructed:
            badges.append("⚡ constructed")
        if v.is_temporary:
            badges.append("⏳ temporary")
        badge_str = f" [{', '.join(badges)}]" if badges else ""

        if v.is_reference:
            self.setPlainText(
                f"  &{v.name}: {v.type} → {v.value}"
            )
        elif v.is_function_object:
            caps = [f"{'&' if c.by_ref else ''}{c.name}={c.value}" for c in v.captures]
            self.setPlainText(
                f"  {v.name}: λ = [{', '.join(caps)}]{badge_str}" if caps else f"  {v.name}: λ{badge_str}"
            )
        elif v.is_object:
            bases = f" : {', '.join(v.base_classes)}" if v.base_classes else ""
            self.setPlainText(
                f"  {v.name}: {v.class_name or v.type}{bases}{badge_str}"
            )
        elif v.is_array and v.elements:
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
                f"  {v.name}: {v.type} = {v.value}{badge_str}"
            )

    def update_value(self, new_value: str):
        self.variable.value = new_value
        self._update_text()
        parent = self.parentItem()
        if parent is not None and hasattr(parent, "refresh_geometry"):
            parent.refresh_geometry()


class StackItem(QGraphicsRectItem):
    TITLE_HEIGHT = 24
    VAR_HEIGHT = 22
    PADDING = 8
    MIN_WIDTH = 160

    def __init__(self, frame: StackFrame, on_item_moved=None):
        super().__init__()
        self.frame = frame
        self.var_items: dict[str, VarItem] = {}
        self._layout_items: list[QGraphicsTextItem] = []
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
        # record layout order for text items so we can reflow/wrap on resize
        self._layout_items.clear()
        y_offset = self.TITLE_HEIGHT
        for var in frame.variables:
            item = VarItem(var, self)
            item.setPos(self.PADDING, y_offset)
            self._layout_items.append(item)
            self.var_items[var.address] = item
            y_offset += self.VAR_HEIGHT

            if var.is_object:
                y_offset = self._draw_object(var, y_offset)
            elif var.is_function_object:
                y_offset = self._draw_function_object(var, y_offset)
            elif var.is_array and var.elements:
                y_offset = self._draw_array_cells(var, y_offset)
            elif var.members:
                y_offset = self._draw_struct_members(var, y_offset)

        self._title_item.setPlainText(frame.frame_name)
        self._title_item.setPos(self.PADDING, 2)
        self._layout_items.insert(0, self._title_item)

        self.refresh_geometry()

        if any(v.is_temporary for v in frame.variables):
            self.setPen(QPen(QColor("#DCDCAA"), 1.5, Qt.PenStyle.DashLine))

    def _clear_children(self):
        for child in list(self.childItems()):
            child.setParentItem(None)
            if child.scene() is not None:
                child.scene().removeItem(child)

    def update_frame(self, frame: StackFrame):
        self.frame = frame
        self.var_items = {}
        self._layout_items = []
        self._array_cells = []
        self._clear_children()

        self._title_item = QGraphicsTextItem(self)
        self._title_item.setDefaultTextColor(QColor(STACK_TITLE))
        self._title_item.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 11, QFont.Weight.Bold))

        self._build(frame)

    def refresh_geometry(self):
        # First, compute a baseline width from heuristics
        heuristic_w = self._calc_width(self.frame)

        # Measure required width using font metrics per-item (avoid document().size() which
        # can be affected by setTextWidth). Record natural widths so we can decide
        # later whether wrapping is needed per-item (only wrap if natural width > avail).
        required_right = 0.0
        natural_w: dict[QGraphicsTextItem, float] = {}
        for item in self._layout_items:
            try:
                text = item.toPlainText()
                font = item.font()
                # account for leading-space indentation which may not be preserved
                # by document().size(), so add explicit space-widths
                metrics = QFontMetricsF(font)
                stripped = text.lstrip(' ')
                leading = len(text) - len(stripped)
                stripped_w = _text_width(stripped or text, font)
                space_w = metrics.horizontalAdvance(' ')
                w = stripped_w + leading * space_w
            except Exception:
                w = 0.0
            natural_w[item] = w
            try:
                x = item.pos().x()
            except Exception:
                x = self.PADDING
            required_right = max(required_right, x + w)

        width = max(self.MIN_WIDTH, required_right + self.PADDING)
        width = max(width, heuristic_w)

        # Add a small horizontal buffer equal to two space characters to avoid
        # measurements that are just barely too small (accounts for font spacing).
        try:
            base_font = self._title_item.font() if hasattr(self, '_title_item') else QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10)
            sp_w = QFontMetricsF(base_font).horizontalAdvance(' ')
            width += sp_w * 2.0
        except Exception:
            pass

        # Now set final text widths: if the natural width fits, disable wrapping (0);
        # otherwise set available width so the item wraps.
        for item in list(self._layout_items):
            try:
                child_x = item.pos().x()
            except Exception:
                child_x = self.PADDING
            nat = natural_w.get(item, 0.0)
            # ensure available width is at least the natural width to avoid wrapping per-character
            avail = max(20.0, width - child_x - self.PADDING, nat)
            try:
                item.setTextWidth(avail)
            except Exception:
                pass

        # Recompute vertical layout based on actual document heights
        y = self.TITLE_HEIGHT
        for item in self._layout_items:
            if item is self._title_item:
                item.setPos(self.PADDING, 2)
                continue
            h = self.VAR_HEIGHT
            try:
                h = item.document().size().height()
            except Exception:
                h = self.VAR_HEIGHT
            item.setPos(item.pos().x(), y)
            y += max(h, self.VAR_HEIGHT) + 4

        total_h = y + 4
        self.prepareGeometryChange()
        self.setRect(0, 0, width, total_h)
        self._clamp_within_scene()
        if self._on_item_moved:
            try:
                self._on_item_moved(self, 'resize')
            except TypeError:
                # fallback for older callbacks that don't accept cause
                self._on_item_moved(self)

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
        """Return the full visual bounds of this stack frame, including child text.

        This can be larger than the frame rect when text extends beyond the box.
        """
        bounds = self.mapRectToParent(self.rect())
        for child in self.childItems():
            try:
                child_bounds = child.mapToParent(child.boundingRect()).boundingRect()
                bounds = bounds.united(child_bounds)
            except Exception:
                continue
        return bounds

    def _calc_height(self, frame: StackFrame) -> float:
        y_offset = self.TITLE_HEIGHT
        for var in frame.variables:
            y_offset += self.VAR_HEIGHT
            if var.is_object:
                y_offset = self._object_height(var, y_offset)
            elif var.is_function_object:
                y_offset = self._function_object_height(var, y_offset)
            elif var.is_array and var.elements:
                y_offset = self._array_height(var, y_offset)
            elif var.members:
                y_offset = self._struct_height(var, y_offset)
        return y_offset + 4

    def _object_height(self, var: Variable, y_offset: float) -> float:
        y = y_offset
        if var.is_destroyed or var.is_constructed or var.is_temporary or var.base_classes or var.virtual_methods:
            y += 16 * sum(
                1 for flag in [
                    var.is_destroyed or var.is_constructed,
                    var.is_temporary,
                    bool(var.base_classes),
                    bool(var.virtual_methods),
                ] if flag
            )
        y += 18 * len([m for m in var.members if m.name != "_vptr"])
        return y

    def _function_object_height(self, var: Variable, y_offset: float) -> float:
        return y_offset + 16 * (1 + len(var.captures))

    def _array_height(self, var: Variable, y_offset: float) -> float:
        cell_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9)
        metrics = QFontMetricsF(cell_font)
        lines = max(1, max(len(elem.value.splitlines() or [elem.value]) for elem in var.elements))
        return y_offset + max(20.0, metrics.lineSpacing() * lines + 6)

    def _struct_height(self, var: Variable, y_offset: float) -> float:
        return y_offset + 18 * len(var.members)

    def _draw_array_cells(self, var: Variable, start_y: float) -> float:
        cell_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9)
        metrics = QFontMetricsF(cell_font)
        gap = 2
        x = self.PADDING + 16
        y = start_y
        self._array_cells.clear()
        cell_w = self._array_cell_width(var, cell_font)
        cell_h = max(20.0, metrics.lineSpacing() + 6)
        for elem in var.elements:
            cell = QGraphicsRectItem(x, y, cell_w, cell_h, self)
            cell.setPen(QPen(QColor(HEAP_BORDER), 1))
            cell.setBrush(QBrush(QColor(HEAP_BG)))
            label = QGraphicsTextItem(f"[{elem.index}] {elem.value}", cell)
            label.setDefaultTextColor(QColor(STACK_VAR_TEXT))
            label.setFont(cell_font)
            label.setPos(2, 1)
            self._array_cells.append(cell)
            x += cell_w + gap
        return y + cell_h + 4

    def _array_cell_width(self, var: Variable, font: QFont) -> float:
        max_width = 0.0
        for elem in var.elements:
            text = f"[{elem.index}] {elem.value}"
            max_width = max(max_width, _text_width(text, font))
        return max(36.0, max_width + 10.0)

    def _draw_struct_members(self, var: Variable, start_y: float) -> float:
        y = start_y
        for m in var.members:
            label = QGraphicsTextItem(
                f"    .{m.name}: {m.type} = {m.value}", self
            )
            label.setDefaultTextColor(QColor("#9CDCFE"))
            label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10))
            label.setPos(self.PADDING + 16, y)
            self._layout_items.append(label)
            y += 18
        return y

    def _draw_object(self, var, y_offset: float) -> float:
        y = y_offset
        if var.is_destroyed:
            badge = QGraphicsTextItem("  💀 destroyed", self)
            badge.setDefaultTextColor(QColor(EDGE_DANGLING))
            badge.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9))
            badge.setPos(self.PADDING + 12, y)
            self._layout_items.append(badge)
            y += 16
        elif var.is_constructed:
            badge = QGraphicsTextItem("  ⚡ constructed", self)
            badge.setDefaultTextColor(QColor("#4EC9B0"))
            badge.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9))
            badge.setPos(self.PADDING + 12, y)
            self._layout_items.append(badge)
            y += 16
        if var.is_temporary:
            badge = QGraphicsTextItem("  ⏳ temporary", self)
            badge.setDefaultTextColor(QColor("#DCDCAA"))
            badge.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9))
            badge.setPos(self.PADDING + 12, y)
            self._layout_items.append(badge)
            y += 16
        if var.base_classes:
            bases_label = QGraphicsTextItem(
                f"  ⬆ extends {', '.join(var.base_classes)}", self
            )
            bases_label.setDefaultTextColor(QColor("#CE9178"))
            bases_label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9))
            bases_label.setPos(self.PADDING + 12, y)
            self._layout_items.append(bases_label)
            y += 16

        if var.virtual_methods:
            vtable_label = QGraphicsTextItem(
                f"  [vtable] {' '.join(var.virtual_methods)}", self
            )
            vtable_label.setDefaultTextColor(QColor("#DCDCAA"))
            vtable_label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9))
            vtable_label.setPos(self.PADDING + 12, y)
            self._layout_items.append(vtable_label)
            y += 16

        for m in var.members:
            if m.name == "_vptr":
                continue
            color = "#9CDCFE"
            label = QGraphicsTextItem(
                f"    .{m.name}: {m.type} = {m.value}", self
            )
            label.setDefaultTextColor(QColor(color))
            label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10))
            label.setPos(self.PADDING + 12, y)
            self._layout_items.append(label)
            y += 18
        return y

    def _draw_function_object(self, var, y_offset: float) -> float:
        y = y_offset
        lambda_label = QGraphicsTextItem("  λ [callable]", self)
        lambda_label.setDefaultTextColor(QColor("#DCDCAA"))
        lambda_label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9))
        lambda_label.setPos(self.PADDING + 12, y)
        self._layout_items.append(lambda_label)
        y += 16
        for c in var.captures:
            ref = "&" if c.by_ref else ""
            label = QGraphicsTextItem(
                f"    [{ref}capture] {c.name}: {c.type} = {c.value}", self
            )
            label.setDefaultTextColor(QColor("#CE9178"))
            label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9))
            label.setPos(self.PADDING + 12, y)
            self._layout_items.append(label)
            y += 16
        return y

    def _calc_width(self, frame: StackFrame) -> float:
        title_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 11, QFont.Weight.Bold)
        body_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10)
        small_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9)
        max_width = _text_width(frame.frame_name, title_font)
        for var in frame.variables:
            if var.is_object:
                max_width = max(max_width, _text_width(f"  {var.name}: {var.class_name or var.type}", body_font))
                for m in var.members:
                    if m.name == "_vptr":
                        continue
                    max_width = max(max_width, _text_width(f"    .{m.name}: {m.type} = {m.value}", body_font))
            elif var.is_function_object:
                max_width = max(max_width, _text_width(f"  {var.name}: λ", body_font))
                for c in var.captures:
                    max_width = max(max_width, _text_width(f"    [capture] {c.name}: {c.type} = {c.value}", small_font))
            elif var.is_array and var.elements:
                cell_font = QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 9)
                cell_metrics = QFontMetricsF(cell_font)
                cell_w = self._array_cell_width(var, cell_metrics)
                w = (len(var.elements) * (cell_w + 2)) + self.PADDING * 2 + 16
                max_width = max(max_width, w)
            elif var.members:
                for m in var.members:
                    max_width = max(max_width, _text_width(f"    .{m.name}: {m.type} = {m.value}", body_font))
            else:
                max_width = max(max_width, _text_width(f"  {var.name}: {var.type} = {var.value}", body_font))
        return max(self.MIN_WIDTH, max_width + self.PADDING * 2)

    def get_var_item(self, address: str) -> VarItem | None:
        return self.var_items.get(address)

    def count_text_indents(self) -> dict:
        """Return a histogram mapping leading-space counts to number of items.

        Counts are the number of leading ASCII space characters in each
        QGraphicsTextItem's plain text. Useful to determine how many textual
        indentation levels are used (e.g. 2, 4 spaces).
        """
        hist: dict[int, int] = {}
        for item in self._layout_items:
            try:
                text = item.toPlainText()
                leading = len(text) - len(text.lstrip(' '))
            except Exception:
                leading = 0
            hist[leading] = hist.get(leading, 0) + 1
        return hist

    def count_pos_indents(self) -> dict:
        """Return a histogram mapping x-offset (float) to number of items.

        This shows positional indentation (based on `setPos` offsets).
        """
        hist: dict[float, int] = {}
        for item in self._layout_items:
            try:
                x = float(item.pos().x())
            except Exception:
                x = float(self.PADDING)
            hist[x] = hist.get(x, 0) + 1
        return hist

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
