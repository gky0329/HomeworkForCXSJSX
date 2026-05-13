from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QLabel, QHBoxLayout, QVBoxLayout, QWidget

from app.models.session import Lesson
from app.pages.widgets import APP_STYLE, menu_button, title_label
from app.services.audio_manager import AudioManager
from app.theme.config import Colors


class LessonIntroPage(QWidget):
    start_requested = Signal()
    back_requested = Signal()

    def __init__(self, audio: AudioManager) -> None:
        super().__init__()
        self.audio = audio
        self.setStyleSheet(APP_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(85, 55, 85, 55)
        self.title = title_label("课程")
        layout.addWidget(self.title)

        self.dialogue_box = QLabel()
        self.dialogue_box.setWordWrap(True)
        self.dialogue_box.setAlignment(Qt.AlignTop)
        self.dialogue_box.setObjectName("mcPanel")
        self.dialogue_box.setStyleSheet(
            f"background: {Colors.PANEL_BG}; border: 4px solid {Colors.STONE_DARK}; padding: 20px;"
        )
        layout.addWidget(self.dialogue_box, 1)

        actions = QHBoxLayout()
        start_button = menu_button("开始挑战")
        back_button = menu_button("返回世界")
        for button in (start_button, back_button):
            button.clicked.connect(self.audio.play_button)
            actions.addWidget(button)
        start_button.clicked.connect(self.start_requested.emit)
        back_button.clicked.connect(self.back_requested.emit)
        layout.addLayout(actions)

    def set_lesson(self, lesson: Lesson) -> None:
        self.title.setText(lesson.title)
        lines = []
        for item in lesson.npc_dialogue:
            speaker = "村民" if item.get("npc") == "villager" else "铁傀儡"
            lines.append(f"{speaker}: {item.get('text', '')}")
        self.dialogue_box.setText("\n\n".join(lines))
