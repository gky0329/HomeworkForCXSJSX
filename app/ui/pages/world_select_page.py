from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from app.core.session import WorldMeta
from app.services.audio_manager import AudioManager
from app.services.storage_service import StorageService
from app.ui.theme.config import Colors
from app.ui.theme.styles import APP_STYLE
from app.ui.widgets.mc_button import McButton


class WorldSelectPage(QWidget):
    back_requested = Signal()
    create_requested = Signal()
    enter_requested = Signal(object)

    def __init__(self, audio: AudioManager, storage: StorageService) -> None:
        super().__init__()
        self.audio = audio
        self.storage = storage
        self.setStyleSheet(APP_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        title = QLabel("选择世界")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size: 36px; font-weight: 900; color: {Colors.CREAM};")

        self._list = QListWidget()
        self._list.setMinimumHeight(300)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        back = McButton("取消")
        back.clicked.connect(self.audio.play_button)
        back.clicked.connect(self.back_requested.emit)

        create = McButton("创建新的世界")
        create.clicked.connect(self.audio.play_button)
        create.clicked.connect(self.create_requested.emit)

        enter = McButton("进入选中的世界")
        enter.clicked.connect(self.audio.play_button)
        enter.clicked.connect(self._on_enter)

        btn_row.addWidget(back)
        btn_row.addStretch()
        btn_row.addWidget(create)
        btn_row.addWidget(enter)

        layout.addWidget(title)
        layout.addWidget(self._list)
        layout.addLayout(btn_row)

    def refresh(self) -> None:
        self._list.clear()
        for w in self.storage.load_worlds():
            item = QListWidgetItem(f"{w.world_name}  [{w.world_type.value}]  {w.game_mode.value}  {w.difficulty.value}")
            item.setData(Qt.ItemDataRole.UserRole, w)
            self._list.addItem(item)

    def _on_enter(self) -> None:
        item = self._list.currentItem()
        if item:
            world = item.data(Qt.ItemDataRole.UserRole)
            if world:
                self.enter_requested.emit(world)
