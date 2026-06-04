import os
import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)
from PySide6.QtCore import QTimer
from PySide6.QtGui import QTextCursor, QTextCharFormat, QColor

from app.core.memory_model import ExecutionTrace, MemoryState
from app.core.state_diff import StateDiffEngine, DiffResult
from app.ui.main_window import MainWindow
from app.ui.canvas.memory_canvas import MemoryCanvas
from app.ui.canvas.canvas_animator import CanvasAnimator
from app.core.execution_worker import ExecutionResult, ExecutionWorker
from app.core.debug_executor import DebugExecutor
from app.ui.widgets import error_dialog
from app.ui.widgets.threading import retire_worker
from app.services import error_store
from app.services.i18n import tr


def _has_api_key() -> bool:
    try:
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        cfg = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        llm_cfg = cfg.get("llm", {})
        provider = str(llm_cfg.get("provider", "deepseek")).lower()
        provider_cfg = llm_cfg.get("providers", {}).get(provider, {})

        env_name = provider_cfg.get("api_key_env", "")
        if env_name and os.environ.get(env_name):
            return True

        key = provider_cfg.get("api_key", "")
        if key and str(key).strip():
            return True

        if provider == "deepseek" and os.environ.get("DEEPSEEK_API_KEY"):
            return True
        if provider == "deepseek":
            legacy_key = llm_cfg.get("api_key", "")
            return bool(legacy_key and str(legacy_key).strip())
    except Exception:
        logger.exception("Failed to read config for API key check")
    return False


def _has_local_debugger() -> bool:
    try:
        return DebugExecutor.is_available()
    except Exception:
        return False


def _can_run_locally(code: str, stdin_text: str = "") -> bool:
    try:
        return DebugExecutor.can_run_code_locally(code, stdin_text)
    except Exception:
        return False


