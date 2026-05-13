from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton, QRadioButton, QVBoxLayout

from app.models.session import AppSession, Difficulty, GameMode
from app.pages.widgets import APP_STYLE, menu_button
from app.services.audio_manager import AudioManager
from app.theme.config import Colors
from app.widgets.health_bar import HealthBar
from app.widgets.mc_button import McButton
from app.widgets.panorama_background import PanoramaBackground


class QuizPage(PanoramaBackground):
    finished = Signal(bool)

    def __init__(self, audio: AudioManager) -> None:
        super().__init__(dim=86, blur_like=True)
        self.audio = audio
        self.session: AppSession | None = None
        self.selected_answer: str | None = None
        self.option_buttons: list[QPushButton] = []
        self.radio_group = QButtonGroup(self)
        self.radio_group.setExclusive(True)
        self.setStyleSheet(APP_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(130, 38, 130, 45)
        root.setSpacing(18)

        top = QHBoxLayout()
        self.health_bar = HealthBar()
        self.skip_label = QLabel()
        self.progress = QProgressBar()
        top.addWidget(self.health_bar)
        top.addWidget(self.progress, 1)
        top.addWidget(self.skip_label)
        root.addLayout(top)

        pause_title = QLabel("编程挑战")
        pause_title.setAlignment(Qt.AlignCenter)
        pause_title.setStyleSheet("font-size: 28px; color: white;")
        root.addWidget(pause_title)

        question_panel = QFrame()
        question_panel.setObjectName("mcPanel")
        question_panel.setStyleSheet("background: rgba(0,0,0,150); border: 3px solid white;")
        question_layout = QVBoxLayout(question_panel)
        self.question_label = QLabel()
        self.question_label.setWordWrap(True)
        self.question_label.setStyleSheet("font-size: 22px; font-weight: 700;")
        question_layout.addWidget(self.question_label)
        root.addWidget(question_panel)

        self.answer_area = QVBoxLayout()
        root.addLayout(self.answer_area, 1)

        actions = QHBoxLayout()
        self.submit_button = menu_button("提交")
        self.skip_button = menu_button("跳过")
        for button in (self.submit_button, self.skip_button):
            button.clicked.connect(self.audio.play_button)
            actions.addWidget(button)
        self.submit_button.clicked.connect(self._submit)
        self.skip_button.clicked.connect(self._skip)
        root.addLayout(actions)

    def set_session(self, session: AppSession) -> None:
        self.session = session
        self.audio.play_quiz_music(critical=False)
        self._render_question()

    def _render_question(self) -> None:
        if not self.session or not self.session.current_lesson:
            return
        lesson = self.session.current_lesson
        if self.session.current_question_index >= len(lesson.questions):
            self.finished.emit(True)
            return

        question = lesson.questions[self.session.current_question_index]
        self.selected_answer = None
        self._clear_answers()
        self._update_status()
        self.question_label.setText(question["prompt"])

        if question["type"] == "single_choice":
            self._render_single_choice(question)
        elif question["type"] == "code_fill_blank":
            self._render_code_fill_blank(question)

    def _render_single_choice(self, question: dict) -> None:
        self.radio_group = QButtonGroup(self)
        for option in question["options"]:
            radio = QRadioButton(f"{option['id']}. {option['text']}")
            radio.setStyleSheet(
                f"background: rgba(0,0,0,125); border: 3px solid {Colors.STONE_DARK}; "
                "padding: 12px; font-size: 18px;"
            )
            radio.toggled.connect(lambda checked, answer=option["id"]: self._choose(answer, checked))
            self.radio_group.addButton(radio)
            self.answer_area.addWidget(radio)

    def _render_code_fill_blank(self, question: dict) -> None:
        code = QLabel(question["code"])
        code.setTextInteractionFlags(Qt.TextSelectableByMouse)
        code.setStyleSheet(
            f"font-family: Consolas, monospace; background: {Colors.CODE_BG}; "
            f"border: 3px solid {Colors.STONE_DARK}; padding: 16px;"
        )
        self.answer_area.addWidget(code)
        hint = QLabel("选择填入空白处的代码：")
        self.answer_area.addWidget(hint)
        for candidate in question["candidates"]:
            button = McButton(candidate)
            button.clicked.connect(self.audio.play_button)
            button.clicked.connect(lambda _, answer=candidate: self._choose_button(answer))
            self.option_buttons.append(button)
            self.answer_area.addWidget(button)

    def _choose(self, answer: str, checked: bool) -> None:
        if checked:
            self.selected_answer = answer

    def _choose_button(self, answer: str) -> None:
        self.selected_answer = answer
        for button in self.option_buttons:
            button.setProperty("selected", button.text() == answer)
            button.style().unpolish(button)
            button.style().polish(button)

    def _submit(self) -> None:
        if not self.session or not self.session.current_lesson:
            return
        if self.selected_answer is None:
            QMessageBox.information(self, "提交", "请先选择一个答案。")
            return
        question = self.session.current_lesson.questions[self.session.current_question_index]
        is_correct = self.selected_answer == question["answer"]
        self._finish_current_question(is_correct)

    def _skip(self) -> None:
        if not self.session:
            return
        if self.session.skips_left <= 0:
            QMessageBox.warning(self, "跳过", "跳过次数已经用完。")
            return
        self.session.skips_left -= 1
        self._advance()

    def _finish_current_question(self, is_correct: bool) -> None:
        assert self.session is not None
        self.session.answered_count += 1
        if is_correct:
            self.session.correct_count += 1
            self.session.streak_count += 1
            self.audio.play_xp()
            if self.session.streak_count > 0 and self.session.streak_count % 3 == 0:
                self.audio.play_level_up()
            QMessageBox.information(self, "结果", "回答正确！")
        else:
            self.session.streak_count = 0
            QMessageBox.warning(self, "结果", "回答错误。")
            if not self.session.is_creative():
                self.session.hearts -= 1
                self.audio.play_hurt()
        world = self.session.current_world
        if (
            world
            and world.game_mode != GameMode.CREATIVE
            and world.difficulty == Difficulty.PEACEFUL
            and self.session.answered_count % 2 == 0
        ):
            self.session.hearts = min(self.session.max_hearts, self.session.hearts + 1)
        if self.session.hearts <= 0:
            self.audio.play_death()
            self.finished.emit(False)
            return
        self._advance()

    def _advance(self) -> None:
        assert self.session is not None
        self.session.current_question_index += 1
        self._render_question()

    def _update_status(self) -> None:
        assert self.session and self.session.current_lesson
        total = len(self.session.current_lesson.questions)
        index = self.session.current_question_index + 1
        skips = "∞" if self.session.is_creative() else str(self.session.skips_left)
        self.health_bar.set_hearts(self.session.hearts, min(self.session.max_hearts, 10), self.session.is_creative())
        self.skip_label.setText(f"跳过: {skips}")
        self.progress.setMaximum(total)
        self.progress.setValue(index - 1)
        self.progress.setFormat(f"{index}/{total}")
        self.audio.play_quiz_music(critical=not self.session.is_creative() and self.session.hearts < 2)

    def _clear_answers(self) -> None:
        while self.answer_area.count():
            item = self.answer_area.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.option_buttons.clear()
