import math
import random

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsView,
    QGraphicsScene, QGraphicsEllipseItem, QGraphicsTextItem,
    QPushButton,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QFont, QColor, QPen, QBrush, QPainter, QLinearGradient,
)

from app.services import error_store
from app.ui.theme.colors import (
    CANVAS_BG, STACK_BORDER, TEXT_PRIMARY,
)


class GraphNode(QGraphicsEllipseItem):
    def __init__(self, x: float, y: float, r: float, label: str,
                 color: QColor):
        super().__init__(-r, -r, 2 * r, 2 * r)
        self.label = label
        self.radius = r
        self.vx = 0.0
        self.vy = 0.0
        self.setPos(x, y)
        self.setPen(QPen(color, 2))
        gradient = QLinearGradient(-r, -r, r, r)
        gradient.setColorAt(0, color.lighter(140))
        gradient.setColorAt(1, color.darker(120))
        self.setBrush(QBrush(gradient))
        self.setFlag(self.GraphicsItemFlag.ItemIsMovable, True)

        self._text = QGraphicsTextItem(label, self)
        self._text.setDefaultTextColor(QColor("#FFFFFF"))
        self._text.setFont(QFont("JetBrains Mono", 10))
        trect = self._text.boundingRect()
        self._text.setPos(-trect.width() / 2, -trect.height() / 2)


class GraphPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._nodes: list[GraphNode] = []
        self._timer = QTimer()
        self._timer.timeout.connect(self._simulate)
        self._setup_ui()
        self._refresh()

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def showEvent(self, event):
        if self._nodes:
            self._timer.start(30)
        super().showEvent(event)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        header = QHBoxLayout()
        header.addWidget(
            self._label("Knowledge Graph", STACK_BORDER, 16, True)
        )
        header.addStretch()
        self._stats_label = self._label("", TEXT_PRIMARY, 12)
        header.addWidget(self._stats_label)
        layout.addLayout(header)

        self._view = QGraphicsView()
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._view.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scene = QGraphicsScene()
        self._scene.setBackgroundBrush(QColor(CANVAS_BG))
        self._scene.setSceneRect(-500, -500, 1000, 1000)
        self._view.setScene(self._scene)
        layout.addWidget(self._view)

        btn_row = QHBoxLayout()
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self._refresh)
        btn_row.addStretch()
        btn_row.addWidget(refresh)
        layout.addLayout(btn_row)

    def _label(self, text: str, color: str, size: int, bold: bool = False) -> QLabel:
        w = "bold" if bold else "normal"
        l = QLabel(text)
        l.setStyleSheet(
            f"color: {color}; font-size: {size}px; font-weight: {w}; "
            f"background: transparent; border: none;"
        )
        return l

    def _refresh(self):
        self._timer.stop()
        for n in self._nodes:
            n.deleteLater()
        self._nodes.clear()

        freq = error_store.get_error_frequency()
        kps = error_store.get_knowledge_points()
        stats = error_store.get_all_stats()

        self._stats_label.setText(
            f"{len(freq)} errored concepts / "
            f"{stats['total_errors']} total errors / "
            f"{stats['knowledge_points']} learned"
        )

        all_names: dict[str, int] = {}
        for name, count in freq.items():
            all_names[name] = all_names.get(name, 0) + count * 3
        for kp in kps:
            name = kp["name"]
            all_names[name] = all_names.get(name, 0) + kp.get("count", 1)

        if not all_names:
            placeholder = QGraphicsTextItem(
                "No data yet — use OJ Analysis or File Import to build knowledge"
            )
            placeholder.setDefaultTextColor(QColor(TEXT_PRIMARY))
            placeholder.setFont(QFont("JetBrains Mono", 14))
            placeholder.setPos(-250, -20)
            self._scene.addItem(placeholder)
            return

        items = sorted(all_names.items(), key=lambda x: -x[1])
        max_w = max(w for _, w in items) if items else 1

        center = len(items) / 2
        for i, (name, weight) in enumerate(items):
            angle = (i / max(len(items), 1)) * 2 * math.pi
            r_base = 180 + random.uniform(-30, 30)
            x = r_base * math.cos(angle)
            y = r_base * math.sin(angle)
            radius = 22 + (weight / max(max_w, 1)) * 35
            ratio = weight / max(max_w, 1)
            r = int(200 * ratio)
            g = int(100 * (1 - ratio))
            b = int(255 * (1 - ratio))
            color = QColor(min(r, 255), min(g, 255), min(b, 255))
            node = GraphNode(x, y, radius, name, color)
            self._scene.addItem(node)
            self._nodes.append(node)

        self._timer.start(30)

    def _simulate(self):
        if not self._nodes:
            self._timer.stop()
            return

        center_x = sum(n.pos().x() for n in self._nodes) / len(self._nodes)
        center_y = sum(n.pos().y() for n in self._nodes) / len(self._nodes)

        for n in self._nodes:
            fx = (center_x - n.pos().x()) * 0.005
            fy = (center_y - n.pos().y()) * 0.005
            n.vx += fx
            n.vy += fy

        for i, a in enumerate(self._nodes):
            for j, b in enumerate(self._nodes):
                if i >= j:
                    continue
                dx = b.pos().x() - a.pos().x()
                dy = b.pos().y() - a.pos().y()
                dist = math.hypot(dx, dy) or 1
                force = 800 / (dist * dist)
                fx = force * dx / dist
                fy = force * dy / dist
                a.vx += fx
                a.vy += fy
                b.vx -= fx
                b.vy -= fy

        for n in self._nodes:
            n.vx *= 0.85
            n.vy *= 0.85
            n.setPos(
                n.pos().x() + n.vx,
                n.pos().y() + n.vy,
            )

        total_v = sum(abs(n.vx) + abs(n.vy) for n in self._nodes)
        if total_v < 0.5:
            self._timer.stop()
