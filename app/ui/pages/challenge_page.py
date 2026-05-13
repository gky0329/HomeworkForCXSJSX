from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from app.core.challenge_loader import ChallengeLoader
from app.core.engine import Engine
from app.ui.theme.config import Colors
from app.ui.theme.styles import APP_STYLE
from app.ui.widgets.mc_button import McButton


_STYLE_INPUT = (
    f"QLineEdit {{"
    f" background: {Colors.CODE_BG}; color: {Colors.GOLD}; "
    f" font-family: Consolas; font-size: 16px; font-weight: 900; "
    f" border: 2px solid {Colors.GOLD}; border-radius: 3px; "
    f" padding: 4px 10px;"
    f"}}"
    f"QLineEdit:focus {{"
    f" border-color: {Colors.GRASS_LIGHT}; "
    f" background: {Colors.BEDROCK};"
    f"}}"
)

_STYLE_INPUT_DISABLED = (
    f"QLineEdit {{"
    f" background: {Colors.DISABLED_BG}; color: {Colors.DISABLED_TEXT}; "
    f" font-family: Consolas; font-size: 16px; font-weight: 900; "
    f" border: 2px solid {Colors.DISABLED_BORDER}; border-radius: 3px; "
    f" padding: 4px 10px;"
    f"}}"
)

_STYLE_CODE_LABEL = (
    f"color: #98FB98; font-family: Consolas; font-size: 16px; "
    f"background: transparent; padding: 2px 0;"
)

_STYLE_PLACEHOLDER = (
    f"color: rgba(255,255,255,100); font-size: 14px; "
    f"background: {Colors.PANEL_BG}; border: 3px solid {Colors.STONE_DARK}; "
    f"padding: 16px; border-radius: 4px; min-height: 100px;"
)


def _btn(color: str) -> str:
    return (
        f"QPushButton {{ background: {color}; color: white; font-weight: 700; "
        f"font-size: 14px; padding: 8px 18px; border: 2px solid {Colors.BLACK}; "
        f"border-radius: 3px; }}"
        f"QPushButton:hover {{ background: {Colors.GOLD}; color: {Colors.BLACK}; }}"
        f"QPushButton:disabled {{ background: {Colors.DISABLED_BG}; color: {Colors.DISABLED_TEXT}; }}"
    )


