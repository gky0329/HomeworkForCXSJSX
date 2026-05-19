import time
from PySide6.QtCore import QTimer, QPointF
from PySide6.QtGui import QColor

from app.core.state_diff import DiffResult
from app.ui.canvas.memory_canvas import MemoryCanvas
from app.ui.canvas.heap_item import HeapItem
from app.ui.canvas.stack_item import VarItem
from app.ui.theme.colors import HIGHLIGHT

import shiboken6


class CanvasAnimator:
    def __init__(self, canvas: MemoryCanvas):
        self._canvas = canvas
        self._pending = 0
        self._on_finished = None
        self._timers: list[QTimer] = []
        self._generation = 0

    def stop_all(self):
        self._generation += 1
        for timer in self._timers:
            try:
                timer.stop()
                try:
                    timer.timeout.disconnect()
                except Exception:
                    pass
            except Exception:
                pass
        self._timers.clear()
        self._pending = 0
        self._on_finished = None

    def animate_diff(self, diff: DiffResult, on_finished=None):
        self.stop_all()

        self._on_finished = on_finished
        self._pending = 0

        self._animate_added_heap(diff)
        self._animate_modified_vars(diff)
        self._animate_modified_heap(diff)
        self._animate_freed_heap(diff)
        self._animate_removed_edges(diff)

        if self._pending == 0 and self._on_finished:
            cb = self._on_finished
            self._on_finished = None
            cb()

    def _check_done(self, gen: int):
        if gen != self._generation:
            return
        self._pending = max(0, self._pending - 1)
        if self._pending == 0 and self._on_finished:
            cb = self._on_finished
            self._on_finished = None
            cb()

    def _alive(self, item) -> bool:
        try:
            return shiboken6.isValid(item)
        except Exception:
            return False

    def _animate_added_heap(self, diff: DiffResult):
        for block in diff.added_heap:
            item = self._find_heap_item(block.address)
            if item is None:
                continue

            target_x = item.pos().x()
            target_y = item.pos().y()
            start_x = target_x + 300

            item.setPos(QPointF(start_x, target_y))
            item.setOpacity(0.0)

            self._pending += 1
            self._tween(
                duration_ms=400,
                on_update=lambda t, it=item, sx=start_x, tx=target_x, ty=target_y: (
                    None if not self._alive(it) else self._fly_update(it, t, sx, tx, ty)
                ),
            )

    def _fly_update(self, item: HeapItem, t: float, start_x: float, target_x: float, target_y: float):
        t = min(max(t, 0.0), 1.0)
        eased = t * t * (3 - 2 * t)
        x = start_x + (target_x - start_x) * eased
        item.setPos(QPointF(x, target_y))
        item.setOpacity(eased)

    def _animate_modified_vars(self, diff: DiffResult):
        for change in diff.modified_vars:
            item = self._find_var_item(change.address)
            if item is None:
                continue

            item.update_value(change.new_value)
            orig_color = item.defaultTextColor()

            self._pending += 1
            self._tween(
                duration_ms=300,
                on_update=lambda t, it=item, oc=orig_color: (
                    None if not self._alive(it) else self._flash_update(it, t, oc)
                ),
            )

    def _flash_update(self, item: VarItem, t: float, orig_color: QColor):
        if t < 0.5:
            item.setDefaultTextColor(QColor(HIGHLIGHT))
        else:
            progress = (t - 0.5) * 2
            hex_hi = HIGHLIGHT.lstrip('#')
            r = int(hex_hi[0:2], 16) * (1 - progress) + orig_color.red() * progress
            g = int(hex_hi[2:4], 16) * (1 - progress) + orig_color.green() * progress
            b = int(hex_hi[4:6], 16) * (1 - progress) + orig_color.blue() * progress
            item.setDefaultTextColor(QColor(int(r), int(g), int(b)))

    def _animate_modified_heap(self, diff: DiffResult):
        for change in diff.modified_heap:
            item = self._find_heap_item(change.address)
            if item is None:
                continue

            item.update_value(change.new_value)

            self._pending += 1
            self._tween(
                duration_ms=300,
                on_update=lambda t, it=item: (
                    None if not self._alive(it) else self._heap_flash_update(it, t)
                ),
            )

    def _heap_flash_update(self, item: HeapItem, t: float):
        if t < 0.5:
            item.setOpacity(0.4)
        else:
            item.setOpacity(0.4 + (t - 0.5) * 2 * 0.6)

    def _animate_removed_edges(self, diff: DiffResult):
        for edge in diff.removed_edges:
            items = [
                e for e in self._canvas.get_edge_items()
                if e.source_addr == edge.source_address
                and e.target_addr == edge.target_address
            ]
            for item in items:
                item.setOpacity(1.0)
                self._pending += 1
                self._tween(
                    duration_ms=400,
                    on_update=lambda t, it=item: (
                        None if not self._alive(it) else it.setOpacity(1.0 - t)
                    ),
                    on_finish=lambda it=item: self._safe_remove_edge(it),
                )

    def _safe_remove_edge(self, item):
        if self._alive(item) and item.scene() is not None:
            item.scene().removeItem(item)

    def _animate_freed_heap(self, diff: DiffResult):
        for block in diff.freed_heap:
            item = self._find_heap_item(block.address)
            if item is None:
                continue

            item.block.is_freed = True
            item.update()
            orig_x = item.pos().x()
            orig_y = item.pos().y()
            item.setOpacity(1.0)

            self._pending += 1
            self._tween(
                duration_ms=600,
                on_update=lambda t, it=item, ox=orig_x, oy=orig_y: (
                    None if not self._alive(it) else self._shake_update(it, t, ox, oy)
                ),
            )

    def _shake_update(self, item: HeapItem, t: float, orig_x: float, orig_y: float):
        if t < 0.6:
            shake_t = t / 0.6
            offsets = [0, -4, 4, -4, 4, -2, 2, 0]
            idx = min(int(shake_t * len(offsets)), len(offsets) - 1)
            item.setPos(QPointF(orig_x + offsets[idx], orig_y))
            item.setOpacity(1.0)
        else:
            fade_t = (t - 0.6) / 0.4
            item.setPos(QPointF(orig_x, orig_y))
            item.setOpacity(1.0 - fade_t)

    def _tween(self, duration_ms: int, on_update, on_finish=None):
        gen = self._generation
        start_time = [None]
        timer = QTimer()
        timer.setInterval(16)
        self._timers.append(timer)

        def tick():
            if gen != self._generation:
                timer.stop()
                return
            if start_time[0] is None:
                start_time[0] = time.time()
            elapsed = (time.time() - start_time[0]) * 1000
            t = elapsed / duration_ms

            if t >= 1.0:
                on_update(1.0)
                timer.stop()
                self._timers[:] = [t for t in self._timers if t is not timer]
                if on_finish:
                    on_finish()
                self._check_done(gen)
            else:
                on_update(t)

        timer.timeout.connect(tick)
        timer.start()

    def _find_var_item(self, address: str) -> VarItem | None:
        for stack_item in self._canvas.get_stack_items():
            var = stack_item.get_var_item(address)
            if var:
                return var
        return None

    def _find_heap_item(self, address: str) -> HeapItem | None:
        for item in self._canvas.get_heap_items():
            if item.address == address:
                return item
        return None
