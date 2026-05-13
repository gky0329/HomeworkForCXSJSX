from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from app.core.session import Difficulty, GameMode, WorldMeta, WorldType
from app.services.audio_manager import AudioManager
from app.ui.theme.config import Colors
from app.ui.theme.styles import APP_STYLE
from app.ui.widgets.mc_button import McButton


class CreateWorldPage(QWidget):
    back_requested = Signal()
    world_created = Signal(object)

    def __init__(self, audio: AudioManager) -> None:
        super().__init__()
        self.setStyleSheet(APP_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 40, 60, 40)
        layout.setSpacing(16)

        title = QLabel("创建新世界")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size: 36px; font-weight: 900; color: {Colors.CREAM};")

        self._name = QLineEdit()
        self._name.setPlaceholderText("世界名称")
        self._name.setMinimumHeight(36)

        self._type = QComboBox()
        self._type.addItems(["cpp", "python", "minecraft"])

        self._mode = QComboBox()
        self._mode.addItems(["survival", "creative"])

        self._diff = QComboBox()
        self._diff.addItems(["peaceful", "easy", "normal", "hard", "hardcore"])

        for label in ["学习类型", "游戏模式", "难度"]:
            lb = QLabel(label)
            lb.setStyleSheet(f"font-size: 16px; color: {Colors.CREAM}; font-weight: 700;")
            layout.addWidget(lb)
            if label == "学习类型":
                layout.addWidget(self._type)
            elif label == "游戏模式":
                layout.addWidget(self._mode)
            else:
                layout.addWidget(self._diff)

        layout.addWidget(QLabel("世界名称"))
        layout.addWidget(self._name)

        btn_row = QHBoxLayout()
        back = McButton("取消")
        back.clicked.connect(lambda: audio.play_button() or self.back_requested.emit())
        create = McButton("创建世界")
        create.clicked.connect(lambda: audio.play_button() or self._create())
        btn_row.addWidget(back)
        btn_row.addStretch()
        btn_row.addWidget(create)

        layout.addStretch()
        layout.addLayout(btn_row)

    def _create(self) -> None:
        name = self._name.text().strip() or "New World"
        world = WorldMeta(
            world_name=name,
            world_type=WorldType(self._type.currentText()),
            game_mode=GameMode(self._mode.currentText()),
            difficulty=Difficulty(self._diff.currentText()),
        )
        self.world_created.emit(world)
