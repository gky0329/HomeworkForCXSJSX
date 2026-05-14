from __future__ import annotations

from PySide6.QtCore import Qt, QRegularExpression, QTimer, Signal
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from app.core.challenge_loader import ChallengeLoader
from app.core.engine import Engine
from app.services.app_settings import AppSettings
from app.services.audio_manager import AudioManager
from app.ui.canvas.oop_canvas import OopCanvas
from app.ui.canvas.canvas_animator import CanvasAnimator
from app.ui.theme.config import Colors
from app.ui.theme.styles import APP_STYLE
from app.ui.widgets.health_bar import HealthBar
from app.ui.widgets.mc_button import McButton
from app.ui.widgets.ai_help_dialog import AiHelpDialog, AiHelpPayload


_VALIDATORS = {
    "cpp_keyword": QRegularExpression(r"^[A-Za-z_]+$"),
    "cpp_access":  QRegularExpression(r"^(public|private|protected)$"),
    "identifier":  QRegularExpression(r"^[A-Za-z_][A-Za-z0-9_]*$"),
    "number":      QRegularExpression(r"^\d+$"),
    "any":         QRegularExpression(r"^.+$"),
}

_S_INPUT = (
    f"QLineEdit {{ background: {Colors.CODE_BG}; color: {Colors.GOLD}; "
    f"font-family: Consolas; font-size: 16px; font-weight: 900; "
    f"border: 2px solid {Colors.GOLD}; border-radius: 3px; padding: 4px 10px; }}"
)
_S_INPUT_OFF = (
    f"QLineEdit {{ background: {Colors.DISABLED_BG}; color: {Colors.DISABLED_TEXT}; "
    f"font-family: Consolas; font-size: 16px; font-weight: 900; "
    f"border: 2px solid {Colors.DISABLED_BORDER}; border-radius: 3px; padding: 4px 10px; }}"
)
_S_CODE = (
    f"color: #98FB98; font-family: Consolas; font-size: 16px; background: transparent; padding: 2px 0;"
)
_NPC_COLORS = {"villager": "#C8A96E", "iron_golem": "#C0C0C0", "steve": "#5B8FB7"}


def _btn_c(color: str) -> str:
    return (
        f"QPushButton {{ background: {color}; color: white; font-weight: 700; "
        f"font-size: 14px; padding: 8px 18px; border: 2px solid {Colors.BLACK}; border-radius: 3px; }}"
        f"QPushButton:hover {{ background: {Colors.GOLD}; color: {Colors.BLACK}; }}"
        f"QPushButton:disabled {{ background: {Colors.DISABLED_BG}; color: {Colors.DISABLED_TEXT}; }}"
    )


