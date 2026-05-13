from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QVBoxLayout, QWidget, QScrollArea,
)

from app.core.challenge_loader import ChallengeLoader
from app.ui.theme.config import Colors
from app.ui.theme.styles import APP_STYLE
from app.ui.widgets.mc_button import McButton


class LevelSelectPage(QWidget):
    back_requested = Signal()
    level_selected = Signal(str)

    def __init__(self, loader: ChallengeLoader) -> None:
        super().__init__()
        self.loader = loader
        self.setStyleSheet(APP_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        title = QLabel("选择关卡")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size: 36px; font-weight: 900; color: {Colors.CREAM};")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background: transparent; }}"
            f"QScrollBar:vertical {{ background: {Colors.BEDROCK}; width: 10px; }}"
            f"QScrollBar::handle:vertical {{ background: {Colors.STONE}; min-height: 30px; }}"
        )

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(8)
        scroll.setWidget(self._list_widget)

        back_btn = McButton("← 返回")
        back_btn.clicked.connect(self.back_requested.emit)

        layout.addWidget(title)
        layout.addWidget(scroll)
        layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def refresh(self) -> None:
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        index = self.loader.load_index()
        for entry in index:
            self._add_row(entry)

    def _add_row(self, entry: dict) -> None:
        row = QWidget()
        row.setStyleSheet(
            f"background: {Colors.PANEL_BG}; border: 2px solid {Colors.STONE_DARK}; "
            f"border-radius: 4px; padding: 10px;"
        )
        rl = QHBoxLayout(row)
        rl.setContentsMargins(16, 10, 16, 10)

        info = QVBoxLayout()
        name = QLabel(f"⛏ {entry['title']}")
        name.setStyleSheet(f"font-size: 18px; font-weight: 900; color: {Colors.CREAM};")
        meta = QLabel(f"Unit {entry.get('unit', '?')}  ·  顺序 #{entry.get('order', '?')}")
        meta.setStyleSheet(f"font-size: 12px; color: {Colors.MUTED};")
        info.addWidget(name)
        info.addWidget(meta)

        btn = McButton("进入")
        btn.setFixedWidth(100)
        level_id = entry["id"]
        btn.clicked.connect(lambda checked, lid=level_id: self.level_selected.emit(lid))

        rl.addLayout(info)
        rl.addStretch()
        rl.addWidget(btn)

        self._list_layout.addWidget(row)
