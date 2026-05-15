import json
import asyncio
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QPlainTextEdit, QGraphicsView, QGraphicsScene,
    QSplitter, QScrollArea, QFrame,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor, QPainter

from app.core.memory_model import ExecutionTrace
from app.core.state_diff import StateDiffEngine
from app.ui.canvas.memory_canvas import MemoryCanvas
from app.ui.canvas.canvas_animator import CanvasAnimator
from app.services.ai_service import AIService
from app.services import error_store
from app.services.prompt_templates import OJ_SYSTEM_PROMPT, OJ_USER_TEMPLATE
from app.ui.theme.colors import (
    CANVAS_BG, SURFACE, BORDER, TEXT_PRIMARY, TEXT_SECONDARY,
    ACCENT, STACK_BORDER, HEAP_BORDER, HIGHLIGHT,
)

logger = logging.getLogger(__name__)

SCENE_W = 1000
SCENE_H = 1200

CARD = (
    f"QFrame {{ background-color: {SURFACE}; border: 1px solid {BORDER}; "
    f"border-radius: 6px; margin: 3px 0; }}"
)
SECTION_TITLE = (
    f"color: {STACK_BORDER}; font-size: 14px; font-weight: bold; "
    f"padding: 4px 0;"
)
BODY_TEXT = f"color: {TEXT_PRIMARY}; font-size: 12px;"
MUTED_TEXT = f"color: {TEXT_SECONDARY}; font-size: 12px;"
CODE_BG = (
    f"background-color: {CANVAS_BG}; border: 1px solid {BORDER}; "
    f"border-radius: 4px; padding: 6px; margin: 4px 0;"
)


class OJWorker(QThread):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, problem: str, code: str, config_path: Path | None = None):
        super().__init__()
        self._problem = problem
        self._code = code
        self._config_path = config_path

    def run(self):
        try:
            service = AIService(self._config_path)
            user_msg = OJ_USER_TEMPLATE.format(
                problem=self._problem[:3000],
                code=self._code[:5000],
            )
            raw = asyncio.run(service.chat_json(
                system_prompt=OJ_SYSTEM_PROMPT,
                user_message=user_msg,
            ))
            data = json.loads(raw)
            trace = ExecutionTrace.model_validate(data)
            self.finished.emit({
                "trace": trace,
                "analysis": {
                    "overview": data.get("overview", ""),
                    "solution_approach": data.get("solution_approach", ""),
                    "knowledge_points": data.get("knowledge_points", []),
                    "complexity": data.get("complexity", ""),
                    "common_mistakes": data.get("common_mistakes", []),
                    "reference_answers": data.get("reference_answers", []),
                },
            })
        except Exception as e:
            logger.exception("OJWorker failed")
            self.error.emit(str(e))


