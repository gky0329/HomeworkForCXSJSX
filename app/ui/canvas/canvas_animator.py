from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, QSequentialAnimationGroup
from PySide6.QtWidgets import QGraphicsItem


class CanvasAnimator:

    def __init__(self) -> None:
        self._group: QSequentialAnimationGroup | None = None
        self._animating = False

    @property
    def is_animating(self) -> bool:
        return self._animating

    def play_fly_in(self, item: QGraphicsItem) -> None:
        effect = item.graphicsEffect()
        item.setGraphicsEffect(None)
        item.setScale(0.1)
        anim = QPropertyAnimation(item, b"scale")
        anim.setDuration(250)
        anim.setStartValue(0.1)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutBack)

        self._ensure_group()
        self._group.addAnimation(anim)

    def play_flash(self, item: QGraphicsItem) -> None:
        anim = QPropertyAnimation(item, b"opacity")
        anim.setDuration(300)
        anim.setKeyValueAt(0.0, 1.0)
        anim.setKeyValueAt(0.25, 0.3)
        anim.setKeyValueAt(0.5, 1.0)
        anim.setKeyValueAt(0.75, 0.3)
        anim.setKeyValueAt(1.0, 1.0)

        self._ensure_group()
        self._group.addAnimation(anim)

    def play_fade_out(self, item: QGraphicsItem) -> None:
        anim = QPropertyAnimation(item, b"opacity")
        anim.setDuration(300)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InQuad)

        self._ensure_group()
        self._group.addAnimation(anim)

    def start(self) -> None:
        if self._group:
            self._animating = True
            self._group.finished.connect(self._on_done)
            self._group.start()

    def _ensure_group(self) -> None:
        if self._group is None:
            self._group = QSequentialAnimationGroup()

    def _on_done(self) -> None:
        self._animating = False
        self._group = None

    def reset(self) -> None:
        if self._group:
            self._group.stop()
            self._group = None
        self._animating = False
