from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QVBoxLayout

from app.models.session import Difficulty, GameMode, WorldMeta, WorldType
from app.pages.widgets import APP_STYLE, menu_button, title_label
from app.services.audio_manager import AudioManager
from app.widgets.panorama_background import PanoramaBackground


class CreateWorldPage(PanoramaBackground):
    world_created = Signal(WorldMeta)
    back_requested = Signal()

    def __init__(self, audio: AudioManager) -> None:
        super().__init__(dim=40, blur_like=True)
        self.audio = audio
        self.setStyleSheet(APP_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(250, 26, 250, 30)
        layout.setSpacing(22)

        tabs = QHBoxLayout()
        for text in ("游戏", "世界", "更多"):
            tab = QLabel(text)
            tab.setAlignment(Qt.AlignCenter)
            tab.setStyleSheet(
                "font-size: 24px; border: 3px solid rgba(255,255,255,190); "
                "background: rgba(0,0,0,130); padding: 12px;"
            )
            tabs.addWidget(tab)
        layout.addLayout(tabs)

        layout.addWidget(title_label("世界名称"))

        form = QFormLayout()
        form.setVerticalSpacing(18)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("新的世界")
        self.type_combo = QComboBox()
        self.type_combo.addItems([item.value for item in WorldType])
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([item.value for item in GameMode])
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems([item.value for item in Difficulty])
        self.rule_label = QLabel()
        self.rule_label.setWordWrap(True)

        form.addRow("世界名称", self.name_edit)
        form.addRow("学习类型", self.type_combo)
        form.addRow("游戏模式", self.mode_combo)
        form.addRow("难度", self.difficulty_combo)
        form.addRow("规则", self.rule_label)
        layout.addLayout(form)
        layout.addStretch(1)

        actions = QHBoxLayout()
        create_button = menu_button("创建新的世界")
        back_button = menu_button("取消")
        for button in (create_button, back_button):
            button.setMinimumWidth(350)
            button.clicked.connect(self.audio.play_button)
            actions.addWidget(button)
        create_button.clicked.connect(self._create_world)
        back_button.clicked.connect(self.back_requested.emit)
        layout.addLayout(actions)

        self.mode_combo.currentTextChanged.connect(self._update_rule_text)
        self._update_rule_text()

    def _update_rule_text(self) -> None:
        if self.mode_combo.currentText() == GameMode.CREATIVE.value:
            self.rule_label.setText("creative：无限跳过，答错不扣生命。")
        else:
            self.rule_label.setText("survival：初始 5 颗心，答错扣心，跳过次数有限。")

    def _create_world(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "创建世界", "请输入 world_name。")
            return
        world = WorldMeta(
            world_name=name,
            world_type=WorldType(self.type_combo.currentText()),
            game_mode=GameMode(self.mode_combo.currentText()),
            difficulty=Difficulty(self.difficulty_combo.currentText()),
        )
        self.world_created.emit(world)
