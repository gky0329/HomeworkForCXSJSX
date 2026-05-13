import logging
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from app.core.memory_model import MemoryModel
from app.core.step_executor import StepExecutor
from app.core.challenge_loader import Challenge, ChallengeLoader
from app.core.state_diff import StateDiff
from app.ui.canvas.memory_canvas import MemoryCanvas

logger = logging.getLogger("cpplab.challenge_page")


class ChallengePage(QWidget):
    completed = Signal()
    back_requested = Signal()

    def __init__(self, challenge_loader: ChallengeLoader, config=None, parent=None):
        super().__init__(parent)
        self._loader = challenge_loader
        self._config = config
        self._executor = StepExecutor()
        self._model: MemoryModel | None = None
        self._challenge: Challenge | None = None
        self._diffs: list[StateDiff] = []
        self._step_index = 0
        self._started = False
        self._finished = False
        self._input_widgets: list[QLineEdit] = []
        self._code_line_rows: list[QWidget] = []
        self._hint_level = 0

        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(400)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background-color: #181830; }
            QScrollBar:vertical { width: 6px; background: #1a1a2e; }
            QScrollBar::handle:vertical { background: #444; border-radius: 3px; min-height: 30px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        self._teaching_panel = QWidget()
        self._teaching_panel.setStyleSheet("background-color: #181830;")
        self._teaching_layout = QVBoxLayout(self._teaching_panel)
        self._teaching_layout.setContentsMargins(16, 16, 16, 16)
        self._teaching_layout.setSpacing(10)
        scroll.setWidget(self._teaching_panel)
        layout.addWidget(scroll)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)

        self._canvas = MemoryCanvas(config=self._config)
        self._canvas._animator.set_on_all_finished(self._on_animations_done)
        right.addWidget(self._canvas, 1)

        self._step_bar = QWidget()
        self._step_bar.setFixedHeight(48)
        self._step_bar.setStyleSheet("background-color: #1a1a30;")
        bar_layout = QHBoxLayout(self._step_bar)
        bar_layout.setContentsMargins(12, 4, 12, 4)

        self._back_btn = self._make_btn("← 返回", "#333", "#555")
        self._reset_btn = self._make_btn("重置", "#444", "#666")
        self._step_prev_btn = self._make_btn("◀", "#444", "#666")
        self._step_btn = self._make_btn("▶ 下一步", "#E8A840", "#F0B850")
        self._step_prev_btn.setFixedWidth(36)

        self._back_btn.clicked.connect(self.back_requested.emit)
        self._reset_btn.clicked.connect(self._on_reset)
        self._step_prev_btn.clicked.connect(self._on_step_prev)
        self._step_btn.clicked.connect(self._on_step)

        bar_layout.addWidget(self._back_btn)
        bar_layout.addStretch()
        bar_layout.addWidget(self._reset_btn)
        bar_layout.addWidget(self._step_prev_btn)
        bar_layout.addWidget(self._step_btn)
        right.addWidget(self._step_bar)

        right_widget = QWidget()
        right_widget.setLayout(right)
        layout.addWidget(right_widget, 1)

    def _make_btn(self, text: str, bg: str, hover: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg}; color: #ddd; border: none;
                border-radius: 4px; padding: 6px 14px; font-size: 12px;
                font-family: "Microsoft YaHei";
            }}
            QPushButton:hover {{ background-color: {hover}; }}
            QPushButton:disabled {{ background-color: #2a2a2a; color: #555; }}
        """)
        return btn

    def _on_animations_done(self):
        self._step_btn.setEnabled(True)

    def load_challenge(self, challenge_id: str):
        self._challenge = self._loader.load(challenge_id)
        self._on_reset()

    def _on_reset(self):
        self._model = MemoryModel()
        self._diffs = []
        self._step_index = 0
        self._started = False
        self._finished = False
        self._input_widgets.clear()
        self._code_line_rows.clear()
        self._hint_level = 0
        self._canvas.reset()
        self._rebuild_teaching()
        self._step_btn.setText("▶ 下一步")
        self._step_btn.setEnabled(True)
        self._step_btn.setStyleSheet(self._make_btn("▶ 下一步", "#E8A840", "#F0B850").styleSheet())
        self._step_prev_btn.setEnabled(False)

    def _clear_teaching(self):
        while self._teaching_layout.count():
            item = self._teaching_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()

    def _rebuild_teaching(self):
        self._clear_teaching()
        ch = self._challenge
        if not ch:
            return

        font_body = QFont("Microsoft YaHei", 10)
        font_title = QFont("Microsoft YaHei", 16, QFont.Bold)
        font_section = QFont("Microsoft YaHei", 11, QFont.Bold)

        title = QLabel(ch.title)
        title.setFont(font_title)
        title.setStyleSheet("color: #E8A840; padding: 4px 0;")
        title.setWordWrap(True)
        self._teaching_layout.addWidget(title)

        if ch.learning_objectives:
            self._teaching_layout.addWidget(self._section_header("🎯 学习目标"))
            for obj in ch.learning_objectives:
                lbl = QLabel(f"  • {obj}")
                lbl.setFont(font_body)
                lbl.setStyleSheet("color: #bbb; padding: 1px 0;")
                lbl.setWordWrap(True)
                self._teaching_layout.addWidget(lbl)

        if ch.theory:
            self._teaching_layout.addWidget(self._section_header("📖 概念讲解"))
            for para in ch.theory.split("\n\n"):
                para = para.strip()
                if not para:
                    continue
                theory_lbl = QLabel(para)
                theory_lbl.setFont(font_body)
                theory_lbl.setStyleSheet("color: #ccc; line-height: 1.6; padding: 2px 0;")
                theory_lbl.setWordWrap(True)
                self._teaching_layout.addWidget(theory_lbl)

        if ch.key_points:
            self._teaching_layout.addWidget(self._section_header("💡 关键点"))
            for kp in ch.key_points:
                kp_lbl = QLabel(f"  ● {kp}")
                kp_lbl.setFont(font_body)
                kp_lbl.setStyleSheet(
                    "color: #F0D080; background: #2a2a20; border-radius: 4px; padding: 4px 8px;"
                )
                kp_lbl.setWordWrap(True)
                self._teaching_layout.addWidget(kp_lbl)

        if ch.task:
            self._teaching_layout.addWidget(self._section_header("🛠️ 任务"))
            task_lbl = QLabel(ch.task)
            task_lbl.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
            task_lbl.setStyleSheet(
                "color: #FFD700; background: #2a2a10; border-left: 3px solid #E8A840; "
                "border-radius: 3px; padding: 6px 10px; margin: 4px 0;"
            )
            task_lbl.setWordWrap(True)
            self._teaching_layout.addWidget(task_lbl)

        if ch.show_code and ch.initial_code:
            self._teaching_layout.addWidget(self._section_header("💻 代码"))
            self._code_container = QWidget()
            self._code_container.setStyleSheet("background-color: #111122; border-radius: 6px; padding: 6px;")
            self._code_layout = QVBoxLayout(self._code_container)
            self._code_layout.setSpacing(1)
            self._code_layout.setContentsMargins(6, 6, 6, 6)
            self._build_code_panel()
            self._teaching_layout.addWidget(self._code_container)

        if ch.hints:
            self._hint_level = 0
            self._hint_container = QWidget()
            hint_outer = QVBoxLayout(self._hint_container)
            hint_outer.setContentsMargins(0, 8, 0, 0)

            self._hint_btn = QPushButton("💡 需要提示？")
            self._hint_btn.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #888; border: 1px dashed #444;
                    border-radius: 4px; padding: 6px; font-size: 11px;
                    font-family: "Microsoft YaHei";
                }
                QPushButton:hover { color: #E8A840; border-color: #E8A840; }
                QPushButton:disabled { color: #555; border-color: #333; }
            """)
            self._hint_btn.clicked.connect(self._show_next_hint)
            hint_outer.addWidget(self._hint_btn)

            self._hint_label = QLabel("")
            self._hint_label.setFont(font_body)
            self._hint_label.setStyleSheet("color: #aaa; padding: 4px 0;")
            self._hint_label.setWordWrap(True)
            self._hint_label.setVisible(False)
            hint_outer.addWidget(self._hint_label)

            self._teaching_layout.addWidget(self._hint_container)

        self._teaching_layout.addStretch()

    def _section_header(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        lbl.setStyleSheet("color: #4A90D9; border-bottom: 1px solid #2a2a3e; padding: 10px 0 2px 0;")
        return lbl

    def _build_code_panel(self):
        self._input_widgets.clear()
        self._code_line_rows.clear()
        while self._code_layout.count():
            item = self._code_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._challenge:
            return

        code = self._challenge.initial_code
        blanks = {b.line: b for b in self._challenge.blanks}
        notes = self._challenge.code_line_notes
        code_font = QFont("Consolas, monospace", 11)
        note_font = QFont("Consolas, monospace", 9)

        for i, line in enumerate(code):
            row = QHBoxLayout()
            row.setSpacing(4)
            row.setContentsMargins(0, 1, 0, 1)

            line_no = QLabel(f"{i+1:>2}")
            line_no.setFont(code_font)
            line_no.setFixedWidth(22)
            line_no.setStyleSheet("color: #555; background: transparent;")
            row.addWidget(line_no)

            if i in blanks:
                blank = blanks[i]
                parts = line.split(blank.placeholder, 1)
                prefix = parts[0] if len(parts) > 0 else ""
                suffix = parts[1] if len(parts) > 1 else ""

                if prefix:
                    pl = QLabel(prefix)
                    pl.setFont(code_font)
                    pl.setStyleSheet("color: #ccc; background: transparent;")
                    row.addWidget(pl)

                inp = QLineEdit()
                inp.setFont(code_font)
                inp.setPlaceholderText("输入代码...")
                inp.setFixedWidth(max(blank.width_chars * 10, 130))
                inp.setStyleSheet("""
                    QLineEdit {
                        background-color: #1a1a30; color: #FFD700;
                        border: 1px solid #E8A840; border-radius: 3px;
                        padding: 2px 6px; font-family: "Consolas", monospace;
                    }
                    QLineEdit:focus { border-color: #F0B850; }
                """)
                self._input_widgets.append(inp)
                row.addWidget(inp)

                if suffix:
                    sl = QLabel(suffix)
                    sl.setFont(code_font)
                    sl.setStyleSheet("color: #ccc; background: transparent;")
                    row.addWidget(sl)
            else:
                ll = QLabel(line)
                ll.setFont(code_font)
                ll.setStyleSheet("color: #ccc; background: transparent;")
                row.addWidget(ll)

            note_key = str(i)
            if note_key in notes:
                note = QLabel(f"  // {notes[note_key]}")
                note.setFont(note_font)
                note.setStyleSheet("color: #6a8; background: transparent;")
                row.addWidget(note)

            row.addStretch()
            container = QWidget()
            container.setLayout(row)
            container.setStyleSheet("background: transparent;")
            self._code_line_rows.append(container)
            self._code_layout.addWidget(container)

        self._code_layout.addStretch()

    def _highlight_line(self, line_idx: int):
        for i, row_widget in enumerate(self._code_line_rows):
            if i == line_idx:
                row_widget.setStyleSheet(
                    "background-color: rgba(232,168,64,0.15); border-left: 3px solid #E8A840;"
                )
            else:
                row_widget.setStyleSheet("background: transparent;")

    def _clear_highlight(self):
        for row_widget in self._code_line_rows:
            row_widget.setStyleSheet("background: transparent;")

    def _show_next_hint(self):
        if not self._challenge or not self._challenge.hints:
            return
        if self._hint_level < len(self._challenge.hints):
            hint_text = self._challenge.hints[self._hint_level]
            self._hint_level += 1
            self._hint_label.setText(f"💬 {hint_text}")
            self._hint_label.setVisible(True)
            left = len(self._challenge.hints) - self._hint_level
            self._hint_btn.setText(
                f"💡 还需要提示？({left}条剩余)" if left > 0 else "💡 已显示全部提示"
            )
            if self._hint_level >= len(self._challenge.hints):
                self._hint_btn.setEnabled(False)

    def _assemble_code(self) -> list[str]:
        if not self._challenge:
            return []
        code = self._challenge.initial_code
        blanks = {b.line: b for b in self._challenge.blanks}
        lines: list[str] = []
        input_idx = 0
        for i, line in enumerate(code):
            if i in blanks:
                user_input = self._input_widgets[input_idx].text().strip()
                blank = blanks[i]
                lines.append(line.replace(blank.placeholder, user_input))
                input_idx += 1
            else:
                lines.append(line)
        return lines

    def _on_step(self):
        if self._finished:
            return
        if self._canvas.is_animating:
            self._step_btn.setEnabled(False)
            return

        ch = self._challenge
        if not ch:
            return

        if not self._started:
            self._model = MemoryModel()
            self._diffs = []
            self._step_index = 0
            self._started = True
            self._canvas.reset()

        code_lines = self._assemble_code()

        if self._step_index >= len(code_lines):
            self._on_finish()
            return

        line = code_lines[self._step_index]
        diff = self._executor.execute_line(line, self._model, line_no=self._step_index + 1)
        self._diffs.append(diff)

        self._step_btn.setEnabled(False)
        self._highlight_line(self._step_index)
        self._canvas.apply_diff(diff, animate=True)
        self._step_index += 1

        if self._step_index >= len(code_lines):
            self._step_btn.setText("✓ 检测目标")
            self._step_btn.setStyleSheet(self._make_btn("✓ 检测目标", "#E8A840", "#F0B850").styleSheet())
        else:
            next_line = code_lines[self._step_index].strip()[:28]
            self._step_btn.setText(f"▶ 下一步 (行 {self._step_index+1})")

    def _on_step_prev(self):
        pass

    def _on_finish(self):
        self._finished = True
        self._clear_highlight()

        if not self._model or not self._challenge:
            return

        passed, details = ChallengeLoader.check_goal(self._challenge, self._model, self._diffs)

        if passed:
            self._step_btn.setText("✓ 已通关")
            self._step_btn.setStyleSheet(self._make_btn("✓ 已通关", "#3a7a3a", "#4a8a4a").styleSheet())
            self._step_btn.setEnabled(False)
            self.completed.emit()
        else:
            detail_text = "；".join(details) if details else "未达到目标状态"
            guidance = self._challenge.failure_guidance or "请检查代码并重试"
            self._show_result(f"✗ 未通过\n\n{detail_text}\n\n{guidance}", False)
            self._started = False
            self._finished = False
            self._step_btn.setText("▶ 重试")
            self._step_btn.setStyleSheet(self._make_btn("▶ 重试", "#E8A840", "#F0B850").styleSheet())

    def _show_result(self, text, success):
        QMessageBox.information(self, "结果", text)
