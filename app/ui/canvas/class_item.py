from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsRectItem

from app.core.oop_model import ClassDef

_CLASS_W = 160
_CLASS_H = 100


class ClassItem(QGraphicsRectItem):

    def __init__(self, cd: ClassDef, x: float = 0, y: float = 0) -> None:
        super().__init__(QRectF(x, y, _CLASS_W, _CLASS_H))
        self._cd = cd
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setBrush(QBrush(QColor(60, 130, 50)))
        self.setPen(QPen(QColor(40, 100, 30), 2))
        self.setZValue(1)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect()

        painter.fillRect(rect, self.brush())
        painter.setPen(self.pen())
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 6, 6)

        painter.setPen(QColor(255, 255, 255))
        f = QFont("Microsoft YaHei", 14)
        f.setBold(True)
        painter.setFont(f)
        painter.drawText(
            QRectF(rect.left() + 8, rect.top() + 6, rect.width() - 16, 24),
            Qt.AlignmentFlag.AlignHCenter,
            f"class {self._cd.name}",
        )

        painty = rect.top() + 36
        for m in self._cd.members:
            icon = "🔓" if m.access == "public" else "🔒"
            painter.setPen(QColor(200, 255, 200))
            pf = QFont("Consolas", 12)
            painter.setFont(pf)
            painter.drawText(
                QRectF(rect.left() + 10, painty, rect.width() - 20, 20),
                Qt.AlignmentFlag.AlignLeft,
                f"  {icon} {m.type} {m.name}",
            )
            painty += 20

    @property
    def class_name(self) -> str:
        return self._cd.name
