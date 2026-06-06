import json
import asyncio
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QPlainTextEdit, QGraphicsView, QGraphicsScene,
    QSplitter, QScrollArea, QFrame,
)
from PySide6.QtCore import Qt, QThread, Signal, QRectF, QSize
from PySide6.QtGui import QFont, QColor, QPainter, QWheelEvent, QIcon

from app.core.memory_model import ExecutionTrace
from app.core.state_diff import StateDiffEngine
from app.ui.canvas.memory_canvas import MemoryCanvas
from app.ui.canvas.canvas_animator import CanvasAnimator
from app.services.ai_service import AIService
from app.services import error_store
from app.services.i18n import tr
from app.services.prompt_templates import OJ_SYSTEM_PROMPT, OJ_USER_TEMPLATE, OJ_AUTOGEN_TEMPLATE
from app.services.compile_runner import compile_and_run
from app.ui.widgets.helpers import clear_layout, build_code_block
from app.ui.widgets.error_dialog import show_error_dialog
from app.ui.widgets.threading import retire_worker
from app.ui.theme.colors import (
    CANVAS_BG, SURFACE, BORDER, TEXT_PRIMARY, TEXT_SECONDARY,
    ACCENT, STACK_BORDER, HEAP_BORDER, HIGHLIGHT, EDGE_DANGLING,
    TEXT_INVERSE, TEXT_BUTTON_PRIMARY, SUCCESS, SUCCESS_BG,
)
from app.ui.theme.minecraft_assets import asset_path

logger = logging.getLogger(__name__)

SCENE_W = 1000
SCENE_H = 1200

