import random

from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout

from app.pages.widgets import APP_STYLE, title_label
from app.theme.config import Colors
from app.widgets.panorama_background import LoadingCube, PanoramaBackground


class CreatingWorldPage(PanoramaBackground):
    finished = Signal()

    TIPS = [
        "正在生成村庄旁的第一间教室...",
        "正在把类声明放进工作台...",
        "正在邀请铁傀儡检查构造函数...",
        "正在铺设通往对象世界的草方块...",
    ]

    def __init__(self) -> None:
        super().__init__(dim=55, blur_like=True)
        self.setStyleSheet(APP_STYLE)
        self.progress = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        self.title = title_label("加载地形中...")
        layout.addWidget(self.title)
        self.tip_label = QLabel()
        self.tip_label.setAlignment(Qt.AlignCenter)
        self.tip_label.setStyleSheet(f"color: {Colors.MUTED};")
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(520)
        layout.addWidget(self.tip_label)
        layout.addSpacing(16)
        layout.addWidget(self.progress_bar, alignment=Qt.AlignCenter)
        layout.addSpacing(28)
        layout.addWidget(LoadingCube(), alignment=Qt.AlignCenter)

    def start(self) -> None:
        self.progress = 0
        self.tip_label.setText(random.choice(self.TIPS))
        self.progress_bar.setValue(0)
        self.timer.start(80)

    def _tick(self) -> None:
        self.progress += random.randint(4, 9)
        self.progress_bar.setValue(min(self.progress, 100))
        if self.progress >= 100:
            self.timer.stop()
            QTimer.singleShot(250, self.finished.emit)
