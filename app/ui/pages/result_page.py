from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.core.session import AppSession
from app.services.audio_manager import AudioManager
from app.ui.theme.config import Colors
from app.ui.theme.styles import APP_STYLE
from app.ui.widgets.mc_button import McButton


class ResultPage(QWidget):
    back_to_worlds_requested = Signal()
    retry_requested = Signal()

    def __init__(self, audio: AudioManager) -> None:
        super().__init__()
        self.setStyleSheet(APP_STYLE)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        self._status = QLabel()
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet(f"font-size: 48px; font-weight: 900;")

        self._detail = QLabel()
        self._detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail.setStyleSheet(f"font-size: 20px; color: {Colors.CREAM};")

        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)
        retry = McButton("再来一次")
        retry.clicked.connect(self.retry_requested.emit)
        back = McButton("返回世界列表")
        back.clicked.connect(self.back_to_worlds_requested.emit)
        btn_row.addStretch()
        btn_row.addWidget(retry)
        btn_row.addWidget(back)
        btn_row.addStretch()

        layout.addWidget(self._status)
        layout.addWidget(self._detail)
        layout.addLayout(btn_row)

    def set_result(self, session: AppSession, success: bool) -> None:
        if success:
            self._status.setText("✅ 挑战完成!")
            self._status.setStyleSheet(
                f"font-size: 48px; font-weight: 900; color: {Colors.GRASS_LIGHT};"
            )
        else:
            self._status.setText("💀 挑战失败")
            self._status.setStyleSheet(
                f"font-size: 48px; font-weight: 900; color: {Colors.HEART};"
            )

        total = len(session.current_lesson.questions) if session.current_lesson else 0
        self._detail.setText(
            f"正确: {session.correct_count} / {session.answered_count}   "
            f"连击: {session.streak_count}   "
            f"生命: {session.hearts}"
        )
