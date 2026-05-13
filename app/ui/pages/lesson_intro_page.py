from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.core.session import Lesson
from app.services.audio_manager import AudioManager
from app.ui.theme.config import Colors
from app.ui.theme.styles import APP_STYLE
from app.ui.widgets.mc_button import McButton


NPC_COLORS = {"villager": "#8B7355", "iron_golem": "#C0C0C0"}


class LessonIntroPage(QWidget):
    back_requested = Signal()
    start_requested = Signal()

    def __init__(self, audio: AudioManager) -> None:
        super().__init__()
        self.setStyleSheet(APP_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 40, 60, 40)
        layout.setSpacing(16)

        self._title = QLabel()
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setStyleSheet(f"font-size: 32px; font-weight: 900; color: {Colors.CREAM};")

        self._dialogue = QLabel()
        self._dialogue.setWordWrap(True)
        self._dialogue.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._dialogue.setStyleSheet(
            f"font-size: 15px; color: {Colors.CREAM}; "
            f"background: {Colors.PANEL_BG}; border: 3px solid {Colors.STONE_DARK}; "
            f"padding: 16px; border-radius: 6px;"
        )
        self._dialogue.setMinimumHeight(200)

        btn_row = QHBoxLayout()
        back = McButton("返回")
        back.clicked.connect(self.back_requested.emit)
        start = McButton("开始挑战")
        start.clicked.connect(audio.play_button)
        start.clicked.connect(self.start_requested.emit)
        btn_row.addWidget(back)
        btn_row.addStretch()
        btn_row.addWidget(start)

        layout.addWidget(self._title)
        layout.addWidget(self._dialogue)
        layout.addStretch()
        layout.addLayout(btn_row)

    def set_lesson(self, lesson: Lesson) -> None:
        self._title.setText(lesson.title)
        lines = []
        for d in lesson.npc_dialogue:
            npc = d.get("npc", "???")
            color = NPC_COLORS.get(npc, Colors.CREAM)
            text = d.get("text", "")
            lines.append(
                f'<span style="color:{color}; font-weight:900;">[{npc}]</span> '
                f'<span style="color:{Colors.CREAM};">{text}</span>'
            )
        self._dialogue.setText("<br><br>".join(lines))
