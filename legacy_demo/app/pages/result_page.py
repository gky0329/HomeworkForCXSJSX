from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QLabel, QHBoxLayout, QVBoxLayout, QWidget

from app.models.session import AppSession
from app.pages.widgets import APP_STYLE, menu_button, title_label
from app.services.audio_manager import AudioManager
from app.theme.config import Colors


class ResultPage(QWidget):
    retry_requested = Signal()
    back_to_worlds_requested = Signal()

    def __init__(self, audio: AudioManager) -> None:
        super().__init__()
        self.audio = audio
        self.setStyleSheet(APP_STYLE)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        self.title = title_label("结算")
        self.summary = QLabel()
        self.summary.setAlignment(Qt.AlignCenter)
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet(f"font-size: 20px; color: {Colors.MUTED};")
        layout.addWidget(self.title)
        layout.addWidget(self.summary)

        actions = QHBoxLayout()
        retry_button = menu_button("重试")
        worlds_button = menu_button("返回世界列表")
        for button in (retry_button, worlds_button):
            button.clicked.connect(self.audio.play_button)
            actions.addWidget(button)
        retry_button.clicked.connect(self.retry_requested.emit)
        worlds_button.clicked.connect(self.back_to_worlds_requested.emit)
        layout.addLayout(actions)

    def set_result(self, session: AppSession, success: bool) -> None:
        total = len(session.current_lesson.questions) if session.current_lesson else 0
        if success:
            self.title.setText("挑战成功")
            self.summary.setText(f"你完成了本关，答对 {session.correct_count}/{total} 题。")
        else:
            self.title.setText("挑战失败")
            self.summary.setText(f"生命值归零。本次答对 {session.correct_count}/{total} 题。")
