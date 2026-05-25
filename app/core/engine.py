from pathlib import Path

from app.ui.widgets.error_dialog import show_error_dialog
from app.core.memory_model import ExecutionTrace, MemoryState
from app.core.state_diff import StateDiffEngine, DiffResult
from app.ui.main_window import MainWindow
from app.ui.canvas.memory_canvas import MemoryCanvas
from app.ui.canvas.canvas_animator import CanvasAnimator
from app.core.execution_worker import ExecutionWorker
from app.services import error_store


class Engine:
    def __init__(self, window: MainWindow, config_path: Path | None = None):
        self._window = window
        self._config_path = config_path
        self._canvas = MemoryCanvas(window.canvas_view, window.canvas_scene)
        self._diff_engine = StateDiffEngine()
        self._animator = CanvasAnimator(self._canvas)
        self._trace: ExecutionTrace | None = None
        self._current_index: int = -1
        self._worker: ExecutionWorker | None = None
        self._last_code: str = ""

        self._connect_signals()

    def _connect_signals(self):
        self._window.btn_run.clicked.connect(self._on_run)
        self._window.btn_next.clicked.connect(self._on_next)
        self._window.btn_prev.clicked.connect(self._on_prev)
        self._window.btn_reset.clicked.connect(self._on_reset)

    def _on_run(self):
        code = self._window.get_code()
        if not code:
            self._window.statusBar().showMessage("No code to run")
            return
        self._last_code = code

        if self._worker is not None and self._worker.isRunning():
            try:
                self._worker.finished.disconnect(self._on_trace_ready)
                self._worker.error.disconnect(self._on_trace_error)
            except Exception:
                pass

        self._window.show_loading(True)
        self._window.statusBar().showMessage("Sending code to AI...")

        self._worker = ExecutionWorker(code, self._config_path)
        self._worker.finished.connect(self._on_trace_ready)
        self._worker.error.connect(self._on_trace_error)
        self._worker.start()

    def _on_trace_ready(self, trace: ExecutionTrace):
        self._window.show_loading(False)
        self._trace = trace

        if trace.steps:
            self._current_index = 0
            self._canvas.render_state(trace.steps[0])
            self._window.tracker_panel.set_state(trace.steps[0])
            self._ingest_knowledge(trace)
            error_store.log_activity("Code Run", f"Executed {len(trace.steps)} steps")
            self._window.statusBar().showMessage(
                f"Ready — {len(trace.steps)} steps loaded"
            )
        else:
            self._current_index = -1
            self._window.statusBar().showMessage("AI returned empty trace")

        self._update_controls()

    def _on_trace_error(self, error_msg: str):
        self._window.show_loading(False)
        self._window.statusBar().showMessage(f"Error: {error_msg.split(chr(10))[0]}")

        raw = ""
        display_msg = error_msg
        if "---RAW RESPONSE---" in error_msg:
            parts = error_msg.split("---RAW RESPONSE---", 1)
            display_msg = parts[0].strip()
            raw = parts[1].strip()

        show_error_dialog(
            self._window,
            "Execution Error",
            display_msg,
            code=self._last_code,
            raw_response=raw,
            on_retry=lambda: self._on_run(),
        )

    def _on_next(self):
        if self._trace is None or self._current_index + 1 >= len(self._trace.steps):
            return

        prev_state = self._trace.steps[self._current_index]
        self._current_index += 1
        curr_state = self._trace.steps[self._current_index]

        diff = self._diff_engine.diff(prev_state, curr_state)
        self._animator.stop_all()
        self._canvas.clear()
        self._canvas.render_state(curr_state)
        self._window.tracker_panel.set_state(curr_state)
        self._animator.animate_diff(diff)
        self._update_controls()

    def _on_prev(self):
        if self._trace is None or self._current_index <= 0:
            return

        self._current_index -= 1
        curr_state = self._trace.steps[self._current_index]
        self._animator.stop_all()
        self._canvas.clear()
        self._canvas.render_state(curr_state)
        self._window.tracker_panel.set_state(curr_state)
        self._update_controls()

    def _on_reset(self):
        self._trace = None
        self._current_index = -1
        self._animator.stop_all()
        self._canvas.clear()
        self._window.tracker_panel.clear()
        self._window.step_label.setText("Ready")
        self._update_controls()

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
        total = len(self._trace.steps) if self._trace else 0
        current = self._current_index + 1 if self._current_index >= 0 else 0

        self._window.btn_next.setEnabled(
            self._trace is not None and self._current_index + 1 < total
        )
        self._window.btn_prev.setEnabled(
            self._trace is not None and self._current_index > 0
        )
        self._window.btn_reset.setEnabled(self._trace is not None)
        self._window.set_step_info(current, total)
