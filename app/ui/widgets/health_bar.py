import random

from PySide6.QtCore import QPoint, QRect, QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from app.ui.theme.config import Assets, Colors


class HealthBar(QWidget):
    def __init__(self, max_hearts: int = 5) -> None:
        super().__init__()
        self.max_hearts = max_hearts
        self.hearts = max_hearts
        self.creative = False
        self.offset = QPoint(0, 0)
        self.full_texture = self._load_texture(Assets.HEART_FULL, Assets.HEART_FULL_ALT)
        self.empty_texture = self._load_texture(Assets.HEART_EMPTY, Assets.HEART_EMPTY_ALT)
        self.shake_timer = QTimer(self)
        self.shake_timer.timeout.connect(self._shake)
        self.setMinimumSize(172, 34)

    def _load_texture(self, *paths) -> QPixmap:
        for path in paths:
            if path.exists():
                return QPixmap(str(path))
        return QPixmap()

    def set_hearts(self, hearts: int, max_hearts: int, creative: bool = False) -> None:
        self.hearts = hearts
        self.max_hearts = max_hearts
        self.creative = creative
        critical = not creative and hearts < 2
        if critical and not self.shake_timer.isActive():
            self.shake_timer.start(90)
        elif not critical and self.shake_timer.isActive():
            self.shake_timer.stop()
            self.offset = QPoint(0, 0)
        self.update()

    def _shake(self) -> None:
        self.offset = QPoint(random.randint(-3, 3), random.randint(-2, 2))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.translate(self.offset)
        if self.creative:
            painter.setPen(QColor(Colors.GOLD))
            painter.drawText(self.rect(), Qt.AlignVCenter | Qt.AlignLeft, "生命: ∞")
            return
        for index in range(min(self.max_hearts, 10)):
            rect = QRect(index * 30, 4, 24, 24)
            if index < self.hearts:
                self._draw_heart(painter, rect, True)
            else:
                self._draw_heart(painter, rect, False)

    def _draw_heart(self, painter: QPainter, rect: QRect, full: bool) -> None:
        texture = self.full_texture if full else self.empty_texture
        if not texture.isNull():
            painter.drawPixmap(rect, texture)
            return
        color = QColor(Colors.HEART if full else Colors.HEART_DARK)
        outline = QColor(Colors.HEART_OUTLINE)
        cells = [
            "01100110",
            "11111111",
            "11111111",
            "01111110",
            "00111100",
            "00011000",
        ]
        cell = rect.width() // 8
        painter.fillRect(rect, Qt.transparent)
        for y, row in enumerate(cells):
            for x, value in enumerate(row):
                if value == "1":
                    painter.fillRect(rect.x() + x * cell, rect.y() + y * cell, cell, cell, color)
        painter.setPen(outline)
        painter.drawRect(rect.adjusted(0, 0, -1, -1))
