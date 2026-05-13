from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QLabel, QRadioButton, QVBoxLayout, QWidget,
)

from app.core.session import AppSession
from app.services.audio_manager import AudioManager
from app.ui.theme.config import Colors
from app.ui.theme.styles import APP_STYLE
from app.ui.widgets.health_bar import HealthBar
from app.ui.widgets.mc_button import McButton


class QuizPage(QWidget):
    finished = Signal(bool)

    def __init__(self, audio: AudioManager) -> None:
        super().__init__()
        self.audio = audio
        self.setStyleSheet(APP_STYLE)
        self._session: AppSession | None = None
        self._group = QButtonGroup(self)
        self._options: list[QRadioButton] = []
        self._candidate_btns: list[McButton] = []
        self._selected_candidate: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 24, 40, 24)
        layout.setSpacing(12)

        top = QHBoxLayout()
        self._title = QLabel()
        self._title.setStyleSheet(f"font-size: 22px; font-weight: 900; color: {Colors.CREAM};")
        self._hearts = HealthBar()
        top.addWidget(self._title)
        top.addStretch()
        top.addWidget(self._hearts)

        self._prompt = QLabel()
        self._prompt.setWordWrap(True)
        self._prompt.setStyleSheet(
            f"font-size: 15px; color: {Colors.CREAM}; "
            f"background: {Colors.PANEL_BG}; border: 3px solid {Colors.STONE_DARK}; "
            f"padding: 12px; border-radius: 4px;"
        )

        self._code_area = QLabel()
        self._code_area.setWordWrap(True)
        self._code_area.setStyleSheet(
            f"font-size: 15px; color: #98FB98; font-family: Consolas; "
            f"background: {Colors.CODE_BG}; border: 2px solid {Colors.STONE_DARK}; "
            f"padding: 12px; border-radius: 4px;"
        )
        self._code_area.setVisible(False)

        self._options_area = QVBoxLayout()
        self._candidates_area = QHBoxLayout()
        self._candidates_area.setSpacing(8)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._confirm_btn = McButton("确认")
        self._confirm_btn.clicked.connect(self._on_confirm)
        self._skip_btn = McButton("跳过")
        self._skip_btn.clicked.connect(self._on_skip)
        btn_row.addWidget(self._skip_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._confirm_btn)

        layout.addLayout(top)
        layout.addWidget(self._prompt)
        layout.addWidget(self._code_area)
        layout.addLayout(self._options_area)
        layout.addLayout(self._candidates_area)
        layout.addStretch()
        layout.addLayout(btn_row)

    def set_session(self, session: AppSession) -> None:
        self._session = session
        self._hearts.set_hearts(session.hearts, session.max_hearts)
        self._render_question()

    def _render_question(self) -> None:
        s = self._session
        q = s.current_lesson.questions[s.current_question_index]

        self._title.setText(f"第 {s.current_question_index + 1}/{len(s.current_lesson.questions)} 题")
        self._prompt.setText(q.get("prompt", ""))

        self._clear_options()
        self._code_area.setVisible(False)
        self._clear_candidates()

        if q.get("type") == "code_fill_blank":
            self._render_code_fill(q)
        else:
            self._render_choice(q)

    def _render_choice(self, q: dict) -> None:
        self._title.setText(self._title.text().replace("题", "题 [选择]"))
        for opt in q.get("options", []):
            rb = QRadioButton(f"{opt['id']}. {opt['text']}")
            rb.setStyleSheet(f"font-size: 15px; color: {Colors.CREAM}; padding: 4px;")
            self._group.addButton(rb)
            self._options.append(rb)
            self._options_area.addWidget(rb)

    def _render_code_fill(self, q: dict) -> None:
        self._title.setText(self._title.text().replace("题", "题 [填空]"))
        code = q.get("code", "")
        self._code_area.setText(code)
        self._code_area.setVisible(True)

        for cand in q.get("candidates", []):
            btn = McButton(cand)
            btn.setMinimumWidth(80)
            btn.clicked.connect(lambda checked, c=cand: self._pick_candidate(c))
            self._candidate_btns.append(btn)
            self._candidates_area.addWidget(btn)

    def _pick_candidate(self, val: str) -> None:
        self._selected_candidate = val
        for b in self._candidate_btns:
            b.setProperty("selected", b.text() == val)
            b.style().unpolish(b)
            b.style().polish(b)

    def _on_confirm(self) -> None:
        s = self._session
        q = s.current_lesson.questions[s.current_question_index]
        correct = False

        if q.get("type") == "code_fill_blank":
            correct = self._selected_candidate == q.get("answer", "")
            given = self._selected_candidate or "(未选)"
        else:
            checked = self._group.checkedButton()
            if checked is None:
                return
            given = checked.text()[0]
            correct = given == q.get("answer", "")

        s.answered_count += 1
        if correct:
            s.correct_count += 1
            s.streak_count += 1
            self.audio.play_xp()
        else:
            s.streak_count = 0
            s.hearts -= 1
            self.audio.play_hurt()
            if s.hearts <= 0:
                self.audio.play_death()
                self.finished.emit(False)
                return

        s.current_question_index += 1
        if s.current_question_index >= len(s.current_lesson.questions):
            self.finished.emit(True)
        else:
            self._selected_candidate = None
            self._hearts.set_hearts(s.hearts, s.max_hearts)
            self._render_question()

    def _on_skip(self) -> None:
        s = self._session
        if s.skips_left <= 0:
            return
        s.skips_left -= 1
        s.current_question_index += 1
        if s.current_question_index >= len(s.current_lesson.questions):
            self.finished.emit(True)
        else:
            self._render_question()

    def _clear_options(self) -> None:
        for rb in self._options:
            self._group.removeButton(rb)
            self._options_area.removeWidget(rb)
            rb.deleteLater()
        self._options.clear()

    def _clear_candidates(self) -> None:
        for b in self._candidate_btns:
            self._candidates_area.removeWidget(b)
            b.deleteLater()
        self._candidate_btns.clear()
        self._selected_candidate = None