class OJPage(QWidget):
    def __init__(self, config_path: Path | None = None, parent=None):
        super().__init__(parent)
        self._config_path = config_path
        self._worker: OJWorker | None = None
        self._trace: ExecutionTrace | None = None
        self._current_index = -1
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        top_splitter = QSplitter(Qt.Orientation.Vertical)

        top_area = QWidget()
        top_layout = QVBoxLayout(top_area)
        top_layout.setContentsMargins(0, 0, 0, 0)

        input_splitter = QSplitter(Qt.Orientation.Horizontal)

        problem_widget = QWidget()
        problem_layout = QVBoxLayout(problem_widget)
        problem_layout.setContentsMargins(0, 0, 0, 0)
        problem_layout.addWidget(QLabel("Problem Description"))
        self._problem_edit = QPlainTextEdit()
        self._problem_edit.setPlaceholderText(
            "Paste OJ problem description here..."
        )
        self._problem_edit.setFont(QFont("JetBrains Mono", 12))
        problem_layout.addWidget(self._problem_edit)
        input_splitter.addWidget(problem_widget)

        code_widget = QWidget()
        code_layout = QVBoxLayout(code_widget)
        code_layout.setContentsMargins(0, 0, 0, 0)
        code_layout.addWidget(QLabel("Reference Code"))
        self._code_edit = QPlainTextEdit()
        self._code_edit.setPlaceholderText(
            "// Enter C++ solution code\n"
        )
        self._code_edit.setFont(QFont("JetBrains Mono", 12))
        code_layout.addWidget(self._code_edit)
        input_splitter.addWidget(code_widget)

        input_splitter.setSizes([350, 350])
        top_layout.addWidget(input_splitter)

        toolbar = QHBoxLayout()
        self._run_btn = QPushButton("Run Analysis")
        self._run_btn.clicked.connect(self._on_run)
        toolbar.addWidget(self._run_btn)

        toolbar.addSpacing(16)
        self._btn_prev = QPushButton("Prev")
        self._btn_next = QPushButton("Next")
        self._btn_prev.setEnabled(False)
        self._btn_next.setEnabled(False)
        self._btn_prev.clicked.connect(self._on_prev)
        self._btn_next.clicked.connect(self._on_next)
        toolbar.addWidget(self._btn_prev)
        toolbar.addWidget(self._btn_next)

        toolbar.addSpacing(16)
        self._step_info = QLabel("Ready")
        self._step_info.setStyleSheet(f"color: {TEXT_SECONDARY};")
        toolbar.addWidget(self._step_info)
        toolbar.addStretch()
        top_layout.addLayout(toolbar)

        top_splitter.addWidget(top_area)

        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)

        canvas_widget = QWidget()
        canvas_layout = QVBoxLayout(canvas_widget)
        canvas_layout.setContentsMargins(0, 0, 0, 0)

        self._canvas_view = QGraphicsView()
        self._canvas_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._canvas_view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._canvas_view.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._canvas_scene = QGraphicsScene()
        self._canvas_scene.setBackgroundBrush(QColor(CANVAS_BG))
        self._canvas_scene.setSceneRect(0, 0, SCENE_W, SCENE_H)
        self._canvas_view.setScene(self._canvas_scene)

        self._memory_canvas = MemoryCanvas(self._canvas_view, self._canvas_scene)
        self._diff_engine = StateDiffEngine()
        self._animator = CanvasAnimator(self._memory_canvas)

        canvas_layout.addWidget(self._canvas_view)
        bottom_splitter.addWidget(canvas_widget)

        commentary = QWidget()
        commentary_layout = QVBoxLayout(commentary)
        commentary_layout.setContentsMargins(8, 0, 0, 0)
        commentary_layout.addWidget(QLabel("AI Analysis"))
        self._analysis_widget = QWidget()
        self._analysis_layout = QVBoxLayout(self._analysis_widget)
        self._analysis_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ border: 1px solid {BORDER}; background: {CANVAS_BG}; }}"
        )
        scroll.setWidget(self._analysis_widget)
        commentary_layout.addWidget(scroll)

        bottom_splitter.addWidget(commentary)
        bottom_splitter.setSizes([500, 350])

        top_splitter.addWidget(bottom_splitter)
        top_splitter.setSizes([250, 450])

        layout.addWidget(top_splitter)

    def _on_run(self):
        problem = self._problem_edit.toPlainText().strip()
        code = self._code_edit.toPlainText().strip()
        if not code:
            code = problem
        if not code:
            return

        self._run_btn.setEnabled(False)
        self._run_btn.setText("Analyzing...")

        self._worker = OJWorker(problem, code, self._config_path)
        self._worker.finished.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_result(self, data: dict):
        self._run_btn.setEnabled(True)
        self._run_btn.setText("Run Analysis")

        trace: ExecutionTrace = data["trace"]
        analysis = data.get("analysis", {})

        # Save knowledge points
        for kp in analysis.get("knowledge_points", []):
            error_store.add_knowledge_point(
                kp.get("name", ""), "oj_analysis"
            )

        self._trace = trace
        self._current_index = 0

        self._build_analysis(analysis)

        if trace.steps:
            self._memory_canvas.render_state(trace.steps[0])
            self._update_controls()

    def _build_analysis(self, a: dict):
        self._clear_analysis()

        overview = a.get("overview", "")
        if overview:
            self._add_section_card("Overview", overview)

        approach = a.get("solution_approach", "")
        if approach:
            self._add_section_card("Solution Approach", approach)

        kps = a.get("knowledge_points", [])
        if kps:
            title = QLabel("Knowledge Points")
            title.setStyleSheet(SECTION_TITLE)
            self._analysis_layout.addWidget(title)
            for kp in kps:
                self._add_kp_card(kp)

        complexity = a.get("complexity", "")
        if complexity:
            self._add_section_card("Complexity", complexity)

        mistakes = a.get("common_mistakes", [])
        if mistakes:
            items = "\n".join(f"  • {m}" for m in mistakes)
            self._add_section_card("Common Mistakes", items)

        refs = a.get("reference_answers", [])
        if refs:
            title = QLabel("Reference Answers")
            title.setStyleSheet(SECTION_TITLE)
            self._analysis_layout.addWidget(title)
            for ref in refs:
                self._add_ref_card(ref)

        self._analysis_layout.addStretch()

    def _add_section_card(self, title_text: str, body: str):
        card = QFrame()
        card.setStyleSheet(CARD)
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(10, 8, 10, 8)
        vbox.setSpacing(4)

        t = QLabel(title_text)
        t.setStyleSheet(SECTION_TITLE)
        vbox.addWidget(t)

        b = QLabel(body)
        b.setWordWrap(True)
        b.setStyleSheet(BODY_TEXT)
        vbox.addWidget(b)

        self._analysis_layout.addWidget(card)

    def _add_kp_card(self, kp: dict):
        card = QFrame()
        card.setStyleSheet(CARD)
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(10, 6, 10, 6)
        vbox.setSpacing(3)

        name = QLabel(kp.get("name", ""))
        name.setStyleSheet(f"color: {HEAP_BORDER}; font-weight: bold; font-size: 13px;")
        vbox.addWidget(name)

        expl = kp.get("explanation", "")
        if expl:
            e = QLabel(expl)
            e.setWordWrap(True)
            e.setStyleSheet(BODY_TEXT)
            vbox.addWidget(e)

        code = kp.get("code", "")
        if code:
            cf = QFrame()
            cf.setStyleSheet(CODE_BG)
            cl = QVBoxLayout(cf)
            cl.setContentsMargins(6, 4, 6, 4)
            c = QLabel(code)
            c.setFont(QFont("JetBrains Mono", 11))
            c.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
            cl.addWidget(c)
            vbox.addWidget(cf)

        self._analysis_layout.addWidget(card)

    def _add_ref_card(self, ref: dict):
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: #1A2A1A; border: 1px solid #4EC9B0; "
            f"border-radius: 6px; margin: 3px 0; }}"
        )
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(10, 6, 10, 6)
        vbox.setSpacing(3)

        name = QLabel(ref.get("approach", ""))
        name.setStyleSheet("color: #4EC9B0; font-weight: bold; font-size: 13px;")
        vbox.addWidget(name)

        expl = ref.get("explanation", "")
        if expl:
            e = QLabel(expl)
            e.setWordWrap(True)
            e.setStyleSheet(BODY_TEXT)
            vbox.addWidget(e)

        code = ref.get("code", "")
        if code:
            cf = QFrame()
            cf.setStyleSheet(CODE_BG)
            cl = QVBoxLayout(cf)
            cl.setContentsMargins(6, 4, 6, 4)
            c = QLabel(code)
            c.setFont(QFont("JetBrains Mono", 11))
            c.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
            c.setWordWrap(True)
            cl.addWidget(c)
            vbox.addWidget(cf)

        self._analysis_layout.addWidget(card)

    def _clear_analysis(self):
        while self._analysis_layout.count():
            item = self._analysis_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_prev(self):
        if self._trace is None or self._current_index <= 0:
            return
        prev_state = self._trace.steps[self._current_index]
        self._current_index -= 1
        curr_state = self._trace.steps[self._current_index]
        diff = self._diff_engine.diff(prev_state, curr_state)
        self._animator.stop_all()
        self._memory_canvas.clear()
        self._memory_canvas.render_state(curr_state)
        self._animator.animate_diff(diff)
        self._update_controls()

    def _on_next(self):
        if (
            self._trace is None
            or self._current_index + 1 >= len(self._trace.steps)
        ):
            return
        prev_state = self._trace.steps[self._current_index]
        self._current_index += 1
        curr_state = self._trace.steps[self._current_index]
        diff = self._diff_engine.diff(prev_state, curr_state)
        self._animator.stop_all()
        self._memory_canvas.clear()
        self._memory_canvas.render_state(curr_state)
        self._animator.animate_diff(diff)
        self._update_controls()

    def _on_error(self, msg: str):
        self._run_btn.setEnabled(True)
        self._run_btn.setText("Run Analysis")
        self._step_info.setText(f"Error: {msg}")

    def _update_controls(self):
        total = len(self._trace.steps) if self._trace else 0
        current = self._current_index + 1 if self._current_index >= 0 else 0
        self._btn_prev.setEnabled(
            self._trace is not None and self._current_index > 0
        )
        self._btn_next.setEnabled(
            self._trace is not None and self._current_index + 1 < total
        )
        self._step_info.setText(f"Step {current}/{total}")