class ChallengePage(QWidget):
    back_requested = Signal()

    def __init__(self, loader: ChallengeLoader, engine: Engine, audio: AudioManager, settings: AppSettings) -> None:
        super().__init__()
        self.loader = loader
        self.engine = engine
        self.audio = audio
        self.settings = settings
        self._animator = CanvasAnimator()
        self._level: dict | None = None
        self._level_id: str = ""
        self._inputs: list[QLineEdit] = []
        self._hint_lines: list[str] = []
        self._ai_dialog = AiHelpDialog(self)
        self._blank_count = 0
        self._current_blank = 0
        self.hearts = 5
        self.streak = 0
        self.setStyleSheet(APP_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(0)

        self._phases = QStackedWidget()
        root.addWidget(self._phases)

        self._intro_w = self._build_intro()
        self._code_w = self._build_code_panel()
        self._phases.addWidget(self._intro_w)
        self._phases.addWidget(self._code_w)

        ids = self.loader.list_ids()
        if ids:
            self.load_level(ids[0])
        else:
            self._title_lb.setText("暂无关卡")

    def load_level(self, level_id: str) -> None:
        self._level_id = level_id
        self._level = self.loader.load(level_id)
        if not self._level:
            self._title_lb.setText("关卡加载失败")
            return
        lv = self._level
        self._title_lb.setText(f"⛏ {lv['title']}")
        self._theory_lb.setText(lv.get("theory", ""))
        pts = lv.get("key_points", [])
        self._key_points_lb.setText("\n".join(f"• {p}" for p in pts) if pts else "")
        self._hint_lb.setVisible(False)
        self._hint_index = 0
        self._hint_lines = []
        self._result_lb.setVisible(False)
        self._result_btns.setVisible(False)
        self._step_btn.setVisible(True)
        self._reset_btn.setVisible(True)
        self._hint_btn.setVisible(True)
        self._current_blank = 0
        self.hearts = 5
        self.streak = 0
        self._hearts.set_hearts(self.hearts, 5)
        self._canvas.reset()
        self.engine.reset()
        self._animator.reset()

        dialogue = lv.get("npc_dialogue")
        if dialogue:
            self._show_intro(lv)
        else:
            self._start_code()
        self._update_nav_btns()

    def _show_intro(self, lv: dict) -> None:
        dialogue = lv.get("npc_dialogue", [])
        if dialogue:
            self._intro_title.setText(lv["title"])
            lines = []
            for d in dialogue:
                npc = d.get("npc", "???")
                color = _NPC_COLORS.get(npc, Colors.CREAM)
                lines.append(
                    f'<span style="color:{color};font-weight:900;">[{npc}]</span> '
                    f'<span style="color:{Colors.CREAM};">{d.get("text", "")}</span>'
                )
            self._intro_dialogue.setText("<br><br>".join(lines))
        self._phases.setCurrentWidget(self._intro_w)

    def _on_start_challenge(self) -> None:
        self._start_code()

    def _start_code(self) -> None:
        self._clear_code()
        self._inputs = []
        lv = self._level
        if lv and lv.get("initial_code"):
            self._render_code(lv["initial_code"], lv.get("blanks", []))
        self._blank_count = len(self._inputs)
        self._current_blank = 0
        self._canvas.reset()
        self.engine.reset()
        self._animator.reset()
        self.hearts = 5
        self.streak = 0
        self._hearts.set_hearts(self.hearts, 5)
        self._result_lb.setVisible(False)
        self._result_btns.setVisible(False)
        self._step_btn.setVisible(True)
        self._reset_btn.setVisible(True)
        self._hint_btn.setVisible(True)
        self._update_blanks_state()
        self._update_status()
        self._phases.setCurrentWidget(self._code_w)

    def _update_nav_btns(self) -> None:
        ids = self.loader.list_ids()
        idx = ids.index(self._level_id) if self._level_id in ids else -1
        self._prev_level_btn.setEnabled(idx > 0)
        self._next_level_btn.setEnabled(idx >= 0 and idx < len(ids) - 1)
        if idx > 0:
            prev = self.loader.load_index()[idx - 1]
            self._prev_level_btn.setToolTip(f"上一关: {prev.get('title', ids[idx-1])}")
        if idx >= 0 and idx < len(ids) - 1:
            nxt = self.loader.load_index()[idx + 1]
            self._next_level_btn.setToolTip(f"下一关: {nxt.get('title', ids[idx+1])}")

    def _prev_level(self) -> None:
        ids = self.loader.list_ids()
        idx = ids.index(self._level_id) if self._level_id in ids else -1
        if idx > 0:
            self.load_level(ids[idx - 1])

    def _next_level(self) -> None:
        ids = self.loader.list_ids()
        idx = ids.index(self._level_id) if self._level_id in ids else -1
        if idx >= 0 and idx < len(ids) - 1:
            self.load_level(ids[idx + 1])

    def _build_intro(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(30, 20, 30, 20)
        l.setSpacing(12)
        self._intro_title = QLabel()
        self._intro_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._intro_title.setStyleSheet(f"font-size: 28px; font-weight: 900; color: {Colors.CREAM};")
        self._intro_dialogue = QLabel()
        self._intro_dialogue.setWordWrap(True)
        self._intro_dialogue.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._intro_dialogue.setStyleSheet(
            f"font-size: 15px; color: {Colors.CREAM}; "
            f"background: {Colors.PANEL_BG}; border: 3px solid {Colors.STONE_DARK}; "
            f"padding: 16px; border-radius: 6px;"
        )
        btn = QPushButton("开始挑战 →")
        btn.setStyleSheet(_btn_c(Colors.GRASS))
        btn.clicked.connect(self._on_start_challenge)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn)
        l.addWidget(self._intro_title)
        l.addWidget(self._intro_dialogue)
        l.addLayout(btn_row)
        return w

    def _build_code_panel(self) -> QWidget:
        w = QWidget()
        pair = QHBoxLayout(w)
        pair.setContentsMargins(0, 0, 0, 0)
        pair.setSpacing(12)
        self._left = self._build_left()
        self._right = self._build_right()
        pair.addWidget(self._left, stretch=3)
        pair.addWidget(self._right, stretch=4)
        return w

    def _build_left(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        top_bar = QHBoxLayout()
        self._prev_level_btn = QPushButton("<")
        self._prev_level_btn.setStyleSheet(_btn_c(Colors.STONE) + "font-size:18px;padding:4px 12px;")
        self._prev_level_btn.setFixedWidth(60)
        self._prev_level_btn.clicked.connect(self._prev_level)
        self._next_level_btn = QPushButton(">")
        self._next_level_btn.setStyleSheet(_btn_c(Colors.STONE) + "font-size:18px;padding:4px 12px;")
        self._next_level_btn.setFixedWidth(60)
        self._next_level_btn.clicked.connect(self._next_level)
        self._title_lb = QLabel()
        self._title_lb.setStyleSheet(f"font-size: 24px; font-weight: 900; color: {Colors.CREAM}; padding: 4px 0;")

        self._hearts = HealthBar(5)
        self._hearts.setFixedSize(130, 30)

        top_bar.addWidget(self._prev_level_btn)
        top_bar.addWidget(self._title_lb)
        top_bar.addStretch()
        top_bar.addWidget(self._hearts)
        top_bar.addWidget(self._next_level_btn)

        self._theory_lb = QLabel()
        self._theory_lb.setWordWrap(True)
        self._theory_lb.setStyleSheet(
            f"font-size: 14px; color: {Colors.MUTED}; "
            f"background: {Colors.PANEL_BG}; border: 3px solid {Colors.STONE_DARK}; "
            f"padding: 10px; border-radius: 4px;"
        )
        self._key_points_lb = QLabel()
        self._key_points_lb.setWordWrap(True)
        self._key_points_lb.setStyleSheet(f"font-size: 13px; color: {Colors.GOLD}; padding: 2px 8px; font-weight: 700;")
        self._hint_lb = QLabel()
        self._hint_lb.setWordWrap(True)
        self._hint_lb.setStyleSheet(
            f"font-size: 13px; color: {Colors.GOLD}; background: rgba(0,0,0,120); "
            f"padding: 8px; border-radius: 2px;"
        )
        self._hint_lb.setVisible(False)
        self._hint_index = 0
        self._hint_lines = []

        code_frame = QWidget()
        code_frame.setStyleSheet(
            f"background: {Colors.CODE_BG}; border: 3px solid {Colors.STONE_DARK}; "
            f"border-radius: 4px; padding: 10px;"
        )
        self._code_layout = QVBoxLayout(code_frame)
        self._code_layout.setContentsMargins(10, 10, 10, 10)
        self._code_layout.setSpacing(2)

        self._status_lb = QLabel()
        self._status_lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lb.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {Colors.MUTED}; padding: 4px;")
        self._result_lb = QLabel()
        self._result_lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_lb.setStyleSheet("font-size: 15px; font-weight: 900; padding: 8px; border-radius: 4px;")
        self._result_lb.setVisible(False)

        self._result_btns = QWidget()
        self._result_btns.setVisible(False)
        rb_layout = QHBoxLayout(self._result_btns)
        rb_layout.setContentsMargins(0, 0, 0, 0)
        rb_layout.setSpacing(8)
        retry_btn = McButton("🔄 重试")
        retry_btn.clicked.connect(self._on_retry)
        self._next_btn = McButton("下一关 ▶")
        self._next_btn.clicked.connect(self._to_next_level)
        rb_layout.addStretch()
        rb_layout.addWidget(retry_btn)
        rb_layout.addWidget(self._next_btn)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        back = QPushButton("← 返回")
        back.setStyleSheet(_btn_c(Colors.STONE))
        back.clicked.connect(self.back_requested.emit)
        self._hint_btn = QPushButton("? 提示")
        self._hint_btn.setStyleSheet(_btn_c(Colors.OAK))
        self._hint_btn.clicked.connect(self._show_next_hint)
        self._step_btn = McButton("▶ 下一步")
        self._step_btn.setEnabled(False)
        self._step_btn.clicked.connect(self._on_step)
        self._reset_btn = McButton("↺ 重置")
        self._reset_btn.clicked.connect(self._on_reset)
        btn_row.addWidget(back)
        btn_row.addWidget(self._hint_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._reset_btn)
        btn_row.addWidget(self._step_btn)

        layout.addLayout(top_bar)
        layout.addWidget(self._theory_lb)
        layout.addWidget(self._key_points_lb)
        layout.addWidget(self._hint_lb)
        layout.addWidget(code_frame)
        layout.addWidget(self._status_lb)
        layout.addWidget(self._result_lb)
        layout.addWidget(self._result_btns)
        layout.addStretch()
        layout.addLayout(btn_row)
        return panel

    def _build_right(self) -> QWidget:
        panel = QWidget()
        l = QVBoxLayout(panel)
        l.setContentsMargins(0, 0, 0, 0)
        self._canvas = OopCanvas()
        l.addWidget(self._canvas)
        return panel

    def _clear_code(self) -> None:
        while self._code_layout.count():
            item = self._code_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            sub = item.layout()
            if sub:
                while sub.count():
                    si = sub.takeAt(0)
                    sw = si.widget()
                    if sw:
                        sw.deleteLater()

    def _render_code(self, code_lines: list[str], blanks: list[dict]) -> None:
        for line_num, line in enumerate(code_lines):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(2)
            lineno = QLabel(f"{line_num:2d} ")
            lineno.setStyleSheet(
                f"color: {Colors.STONE_LIGHT}; font-family: Consolas; font-size: 13px; "
                f"background: transparent; min-width: 24px;"
            )
            row.addWidget(lineno)
            while "____" in line:
                idx = line.index("____")
                if idx > 0:
                    prefix = QLabel(line[:idx])
                    prefix.setStyleSheet(_S_CODE)
                    row.addWidget(prefix)
                inp = QLineEdit()
                inp.setPlaceholderText("___")
                inp.setAlignment(Qt.AlignmentFlag.AlignCenter)
                inp.setFixedWidth(120)
                inp.setEnabled(False)
                inp.setStyleSheet(_S_INPUT_OFF)
                inp.returnPressed.connect(self._on_step)
                bd = blanks[len(self._inputs)] if len(self._inputs) < len(blanks) else {}
                vtype = bd.get("validator", "any")
                rx = _VALIDATORS.get(vtype)
                if rx:
                    inp.setValidator(QRegularExpressionValidator(rx))
                self._inputs.append(inp)
                row.addWidget(inp)
                line = line[idx + 4:]
            if line:
                suffix = QLabel(line)
                suffix.setStyleSheet(_S_CODE)
                row.addWidget(suffix)
            row.addStretch()
            self._code_layout.addLayout(row)

    def _update_blanks_state(self) -> None:
        all_done = self._current_blank >= self._blank_count
        for i, inp in enumerate(self._inputs):
            if i == self._current_blank and not all_done:
                inp.setEnabled(True)
                inp.setStyleSheet(_S_INPUT)
                inp.setFocus()
            else:
                inp.setEnabled(False)
                inp.setStyleSheet(_S_INPUT_OFF)
        self._step_btn.setEnabled(self._blank_count > 0 or all_done)
        self._step_btn.setText("⛏ 执行" if all_done else "▶ 下一步")

    def _update_status(self) -> None:
        if self._blank_count == 0:
            self._status_lb.setText("本关无填空 — 按 '执行'")
        elif self._current_blank < self._blank_count:
            self._status_lb.setText(f"空白 {self._current_blank + 1}/{self._blank_count}")
        else:
            self._status_lb.setText("已就绪 — 点 '执行' 运行")

    def _on_step(self) -> None:
        all_done = self._current_blank >= self._blank_count
        if not all_done:
            inp = self._inputs[self._current_blank]
            if not inp.text().strip():
                return
            self._current_blank += 1
            self._update_blanks_state()
            self._update_status()
        else:
            self._run_engine()

    def _on_reset(self) -> None:
        self._current_blank = 0
        for inp in self._inputs:
            inp.clear()
        self._result_lb.setVisible(False)
        self._result_btns.setVisible(False)
        self._step_btn.setVisible(True)
        self._reset_btn.setVisible(True)
        self._hint_btn.setVisible(True)
        self.hearts = 5
        self.streak = 0
        self._hearts.set_hearts(5, 5)
        self._canvas.reset()
        self.engine.reset()
        self._animator.reset()
        self._update_blanks_state()
        self._update_status()

    def _run_engine(self) -> None:
        code = self._assemble_code()
        lines = code.split("\n")
        self.engine.reset()
        self._canvas.reset()
        self._animator.reset()
        diffs = self.engine.execute(lines)
        for diff in diffs:
            if not diff.is_empty:
                self._canvas.apply(diff)
        lv = self._level or {}
        ok, msg = self.loader.check_goal(lv, self.engine.last_model())

        self._step_btn.setVisible(False)
        self._reset_btn.setVisible(False)
        self._hint_btn.setVisible(False)
        self._result_btns.setVisible(True)

        if ok:
            self.streak += 1
            self.audio.play_xp()
            if self.streak >= 3:
                self.audio.play_level_up()
            ids = self.loader.list_ids()
            idx = ids.index(self._level_id) if self._level_id in ids else -1
            is_last = idx >= len(ids) - 1 or idx < 0
            if is_last:
                self._next_btn.setText("🎉 全部通关!")
                self._next_btn.setEnabled(False)
            else:
                self._next_btn.setText("下一关 ▶")
                self._next_btn.setEnabled(True)
            self._result_lb.setText(f"✅ 通关！连击 x{self.streak}  {lv.get('success_message', '')}")
            self._result_lb.setStyleSheet(
                f"font-size: 15px; font-weight: 900; padding: 8px; border-radius: 4px; "
                f"background: {Colors.GRASS}; color: white;"
            )
        else:
            self.hearts -= 1
            self.streak = 0
            self.audio.play_hurt()
            self._hearts.set_hearts(self.hearts, 5)
            if self.hearts <= 0:
                self.audio.play_death()
                self._result_lb.setText("💀 你被苦力怕炸飞了！所有生命耗尽。点 '重试' 再来一次。")
                self._result_lb.setStyleSheet(
                    f"font-size: 15px; font-weight: 900; padding: 8px; border-radius: 4px; "
                    f"background: {Colors.HEART_DARK}; color: white;"
                )
                self._next_btn.setVisible(False)
            else:
                extra = lv.get("failure_guidance", "")
                full = f"❌ {msg}  ❤️ x{self.hearts}"
                if extra:
                    full += f"\n💡 {extra}"
                self._result_lb.setText(full)
                self._result_lb.setStyleSheet(
                    f"font-size: 15px; font-weight: 900; padding: 8px; border-radius: 4px; "
                    f"background: {Colors.HEART}; color: white;"
                )
                self._next_btn.setVisible(True if self._level else False)
        self._result_lb.setVisible(True)

    def _on_retry(self) -> None:
        self._result_lb.setVisible(False)
        self._result_btns.setVisible(False)
        self._step_btn.setVisible(True)
        self._reset_btn.setVisible(True)
        self._hint_btn.setVisible(True)
        self._current_blank = 0
        for inp in self._inputs:
            inp.clear()
        self.hearts = 5
        self.streak = 0
        self._hearts.set_hearts(5, 5)
        self._canvas.reset()
        self.engine.reset()
        self._animator.reset()
        self._update_blanks_state()
        self._update_status()

    def _to_next_level(self) -> None:
        ids = self.loader.list_ids()
        idx = ids.index(self._level_id) if self._level_id in ids else -1
        if idx >= 0 and idx < len(ids) - 1:
            self.load_level(ids[idx + 1])

    def _assemble_code(self) -> str:
        code = self._level.get("initial_code", []) if self._level else []
        lines = [str(line) for line in code]
        input_idx = 0
        result: list[str] = []
        for line in lines:
            while "____" in line and input_idx < len(self._inputs):
                val = self._inputs[input_idx].text().strip() or "___"
                line = line.replace("____", val, 1)
                input_idx += 1
            result.append(line)
        return "\n".join(result)

    def _show_next_hint(self) -> None:
        lv = self._level
        if not lv:
            return
        hints = lv.get("hints", [])
        if self._hint_index < len(hints):
            self._hint_lines.append(f"💡 提示 #{self._hint_index + 1}: {hints[self._hint_index]}")
            self._hint_lb.setText("\n".join(self._hint_lines))
            self._hint_lb.setVisible(True)
            self._hint_index += 1
            return
        self._open_ai_help()

    def _open_ai_help(self) -> None:
        lv = self._level or {}
        if not self.settings.api_url or not self.settings.model:
            self._hint_lb.setText("⚠ 请先在设置中填写 URL 和 Model")
            self._hint_lb.setVisible(True)
            return
        if not self.settings.api_key:
            self._hint_lb.setText("⚠ 请先在设置中填写 API Key")
            self._hint_lb.setVisible(True)
            return
        initial_code = lv.get("initial_code", [])
        question = "\n".join(str(line) for line in initial_code)
        answer = self._current_answer_text()
        system_prompt = (
            "请帮助学生学习C++程序设计，给他合适的提示和详细的讲解，但不要直接给出答案。"
            "这是一道填空题，题目为{question}"
        ).replace("{question}", question)
        user_prompt = (
            "我当前在题目中填的空为{answer}（每空之间用@分割），我的困惑为{problem}"
        ).replace("{answer}", answer)
        payload = AiHelpPayload(
            api_url=self.settings.api_url,
            api_key=self.settings.api_key,
            model=self.settings.model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            question_type="fill_blank",
        )
        self._ai_dialog.start(payload)
        self._ai_dialog.exec()

    def _current_answer_text(self) -> str:
        answers = [inp.text().strip() or "___" for inp in self._inputs]
        return "@".join(answers)
