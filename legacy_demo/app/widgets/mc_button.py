from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from PySide6.QtWidgets import QPushButton

from app.theme.config import Assets


class McButton(QPushButton):
    """Pixel-style button that is skinned globally through Qt StyleSheet."""

    def __init__(self, text: str = "", min_width: int = 260) -> None:
        super().__init__(text)
        self.normal_pixmap = self._load_pixmap(Assets.BUTTON_NORMAL)
        self.hover_pixmap = self._load_pixmap(Assets.BUTTON_HOVER)
        self.disabled_pixmap = self._load_pixmap(Assets.BUTTON_DISABLED)
        self.setMinimumWidth(min_width)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("mcButton", True)
        self.setProperty("selected", False)
        self.setFlat(True)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(0)
        shadow.setOffset(5, 6)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.setGraphicsEffect(shadow)

    def _load_pixmap(self, path) -> QPixmap:
        if path.exists():
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                return pixmap
        return QPixmap()

    def sizeHint(self) -> QSize:
        size = super().sizeHint()
        return QSize(max(size.width(), self.minimumWidth()), max(size.height(), 48))

    def paintEvent(self, event) -> None:
        if self.normal_pixmap.isNull():
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        rect = self.rect()
        pixmap = self._current_pixmap()
        painter.drawPixmap(rect, pixmap.scaled(rect.size(), Qt.IgnoreAspectRatio, Qt.FastTransformation))

        if self.isDown():
            painter.fillRect(rect.adjusted(4, 4, -2, -2), QColor(0, 0, 0, 45))
            text_rect = rect.translated(2, 2)
        else:
            painter.fillRect(QRect(rect.left() + 4, rect.bottom() - 9, rect.width() - 8, 5), QColor(0, 0, 0, 80))
            painter.fillRect(QRect(rect.right() - 8, rect.top() + 5, 4, rect.height() - 12), QColor(0, 0, 0, 65))
            text_rect = rect

        if self.property("selected"):
            painter.fillRect(rect.adjusted(5, 5, -5, -5), QColor(90, 210, 85, 55))

        color = QColor(255, 255, 255) if self.isEnabled() else QColor(155, 155, 155)
        if self.underMouse() and self.isEnabled():
            color = QColor(255, 255, 120)

        font = self.font()
        font.setPointSize(max(font.pointSize(), 17))
        font.setBold(True)
        painter.setFont(font)
        for dx, dy in ((2, 2), (-2, 2), (2, -2), (-2, -2)):
            painter.setPen(QColor(35, 35, 35))
            painter.drawText(text_rect.translated(dx, dy), Qt.AlignCenter, self.text())
        painter.setPen(color)
        painter.drawText(text_rect, Qt.AlignCenter, self.text())

    def _current_pixmap(self) -> QPixmap:
        if not self.isEnabled() and not self.disabled_pixmap.isNull():
            return self.disabled_pixmap
        if (self.underMouse() or self.property("selected")) and not self.hover_pixmap.isNull():
            return self.hover_pixmap
        return self.normal_pixmap
