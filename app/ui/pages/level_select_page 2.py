from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QLabel, QListWidget, QListWidgetItem, QPushButton,
    QVBoxLayout, QWidget,
)

from app.core.challenge_loader import ChallengeLoader


class LevelSelectPage(QWidget):
    level_selected = Signal(str)
    back_requested = Signal()

    def __init__(self, challenge_loader: ChallengeLoader, parent=None):
        super().__init__(parent)
        self._loader = challenge_loader

        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 40, 60, 40)
        layout.setSpacing(12)

        title = QLabel("选择关卡")
        title.setFont(QFont("Microsoft YaHei", 22, QFont.Bold))
        title.setStyleSheet("color: #E8A840;")
        layout.addWidget(title)

        self._list = QListWidget()
        self._list.setStyleSheet("""
            QListWidget {
                background-color: #1a1a2e;
                border: 1px solid #333;
                border-radius: 6px;
                color: white;
                font-size: 14px;
                font-family: "Microsoft YaHei";
                padding: 6px;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #2a2a3e;
            }
            QListWidget::item:selected {
                background-color: #3a3a5e;
            }
            QListWidget::item:hover {
                background-color: #2a2a4e;
            }
        """)
        self._list.itemDoubleClicked.connect(self._on_select)
        layout.addWidget(self._list)

        ctrl_layout = QVBoxLayout()
        enter_btn = QPushButton("进入关卡")
        enter_btn.setStyleSheet(self._btn_style("#E8A840"))
        enter_btn.clicked.connect(self._on_enter)
        back_btn = QPushButton("← 返回主菜单")
        back_btn.setStyleSheet(self._btn_style("#555"))
        back_btn.clicked.connect(self.back_requested.emit)
        ctrl_layout.addWidget(enter_btn)
        ctrl_layout.addWidget(back_btn)
        layout.addLayout(ctrl_layout)

        self.setStyleSheet("background-color: #14142a;")

    def _btn_style(self, color: str) -> str:
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-family: "Microsoft YaHei";
            }}
            QPushButton:hover {{ background-color: {color}CC; }}
        """

    def load_levels(self):
        self._list.clear()
        index = self._loader.load_index()
        for entry in index:
            item = QListWidgetItem(
                f"Unit {entry['unit']} — {entry['title']}"
            )
            item.setData(Qt.UserRole, entry["id"])
            self._list.addItem(item)

    def _on_select(self, item: QListWidgetItem):
        level_id = item.data(Qt.UserRole)
        if level_id:
            self.level_selected.emit(level_id)

    def _on_enter(self):
        current = self._list.currentItem()
        if current:
            self._on_select(current)