class Engine:
    def __init__(self, window: MainWindow, config_path: Path | None = None):
        self._window = window
        self._window._engine = self
        self._config_path = config_path
        self._canvas = MemoryCanvas(window.canvas_view, window.canvas_scene)
        self._diff_engine = StateDiffEngine()
        self._animator = CanvasAnimator(self._canvas)
        self._trace: ExecutionTrace | None = None
        self._current_index: int = -1
        self._worker: ExecutionWorker | None = None
        self._retired_workers: list[ExecutionWorker] = []
        self._last_code: str = ""
        self._execution_diagnostics: str = ""
        self._auto_play_timer = QTimer()
        self._auto_play_timer.timeout.connect(self._on_next)
        self._auto_play_ms = 800

        self._connect_signals()

    def _connect_signals(self):
        self._window.btn_run.clicked.connect(self._on_run)
        self._window.btn_next.clicked.connect(self._on_next)
        self._window.btn_prev.clicked.connect(self._on_prev)
        self._window.btn_reset.clicked.connect(self._on_reset)
        self._window.btn_next_big.clicked.connect(self._on_next)
        self._window.btn_prev_big.clicked.connect(self._on_prev)
        self._window.btn_autoplay.toggled.connect(self._toggle_autoplay)
        self._window._speed_slider.valueChanged.connect(self._set_autoplay_speed)

    def cancel_current_run(self):
        if self._worker is not None and self._worker.isRunning():
            retire_worker(
                self,
                self._worker,
                disconnect=[
                    (self._worker.finished, self._on_trace_ready),
                    (self._worker.error, self._on_trace_error),
                ],
            )
            self._worker = None
        self._execution_diagnostics = ""
        self._window.show_loading(False)
        self._window.statusBar().showMessage(tr("Ready - Enter C++ code and click Run"))

    def _on_run(self):
        code = self._window.get_code()
        if not code:
            self._window.statusBar().showMessage(tr("No code to run"))
            return
        stdin_text = self._window.get_stdin()

        if not _has_api_key() and not _can_run_locally(code, stdin_text):
            from app.ui.widgets.api_key_dialog import show_api_key_dialog
            show_api_key_dialog(self._window)
            if not _has_api_key() and not _can_run_locally(code, stdin_text):
                self._window.statusBar().showMessage(
                    tr("API key not configured - click Settings or set provider API key")
                )
                return
        self._last_code = code

        self.cancel_current_run()

        self._window.show_loading(True)
        self._window.statusBar().showMessage(tr("Analyzing code..."))

        self._worker = ExecutionWorker(code, self._config_path, stdin_text)
        self._worker.finished.connect(self._on_trace_ready)
        self._worker.error.connect(self._on_trace_error)
        self._worker.start()

    def _on_trace_ready(self, result: ExecutionTrace | ExecutionResult):
        if isinstance(result, ExecutionResult):
            trace = result.trace
            diagnostics = result.diagnostics
        else:
            trace = result
            diagnostics = ""
        self._execution_diagnostics = diagnostics

        self._window.show_loading(False)
        self._trace = trace
        self._canvas.clear()

        if trace.steps:
            self._canvas.prepare_trace_layout(trace.steps)
            self._window.canvas_view.set_stable_fit_bounds(self._canvas.stable_fit_bounds())
            self._current_index = 0
            self._canvas.render_state(trace.steps[0])
            self._window.tracker_panel.set_state(trace.steps[0])
            self._queue_canvas_fit()
            self._ingest_knowledge(trace)
            error_store.log_activity("Code Run", f"Executed {len(trace.steps)} steps")
            message = tr("Step 1/{total} - Press PageDown for next step", total=len(trace.steps))
            if diagnostics:
                message = f"{message} [{diagnostics}]"
            self._window.statusBar().showMessage(message)
        else:
            self._current_index = -1
            self._execution_diagnostics = ""
            self._window.canvas_view.clear_stable_fit_bounds()
            self._window.statusBar().showMessage(tr("AI returned empty trace"))

        self._update_controls()
        self._highlight_current_line()

    def _on_trace_error(self, error_msg: str):
        self._window.show_loading(False)
        self._execution_diagnostics = ""
        self._window.statusBar().showMessage(
            tr("Error: {message}", message=error_msg.split(chr(10))[0])
        )

        raw = ""
        display_msg = error_msg
        if "---RAW RESPONSE---" in error_msg:
            parts = error_msg.split("---RAW RESPONSE---", 1)
            display_msg = parts[0].strip()
            raw = parts[1].strip()

        error_dialog.show_error_dialog(
            self._window,
            tr("Execution Error"),
            display_msg,
            code=self._last_code,
            raw_response=raw,
            on_retry=lambda: self._on_run(),
        )

    def _on_next(self):
        if self._trace is None:
            self._auto_play_timer.stop()
            return
        if self._current_index + 1 >= len(self._trace.steps):
            self._auto_play_timer.stop()
            self._window.btn_autoplay.setChecked(False)
            self._update_controls()
            return

        prev_state = self._trace.steps[self._current_index]
        self._current_index += 1
        curr_state = self._trace.steps[self._current_index]

        diff = self._diff_engine.diff(prev_state, curr_state)
        self._animator.stop_all()
        self._canvas.render_state(curr_state)
        self._window.tracker_panel.set_state(curr_state)
        self._animator.animate_diff(diff)
        if getattr(self._window, "auto_fit_check", None) is not None and self._window.auto_fit_check.isChecked():
            self._queue_canvas_fit()
        self._update_controls()
        self._highlight_current_line()

    def _on_prev(self):
        if self._trace is None or self._current_index <= 0:
            return

        self._current_index -= 1
        curr_state = self._trace.steps[self._current_index]
        self._animator.stop_all()
        self._canvas.render_state(curr_state)
        self._window.tracker_panel.set_state(curr_state)
        if getattr(self._window, "auto_fit_check", None) is not None and self._window.auto_fit_check.isChecked():
            self._queue_canvas_fit()
        self._update_controls()
        self._highlight_current_line()

    def _queue_canvas_fit(self):
        QTimer.singleShot(0, self._window.canvas_view.zoom_fit)

    def _on_reset(self):
        self._auto_play_timer.stop()
        self._trace = None
        self._current_index = -1
        self._execution_diagnostics = ""
        self._animator.stop_all()
        self._canvas.clear()
        self._window.canvas_view.clear_stable_fit_bounds()
        self._window.canvas_view.reset_view()
        self._window.tracker_panel.clear()
        self._window.step_label.setText(tr("Ready"))
        self._window.statusBar().showMessage(tr("Ready - Enter C++ code and click Run"))
        self._update_controls()

    def _toggle_autoplay(self, active: bool):
        if active:
            self._auto_play_timer.start(self._auto_play_ms)
            self._on_next()
        else:
            self._auto_play_timer.stop()

    def _set_autoplay_speed(self, ms: int):
        self._auto_play_ms = ms
        if self._auto_play_timer.isActive():
            self._auto_play_timer.setInterval(ms)

    def _highlight_current_line(self):
        if self._trace is None or self._current_index < 0:
            return
        try:
            step = self._trace.steps[self._current_index]
        except IndexError:
            return

        editor = self._window.code_editor
        editor.blockSignals(True)

        cursor = editor.textCursor()
        fmt_clear = QTextCharFormat()
        fmt_clear.setBackground(QColor(0, 0, 0, 0))
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setCharFormat(fmt_clear)

        line = max(0, step.line_number - 1)
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        for _ in range(line):
            cursor.movePosition(QTextCursor.MoveOperation.Down)

        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)

        fmt_highlight = QTextCharFormat()
        fmt_highlight.setBackground(QColor("#2A4A2A"))
        cursor.setCharFormat(fmt_highlight)

        cursor.clearSelection()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        editor.setTextCursor(cursor)
        editor.ensureCursorVisible()
        editor.blockSignals(False)

    def _ingest_knowledge(self, trace: ExecutionTrace):
        concepts: set[str] = set()
        for step in trace.steps:
            for frame in step.stack:
                for var in frame.variables:
                    if var.is_object and var.class_name:
                        concepts.add(var.class_name)
                    if var.is_array:
                        concepts.add("数组")
                    if var.is_function_object:
                        concepts.add("Lambda/函数对象")
                    if var.virtual_methods:
                        concepts.add("虚函数/多态")
                    if var.is_reference:
                        concepts.add("引用")
                    if var.is_pointer:
                        concepts.add("指针")
                    if var.base_classes:
                        concepts.add("继承")
                    if var.is_constructed:
                        concepts.add("构造/析构")
            for block in step.heap:
                if block.is_array:
                    concepts.add("堆数组")
        for c in concepts:
            error_store.add_knowledge_point(c, "code_editor")

    def _update_controls(self):
        total = len(self._trace.steps) if self._trace else 0
        current = self._current_index + 1 if self._current_index >= 0 else 0

        has_next = self._trace is not None and self._current_index + 1 < total
        has_prev = self._trace is not None and self._current_index > 0

        self._window.btn_next.setEnabled(has_next)
        self._window.btn_prev.setEnabled(has_prev)
        self._window.btn_next_big.setEnabled(has_next)
        self._window.btn_prev_big.setEnabled(has_prev)
        self._window.btn_reset.setEnabled(self._trace is not None)
        self._window.set_step_info(current, total)
        self._window.btn_autoplay.setEnabled(has_next)
        if not has_next:
            self._window.btn_autoplay.setChecked(False)
        message = tr(
            "Step {current}/{total} - {hint}",
            current=current,
            total=total,
            hint=tr("PageDown=next PageUp=prev") if self._trace else tr("Enter C++ code and click Run"),
        )
        if self._trace and self._execution_diagnostics:
            message = f"{message} [{self._execution_diagnostics}]"
        self._window.statusBar().showMessage(message)