CARD = (
    f"QFrame#ojCard {{ background-color: {SURFACE}; border: 2px solid {BORDER}; "
    f"margin: 3px 0; }}"
    f"QFrame#ojCard QLabel {{ border: none; background: transparent; outline: none; }}"
)
SECTION_TITLE = (
    f"color: {STACK_BORDER}; font-size: 19px; font-weight: 700; "
    f"padding: 6px 0;"
)
BODY_TEXT = f"color: {TEXT_PRIMARY}; font-size: 15px; font-weight: 500;"
MUTED_TEXT = f"color: {TEXT_SECONDARY}; font-size: 14px; font-weight: 600;"
CODE_BG = (
    f"background-color: {CANVAS_BG}; border: 1px solid {BORDER}; "
    f"padding: 6px; margin: 4px 0;"
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
            if self._code.strip():
                template = OJ_USER_TEMPLATE
                user_msg = template.format(
                    problem=self._problem[:3000],
                    code=self._code[:5000],
                )
            else:
                template = OJ_AUTOGEN_TEMPLATE
                user_msg = template.format(
                    problem=self._problem[:3000],
                )
            raw = asyncio.run(service.chat_json(
                system_prompt=OJ_SYSTEM_PROMPT,
                user_message=user_msg,
            ))
            data = json.loads(raw)
            trace = ExecutionTrace.model_validate(data)
            analysis = {
                "overview": data.get("overview", ""),
                "solution_approach": data.get("solution_approach", ""),
                "knowledge_points": data.get("knowledge_points", []),
                "complexity": data.get("complexity", ""),
                "common_mistakes": data.get("common_mistakes", []),
                "reference_answers": data.get("reference_answers", []),
            }
            missing = [k for k, v in analysis.items() if not v and k != "knowledge_points"]
            if missing:
                logger.warning("OJ analysis missing fields: %s", ", ".join(missing))
            self.finished.emit({
                "trace": trace,
                "analysis": analysis,
            })
        except Exception as e:
            logger.error("OJWorker failed: %s", e)
            self.error.emit(str(e))


class OJPage(QWidget):
    visualize_requested = Signal(str)

    def __init__(self, config_path: Path | None = None, parent=None):
        super().__init__(parent)
        self._config_path = config_path
        self._worker: OJWorker | None = None
        self._retired_workers: list[OJWorker] = []
        self._trace: ExecutionTrace | None = None
        self._current_index = -1
        self._autogen = False
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
        self._problem_label = QLabel(tr("Problem Description"))
        problem_layout.addWidget(self._problem_label)
        self._problem_edit = QPlainTextEdit()
        self._problem_edit.setPlaceholderText(
            tr("Paste OJ problem description here...")
        )
        self._problem_edit.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 12))
        problem_layout.addWidget(self._problem_edit)
        input_splitter.addWidget(problem_widget)

        code_widget = QWidget()
        code_layout = QVBoxLayout(code_widget)
        code_layout.setContentsMargins(0, 0, 0, 0)
        self._code_label = QLabel(tr("Reference Code"))
        code_layout.addWidget(self._code_label)
        self._code_edit = QPlainTextEdit()
        self._code_edit.setPlaceholderText(
            "// Enter C++ solution code\n"
        )
        self._code_edit.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 12))
        code_layout.addWidget(self._code_edit)
        input_splitter.addWidget(code_widget)

        input_splitter.setSizes([350, 350])
        top_layout.addWidget(input_splitter)

        toolbar = QHBoxLayout()
        self._run_btn = QPushButton(tr("Run Analysis"))
        self._run_btn.setIcon(QIcon(asset_path("icons", "action_run")))
        self._run_btn.setIconSize(QSize(18, 18))
        self._run_btn.clicked.connect(self._on_run)
        toolbar.addWidget(self._run_btn)

        toolbar.addSpacing(16)
        self._btn_prev = QPushButton(tr("Prev"))
        self._btn_next = QPushButton(tr("Next"))
        self._btn_prev.setEnabled(False)
        self._btn_next.setEnabled(False)
        self._btn_prev.clicked.connect(self._on_prev)
        self._btn_next.clicked.connect(self._on_next)
        toolbar.addWidget(self._btn_prev)
        toolbar.addWidget(self._btn_next)

        toolbar.addSpacing(16)
        self._step_info = QLabel(tr("Ready"))
        self._step_info.setStyleSheet(f"color: {TEXT_SECONDARY};")
        toolbar.addWidget(self._step_info)
        toolbar.addStretch()
        top_layout.addLayout(toolbar)

        self._build_test_panel(top_layout)

        top_splitter.addWidget(top_area)

        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)

        canvas_widget = QWidget()
        canvas_layout = QVBoxLayout(canvas_widget)
        canvas_layout.setContentsMargins(0, 0, 0, 0)

        self._canvas_view = self._create_canvas_view()
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
        self._analysis_label = QLabel(tr("AI Analysis"))
        commentary_layout.addWidget(self._analysis_label)
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
        self._autogen = not code and bool(problem)
        if not code and not problem:
            return

        self._run_btn.setEnabled(False)
        self._run_btn.setText(tr("Analyzing..."))

        if self._worker is not None and self._worker.isRunning():
            retire_worker(
                self,
                self._worker,
                disconnect=[
                    (self._worker.finished, self._on_result),
                    (self._worker.error, self._on_error),
                ],
            )

        self._worker = OJWorker(problem, code, self._config_path)
        self._worker.finished.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_result(self, data: dict):
        self._run_btn.setEnabled(True)
        self._run_btn.setText(tr("Run Analysis"))

        trace: ExecutionTrace = data["trace"]
        analysis = data.get("analysis", {})

        # Save knowledge points
        for kp in analysis.get("knowledge_points", []):
            name = kp.get("name", "")
            error_store.add_knowledge_point(name, "oj_analysis")
            expl = kp.get("explanation", "")
            if expl and not any(k.get("name") == name and k.get("description") for k in error_store.get_knowledge_points()):
                error_store.set_knowledge_description(name, expl)

        self._trace = trace
        self._current_index = 0

        if self._autogen:
            refs = analysis.get("reference_answers", [])
            if refs:
                gen_code = refs[0].get("code", "") or refs[0].get("explanation", "")
                if gen_code:
                    self._code_edit.setPlainText(gen_code)
                    self._autogen = False

        error_store.log_activity("OJ Analysis", f"Analyzed {len(trace.steps)} steps")
        self._build_analysis(analysis)

        if trace.steps:
            self._memory_canvas.clear()
            self._memory_canvas.prepare_trace_layout(trace.steps)
            self._canvas_view.set_stable_fit_bounds(self._memory_canvas.stable_fit_bounds())
            self._memory_canvas.render_state(trace.steps[0])
            self._canvas_view.zoom_fit()
            self._update_controls()

    def _build_analysis(self, a: dict):
        self._clear_analysis()

        overview = a.get("overview", "")
        if overview:
            self._add_section_card(tr("Overview"), overview)

        approach = a.get("solution_approach", "")
        if approach:
            self._add_section_card(tr("Solution Approach"), approach)

        kps = a.get("knowledge_points", [])
        if kps:
            title = QLabel(tr("Knowledge Points"))
            title.setStyleSheet(SECTION_TITLE)
            self._analysis_layout.addWidget(title)
            for kp in kps:
                self._add_kp_card(kp)

        complexity = a.get("complexity", "")
        if complexity:
            self._add_section_card(tr("Complexity"), complexity)

        mistakes = a.get("common_mistakes", [])
        if mistakes:
            items = "\n".join(f"  • {m}" for m in mistakes)
            self._add_section_card(tr("Common Mistakes"), items)

        refs = a.get("reference_answers", [])
        if refs:
            title = QLabel(tr("Reference Answers"))
            title.setStyleSheet(SECTION_TITLE)
            self._analysis_layout.addWidget(title)
            for ref in refs:
                self._add_ref_card(ref)

        self._analysis_layout.addStretch()

    def _add_section_card(self, title_text: str, body: str):
        card = QFrame()
        card.setObjectName("ojCard")
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
        card.setObjectName("ojCard")
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
            cf = build_code_block(code, text_color=TEXT_PRIMARY,
                                  bg_color=CANVAS_BG, border_color=BORDER)
            vbox.addWidget(cf)

        review_btn = QPushButton(tr("Add to Review"))
        review_btn.setStyleSheet(
            f"QPushButton {{ background-color: transparent; "
            f"color: {ACCENT}; border: 2px solid {ACCENT}; "
            f"padding: 4px 12px; font-size: 13px; font-weight: 600; "
            f"margin-top: 4px; }}"
            f"QPushButton:hover {{ background-color: {ACCENT}; color: {TEXT_BUTTON_PRIMARY}; }}"
        )
        kp_name = kp.get("name", "")
        kp_expl = kp.get("explanation", "")
        def save_and_feedback():
            question = tr("Review: {name}", name=kp_name)
            error_store.add_error(
                knowledge_point=kp_name, question=question,
                user_answer="", correct_answer=kp_expl or tr("Study concept: {name}", name=kp_name),
                deck=error_store.suggest_deck(kp_name),
            )
            review_btn.setText("✓ " + tr("Added"))
            review_btn.setStyleSheet(
                f"QPushButton {{ background-color: {SUCCESS_BG}; "
                f"color: {SUCCESS}; border: 2px solid {SUCCESS}; "
                f"padding: 4px 12px; font-size: 13px; font-weight: 600; "
                f"margin-top: 4px; }}"
            )
            review_btn.setEnabled(False)
        review_btn.clicked.connect(lambda: save_and_feedback())
        vbox.addWidget(review_btn)

        self._analysis_layout.addWidget(card)

    def _add_ref_card(self, ref: dict):
        card = QFrame()
        card.setObjectName("ojRefCard")
        card.setStyleSheet(
            f"QFrame#ojRefCard {{ background-color: {SUCCESS_BG}; border: 2px solid {SUCCESS}; "
            f"margin: 3px 0; }}"
            f"QFrame#ojRefCard QLabel {{ border: none; background: transparent; outline: none; }}"
        )
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(10, 6, 10, 6)
        vbox.setSpacing(3)

        name = QLabel(ref.get("approach", ""))
        name.setStyleSheet(f"color: {SUCCESS}; font-weight: bold; font-size: 13px;")
        vbox.addWidget(name)

        expl = ref.get("explanation", "")
        if expl:
            e = QLabel(expl)
            e.setWordWrap(True)
            e.setStyleSheet(BODY_TEXT)
            vbox.addWidget(e)

        code = ref.get("code", "")
        if code:
            cf = build_code_block(code, text_color=TEXT_PRIMARY,
                                  bg_color=CANVAS_BG, border_color=BORDER)
            vbox.addWidget(cf)

            viz = QPushButton(tr("Visualize this code"))
            viz.clicked.connect(lambda: self.visualize_requested.emit(code))
            vbox.addWidget(viz)

        self._analysis_layout.addWidget(card)

    def _clear_analysis(self):
        clear_layout(self._analysis_layout)

    def _on_prev(self):
        if self._trace is None or self._current_index <= 0:
            return
        self._current_index -= 1
        curr_state = self._trace.steps[self._current_index]
        self._animator.stop_all()
        self._memory_canvas.render_state(curr_state)
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
        self._memory_canvas.render_state(curr_state)
        self._animator.animate_diff(diff)
        self._update_controls()

    def _on_error(self, msg: str):
        self._run_btn.setEnabled(True)
        self._run_btn.setText(tr("Run Analysis"))
        self._step_info.setText(tr("Error: {message}", message=msg[:60]))

        raw = ""
        display_msg = msg
        if "---RAW RESPONSE---" in msg:
            parts = msg.split("---RAW RESPONSE---", 1)
            display_msg = parts[0].strip()
            raw = parts[1].strip()

        show_error_dialog(
            self,
            tr("OJ Analysis Error"),
            display_msg,
            code=self._code_edit.toPlainText().strip(),
            raw_response=raw,
            on_retry=lambda: self._on_run(),
        )

    def _update_controls(self):
        total = len(self._trace.steps) if self._trace else 0
        current = self._current_index + 1 if self._current_index >= 0 else 0
        self._btn_prev.setEnabled(
            self._trace is not None and self._current_index > 0
        )
        self._btn_next.setEnabled(
            self._trace is not None and self._current_index + 1 < total
        )
        self._step_info.setText(tr("Step {current}/{total}", current=current, total=total))

    def _build_test_panel(self, parent_layout):
        test_header = QHBoxLayout()
        self._test_cases_label = QLabel(tr("Test Cases:"))
        test_header.addWidget(self._test_cases_label)
        self._test_input = QPlainTextEdit()
        self._test_input.setPlaceholderText(tr("Input"))
        self._test_input.setMaximumHeight(50)
        self._test_input.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 11))
        self._test_expected = QPlainTextEdit()
        self._test_expected.setPlaceholderText(tr("Expected output"))
        self._test_expected.setMaximumHeight(50)
        self._test_expected.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 11))
        self._add_case_btn = QPushButton(tr("Add Case"))
        self._add_case_btn.setIcon(QIcon(asset_path("icons", "action_add")))
        self._add_case_btn.setIconSize(QSize(18, 18))
        self._add_case_btn.clicked.connect(self._on_add_test_case)
        test_header.addWidget(self._test_input)
        test_header.addWidget(self._test_expected)
        test_header.addWidget(self._add_case_btn)
        parent_layout.addLayout(test_header)

        self._test_cases: list[dict] = []
        self._test_list = QVBoxLayout()
        parent_layout.addLayout(self._test_list)

        run_row = QHBoxLayout()
        self._run_tests_btn = QPushButton(tr("Run Tests"))
        self._run_tests_btn.setIcon(QIcon(asset_path("icons", "action_run")))
        self._run_tests_btn.setIconSize(QSize(18, 18))
        self._run_tests_btn.clicked.connect(self._on_compile_run)
        self._run_tests_btn.setVisible(False)
        run_row.addWidget(self._run_tests_btn)
        run_row.addStretch()
        parent_layout.addLayout(run_row)

        self._test_results = QVBoxLayout()
        parent_layout.addLayout(self._test_results)

    def _on_add_test_case(self):
        inp = self._test_input.toPlainText()
        exp = self._test_expected.toPlainText()
        if not inp and not exp:
            return
        self._test_cases.append({"input": inp, "expected": exp})
        self._test_input.clear()
        self._test_expected.clear()
        self._run_tests_btn.setVisible(True)
        self._refresh_test_list()

    def _refresh_test_list(self):
        clear_layout(self._test_list)
        for i, tc in enumerate(self._test_cases):
            row = QHBoxLayout()
            label = QLabel(tr(
                "Case #{index}: in {input} | out {output}",
                index=i + 1,
                input=tc['input'][:30],
                output=tc['expected'][:30],
            ))
            label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: 600;")
            row.addWidget(label)
            del_btn = QPushButton("×")
            del_btn.setFixedSize(24, 24)
            del_btn.clicked.connect(lambda checked=None, idx=i: self._remove_test_case(idx))
            row.addWidget(del_btn)
            row.addStretch()
            self._test_list.addLayout(row)

    def _remove_test_case(self, idx: int):
        if 0 <= idx < len(self._test_cases):
            self._test_cases.pop(idx)
        if not self._test_cases:
            self._run_tests_btn.setVisible(False)
        self._refresh_test_list()

    def _on_compile_run(self):
        code = self._code_edit.toPlainText().strip()
        if not code or not self._test_cases:
            return
        clear_layout(self._test_results)
        result = compile_and_run(code, self._test_cases)
        compile_ok = result["compile"]
        if not compile_ok.success:
            err = QLabel(tr("Compile error:\n{error}", error=compile_ok.error))
            err.setStyleSheet(f"color: {EDGE_DANGLING}; font-size: 13px; font-weight: 600; white-space: pre-wrap;")
            err.setWordWrap(True)
            self._test_results.addWidget(err)
            return
        for t in result["tests"]:
            if t.passed:
                r = QLabel(tr("Case #{index} passed", index=t.case_index))
                r.setStyleSheet(f"color: {SUCCESS}; font-size: 14px; font-weight: bold;")
            else:
                r = QLabel(tr(
                    "Case #{index} FAILED\nExpected: {expected}\nGot:      {actual}",
                    index=t.case_index,
                    expected=t.expected,
                    actual=t.actual,
                ))
                r.setStyleSheet(f"color: {EDGE_DANGLING}; font-size: 13px; font-weight: 600; white-space: pre-wrap;")
                r.setWordWrap(True)
            self._test_results.addWidget(r)

    def retranslate_ui(self):
        self._problem_label.setText(tr("Problem Description"))
        self._problem_edit.setPlaceholderText(tr("Paste OJ problem description here..."))
        self._code_label.setText(tr("Reference Code"))
        self._run_btn.setText(tr("Run Analysis"))
        self._btn_prev.setText(tr("Prev"))
        self._btn_next.setText(tr("Next"))
        self._analysis_label.setText(tr("AI Analysis"))
        self._test_cases_label.setText(tr("Test Cases:"))
        self._test_input.setPlaceholderText(tr("Input"))
        self._test_expected.setPlaceholderText(tr("Expected output"))
        self._add_case_btn.setText(tr("Add Case"))
        self._run_tests_btn.setText(tr("Run Tests"))
        if self._trace is not None:
            self._update_controls()
        else:
            self._step_info.setText(tr("Ready"))

    @staticmethod
    def _create_canvas_view() -> QGraphicsView:
        class _OJCanvasView(QGraphicsView):
            def zoom_fit(self):
                fit_rect = getattr(self, "_stable_fit_bounds", QRectF())
                if not fit_rect.isValid():
                    fit_rect = self._fit_bounds()
                if not fit_rect.isValid() or fit_rect.isEmpty():
                    return
                self.fitInView(fit_rect, Qt.AspectRatioMode.KeepAspectRatio)

            def set_stable_fit_bounds(self, bounds: QRectF):
                self._stable_fit_bounds = QRectF(bounds)

            def clear_stable_fit_bounds(self):
                self._stable_fit_bounds = QRectF()

            def _fit_bounds(self):
                scene = self.scene()
                if scene is None:
                    return QRectF()

                scene_rect = scene.sceneRect()
                bounds = QRectF()

                for item in scene.items():
                    if item.parentItem() is not None or not item.isVisible():
                        continue

                    visual_bounds = getattr(item, "visual_bounds", None)
                    if callable(visual_bounds):
                        item_bounds = item.mapRectToScene(visual_bounds())
                    else:
                        item_bounds = item.sceneBoundingRect()

                    item_bounds = item_bounds.intersected(scene_rect)
                    if item_bounds.isEmpty():
                        continue

                    bounds = item_bounds if bounds.isNull() else bounds.united(item_bounds)

                return bounds.adjusted(-24.0, -24.0, 24.0, 24.0)

            def wheelEvent(self, event: QWheelEvent):
                event.accept()
        return _OJCanvasView()
