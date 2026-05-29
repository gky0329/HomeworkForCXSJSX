from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsTextItem
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainterPath, QPen, QColor, QPolygonF, QPainter
from math import atan2, pi, sin, cos

from app.ui.theme.colors import EDGE_SOLID, EDGE_DANGLING


class EdgeItem(QGraphicsPathItem):
    ARROW_SIZE = 8.0

    def __init__(self, source_addr: str, target_addr: str, is_dangling: bool,
                 address_map: dict):
        super().__init__()
        self.source_addr = source_addr
        self.target_addr = target_addr
        self._is_dangling = is_dangling
        self._address_map = address_map
        self._arrow_polygon = QPolygonF()
        self.setZValue(1)
        self.recalc()

    def recalc(self):
        src_item = self._address_map.get(self.source_addr)
        tgt_item = self._address_map.get(self.target_addr)
        if src_item is None or tgt_item is None:
            return

        src_br = src_item.sceneBoundingRect()
        tgt_br = tgt_item.sceneBoundingRect()

        src_center = src_br.center()
        tgt_center = tgt_br.center()
        h_dist = abs(tgt_center.x() - src_center.x())
        close = h_dist < 150

        if close:
            src_pos = QPointF(src_br.left(), src_center.y())
            tgt_pos = QPointF(tgt_br.left(), tgt_center.y())
        else:
            src_pos = QPointF(src_br.right(), src_center.y())
            tgt_pos = QPointF(tgt_br.left(), tgt_center.y())

        vert_gap = abs(tgt_pos.y() - src_pos.y())
        if close:
            cx_offset = min(30.0, h_dist * 0.6 + 10)
            if src_pos.y() < tgt_pos.y():
                c1 = QPointF(src_pos.x() - cx_offset, src_pos.y())
                c2 = QPointF(tgt_pos.x() - cx_offset, tgt_pos.y())
            else:
                c1 = QPointF(src_pos.x() - cx_offset, src_pos.y())
                c2 = QPointF(tgt_pos.x() - cx_offset, tgt_pos.y())
        else:
            dx = tgt_pos.x() - src_pos.x()
            cx_offset = max(abs(dx) * 0.4, 40.0)
            c1 = QPointF(src_pos.x() + cx_offset, src_pos.y())
            c2 = QPointF(tgt_pos.x() - cx_offset, tgt_pos.y())

        color = QColor(EDGE_DANGLING) if self._is_dangling else QColor(EDGE_SOLID)
        style = Qt.PenStyle.DashLine if self._is_dangling else Qt.PenStyle.SolidLine
        self.setPen(QPen(color, 1.5, style))

        path = QPainterPath()
        path.moveTo(src_pos)
        path.cubicTo(c1, c2, tgt_pos)
        self.setPath(path)

        angle = atan2(tgt_pos.y() - c2.y(), tgt_pos.x() - c2.x())
        self._arrow_polygon = self._make_arrow(tgt_pos, angle)

    def visual_bounds(self) -> QRectF:
        bounds = self.path().boundingRect()
        bounds = bounds.united(self._arrow_polygon.boundingRect())
        return bounds.adjusted(-3.0, -3.0, 3.0, 3.0)

    def _make_arrow(self, tip: QPointF, angle: float) -> QPolygonF:
        p1 = tip
        p2 = QPointF(
            tip.x() - self.ARROW_SIZE * cos(angle - pi / 6),
            tip.y() - self.ARROW_SIZE * sin(angle - pi / 6),
        )
        p3 = QPointF(
            tip.x() - self.ARROW_SIZE * cos(angle + pi / 6),
            tip.y() - self.ARROW_SIZE * sin(angle + pi / 6),
        )
        return QPolygonF([p1, p2, p3])

    def paint(self, painter: QPainter, option=None, widget=None):
        super().paint(painter, option, widget)
        color = QColor(EDGE_DANGLING) if self._is_dangling else QColor(EDGE_SOLID)
        painter.setBrush(color)
        painter.setPen(QPen(color, 1.0))
        painter.drawPolygon(self._arrow_polygon)

    def update_dangling(self, is_dangling: bool):
        self._is_dangling = is_dangling
        self.recalc()
