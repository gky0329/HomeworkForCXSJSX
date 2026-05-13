from typing import Callable

from PySide6.QtCore import QEasingCurve, QParallelAnimationGroup, QPointF, QPropertyAnimation

from .heap_item import HeapItem
from .pointer_edge import PointerEdge


class CanvasAnimator:
    def __init__(self, scene):
        self._scene = scene
        self._active_count = 0
        self._on_finished: Callable[[], None] | None = None

    @property
    def is_animating(self) -> bool:
        return self._active_count > 0

    def set_on_all_finished(self, callback: Callable[[], None]):
        self._on_finished = callback

    def _on_anim_started(self):
        self._active_count += 1

    def _on_anim_finished(self):
        self._active_count = max(0, self._active_count - 1)
        if self._active_count == 0 and self._on_finished:
            self._on_finished()

    def animate_heap_added(self, item: HeapItem, target_pos: QPointF,
                           from_pos: QPointF | None = None, duration_ms: int = 300):
        item.setPos(from_pos or QPointF(target_pos.x(), -100))
        item.setScale(0.3)

        anim_group = QParallelAnimationGroup()

        pos_anim = QPropertyAnimation(item, b"pos")
        pos_anim.setDuration(duration_ms)
        pos_anim.setStartValue(item.pos())
        pos_anim.setEndValue(target_pos)
        pos_anim.setEasingCurve(QEasingCurve.OutBack)

        scale_anim = QPropertyAnimation(item, b"scale")
        scale_anim.setDuration(duration_ms)
        scale_anim.setStartValue(0.3)
        scale_anim.setEndValue(1.0)

        anim_group.addAnimation(pos_anim)
        anim_group.addAnimation(scale_anim)

        self._on_anim_started()
        anim_group.finished.connect(self._on_anim_finished)
        anim_group.start()

    def animate_heap_freed(self, item: HeapItem, duration_ms: int = 300):
        def _remove():
            if item.scene():
                item.scene().removeItem(item)

        anim = QPropertyAnimation(item, b"scale")
        anim.setDuration(duration_ms)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.InBack)
        anim.finished.connect(_remove)

        self._on_anim_started()
        anim.finished.connect(self._on_anim_finished)
        anim.start()

    def animate_edge_added(self, edge: PointerEdge, duration_ms: int = 200):
        edge.setOpacity(1.0)
        anim = QPropertyAnimation(edge, b"opacity")
        anim.setDuration(duration_ms)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)

        self._on_anim_started()
        anim.finished.connect(self._on_anim_finished)
        anim.start()

    def flash_error(self, item, times: int = 3, duration_ms: int = 350):
        anim = QPropertyAnimation(item, b"opacity")
        anim.setDuration(duration_ms)
        anim.setStartValue(1.0)
        anim.setEndValue(0.3)
        anim.setLoopCount(times * 2)
        anim.setEasingCurve(QEasingCurve.InOutSine)

        self._on_anim_started()
        anim.finished.connect(self._on_anim_finished)
        anim.start()
