from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem
from PySide6.QtCore import Qt, QPointF, QRectF

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

    def render_state(self, state: MemoryState):
        self.clear()

        stack_y = START_Y
        for frame in state.stack:
            item = StackItem(frame, on_item_moved=self._on_item_moved)
            item.setPos(STACK_ITEM_X, stack_y)
            self._scene.addItem(item)
            self._stack_items.append(item)
            for addr, var_item in item.var_items.items():
                self._address_to_item[addr] = var_item
            stack_y += item.rect().height() + ITEM_GAP

        heap_y = START_Y
        for block in state.heap:
            item = HeapItem(block, on_item_moved=self._on_item_moved)
            item.setPos(HEAP_ITEM_X, heap_y)
            self._scene.addItem(item)
            self._heap_items.append(item)
            self._address_to_item[block.address] = item
            heap_y += HeapItem.HEIGHT + ITEM_GAP

        self._render_edges(state.edges)

        self._auto_center()

    def _auto_center(self):
        rect = self._content_bounds()
        if rect.isValid() and not rect.isEmpty():
            self._view.centerOn(rect.center())

    def _content_bounds(self) -> QRectF:
        items = self._stack_items + self._heap_items
        if not items:
            return QRectF()
        rect = items[0].sceneBoundingRect()
        for it in items[1:]:
            rect = rect.united(it.sceneBoundingRect())
        return rect

    def _on_item_moved(self, item: QGraphicsItem):
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
