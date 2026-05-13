from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsRectItem, QGraphicsOpacityEffect

from app.core.oop_model import ObjectInstance

_INST_W = 140
_INST_H = 110


class InstanceItem(QGraphicsRectItem):

    def __init__(self, inst: ObjectInstance, class_x: float = 0, class_y: float = 0) -> None:
        from_x = class_x + 180
        from_y = class_y + 20
        super().__init__(QRectF(from_x, from_y, _INST_W, _INST_H))
        self._inst = inst
        self._label_parts: list[QGraphicsRectItem] = []
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setBrush(QBrush(QColor(50, 90, 180)))
        self.setPen(QPen(QColor(30, 70, 150), 2))
        self.setZValue(2)

    def set_values(self, values: dict) -> None:
        pass

    @property
    def var_name(self) -> str:
        return self._inst.var_name

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect()

        painter.fillRect(rect, self.brush())
        painter.setPen(self.pen())
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 6, 6)

        painter.setPen(QColor(255, 255, 255))
        f = QFont("Microsoft YaHei", 13)
        f.setBold(True)
        painter.setFont(f)
        painter.drawText(
            QRectF(rect.left() + 8, rect.top() + 6, rect.width() - 16, 22),
            Qt.AlignmentFlag.AlignHCenter,
            self._inst.var_name,
        )

        painter.setPen(QColor(180, 200, 255))
        sf = QFont("Consolas", 11)
        painter.setFont(sf)
        painter.drawText(
            QRectF(rect.left() + 8, rect.top() + 28, rect.width() - 16, 16),
            Qt.AlignmentFlag.AlignHCenter,
            f"({self._inst.cls_name})",
        )

        painter.setPen(QColor(255, 255, 255))
        vf = QFont("Consolas", 11)
        painter.setFont(vf)
        line_y = rect.top() + 50
        for key, val in sorted(self._inst.values.items()):
            painter.drawText(
                QRectF(rect.left() + 10, line_y, rect.width() - 20, 18),
                Qt.AlignmentFlag.AlignLeft,
                f"{key} = {val}",
            )
            line_y += 18
