from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from app.core.oop_model import OopModel
from app.core.state_diff import StateDiff
from app.ui.canvas.class_item import ClassItem
from app.ui.canvas.instance_item import InstanceItem

_CLASS_COL = 30
_INST_COL = 480
_ROW_H = 120


class OopCanvas(QGraphicsView):

    def __init__(self) -> None:
        super().__init__()
        self._scene = QGraphicsScene()
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setBackgroundBrush(QBrush(QColor(30, 45, 30)))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._class_items: dict[str, ClassItem] = {}
        self._instance_items: dict[str, InstanceItem] = {}
        self._class_row = 0
        self._instance_row = 0

        self._draw_labels()

    def _draw_labels(self) -> None:
        f = QFont("Microsoft YaHei", 13)
        f.setBold(True)

        c_label = self._scene.addText("Class 定义", f)
        c_label.setPos(_CLASS_COL + 10, 4)
        c_label.setDefaultTextColor(QColor(100, 200, 100))

        i_label = self._scene.addText("实例", f)
        i_label.setPos(_INST_COL + 10, 4)
        i_label.setDefaultTextColor(QColor(100, 150, 255))

        divider = self._scene.addRect(
            QRectF(380, 0, 2, 700),
            QPen(Qt.PenStyle.NoPen),
            QBrush(QColor(60, 60, 60)),
        )
        divider.setZValue(-1)

    def apply(self, diff: StateDiff) -> None:
        for cd in diff.added_classes:
            self._add_class(cd)
        for inst in diff.added_instances:
            self._add_instance(inst)
        for var, prop, val in diff.updated_instances:
            self._update_instance(var, prop, val)
        for name in diff.removed_instances:
            self._remove_instance(name)

    def _add_class(self, cd) -> None:
        y = 30 + self._class_row * _ROW_H
        item = ClassItem(cd, _CLASS_COL, y)
        self._scene.addItem(item)
        self._class_items[cd.name] = item
        self._class_row += 1

    def _add_instance(self, inst) -> None:
        cd_item = self._class_items.get(inst.cls_name)
        cx, cy = (0, 0) if cd_item is None else (cd_item.rect().x(), cd_item.rect().y())
        y = 30 + self._instance_row * _ROW_H
        item = InstanceItem(inst, cx, cy)
        item.setPos(_INST_COL, y)
        self._scene.addItem(item)
        self._instance_items[inst.var_name] = item
        self._instance_row += 1

    def _update_instance(self, var_name: str, prop: str, val) -> None:
        item = self._instance_items.get(var_name)
        if item:
            item._inst.values[prop] = val
            item.update()

    def _remove_instance(self, name: str) -> None:
        item = self._instance_items.pop(name, None)
        if item:
            self._scene.removeItem(item)

    def reset(self) -> None:
        self._scene.clear()
        self._class_items.clear()
        self._instance_items.clear()
        self._class_row = 0
        self._instance_row = 0
        self._draw_labels()
