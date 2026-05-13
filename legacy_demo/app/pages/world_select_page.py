from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QHBoxLayout, QMessageBox, QVBoxLayout, QWidget

from app.models.session import WorldMeta
from app.pages.widgets import APP_STYLE, menu_button, subtitle_label, title_label
from app.services.audio_manager import AudioManager


class WorldSelectPage(QWidget):
    create_requested = Signal()
    enter_requested = Signal(WorldMeta)
    back_requested = Signal()

    def __init__(self, audio: AudioManager) -> None:
        super().__init__()
        self.audio = audio
        self.worlds: list[WorldMeta] = []
        self.setStyleSheet(APP_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(80, 50, 80, 50)
        layout.addWidget(title_label("选择世界"))
        layout.addWidget(subtitle_label("选择一个学习存档，或创建新的编程世界"))

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget, 1)

        actions = QHBoxLayout()
        create_button = menu_button("创建世界")
        enter_button = menu_button("进入世界")
        back_button = menu_button("返回")
        for button in (create_button, enter_button, back_button):
            button.clicked.connect(self.audio.play_button)
            actions.addWidget(button)

        create_button.clicked.connect(self.create_requested.emit)
        enter_button.clicked.connect(self._enter_selected)
        back_button.clicked.connect(self.back_requested.emit)
        layout.addLayout(actions)

    def set_worlds(self, worlds: list[WorldMeta]) -> None:
        self.worlds = worlds
        self.list_widget.clear()
        if not worlds:
            self.list_widget.addItem("暂无世界，请先创建一个。")
            return
        for world in worlds:
            completed = len(world.completed_lessons)
            item = QListWidgetItem(
                f"{world.world_name}  |  {world.world_type.value}  |  "
                f"{world.game_mode.value}  |  {world.difficulty.value}  |  完成 {completed} 关"
            )
            item.setData(Qt.UserRole, world.id)
            self.list_widget.addItem(item)

    def _enter_selected(self) -> None:
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.worlds):
            QMessageBox.warning(self, "选择世界", "请先选择一个已有世界。")
            return
        self.enter_requested.emit(self.worlds[row])
