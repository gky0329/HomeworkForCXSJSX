from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPen, QColor

from app.core.memory_model import MemoryState, PointerEdge
from app.ui.canvas.stack_item import StackItem
from app.ui.canvas.heap_item import HeapItem
from app.ui.canvas.edge_item import EdgeItem


STACK_ITEM_X = 20
HEAP_ITEM_X = 220
START_Y = 20
ITEM_GAP = 16


class MemoryCanvas:
    def __init__(self, view: QGraphicsView, scene: QGraphicsScene):
        self._view = view
        self._scene = scene
        self._stack_items: list[StackItem] = []
        self._heap_items: list[HeapItem] = []
        self._edge_items: list[EdgeItem] = []
        self._address_to_item: dict[str, object] = {}
        self._edge_by_source: dict[str, list[EdgeItem]] = {}
        self._edge_by_target: dict[str, list[EdgeItem]] = {}
        self._next_layout_frame: int = 0
        self._position_cache: dict[tuple[str, str, int], QPointF] = {}

    def clear(self):
        all_items = self._stack_items + self._heap_items + self._edge_items
        for item in all_items:
            if item.scene() is not None:
                self._scene.removeItem(item)
        self._stack_items.clear()
        self._heap_items.clear()
        self._edge_items.clear()
        self._address_to_item.clear()
        self._edge_by_source.clear()
        self._edge_by_target.clear()

    def _snapshot_positions(self):
        cache: dict[tuple[str, str, int], QPointF] = {}

        stack_name_counts: dict[str, int] = {}
        for item in self._stack_items:
            frame_name = getattr(getattr(item, "frame", None), "frame_name", "")
            index = stack_name_counts.get(frame_name, 0)
            stack_name_counts[frame_name] = index + 1
            cache[("stack", frame_name, index)] = QPointF(item.pos())

        for item in self._heap_items:
            cache[("heap", getattr(item, "address", ""), 0)] = QPointF(item.pos())

        self._position_cache = cache

    def render_state(self, state: MemoryState):
        self._snapshot_positions()
        self.clear()

        stack_y = START_Y
        stack_name_counts: dict[str, int] = {}
        for frame in state.stack:
            item = StackItem(frame, on_item_moved=self._on_item_moved)
            frame_index = stack_name_counts.get(frame.frame_name, 0)
            stack_name_counts[frame.frame_name] = frame_index + 1
            preferred_pos = self._position_cache.get(("stack", frame.frame_name, frame_index))
            item.setPos(preferred_pos if preferred_pos is not None else QPointF(STACK_ITEM_X, stack_y))
            self._scene.addItem(item)
            self._register_layout_frame(item, fixed_zero=(frame.frame_name == "main"))
            self._stack_items.append(item)
            for addr, var_item in item.var_items.items():
                self._address_to_item[addr] = var_item
            stack_y += item.rect().height() + ITEM_GAP

        heap_y = START_Y
        for block in state.heap:
            item = HeapItem(block, on_item_moved=self._on_item_moved)
            preferred_pos = self._position_cache.get(("heap", block.address, 0))
            item.setPos(preferred_pos if preferred_pos is not None else QPointF(HEAP_ITEM_X, heap_y))
            self._scene.addItem(item)
            self._register_layout_frame(item, fixed_zero=False)
            self._heap_items.append(item)
            self._address_to_item[block.address] = item
            heap_y += item.rect().height() + ITEM_GAP

        # Resolve overlaps once in layout order before edges are created.
        self._resolve_layout_once()

        self._render_edges(state.edges)

        self._render_ref_edges(state)

    def _render_ref_edges(self, state: MemoryState):
        for frame in state.stack:
            for var in frame.variables:
                if not var.is_reference:
                    continue
                target_addr = var.value
                if not target_addr.startswith("0xS") and not target_addr.startswith("0xH"):
                    continue
                ref_item = self._address_to_item.get(var.address)
                tgt_item = self._address_to_item.get(target_addr)
                if ref_item is None or tgt_item is None:
                    continue
                edge = EdgeItem(
                    source_addr=var.address,
                    target_addr=target_addr,
                    is_dangling=False,
                    address_map=self._address_to_item,
                )
                edge.setPen(QPen(QColor("#4EC9B0"), 1, Qt.PenStyle.DotLine))
                self._scene.addItem(edge)
                self._edge_items.append(edge)
                self._edge_by_source.setdefault(var.address, []).append(edge)
                self._edge_by_target.setdefault(target_addr, []).append(edge)

    def _auto_center(self):
        rect = self._content_bounds()
        if rect.isValid() and not rect.isEmpty():
            self._view.centerOn(rect.center())

    def _content_bounds(self) -> QRectF:
        items = self._stack_items + self._heap_items
        if not items:
            return QRectF()
        rect = self._item_visual_bounds(items[0])
        for it in items[1:]:
            rect = rect.united(self._item_visual_bounds(it))
        return rect

    def _on_item_moved(self, item: QGraphicsItem, cause: str = "move"):
        # Update edges for moved/changed item
        if isinstance(item, StackItem):
            for addr in item.var_items:
                self._update_edges_for_address(addr)
        elif isinstance(item, HeapItem):
            self._update_edges_for_address(item.address)

        # Only attempt layout reordering when the item changed size/content.
        # Do not attempt during interactive moves to avoid re-entrant moves.
        if cause == "resize":
            self._resolve_layout_once()

    def _register_layout_frame(self, item: QGraphicsItem, fixed_zero: bool = False):
        if fixed_zero:
            frame_id = 0
        else:
            frame_id = self._next_layout_frame
            self._next_layout_frame += 1
        item.setData(0, frame_id)

    def _layout_frame_id(self, item: QGraphicsItem) -> int:
        data = item.data(0)
        try:
            return int(data)
        except Exception:
            return 0

    def _intersects_placed(self, item: QGraphicsItem, placed: list[QGraphicsItem]) -> bool:
        rect = self._item_collision_bounds(item)
        for other in placed:
            if other.scene() is None:
                continue
            if rect.intersects(self._item_collision_bounds(other)):
                return True
        return False

    def _candidate_position_for_item(self, item: QGraphicsItem, placed: list[QGraphicsItem]) -> QPointF:
        scene = self._scene
        if scene is None:
            return item.pos()

        current = item.pos()
        item_rect = self._item_local_collision_bounds(item)
        scene_rect = scene.sceneRect()
        if not placed:
            return current

        right_edge = max(self._item_collision_bounds(other).right() for other in placed if other.scene() is not None)
        bottom_edge = max(self._item_collision_bounds(other).bottom() for other in placed if other.scene() is not None)

        # Right-first: place the item to the right of all already-placed lower frames.
        right_x = max(current.x(), right_edge + ITEM_GAP)
        right_pos = QPointF(right_x, current.y())
        right_rect = item_rect.translated(right_pos)
        within_right_bounds = right_rect.right() <= scene_rect.right()
        if within_right_bounds and not any(right_rect.intersects(self._item_collision_bounds(other)) for other in placed if other.scene() is not None):
            return right_pos

        # Fallback: move down below all already-placed lower frames.
        down_y = max(current.y(), bottom_edge + ITEM_GAP)
        down_pos = QPointF(current.x(), down_y)
        down_rect = item_rect.translated(down_pos)
        within_down_bounds = down_rect.bottom() <= scene_rect.bottom()
        if within_down_bounds and not any(down_rect.intersects(self._item_collision_bounds(other)) for other in placed if other.scene() is not None):
            return down_pos

        return current

    def _item_collision_bounds(self, item: QGraphicsItem) -> QRectF:
        try:
            return item.sceneBoundingRect()
        except Exception:
            return item.mapRectToScene(item.boundingRect())

    def _item_local_collision_bounds(self, item: QGraphicsItem) -> QRectF:
        return item.boundingRect()

    def _resolve_layout_once(self):
        items = self._stack_items + self._heap_items
        if not items:
            return

        ordered = sorted(items, key=self._layout_frame_id)
        placed: list[QGraphicsItem] = []
        moved_items: list[QGraphicsItem] = []

        for item in ordered:
            frame_id = self._layout_frame_id(item)
            if frame_id == 0:
                placed.append(item)
                continue

            if self._intersects_placed(item, placed):
                new_pos = self._candidate_position_for_item(item, placed)
                if new_pos != item.pos():
                    item.setPos(new_pos)
                    moved_items.append(item)
            placed.append(item)

        for item in moved_items:
            if isinstance(item, StackItem):
                for addr in item.var_items:
                    self._update_edges_for_address(addr)
            elif isinstance(item, HeapItem):
                self._update_edges_for_address(item.address)

    def _update_edges_for_address(self, address: str):
        for edge in self._edge_by_source.get(address, []):
            edge.recalc()
        for edge in self._edge_by_target.get(address, []):
            edge.recalc()

    def _render_edges(self, edges: list[PointerEdge]):
        for edge_data in edges:
            edge = EdgeItem(
                source_addr=edge_data.source_address,
                target_addr=edge_data.target_address,
                is_dangling=edge_data.is_dangling,
                address_map=self._address_to_item,
            )
            self._scene.addItem(edge)
            self._edge_items.append(edge)
            src = edge_data.source_address
            tgt = edge_data.target_address
            self._edge_by_source.setdefault(src, []).append(edge)
            self._edge_by_target.setdefault(tgt, []).append(edge)

    def get_stack_items(self) -> list[StackItem]:
        return self._stack_items

    def get_heap_items(self) -> list[HeapItem]:
        return self._heap_items

    def get_edge_items(self) -> list[EdgeItem]:
        return self._edge_items

    def get_item_by_address(self, address: str):
        return self._address_to_item.get(address)
