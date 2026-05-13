import random

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from app.ui.theme.config import Colors
from app.ui.theme.styles import APP_STYLE


TIPS = [
    "正在生成村庄旁的第一间教室...",
    "正在把类声明放进工作台...",
    "正在邀请铁傀儡检查构造函数...",
    "正在铺设通往对象世界的草方块...",
    "正在驯服一只野生的指针...",
    "正在搭建栈帧小屋...",
    "正在点燃红石教学电路...",
]


class CreatingWorldPage(QWidget):
    finished = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setStyleSheet(APP_STYLE)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(24)

        title = QLabel("正在创建世界...")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size: 32px; font-weight: 900; color: {Colors.CREAM};")

        self._bar = QProgressBar()
        self._bar.setMinimum(0)
        self._bar.setMaximum(100)
        self._bar.setMinimumWidth(400)

        self._tip = QLabel(random.choice(TIPS))
        self._tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tip.setWordWrap(True)
        self._tip.setStyleSheet(f"font-size: 16px; color: {Colors.MUTED};")

        layout.addWidget(title)
        layout.addWidget(self._bar)
        layout.addWidget(self._tip)

        self._tick = 0

    def start(self) -> None:
        self._tick = 0
        self._bar.setValue(0)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(60)

    def _step(self) -> None:
        self._tick += 1
        self._bar.setValue(min(100, self._tick * 2))
        if self._tick % 10 == 0:
            self._tip.setText(random.choice(TIPS))
        if self._tick >= 50:
            self._timer.stop()
            self.finished.emit()
