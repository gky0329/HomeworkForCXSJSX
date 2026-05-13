from PySide6.QtCore import QRect, QTimer, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPixmap, QRadialGradient
from PySide6.QtWidgets import QWidget

from app.ui.theme.config import Assets, Colors


class PanoramaBackground(QWidget):
    def __init__(self, dim: int = 0, blur_like: bool = False) -> None:
        super().__init__()
        self.panorama_offset = 0
        self.dim = dim
        self.blur_like = blur_like
        self.panorama_images = self._load_panorama_images()
        self.panorama_timer = QTimer(self)
        self.panorama_timer.timeout.connect(self._tick_panorama)
        self.panorama_timer.start(70)

    def _tick_panorama(self) -> None:
        self.panorama_offset = (self.panorama_offset + 1) % 3600
        self.update()

    def _load_panorama_images(self) -> list[QPixmap]:
        images = []
        for index in range(6):
            matches = sorted(Assets.PANORAMA_DIR.glob(f"*panorama_{index}.png"))
            path = matches[0] if matches else Assets.PANORAMA_DIR / f"panorama_{index}.png"
            if path.exists():
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    images.append(pixmap)
        return images

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        if self.panorama_images:
            self._paint_texture_panorama(painter)
        else:
            self._paint_panorama(painter)
        if self.dim:
            painter.fillRect(self.rect(), QColor(0, 0, 0, self.dim))

    def _paint_texture_panorama(self, painter: QPainter) -> None:
        width = max(self.width(), 1)
        height = max(self.height(), 1)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        phase = self.panorama_offset / 230.0
        face = int(phase) % len(self.panorama_images)
        blend = phase - int(phase)
        center_shift = int((blend - 0.5) * width * 0.32)

        previous_face = (face - 1) % len(self.panorama_images)
        next_face = (face + 1) % len(self.panorama_images)
        center_rect = QRect(-width // 7 - center_shift, -height // 14, width + width // 3, height + height // 7)
        left_rect = QRect(-width * 3 // 5 - center_shift, -height // 18, width * 3 // 5, height + height // 9)
        right_rect = QRect(width - center_shift, -height // 18, width * 3 // 5, height + height // 9)

        painter.fillRect(self.rect(), QColor("#78A7F1"))
        self._draw_skybox_panel(painter, self.panorama_images[previous_face], left_rect, 0.82)
        self._draw_skybox_panel(painter, self.panorama_images[next_face], right_rect, 0.82)
        self._draw_skybox_panel(painter, self.panorama_images[face], center_rect, 1.0)

        seam = QLinearGradient(0, 0, width, 0)
        seam.setColorAt(0.0, QColor(0, 0, 0, 95))
        seam.setColorAt(0.18, QColor(0, 0, 0, 0))
        seam.setColorAt(0.82, QColor(0, 0, 0, 0))
        seam.setColorAt(1.0, QColor(0, 0, 0, 95))
        painter.fillRect(self.rect(), QBrush(seam))

        glow = QLinearGradient(0, 0, 0, height)
        glow.setColorAt(0.0, QColor(255, 255, 255, 18))
        glow.setColorAt(0.42, QColor(255, 255, 255, 0))
        glow.setColorAt(1.0, QColor(0, 0, 0, 72))
        painter.fillRect(self.rect(), QBrush(glow))
        vignette = QRadialGradient(width / 2, height / 2, max(width, height) * 0.72)
        vignette.setColorAt(0.0, QColor(0, 0, 0, 0))
        vignette.setColorAt(0.75, QColor(0, 0, 0, 25))
        vignette.setColorAt(1.0, QColor(0, 0, 0, 118))
        painter.fillRect(self.rect(), QBrush(vignette))

    def _draw_skybox_panel(self, painter: QPainter, pixmap: QPixmap, target: QRect, opacity: float) -> None:
        scaled = pixmap.scaled(target.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        source = QRect(
            max((scaled.width() - target.width()) // 2, 0),
            max((scaled.height() - target.height()) // 2, 0),
            min(target.width(), scaled.width()),
            min(target.height(), scaled.height()),
        )
        painter.setOpacity(opacity)
        painter.drawPixmap(target, scaled, source)
        painter.setOpacity(1.0)

    def _draw_panorama_face(self, painter: QPainter, pixmap: QPixmap, target: QRect, drift: int, opacity: float) -> None:
        scaled = pixmap.scaled(
            target.width() + target.width() // 3,
            target.height() + target.height() // 4,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        max_x = max(scaled.width() - target.width(), 1)
        max_y = max(scaled.height() - target.height(), 1)
        source_x = drift % max_x
        source_y = max_y // 2
        painter.setOpacity(opacity)
        painter.drawPixmap(target, scaled.copy(source_x, source_y, target.width(), target.height()))

    def _paint_panorama(self, painter: QPainter) -> None:
        width = max(self.width(), 1)
        height = max(self.height(), 1)
        block = max(18, width // 80)
        painter.fillRect(self.rect(), QColor("#86AEF4"))
        self._clouds(painter, block, width)
        self._hills(painter, block, width, height)
        self._ground(painter, block, width, height)
        self._trees(painter, block, width, height)
        self._flowers(painter, block, width, height)

    def _x(self, value: int, width: int) -> int:
        return (value - self.panorama_offset * 3) % (width + 260) - 130

    def _clouds(self, painter: QPainter, block: int, width: int) -> None:
        painter.setBrush(QColor(245, 248, 255, 190))
        painter.setPen(Qt.NoPen)
        for base in (-120, 120, 420, 760, 1080, 1460):
            x = self._x(base, width)
            y = 58 + (base % 3) * 34
            for dx, dy, w in [(0, 0, 4), (3, -1, 5), (7, 0, 4), (11, 1, 3)]:
                painter.drawRect(x + dx * block, y + dy * block, w * block, block)

    def _hills(self, painter: QPainter, block: int, width: int, height: int) -> None:
        colors = ["#617247", "#53663C", "#73824F"]
        for index, base in enumerate((-100, 220, 520, 880, 1220)):
            painter.setBrush(QColor(colors[index % len(colors)]))
            x = self._x(base, width)
            y = int(height * 0.48) + (index % 2) * block
            painter.drawRect(x, y, block * 18, block * 5)
            painter.drawRect(x + block * 3, y - block * 2, block * 11, block * 2)

    def _ground(self, painter: QPainter, block: int, width: int, height: int) -> None:
        top = int(height * 0.58)
        painter.fillRect(0, top, width, height - top, QColor("#6EA044"))
        for row in range(top, height, block):
            shade = QColor("#5D8E39" if (row // block) % 2 else "#78AD4A")
            painter.fillRect(0, row, width, block, shade)
        for x in range(-block * 2, width + block * 2, block * 3):
            painter.fillRect(x - self.panorama_offset % (block * 3), top + block * 3, block * 3, block, QColor("#4D321F"))
            painter.fillRect(x - self.panorama_offset % (block * 3), top + block * 2, block * 3, block, QColor("#72A84A"))

    def _trees(self, painter: QPainter, block: int, width: int, height: int) -> None:
        for base in (-60, 260, 540, 880, 1200, 1540):
            x = self._x(base, width)
            ground = int(height * 0.58)
            painter.fillRect(x + block * 5, ground - block * 8, block * 2, block * 8, QColor("#3A2028"))
            painter.fillRect(x + block * 4, ground - block * 10, block * 4, block * 2, QColor("#4B2932"))
            for dx, dy, w, h in [
                (0, -15, 11, 3),
                (1, -18, 10, 4),
                (3, -21, 7, 3),
                (7, -16, 5, 3),
                (-1, -12, 7, 3),
            ]:
                painter.fillRect(x + dx * block, ground + dy * block, w * block, h * block, QColor("#E7A3C9"))
                painter.fillRect(x + (dx + 1) * block, ground + (dy + 1) * block, w * block // 2, block, QColor("#F3C0DC"))
                painter.fillRect(x + (dx + 3) * block, ground + dy * block, block, block, QColor("#5E7C36"))

    def _flowers(self, painter: QPainter, block: int, width: int, height: int) -> None:
        top = int(height * 0.64)
        colors = ["#F5BDD8", "#E85AAB", "#FFD4EA"]
        for index in range(52):
            x = (index * 97 - self.panorama_offset * 5) % (width + block * 4) - block * 2
            y = top + ((index * 43) % max(block * 12, 1))
            painter.fillRect(x, y, block, block, QColor(colors[index % len(colors)]))
            painter.fillRect(x + block, y + block, block, block, QColor(colors[(index + 1) % len(colors)]))


class LoadingCube(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(80)
        self.setFixedSize(170, 170)

    def _tick(self) -> None:
        self.angle = (self.angle + 1) % 4
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.fillRect(self.rect(), QColor(0, 0, 0))
        size = 92
        x = (self.width() - size) // 2
        y = (self.height() - size) // 2
        colors = [Colors.STONE_LIGHT, Colors.GRASS_LIGHT, Colors.DIRT, Colors.STONE]
        painter.fillRect(x, y, size, size, QColor(colors[self.angle]))
        painter.fillRect(x + 28, y + 28, 36, 36, QColor(colors[(self.angle + 1) % len(colors)]))