class ChallengePage(QWidget):
    back_requested = Signal()

    def __init__(self, loader: ChallengeLoader, engine: Engine) -> None:
        super().__init__()
        self.loader = loader
        self.engine = engine
        self._level: dict | None = None
        self._inputs: list[QLineEdit] = []
        self._blank_count = 0
        self._current_blank = 0

        self.setStyleSheet(APP_STYLE)

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        left = self._build_left()
        right = self._build_right()
        root.addWidget(left, stretch=3)
        root.addWidget(right, stretch=4)

        self._load_level("oop_001")

    def _build_left(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._title_lb = QLabel()
        self._title_lb.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._title_lb.setStyleSheet(
            f"font-size: 26px; font-weight: 900; color: {Colors.CREAM}; padding: 4px 0;"
        )

        self._theory_lb = QLabel()
        self._theory_lb.setWordWrap(True)
        self._theory_lb.setStyleSheet(
            f"font-size: 14px; color: {Colors.MUTED}; "
            f"background: {Colors.PANEL_BG}; border: 3px solid {Colors.STONE_DARK}; "
            f"padding: 12px; border-radius: 4px;"
        )

        self._key_points_lb = QLabel()
        self._key_points_lb.setWordWrap(True)
        self._key_points_lb.setStyleSheet(
            f"font-size: 13px; color: {Colors.GOLD}; padding: 4px 8px; font-weight: 700;"
        )

        self._hint_lb = QLabel()
        self._hint_lb.setWordWrap(True)
        self._hint_lb.setStyleSheet(
            f"font-size: 13px; color: {Colors.GOLD}; "
            f"background: rgba(0,0,0,120); padding: 8px; border-radius: 2px;"
        )
        self._hint_lb.setVisible(False)
        self._hint_index = 0

        code_frame = QWidget()
        code_frame.setStyleSheet(
            f"background: {Colors.CODE_BG}; "
            f"border: 3px solid {Colors.STONE_DARK}; border-radius: 4px; padding: 12px;"
        )
        self._code_layout = QVBoxLayout(code_frame)
        self._code_layout.setContentsMargins(12, 12, 12, 12)
        self._code_layout.setSpacing(3)

        self._status_lb = QLabel()
        self._status_lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lb.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {Colors.MUTED}; padding: 4px;"
        )

        self._result_lb = QLabel()
        self._result_lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_lb.setStyleSheet(
            "font-size: 16px; font-weight: 900; padding: 8px; border-radius: 4px;"
        )
        self._result_lb.setVisible(False)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        back = QPushButton("← 返回")
        back.setStyleSheet(_btn(Colors.STONE))
        back.clicked.connect(self.back_requested.emit)

        hint_btn = QPushButton("? 提示")
        hint_btn.setStyleSheet(_btn(Colors.OAK))
        hint_btn.clicked.connect(self._show_next_hint)

        self._check_btn = McButton("✓ 检查")
        self._check_btn.clicked.connect(self._on_check)
        self._check_btn.setEnabled(False)

        self._step_btn = McButton("▶ 下一步")
        self._step_btn.clicked.connect(self._on_step)
        self._step_btn.setEnabled(False)

        reset_btn = McButton("↺ 重置")
        reset_btn.clicked.connect(self._on_reset)

        btn_row.addWidget(back)
        btn_row.addWidget(hint_btn)
        btn_row.addStretch()
        btn_row.addWidget(reset_btn)
        btn_row.addWidget(self._check_btn)
        btn_row.addWidget(self._step_btn)

        layout.addWidget(self._title_lb)
        layout.addWidget(self._theory_lb)
        layout.addWidget(self._key_points_lb)
        layout.addWidget(self._hint_lb)
        layout.addWidget(code_frame)
        layout.addWidget(self._status_lb)
        layout.addWidget(self._result_lb)
        layout.addStretch()
        layout.addLayout(btn_row)

        return panel

    def _build_right(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel("OopCanvas\n(Phase 2 实现)")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(_STYLE_PLACEHOLDER)

        layout.addWidget(label)
        return panel

    def _load_level(self, level_id: str) -> None:
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
        self._result_lb.setVisible(False)
        self._current_blank = 0

        self._clear_code()
        self._inputs = []
        self._render_code(lv["initial_code"])
        self._blank_count = len(self._inputs)
        self._update_blanks_state()
        self._update_status()

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

    def _render_code(self, code_lines: list[str]) -> None:
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
                    prefix.setStyleSheet(_STYLE_CODE_LABEL)
                    row.addWidget(prefix)
                inp = QLineEdit()
                inp.setStyleSheet(_STYLE_INPUT_DISABLED)
                inp.setPlaceholderText("___")
                inp.setAlignment(Qt.AlignmentFlag.AlignCenter)
                inp.setFixedWidth(120)
                inp.setEnabled(False)
                inp.returnPressed.connect(self._on_step)
                self._inputs.append(inp)
                row.addWidget(inp)
                line = line[idx + 4:]

            if line:
                suffix = QLabel(line)
                suffix.setStyleSheet(_STYLE_CODE_LABEL)
                row.addWidget(suffix)

            row.addStretch()
            self._code_layout.addLayout(row)

    def _update_blanks_state(self) -> None:
        for i, inp in enumerate(self._inputs):
            if i == self._current_blank and self._current_blank < self._blank_count:
                inp.setEnabled(True)
                inp.setStyleSheet(_STYLE_INPUT)
                inp.setFocus()
            else:
                inp.setEnabled(False)
                inp.setStyleSheet(_STYLE_INPUT_DISABLED)

        self._step_btn.setEnabled(self._current_blank > 0 or self._blank_count == 0)
        self._check_btn.setEnabled(self._current_blank >= self._blank_count)

    def _update_status(self) -> None:
        if self._blank_count == 0:
            self._status_lb.setText("本关无填空，按 '检查' 运行代码")
        elif self._current_blank < self._blank_count:
            self._status_lb.setText(
                f"填空 {self._current_blank + 1}/{self._blank_count}  "
                f"— 请输入第 {self._current_blank + 1} 个空白处的内容"
            )
        else:
            correct, total = 0, self._blank_count
            for i, inp in enumerate(self._inputs):
                blank = self._level["blanks"][i] if i < len(self._level.get("blanks", [])) else {}
                expected = blank.get("placeholder", "")
                if inp.text().strip().lower() == expected.lower():
                    correct += 1
            self._status_lb.setText(f"所有空白已填写就绪 ({correct}/{total} 与预期匹配) — 按 '检查' 验证")

    def _on_step(self) -> None:
        if self._current_blank < self._blank_count:
            self._current_blank += 1
        self._update_blanks_state()
        self._update_status()

    def _on_check(self) -> None:
        if not self._level:
            return

        lv = self._level
        code = self._assemble_code()
        lines = code.split("\n")

        self.engine.reset()
        diffs = self.engine.execute(lines)
        ok, msg = self.loader.check_goal(lv, self.engine.last_model())

        if ok:
            self._result_lb.setText(f"✅ 通关！{lv.get('success_message', '')}")
            self._result_lb.setStyleSheet(
                f"font-size: 16px; font-weight: 900; padding: 8px; border-radius: 4px; "
                f"background: {Colors.GRASS}; color: white;"
            )
        else:
            self._result_lb.setText(f"❌ {msg}")
            self._result_lb.setStyleSheet(
                f"font-size: 16px; font-weight: 900; padding: 8px; border-radius: 4px; "
                f"background: {Colors.HEART}; color: white;"
            )
        self._result_lb.setVisible(True)

    def _on_reset(self) -> None:
        self._current_blank = 0
        for inp in self._inputs:
            inp.clear()
        self._result_lb.setVisible(False)
        self._update_blanks_state()
        self._update_status()
        self.engine.reset()

    def _assemble_code(self) -> str:
        code = self._level["initial_code"]
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
            self._hint_lb.setText(f"💡 提示 #{self._hint_index + 1}: {hints[self._hint_index]}")
            self._hint_lb.setVisible(True)
            self._hint_index += 1
