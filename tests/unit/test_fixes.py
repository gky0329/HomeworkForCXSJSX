"""
Smoke tests for Phase 1-5 fixes.

Run:  python tests/unit/test_fixes.py
Required env: project root in PYTHONPATH (or run from project root).
"""

import json
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch, MagicMock

_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@contextmanager
def _temporary_error_path():
    from app.services import error_store

    old_path = error_store.ERRORS_PATH
    with tempfile.TemporaryDirectory() as tmpdir:
        error_store.ERRORS_PATH = Path(tmpdir) / "errors.json"
        try:
            yield error_store.ERRORS_PATH
        finally:
            error_store.ERRORS_PATH = old_path


# ── Phase 1: error_store lazy init + tmp fallback ──────────────────────

def test_error_store_lazy_init():
    """_ensure_data_dir() is called on first save, not at import time."""
    from app.services.error_store import _save, _load

    with _temporary_error_path() as errors_path:
        data = [{"id": "test1", "name": "test"}]
        _save(errors_path, data)
        loaded = _load(errors_path)
        assert len(loaded) == 1
        assert loaded[0]["name"] == "test"


def test_error_store_atomic_write():
    """_save writes to .tmp first, then os.replace."""
    from app.services.error_store import _save

    with _temporary_error_path() as errors_path:
        data = [{"id": "a"}]
        _save(errors_path, data)
        tmp_path = errors_path.with_suffix(errors_path.suffix + ".tmp")
        assert not tmp_path.exists(), "tmp file should be cleaned up after atomic rename"


# ── Phase 2: _pending guard ────────────────────────────────────────────

def test_canvas_animator_pending_guard():
    """_check_done does not decrement _pending below zero."""
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    try:
        from app.ui.canvas.canvas_animator import CanvasAnimator

        animator = CanvasAnimator(None)
        animator._pending = 0
        animator._generation = 1
        animator._check_done(1)  # gen matches
        assert animator._pending == 0, "_pending should stay at 0"
    finally:
        pass  # don't exit the app, other tests may need it


def test_memory_model_normalizes_llm_nulls_and_numbers():
    """ExecutionTrace accepts common LLM slips: null lists and numeric values."""
    from app.core.memory_model import ExecutionTrace

    trace = ExecutionTrace.model_validate({
        "steps": [{
            "line_number": 1,
            "source_code": "int a = 42;",
            "stack": [{
                "frame_name": "main",
                "variables": [{
                    "name": "a",
                    "type": "int",
                    "value": 42,
                    "address": "0xS001",
                    "is_pointer": False,
                    "elements": None,
                    "members": None,
                }],
            }],
            "heap": None,
            "edges": None,
        }],
    })

    step = trace.steps[0]
    assert step.stack[0].variables[0].value == "42"
    assert step.stack[0].variables[0].elements == []
    assert step.heap == []
    assert step.edges == []


def test_clear_layout_recurses_nested_layouts():
    """clear_layout() deletes widgets inside child layouts too."""
    from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QVBoxLayout, QWidget
    import sys

    QApplication.instance() or QApplication(sys.argv)

    from app.ui.widgets.helpers import clear_layout

    parent = QWidget()
    outer = QVBoxLayout(parent)
    inner = QHBoxLayout()
    label = QLabel("nested")
    inner.addWidget(label)
    outer.addLayout(inner)

    clear_layout(outer)
    assert outer.count() == 0
    assert inner.count() == 0


def test_memory_canvas_does_not_remove_rekeyed_stack_item():
    """Rendering a differently named frame should leave the new item in scene."""
    from PySide6.QtWidgets import QApplication, QGraphicsScene, QGraphicsView
    import sys

    QApplication.instance() or QApplication(sys.argv)

    from app.core.memory_model import MemoryState, StackFrame, Variable
    from app.ui.canvas.memory_canvas import MemoryCanvas

    view = QGraphicsView()
    scene = QGraphicsScene()
    scene.setSceneRect(0, 0, 800, 600)
    view.setScene(scene)
    canvas = MemoryCanvas(view, scene)

    first = MemoryState(
        line_number=1,
        source_code="int a = 1;",
        stack=[StackFrame(frame_name="main", variables=[
            Variable(name="a", type="int", value="1", address="0xS001", is_pointer=False),
        ])],
        heap=[],
        edges=[],
    )
    second = MemoryState(
        line_number=2,
        source_code="foo();",
        stack=[StackFrame(frame_name="foo", variables=[
            Variable(name="b", type="int", value="2", address="0xS002", is_pointer=False),
        ])],
        heap=[],
        edges=[],
    )

    canvas.render_state(first)
    canvas.render_state(second)

    stack_items = canvas.get_stack_items()
    assert len(stack_items) == 1
    assert stack_items[0].scene() is scene
    assert stack_items[0].frame.frame_name == "foo"


def test_memory_canvas_registers_member_pointer_edge_sources():
    """Member pointer edges should originate from the member label, not disappear."""
    from PySide6.QtWidgets import QApplication, QGraphicsScene, QGraphicsView
    import sys

    QApplication.instance() or QApplication(sys.argv)

    from app.core.memory_model import MemoryState, PointerEdge, StackFrame, StructMember, Variable
    from app.ui.canvas.memory_canvas import MemoryCanvas

    view = QGraphicsView()
    scene = QGraphicsScene()
    scene.setSceneRect(0, 0, 800, 600)
    view.setScene(scene)
    canvas = MemoryCanvas(view, scene)

    state = MemoryState(
        line_number=5,
        source_code="head->next->value = 3;",
        stack=[StackFrame(frame_name="main", variables=[
            Variable(
                name="first",
                type="Node",
                value="{value=3, next=nullptr}",
                address="0xS001",
                is_pointer=False,
                is_object=True,
                members=[
                    StructMember(name="value", type="int", value="3", address="0xS001.value"),
                    StructMember(name="next", type="Node*", value="nullptr", address="0xS001.next"),
                ],
            ),
            Variable(
                name="second",
                type="Node",
                value="{value=2, next=0xS001}",
                address="0xS002",
                is_pointer=False,
                is_object=True,
                members=[
                    StructMember(name="value", type="int", value="2", address="0xS002.value"),
                    StructMember(name="next", type="Node*", value="0xS001", address="0xS002.next"),
                ],
            ),
        ])],
        heap=[],
        edges=[PointerEdge(source_address="0xS002.next", target_address="0xS001")],
    )

    canvas.render_state(state)

    assert canvas.get_item_by_address("0xS002.next") is not None
    assert canvas.get_item_by_address("0xS001") is not None
    assert len(canvas.get_edge_items()) == 1


def test_memory_canvas_registers_array_element_pointer_edge_sources():
    """Array pointer edges should originate from the element cell, not the whole var."""
    from PySide6.QtWidgets import QApplication, QGraphicsScene, QGraphicsView
    import sys

    QApplication.instance() or QApplication(sys.argv)

    from app.core.memory_model import ArrayElement, MemoryState, PointerEdge, StackFrame, Variable
    from app.ui.canvas.memory_canvas import MemoryCanvas

    view = QGraphicsView()
    scene = QGraphicsScene()
    scene.setSceneRect(0, 0, 800, 600)
    view.setScene(scene)
    canvas = MemoryCanvas(view, scene)

    state = MemoryState(
        line_number=6,
        source_code="*ptrs[1] = 9;",
        stack=[StackFrame(frame_name="main", variables=[
            Variable(name="a", type="int", value="1", address="0xS001", is_pointer=False),
            Variable(name="b", type="int", value="9", address="0xS002", is_pointer=False),
            Variable(
                name="ptrs",
                type="std::vector<int*>",
                value="{[0]=0xS001, [1]=0xS002}",
                address="0xS003",
                is_pointer=False,
                is_array=True,
                elements=[
                    ArrayElement(index=0, type="int*", value="0xS001", address="0xS003[0]"),
                    ArrayElement(index=1, type="int*", value="0xS002", address="0xS003[1]"),
                ],
            ),
        ])],
        heap=[],
        edges=[PointerEdge(source_address="0xS003[1]", target_address="0xS002")],
    )

    canvas.render_state(state)

    assert canvas.get_item_by_address("0xS003[1]") is not None
    assert canvas.get_item_by_address("0xS002") is not None
    assert len(canvas.get_edge_items()) == 1


def test_canvas_view_uses_stable_fit_bounds():
    """Auto-fit should use trace-wide bounds instead of per-step item bounds."""
    from PySide6.QtCore import QRectF
    from PySide6.QtWidgets import QApplication, QGraphicsScene
    import sys

    QApplication.instance() or QApplication(sys.argv)

    from app.ui.main_window import CanvasView

    view = CanvasView()
    view.resize(420, 300)
    scene = QGraphicsScene()
    scene.setSceneRect(0, 0, 2000, 2000)
    view.setScene(scene)
    view.set_stable_fit_bounds(QRectF(0, 0, 800, 600))
    view.zoom_fit()
    first_scale = view.transform().m11()
    first_center = view.mapToScene(view.viewport().rect().center())

    scene.addRect(0, 0, 1600, 1600)
    view.zoom_fit()
    second_scale = view.transform().m11()
    second_center = view.mapToScene(view.viewport().rect().center())

    assert abs(first_scale - second_scale) < 0.000001
    assert abs(first_center.x() - second_center.x()) < 0.000001
    assert abs(first_center.y() - second_center.y()) < 0.000001


def test_code_editor_auto_fit_defaults_to_initial_fit_only():
    """The code editor should fit a new trace once, then preserve the view while stepping."""
    from PySide6.QtWidgets import QApplication
    import sys

    QApplication.instance() or QApplication(sys.argv)

    from app.core.engine import Engine
    from app.core.memory_model import ExecutionTrace, MemoryState, StackFrame, Variable
    from app.ui.main_window import MainWindow

    window = MainWindow()
    try:
        engine = Engine(window)
        fit_calls = []
        engine._queue_canvas_fit = lambda: fit_calls.append("fit")
        trace = ExecutionTrace(steps=[
            MemoryState(
                line_number=1,
                source_code="int a = 1;",
                stack=[StackFrame(frame_name="main", variables=[
                    Variable(name="a", type="int", value="1", address="0xS001", is_pointer=False),
                ])],
                heap=[],
                edges=[],
            ),
            MemoryState(
                line_number=2,
                source_code="int b = a + 1;",
                stack=[StackFrame(frame_name="main", variables=[
                    Variable(name="a", type="int", value="1", address="0xS001", is_pointer=False),
                    Variable(name="b", type="int", value="2", address="0xS002", is_pointer=False),
                ])],
                heap=[],
                edges=[],
            ),
        ])

        assert window.auto_fit_check.isChecked() is False
        with patch("app.core.engine.error_store.log_activity"), patch("app.core.engine.error_store.add_knowledge_point"):
            engine._on_trace_ready(trace)
        assert fit_calls == ["fit"]

        fit_calls.clear()
        engine._on_next()
        assert fit_calls == []

        window.auto_fit_check.setChecked(True)
        engine._on_prev()
        assert fit_calls == ["fit"]
    finally:
        window.close()


def test_code_editor_status_shows_execution_diagnostics():
    """Successful runs should show whether the trace came from native or AI fallback."""
    from PySide6.QtWidgets import QApplication
    import sys

    QApplication.instance() or QApplication(sys.argv)

    from app.core.engine import Engine
    from app.core.execution_worker import ExecutionResult
    from app.core.memory_model import ExecutionTrace, MemoryState, StackFrame, Variable
    from app.ui.main_window import MainWindow

    window = MainWindow()
    try:
        engine = Engine(window)
        engine._queue_canvas_fit = lambda: None
        trace = ExecutionTrace(steps=[
            MemoryState(
                line_number=1,
                source_code="int a = 1;",
                stack=[StackFrame(frame_name="main", variables=[
                    Variable(name="a", type="int", value="1", address="0xS001", is_pointer=False),
                ])],
                heap=[],
                edges=[],
            ),
        ])

        with patch("app.core.engine.error_store.log_activity"), patch("app.core.engine.error_store.add_knowledge_point"):
            engine._on_trace_ready(ExecutionResult(
                trace=trace,
                diagnostics="Native debugger: MSVC / PDB",
            ))

        assert "Native debugger: MSVC / PDB" in window.statusBar().currentMessage()
    finally:
        window.close()


def test_settings_dialog_saves_experimental_pdb_toggle():
    """Settings should expose the experimental PDB flag without hand-editing YAML."""
    from PySide6.QtWidgets import QApplication
    import sys
    import yaml

    QApplication.instance() or QApplication(sys.argv)

    from app.ui.widgets.api_key_dialog import ApiKeyDialog

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text(
            "llm:\n"
            "  provider: deepseek\n"
            "  providers:\n"
            "    deepseek:\n"
            "      api_key: ''\n"
            "      api_key_env: DEEPSEEK_API_KEY\n"
            "      api_base: https://api.deepseek.com\n"
            "      model: deepseek-chat\n",
            encoding="utf-8",
        )
        dialog = ApiKeyDialog(config_path=config_path)
        try:
            dialog._pdb_check.setChecked(True)
            dialog._save_and_accept()
        finally:
            dialog.close()

        saved = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert saved["debugger"]["enable_experimental_pdb"] is True


def test_memory_canvas_prepares_trace_wide_fit_bounds():
    """Trace layout planning should include later heap/object-heavy steps."""
    from PySide6.QtWidgets import QApplication, QGraphicsScene, QGraphicsView
    import sys

    QApplication.instance() or QApplication(sys.argv)

    from app.core.memory_model import HeapBlock, MemoryState, StackFrame, StructMember, Variable
    from app.ui.canvas.memory_canvas import MemoryCanvas

    scene = QGraphicsScene()
    scene.setSceneRect(0, 0, 1600, 2000)
    canvas = MemoryCanvas(QGraphicsView(), scene)
    simple = MemoryState(
        line_number=1,
        source_code="int a = 1;",
        stack=[StackFrame(frame_name="main", variables=[
            Variable(name="a", type="int", value="1", address="0xS001", is_pointer=False),
        ])],
        heap=[],
        edges=[],
    )
    object_step = MemoryState(
        line_number=2,
        source_code="Point* p = new Point{1, 2};",
        stack=[StackFrame(frame_name="main", variables=[
            Variable(name="p", type="Point*", value="0xH001", address="0xS001", is_pointer=True),
        ])],
        heap=[HeapBlock(
            address="0xH001",
            type="Point",
            value="{x=1, label=long_member_name_for_layout}",
            is_object=True,
            class_name="Point",
            members=[
                StructMember(name="x", type="int", value="1"),
                StructMember(name="label", type="string", value="long_member_name_for_layout"),
            ],
        )],
        edges=[],
    )

    canvas.prepare_trace_layout([simple, object_step])
    bounds = canvas.stable_fit_bounds()

    assert bounds.isValid()
    assert bounds.width() > 260
    assert bounds.height() > 80


def test_state_diff_detects_member_changes():
    """Nested struct/object member edits should count as value changes."""
    from app.core.memory_model import MemoryState, StackFrame, StructMember, Variable
    from app.core.state_diff import StateDiffEngine

    prev = MemoryState(
        line_number=1,
        source_code="Point p{1, 2};",
        stack=[StackFrame(frame_name="main", variables=[
            Variable(
                name="p",
                type="struct Point",
                value="{x=1, y=2}",
                address="0xS001",
                is_pointer=False,
                members=[
                    StructMember(name="x", type="int", value="1"),
                    StructMember(name="y", type="int", value="2"),
                ],
            ),
        ])],
        heap=[],
        edges=[],
    )
    curr = MemoryState(
        line_number=2,
        source_code="p.x = 3;",
        stack=[StackFrame(frame_name="main", variables=[
            Variable(
                name="p",
                type="struct Point",
                value="{x=1, y=2}",
                address="0xS001",
                is_pointer=False,
                members=[
                    StructMember(name="x", type="int", value="3"),
                    StructMember(name="y", type="int", value="2"),
                ],
            ),
        ])],
        heap=[],
        edges=[],
    )

    diff = StateDiffEngine().diff(prev, curr)
    assert len(diff.modified_vars) == 1
    assert diff.modified_vars[0].address == "0xS001"


def test_oj_page_autogen_passes_empty_code_to_worker():
    """When no reference code is provided, OJ analysis should use autogen mode."""
    from PySide6.QtWidgets import QApplication
    import sys

    QApplication.instance() or QApplication(sys.argv)

    captured = {}

    class FakeSignal:
        def connect(self, slot):
            self.slot = slot

    class FakeWorker:
        def __init__(self, problem, code, config_path=None):
            captured["problem"] = problem
            captured["code"] = code
            captured["config_path"] = config_path
            self.finished = FakeSignal()
            self.error = FakeSignal()

        def isRunning(self):
            return False

        def start(self):
            captured["started"] = True

    with patch("app.ui.pages.oj_page.OJWorker", new=FakeWorker):
        from app.ui.pages.oj_page import OJPage

        page = OJPage()
        page._problem_edit.setPlainText("给定两个整数，输出它们的和")
        page._code_edit.clear()
        page._on_run()

    assert captured["problem"] == "给定两个整数，输出它们的和"
    assert captured["code"] == ""
    assert captured["started"] is True
    assert page._autogen is True


def test_debug_executor_parses_lldb_snapshots():
    """LLDB snapshots should map stack, heap, pointer, and delete states."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int a = 42;\n"
        "int* p = new int(100);\n"
        "*p = 200;\n"
        "delete p;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l1 = generated_lines[1]
    l2 = generated_lines[2]
    l3 = generated_lines[3]
    l4 = generated_lines[4]
    l5 = l4 + 1
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l1}:7
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l2}:12
0x000000016fdfe728: (int) a = 42
0x000000016fdfe720: (int *) p = 0x0000000000000000
__CXXMV_BEFORE__1
frame #0: 0x2 program`main at program.cpp:{l2}:12
__CXXMV_AFTER__1
frame #0: 0x3 program`main at program.cpp:{l3}:4
0x000000016fdfe728: (int) a = 42
0x000000016fdfe720: (int *) p = 0x00000001006446a0 {{
0x00000001006446a0:   (int) *p = 100
}}
__CXXMV_BEFORE__2
frame #0: 0x3 program`main at program.cpp:{l3}:4
__CXXMV_AFTER__2
frame #0: 0x4 program`main at program.cpp:{l4}:10
0x000000016fdfe728: (int) a = 42
0x000000016fdfe720: (int *) p = 0x00000001006446a0 {{
0x00000001006446a0:   (int) *p = 200
}}
__CXXMV_BEFORE__3
frame #0: 0x4 program`main at program.cpp:{l4}:10
__CXXMV_AFTER__3
frame #0: 0x5 program`main at program.cpp:{l5}:3
0x000000016fdfe728: (int) a = 42
0x000000016fdfe720: (int *) p = 0x00000001006446a0
"""

    trace = executor._parse_lldb_output(output, prepared)

    assert [s.line_number for s in trace.steps] == [1, 2, 3, 4]
    assert [v.name for v in trace.steps[0].stack[0].variables] == ["a"]
    assert trace.steps[1].heap[0].address == "0xH001"
    assert trace.steps[1].heap[0].value == "100"
    assert trace.steps[2].heap[0].value == "200"
    assert trace.steps[3].heap[0].is_freed is True
    assert trace.steps[3].edges[0].is_dangling is True


def test_debug_executor_parses_arrays_and_struct_members():
    """LLDB child values should populate array elements and struct members."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int arr[3] = {1, 2, 3};\n"
        "arr[1] = 7;\n"
        "struct Point { int x; int y; };\n"
        "Point pt{1, 2};\n"
        "pt.x = 5;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l1 = generated_lines[1]
    l2 = generated_lines[2]
    l4 = generated_lines[4]
    l5 = generated_lines[5]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l1}:7
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l2}:8
0x000000016fdfe6b8: (int[3]) arr = {{
0x000000016fdfe6b8:   (int) [0] = 1
0x000000016fdfe6bc:   (int) [1] = 2
0x000000016fdfe6c0:   (int) [2] = 3
}}
__CXXMV_BEFORE__1
frame #0: 0x2 program`main at program.cpp:{l2}:8
__CXXMV_AFTER__1
frame #0: 0x3 program`main at program.cpp:{l4}:9
0x000000016fdfe6b8: (int[3]) arr = {{
0x000000016fdfe6b8:   (int) [0] = 1
0x000000016fdfe6bc:   (int) [1] = 7
0x000000016fdfe6c0:   (int) [2] = 3
}}
__CXXMV_BEFORE__2
frame #0: 0x3 program`main at program.cpp:{l4}:9
__CXXMV_AFTER__2
frame #0: 0x4 program`main at program.cpp:{l5}:4
0x000000016fdfe6b8: (int[3]) arr = {{
0x000000016fdfe6b8:   (int) [0] = 1
0x000000016fdfe6bc:   (int) [1] = 7
0x000000016fdfe6c0:   (int) [2] = 3
}}
0x000000016fdfe6d0: (Point) pt = {{
0x000000016fdfe6d0:   (int) x = 1
0x000000016fdfe6d4:   (int) y = 2
}}
__CXXMV_BEFORE__3
frame #0: 0x4 program`main at program.cpp:{l5}:4
__CXXMV_AFTER__3
frame #0: 0x5 program`main at program.cpp:{l5 + 1}:3
0x000000016fdfe6b8: (int[3]) arr = {{
0x000000016fdfe6b8:   (int) [0] = 1
0x000000016fdfe6bc:   (int) [1] = 7
0x000000016fdfe6c0:   (int) [2] = 3
}}
0x000000016fdfe6d0: (Point) pt = {{
0x000000016fdfe6d0:   (int) x = 5
0x000000016fdfe6d4:   (int) y = 2
}}
"""

    trace = executor._parse_lldb_output(output, prepared)

    first_arr = trace.steps[0].stack[0].variables[0]
    changed_arr = trace.steps[1].stack[0].variables[0]
    point = trace.steps[3].stack[0].variables[1]
    assert first_arr.is_array is True
    assert [(e.index, e.value) for e in first_arr.elements] == [(0, "1"), (1, "2"), (2, "3")]
    assert changed_arr.value == "{[0]=1, [1]=7, [2]=3}"
    assert point.is_object is True
    assert point.class_name == "Point"
    assert [(m.name, m.type, m.value) for m in point.members] == [
        ("x", "int", "5"),
        ("y", "int", "2"),
    ]


def test_debug_executor_parses_lldb_class_object_members():
    """Class instances should be represented as objects with member values."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "class Counter {\n"
        "public:\n"
        "    int value;\n"
        "    Counter(int v) : value(v) {}\n"
        "    void inc() { value++; }\n"
        "};\n"
        "int main() {\n"
        "    Counter c(3);\n"
        "    c.value = 4;\n"
        "    return c.value;\n"
        "}\n"
    )
    output = """
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:8:13
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:9:5
__CXXMV_FRAME__0__9__main
0x000000016fdfe710: (Counter) c = {
0x000000016fdfe710:   (int) value = 3
}
__CXXMV_BEFORE__1
frame #0: 0x2 program`main at program.cpp:9:5
__CXXMV_AFTER__1
frame #0: 0x3 program`main at program.cpp:10:12
__CXXMV_FRAME__0__10__main
0x000000016fdfe710: (Counter) c = {
0x000000016fdfe710:   (int) value = 4
}
"""

    trace = executor._parse_lldb_output(output, prepared)

    assert [step.line_number for step in trace.steps] == [8, 9]
    first = trace.steps[0].stack[0].variables[0]
    changed = trace.steps[1].stack[0].variables[0]
    assert first.is_object is True
    assert first.class_name == "Counter"
    assert first.value == "{value=3}"
    assert changed.members[0].value == "4"


def test_debug_executor_parses_lldb_inherited_virtual_object_metadata():
    """Native object snapshots should carry base-class and virtual-method metadata."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "class Animal { public: int age; virtual int speak() { return age; } };\n"
        "class Dog : public Animal { public: int bones; int speak() override { return age + bones; } };\n"
        "Dog d;\n"
        "d.age = 3;\n"
        "d.bones = 4;\n"
        "Animal* a = &d;\n"
        "int sound = a->speak();\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l7 = generated_lines[7]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l7}:13
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l7 + 1}:3
__CXXMV_FRAME__0__{l7 + 1}__main
0x000000016fdfe700: (Dog) d = {{
0x000000016fdfe700:   (Animal) Animal = {{age=3}}
0x000000016fdfe708:   (int) bones = 4
}}
0xf000000000000001: (Dog *) a = 0x000000016fdfe700
0x000000016fdfe6fc: (int) sound = 7
"""

    trace = executor._parse_lldb_output(output, prepared)
    state = trace.steps[0]
    values = {var.name: var for var in state.stack[0].variables}
    dog = values["d"]
    pointer = values["a"]

    assert dog.is_object is True
    assert dog.class_name == "Dog"
    assert dog.base_classes == ["Animal"]
    assert dog.virtual_methods == ["speak()"]
    assert [(member.name, member.value) for member in dog.members] == [
        ("Animal", "{age=3}"),
        ("bones", "4"),
    ]
    assert pointer.value == dog.address
    assert pointer.address != dog.address
    assert state.edges[0].source_address == pointer.address
    assert state.edges[0].target_address == dog.address
    assert values["sound"].value == "7"


def test_debug_executor_formats_double_values_for_display():
    """Floating point scalar values should render readably on the canvas."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "double pi = 3.14;\n"
        "double area = pi * 2.0;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l1 = generated_lines[1]
    l2 = generated_lines[2]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l1}:12
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l2}:15
0x000000016fdfe710: (double) pi = 3.1400000000000001
__CXXMV_BEFORE__1
frame #0: 0x2 program`main at program.cpp:{l2}:15
__CXXMV_AFTER__1
frame #0: 0x3 program`main at program.cpp:{l2 + 1}:1
0x000000016fdfe710: (double) pi = 3.1400000000000001
0x000000016fdfe718: (double) area = 6.2800000000000002
"""

    trace = executor._parse_lldb_output(output, prepared)

    first = trace.steps[0].stack[0].variables[0]
    second_vars = trace.steps[1].stack[0].variables
    assert first.type == "double"
    assert first.value == "3.14"
    assert [(var.name, var.type, var.value) for var in second_vars] == [
        ("pi", "double", "3.14"),
        ("area", "double", "6.28"),
    ]


def test_debug_executor_filters_future_long_long_locals():
    """Compound scalar declarations should not appear before their source line."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "bool ok = true;\n"
        "char ch = 'A';\n"
        "long long big = 1234567890123LL;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l1 = generated_lines[1]
    l2 = generated_lines[2]
    l3 = generated_lines[3]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l1}:9
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l2}:9
__CXXMV_FRAME__0__{l2}__main
0x000000016fdfe700: (bool) ok = true
0x000000016fdfe708: (long long) big = 6171913536
__CXXMV_BEFORE__1
frame #0: 0x2 program`main at program.cpp:{l2}:9
__CXXMV_AFTER__1
frame #0: 0x3 program`main at program.cpp:{l3}:15
__CXXMV_FRAME__0__{l3}__main
0x000000016fdfe700: (bool) ok = true
0x000000016fdfe701: (char) ch = 'A'
0x000000016fdfe708: (long long) big = 6171913536
__CXXMV_BEFORE__2
frame #0: 0x3 program`main at program.cpp:{l3}:15
__CXXMV_AFTER__2
frame #0: 0x4 program`main at program.cpp:{l3 + 1}:3
__CXXMV_FRAME__0__{l3 + 1}__main
0x000000016fdfe700: (bool) ok = true
0x000000016fdfe701: (char) ch = 'A'
0x000000016fdfe708: (long long) big = 1234567890123
"""

    trace = executor._parse_lldb_output(output, prepared)

    assert [var.name for var in trace.steps[0].stack[0].variables] == ["ok"]
    assert [var.name for var in trace.steps[1].stack[0].variables] == ["ok", "ch"]
    assert [(var.name, var.value) for var in trace.steps[2].stack[0].variables] == [
        ("ok", "true"),
        ("ch", "'A'"),
        ("big", "1234567890123"),
    ]


def test_debug_executor_filters_future_double_pointer_locals():
    """Pointer declarators with repeated stars should not appear before declaration."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int a = 1;\n"
        "int *p = &a;\n"
        "int **pp = &p;\n"
        "**pp = 7;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l1 = generated_lines[1]
    l2 = generated_lines[2]
    l3 = generated_lines[3]
    l4 = generated_lines[4]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l1}:9
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l2}:13
__CXXMV_FRAME__0__{l2}__main
0x000000016fdfe700: (int) a = 1
0x000000016fdfe708: (int *) p = 0x000000016fdfe700
0x000000016fdfe710: (int **) pp = 0x000000016fdfe708
__CXXMV_BEFORE__1
frame #0: 0x2 program`main at program.cpp:{l2}:13
__CXXMV_AFTER__1
frame #0: 0x3 program`main at program.cpp:{l3}:15
__CXXMV_FRAME__0__{l3}__main
0x000000016fdfe700: (int) a = 1
0x000000016fdfe708: (int *) p = 0x000000016fdfe700
0x000000016fdfe710: (int **) pp = 0x000000016fdfe708
__CXXMV_BEFORE__2
frame #0: 0x3 program`main at program.cpp:{l3}:15
__CXXMV_AFTER__2
frame #0: 0x4 program`main at program.cpp:{l4}:8
__CXXMV_FRAME__0__{l4}__main
0x000000016fdfe700: (int) a = 1
0x000000016fdfe708: (int *) p = 0x000000016fdfe700
0x000000016fdfe710: (int **) pp = 0x000000016fdfe708
__CXXMV_BEFORE__3
frame #0: 0x4 program`main at program.cpp:{l4}:8
__CXXMV_AFTER__3
frame #0: 0x5 program`main at program.cpp:{l4 + 1}:3
__CXXMV_FRAME__0__{l4 + 1}__main
0x000000016fdfe700: (int) a = 7
0x000000016fdfe708: (int *) p = 0x000000016fdfe700
0x000000016fdfe710: (int **) pp = 0x000000016fdfe708
"""

    trace = executor._parse_lldb_output(output, prepared)

    assert [var.name for var in trace.steps[0].stack[0].variables] == ["a"]
    assert [var.name for var in trace.steps[1].stack[0].variables] == ["a", "p"]
    assert [var.name for var in trace.steps[2].stack[0].variables] == ["a", "p", "pp"]
    values = {var.name: var for var in trace.steps[-1].stack[0].variables}
    assert values["a"].value == "7"
    assert values["p"].value == values["a"].address
    assert values["pp"].value == values["p"].address
    assert trace.steps[-1].heap == []
    assert {
        (edge.source_address, edge.target_address)
        for edge in trace.steps[-1].edges
    } == {
        (values["p"].address, values["a"].address),
        (values["pp"].address, values["p"].address),
    }


def test_debug_executor_parses_nullptr_pointer_value():
    """Null native pointers should render as nullptr, not an empty string."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source("int* p = nullptr;\n")
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l1 = generated_lines[1]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l1}:10
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l1 + 1}:3
__CXXMV_FRAME__0__{l1 + 1}__main
0x000000016fdfe700: (int *) p = 0x0
"""

    trace = executor._parse_lldb_output(output, prepared)
    pointer = trace.steps[0].stack[0].variables[0]

    assert pointer.name == "p"
    assert pointer.is_pointer is True
    assert pointer.value == "nullptr"
    assert trace.steps[0].heap == []
    assert trace.steps[0].edges == []


def test_debug_executor_parses_c_string_pointer_summary():
    """char pointers should point to a readable C-string block, not only the first char."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source('const char* s = "hello";\n')
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l1 = generated_lines[1]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l1}:17
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l1 + 1}:3
__CXXMV_FRAME__0__{l1 + 1}__main
0x000000016fdfe700: (const char *) s = 0x0000000100003f9a {{
0x0000000100003f9a:   (const char[]) *s = "hello"
}}
"""

    trace = executor._parse_lldb_output(output, prepared)
    pointer = trace.steps[0].stack[0].variables[0]
    heap = trace.steps[0].heap[0]

    assert pointer.value == "0xH001"
    assert heap.type == "const char[]"
    assert heap.value == "hello"
    assert trace.steps[0].edges[0].target_address == "0xH001"


def test_debug_executor_keeps_locals_on_wrapped_snippet_last_line():
    """Snippet wrappers should not clear locals after the final user line runs."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int a = 42;\n"
        "int b = a + 10;\n"
        "double pi = 3.14;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l1 = generated_lines[1]
    l2 = generated_lines[2]
    l3 = generated_lines[3]
    wrapper_return_line = l3 + 1
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l1}:9
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l2}:9
__CXXMV_FRAME__0__{l2}__main
0x000000016fdfe700: (int) a = 42
__CXXMV_BEFORE__1
frame #0: 0x2 program`main at program.cpp:{l2}:9
__CXXMV_AFTER__1
frame #0: 0x3 program`main at program.cpp:{l3}:12
__CXXMV_FRAME__0__{l3}__main
0x000000016fdfe700: (int) a = 42
0x000000016fdfe704: (int) b = 52
__CXXMV_BEFORE__2
frame #0: 0x3 program`main at program.cpp:{l3}:12
__CXXMV_AFTER__2
frame #0: 0x4 program`main at program.cpp:{wrapper_return_line}:3
__CXXMV_FRAME__0__{wrapper_return_line}__main
0x000000016fdfe700: (int) a = 42
0x000000016fdfe704: (int) b = 52
0x000000016fdfe708: (double) pi = 3.1400000000000001
"""

    trace = executor._parse_lldb_output(output, prepared)

    assert [step.line_number for step in trace.steps] == [1, 2, 3]
    assert [(var.name, var.type, var.value) for var in trace.steps[2].stack[0].variables] == [
        ("a", "int", "42"),
        ("b", "int", "52"),
        ("pi", "double", "3.14"),
    ]


def test_debug_executor_parses_reference_target_address():
    """C++ references should point at their referent instead of rendering as objects."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int a = 5;\n"
        "int& r = a;\n"
        "r = 9;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l1 = generated_lines[1]
    l2 = generated_lines[2]
    l3 = generated_lines[3]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l1}:9
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l2}:8
__CXXMV_FRAME__0__{l2}__main
0x000000016fdfe700: (int) a = 5
__CXXMV_BEFORE__1
frame #0: 0x2 program`main at program.cpp:{l2}:8
__CXXMV_AFTER__1
frame #0: 0x3 program`main at program.cpp:{l3}:3
__CXXMV_FRAME__0__{l3}__main
0x000000016fdfe700: (int) a = 5
0x000000016fdfe708: (int &) r = 0x000000016fdfe700
__CXXMV_BEFORE__2
frame #0: 0x3 program`main at program.cpp:{l3}:3
__CXXMV_AFTER__2
frame #0: 0x4 program`main at program.cpp:{l3 + 1}:3
__CXXMV_FRAME__0__{l3 + 1}__main
0x000000016fdfe700: (int) a = 9
0x000000016fdfe708: (int &) r = 0x000000016fdfe700
"""

    trace = executor._parse_lldb_output(output, prepared)

    ref_step = trace.steps[1]
    changed_step = trace.steps[2]
    a = ref_step.stack[0].variables[0]
    ref = ref_step.stack[0].variables[1]
    changed_a = changed_step.stack[0].variables[0]
    changed_ref = changed_step.stack[0].variables[1]
    assert ref.is_reference is True
    assert ref.is_pointer is False
    assert ref.is_object is False
    assert ref.value == a.address
    assert ref_step.edges == []
    assert changed_a.value == "9"
    assert changed_ref.value == changed_a.address


def test_debug_executor_marks_expired_stack_pointer_dangling():
    """Pointers to locals that left scope should not become fake heap blocks."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int* p = nullptr;\n"
        "{\n"
        "    int local = 5;\n"
        "    p = &local;\n"
        "}\n"
        "int after = 9;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l3 = generated_lines[3]
    l4 = generated_lines[4]
    l6 = generated_lines[6]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l3}:15
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l4}:8
__CXXMV_FRAME__0__{l4}__main
0x000000016fdfe700: (int *) p = 0x0
0x000000016fdfe704: (int) local = 5
__CXXMV_BEFORE__1
frame #0: 0x2 program`main at program.cpp:{l4}:8
__CXXMV_AFTER__1
frame #0: 0x3 program`main at program.cpp:{l6}:11
__CXXMV_FRAME__0__{l6}__main
0x000000016fdfe700: (int *) p = 0x000000016fdfe704
__CXXMV_BEFORE__2
frame #0: 0x3 program`main at program.cpp:{l6}:11
__CXXMV_AFTER__2
frame #0: 0x4 program`main at program.cpp:{l6 + 1}:3
__CXXMV_FRAME__0__{l6 + 1}__main
0x000000016fdfe700: (int *) p = 0x000000016fdfe704
0x000000016fdfe708: (int) after = 9
"""

    trace = executor._parse_lldb_output(output, prepared)
    assign_step = trace.steps[1]
    final = trace.steps[-1]
    p = next(var for var in final.stack[0].variables if var.name == "p")
    after = next(var for var in final.stack[0].variables if var.name == "after")

    assert p.value == "0xS002"
    assert after.value == "9"
    assert assign_step.heap == []
    assert final.heap == []
    assert assign_step.edges[0].target_address == "0xS002"
    assert assign_step.edges[0].is_dangling is True
    assert final.edges[0].target_address == "0xS002"
    assert final.edges[0].is_dangling is True


def test_debug_executor_formats_std_string_summary_as_scalar():
    """std::string should show its readable value instead of an empty object shell."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        '#include <string>\n'
        'using namespace std;\n'
        'int main() {\n'
        '    string s = "abc";\n'
        '    s += "d";\n'
        '}\n'
    )
    output = """
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:4:12
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:5:5
__CXXMV_FRAME__0__5__main
0x000000016fdfe700: (std::__1::string) s = "abc"
__CXXMV_BEFORE__1
frame #0: 0x2 program`main at program.cpp:5:5
__CXXMV_AFTER__1
frame #0: 0x3 program`main at program.cpp:6:1
__CXXMV_FRAME__0__6__main
0x000000016fdfe700: (std::__1::string) s = "abcd"
"""

    trace = executor._parse_lldb_output(output, prepared)

    first = trace.steps[0].stack[0].variables[0]
    changed = trace.steps[1].stack[0].variables[0]
    assert first.type == "std::__1::string"
    assert first.value == "abc"
    assert first.is_object is False
    assert changed.value == "abcd"


def test_debug_executor_lldb_script_expands_string_keyed_containers():
    """A container type containing string should not be emitted as scalar text."""
    from app.core.debug_executor import DebugExecutor

    script = DebugExecutor._lldb_stack_snapshot_command()
    assert "def is_std_string_type" in script
    assert "def is_expandable_container_type" in script
    assert "def is_c_array_type" in script
    assert "if is_std_string_type(typ) and val:" in script
    assert "if val and not is_expandable_container_type(typ) and not is_c_array_type(typ):" in script
    assert "'string' in typ and 'vector' not in typ" not in script


def test_debug_executor_lldb_script_expands_smart_pointers():
    """LLDB snapshots should dereference smart pointers like heap owners."""
    from app.core.debug_executor import DebugExecutor

    script = DebugExecutor._lldb_stack_snapshot_command()

    assert "def is_smart_pointer_type" in script
    assert "def top_level_template_type_key" in script
    assert "def smart_pointer_child" in script
    assert "if is_smart_pointer_type(typ):" in script
    assert "if not raw_val:" in script
    assert "return '0x0'" in script
    assert "return raw_val + ' {' + deref_val + '}'" in script
    assert "emit_child(deref, '*' + name" in script


def test_debug_executor_lldb_script_uses_top_level_pointer_checks():
    """LLDB snapshots should not treat template element pointers as owner pointers."""
    from app.core.debug_executor import DebugExecutor

    script = DebugExecutor._lldb_stack_snapshot_command()

    assert "def is_pointer_type" in script
    assert "def has_top_level_symbol" in script
    assert "loc == 'scalar' and is_pointer_type(typ)" in script
    assert "if is_pointer_type(typ) and not val:" in script
    assert "if '*' in typ and not val:" not in script
    assert "loc == 'scalar' and '*' in typ" not in script
    assert "'*' in child_typ" not in script


def test_debug_executor_smart_pointer_checks_are_top_level_only():
    """Container template args should not make the container itself pointer-like."""
    from app.core.debug_executor import DebugExecutor

    assert DebugExecutor._is_smart_pointer_type("std::__1::shared_ptr<int>") is True
    assert DebugExecutor._is_smart_pointer_type("const std::unique_ptr<int> &") is True
    assert DebugExecutor._is_weak_pointer_type("std::weak_ptr<int>") is True
    assert DebugExecutor._is_smart_pointer_type("std::__1::vector<std::__1::shared_ptr<int> >") is False
    assert DebugExecutor._is_shared_pointer_type("std::map<std::string, std::shared_ptr<int> >") is False
    assert DebugExecutor._is_weak_pointer_type("std::array<std::weak_ptr<int>, 2>") is False


def test_debug_executor_detects_std_array_declarations_with_nested_templates():
    """LLDB probes should know std::array<T,N> sizes even when T has commas."""
    from app.core.debug_executor import DebugExecutor

    declarations = DebugExecutor._std_array_declarations([
        "array<shared_ptr<int>,2> xs = {alias, nullptr};",
        "std::array<std::pair<int, int>, 3> pairs{};",
    ])

    assert declarations == {
        "xs": ("shared_ptr<int>", 2),
        "pairs": ("std::pair<int, int>", 3),
    }


def test_debug_executor_parses_lambda_captures_as_function_object():
    """LLDB lambda closure members should become LambdaCapture rows."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int base = 3;\n"
        "int factor = 4;\n"
        "auto f = [base, &factor](int x) { return base + factor + x; };\n"
        "factor = 7;\n"
        "int result = f(6);\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l3 = generated_lines[3]
    l4 = generated_lines[4]
    l5 = generated_lines[5]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l3}:10
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l4}:8
__CXXMV_FRAME__0__{l4}__main
0x000000016fdfe6b0: (int) base = 3
0x000000016fdfe6b4: (int) factor = 4
0x000000016fdfe6b8: ((unnamed class)) f = {{
0x000000016fdfe6b8:   (int) base = 3
0x000000016fdfe6bc:   (int &) factor = 0x000000016fdfe6b4
}}
__CXXMV_BEFORE__1
frame #0: 0x2 program`main at program.cpp:{l4}:8
__CXXMV_AFTER__1
frame #0: 0x3 program`main at program.cpp:{l5}:14
__CXXMV_FRAME__0__{l5}__main
0x000000016fdfe6b0: (int) base = 3
0x000000016fdfe6b4: (int) factor = 7
0x000000016fdfe6b8: ((unnamed class)) f = {{
0x000000016fdfe6b8:   (int) base = 3
0x000000016fdfe6bc:   (int &) factor = 0x000000016fdfe6b4
}}
__CXXMV_BEFORE__2
frame #0: 0x3 program`main at program.cpp:{l5}:14
__CXXMV_AFTER__2
frame #0: 0x4 program`main at program.cpp:{l5 + 1}:1
__CXXMV_FRAME__0__{l5 + 1}__main
0x000000016fdfe6b0: (int) base = 3
0x000000016fdfe6b4: (int) factor = 7
0x000000016fdfe6b8: ((unnamed class)) f = {{
0x000000016fdfe6b8:   (int) base = 3
0x000000016fdfe6bc:   (int &) factor = 0x000000016fdfe6b4
}}
0x000000016fdfe6c0: (int) result = 16
"""

    trace = executor._parse_lldb_output(output, prepared)
    final = trace.steps[-1]
    values = {var.name: var for var in final.stack[0].variables}
    fn = values["f"]

    assert fn.type == "lambda"
    assert fn.value == "<lambda>"
    assert fn.is_function_object is True
    assert fn.is_object is False
    assert [(capture.name, capture.type, capture.value, capture.by_ref) for capture in fn.captures] == [
        ("base", "int", "3", False),
        ("factor", "int&", values["factor"].address, True),
    ]
    assert values["result"].value == "16"


def test_debug_executor_parses_lldb_member_pointer_edges():
    """LLDB object members that are pointers should become member-origin edges."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "struct Node { int value; Node* next; };\n"
        "Node first{1, nullptr};\n"
        "Node second{2, &first};\n"
        "Node* head = &second;\n"
        "head->next->value = 3;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l5 = generated_lines[5]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l5}:5
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l5 + 1}:1
__CXXMV_FRAME__0__{l5 + 1}__main
0x000000016fdfe6b0: (Node) first = {{
0x000000016fdfe6b0:   (int) value = 3
0x000000016fdfe6b8:   (Node *) next = 0x0000000000000000
}}
0x000000016fdfe6c0: (Node) second = {{
0x000000016fdfe6c0:   (int) value = 2
0x000000016fdfe6c8:   (Node *) next = 0x000000016fdfe6b0
}}
0x000000016fdfe6d0: (Node *) head = 0x000000016fdfe6c0
"""

    trace = executor._parse_lldb_output(output, prepared)
    step = trace.steps[0]
    values = {var.name: var for var in step.stack[0].variables}
    first = values["first"]
    second = values["second"]
    head = values["head"]
    next_member = next(member for member in second.members if member.name == "next")

    assert first.members[0].value == "3"
    assert next_member.value == first.address
    assert next_member.address == f"{second.address}.next"
    assert head.value == second.address
    assert {
        (edge.source_address, edge.target_address)
        for edge in step.edges
    } == {
        (head.address, second.address),
        (next_member.address, first.address),
    }
    assert step.heap == []


def test_debug_executor_parses_lldb_std_array_as_array_variable():
    """LLDB std::array implementation storage should unwrap to elements."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <array>\n"
        "using namespace std;\n"
        "array<int,3> a = {1, 2, 3};\n"
        "a[1] = 8;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l4 = generated_lines[4]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l4}:5
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l4 + 1}:1
__CXXMV_FRAME__0__{l4 + 1}__main
0x000000016fdfe6b0: (std::__1::array<int, 3>) a = {{
0x000000016fdfe6b0:   (int[3]) __elems_ = {{[0]=1, [1]=8, [2]=3}}
}}
"""

    trace = executor._parse_lldb_output(output, prepared)
    var = trace.steps[0].stack[0].variables[0]

    assert var.name == "a"
    assert var.is_array is True
    assert var.is_object is False
    assert var.element_count == 3
    assert var.value == "{[0]=1, [1]=8, [2]=3}"
    assert [(element.index, element.value) for element in var.elements] == [(0, "1"), (1, "8"), (2, "3")]
    assert var.members == []


def test_debug_executor_maps_lldb_std_array_object_member_pointer_edges():
    """std::array<Node> elements should map pointer members to simulated targets."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <array>\n"
        "using namespace std;\n"
        "struct Node { int value; Node* next; };\n"
        "Node first{1, nullptr};\n"
        "Node second{2, &first};\n"
        "array<Node,2> nodes = {first, second};\n"
        "nodes[1].next->value = 5;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    line = generated_lines[7]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{line}:5
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{line + 1}:1
__CXXMV_FRAME__0__{line + 1}__main
0x000000016fdfe6a0: (Node) first = {{
0x000000016fdfe6a0:   (int) value = 5
0x000000016fdfe6a8:   (Node *) next = 0x0000000000000000
}}
0x000000016fdfe6b0: (Node) second = {{
0x000000016fdfe6b0:   (int) value = 2
0x000000016fdfe6b8:   (Node *) next = 0x000000016fdfe6a0
}}
0x000000016fdfe6c0: (std::__1::array<Node, 2>) nodes = {{
0x000000016fdfe6c0:   (Node[2]) __elems_ = {{[0]={{value=1, next=0x0000000000000000}}, [1]={{value=2, next=0x000000016fdfe6a0}}}}
}}
"""

    trace = executor._parse_lldb_output(output, prepared)
    step = trace.steps[0]
    values = {var.name: var for var in step.stack[0].variables}
    first = values["first"]
    second = values["second"]
    nodes = values["nodes"]
    second_next = next(member for member in second.members if member.name == "next")

    assert first.members[0].value == "5"
    assert second_next.value == first.address
    assert nodes.is_array is True
    assert nodes.is_object is False
    assert [(element.index, element.type, element.value, element.address) for element in nodes.elements] == [
        (0, "Node", "{value=1, next=nullptr}", f"{nodes.address}[0]"),
        (1, "Node", "{value=2, next=" + first.address + "}", f"{nodes.address}[1]"),
    ]
    assert {
        (edge.source_address, edge.target_address)
        for edge in step.edges
    } == {
        (second_next.address, first.address),
        (nodes.elements[1].address, first.address),
    }
    assert step.heap == []


def test_debug_executor_parses_lldb_container_adapters_as_array_variables():
    """LLDB stack/priority_queue adapter storage should unwrap to elements."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <queue>\n"
        "using namespace std;\n"
        "priority_queue<int> pq;\n"
        "pq.push(1);\n"
        "pq.push(3);\n"
        "pq.push(2);\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l6 = generated_lines[6]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l6}:5
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l6 + 1}:1
__CXXMV_FRAME__0__{l6 + 1}__main
0x000000016fdfe6b0: (std::__1::priority_queue<int, std::__1::vector<int, std::__1::allocator<int> >, std::__1::less<int> >) pq = {{
0x000000016fdfe6b0:   (std::__1::priority_queue<int>::container_type) c = {{[0]=3, [1]=1, [2]=2}}
}}
"""

    trace = executor._parse_lldb_output(output, prepared)
    var = trace.steps[0].stack[0].variables[0]

    assert var.name == "pq"
    assert var.is_array is True
    assert var.is_object is False
    assert var.value == "{[0]=3, [1]=1, [2]=2}"
    assert [(element.index, element.value) for element in var.elements] == [(0, "3"), (1, "1"), (2, "2")]
    assert var.members == []


def test_debug_executor_parses_vector_elements_as_array_variable():
    """std::vector child snapshots should render like indexed array cells."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <vector>\n"
        "using namespace std;\n"
        "int main() {\n"
        "    vector<int> v = {1, 2, 3};\n"
        "    v.push_back(4);\n"
        "    v[1] = 8;\n"
        "}\n"
    )
    output = """
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:4:17
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:5:5
__CXXMV_FRAME__0__5__main
0x000000016fdfe700: (std::__1::vector<int, std::__1::allocator<int> >) v = {
0x000000010065c6a0:   (int) [0] = 1
0x000000010065c6a4:   (int) [1] = 2
0x000000010065c6a8:   (int) [2] = 3
}
__CXXMV_BEFORE__1
frame #0: 0x2 program`main at program.cpp:5:5
__CXXMV_AFTER__1
frame #0: 0x3 program`main at program.cpp:6:5
__CXXMV_FRAME__0__6__main
0x000000016fdfe700: (std::__1::vector<int, std::__1::allocator<int> >) v = {
0x000000010065c6a0:   (int) [0] = 1
0x000000010065c6a4:   (int) [1] = 2
0x000000010065c6a8:   (int) [2] = 3
0x000000010065c6ac:   (int) [3] = 4
}
__CXXMV_BEFORE__2
frame #0: 0x3 program`main at program.cpp:6:5
__CXXMV_AFTER__2
frame #0: 0x4 program`main at program.cpp:7:1
__CXXMV_FRAME__0__7__main
0x000000016fdfe700: (std::__1::vector<int, std::__1::allocator<int> >) v = {
0x000000010065c6a0:   (int) [0] = 1
0x000000010065c6a4:   (int) [1] = 8
0x000000010065c6a8:   (int) [2] = 3
0x000000010065c6ac:   (int) [3] = 4
}
"""

    trace = executor._parse_lldb_output(output, prepared)

    first = trace.steps[0].stack[0].variables[0]
    pushed = trace.steps[1].stack[0].variables[0]
    changed = trace.steps[2].stack[0].variables[0]
    assert first.is_array is True
    assert first.element_count == 3
    assert first.value == "{[0]=1, [1]=2, [2]=3}"
    assert [(element.index, element.value) for element in pushed.elements] == [
        (0, "1"),
        (1, "2"),
        (2, "3"),
        (3, "4"),
    ]
    assert changed.value == "{[0]=1, [1]=8, [2]=3, [3]=4}"


def test_debug_executor_parses_lldb_vector_of_pointers_as_array_not_pointer():
    """A vector<int*> should keep container cells instead of becoming one pointer."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <vector>\n"
        "using namespace std;\n"
        "int a = 1;\n"
        "int b = 2;\n"
        "vector<int*> ptrs = {&a, &b};\n"
        "*ptrs[1] = 9;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    line = generated_lines[6]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{line}:5
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{line + 1}:1
__CXXMV_FRAME__0__{line + 1}__main
0x000000016fdfe6b0: (int) a = 1
0x000000016fdfe6b4: (int) b = 9
0x000000016fdfe6c0: (std::__1::vector<int *, std::__1::allocator<int *> >) ptrs = {{
0x000000010065c6a0:   (int *) [0] = 0x000000016fdfe6b0
0x000000010065c6a8:   (int *) [1] = 0x000000016fdfe6b4
}}
"""

    trace = executor._parse_lldb_output(output, prepared)
    step = trace.steps[0]
    values = {var.name: var for var in step.stack[0].variables}
    ptrs = values["ptrs"]

    assert values["b"].value == "9"
    assert ptrs.is_array is True
    assert ptrs.is_pointer is False
    assert ptrs.is_object is False
    assert [(element.index, element.type, element.value, element.address) for element in ptrs.elements] == [
        (0, "int*", values["a"].address, f"{ptrs.address}[0]"),
        (1, "int*", values["b"].address, f"{ptrs.address}[1]"),
    ]
    assert {
        (edge.source_address, edge.target_address)
        for edge in step.edges
    } == {
        (ptrs.elements[0].address, values["a"].address),
        (ptrs.elements[1].address, values["b"].address),
    }
    assert step.heap == []


def test_debug_executor_parses_lldb_optional_pointer_member_edge():
    """optional<T*> should expose its engaged value as a member pointer edge."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <optional>\n"
        "using namespace std;\n"
        "int a = 1;\n"
        "optional<int*> op = &a;\n"
        "*op.value() = 5;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    line = generated_lines[5]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{line}:5
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{line + 1}:1
__CXXMV_FRAME__0__{line + 1}__main
0x000000016fdfe6b0: (int) a = 5
0x000000016fdfe6c0: (std::__1::optional<int *>) op = {{
0x000000016fdfe6c0:   (std::__1::remove_cv_t<value_type>) Value = 0x000000016fdfe6b0
}}
"""

    trace = executor._parse_lldb_output(output, prepared)
    step = trace.steps[0]
    values = {var.name: var for var in step.stack[0].variables}
    op = values["op"]
    value_member = op.members[0]

    assert values["a"].value == "5"
    assert op.is_object is True
    assert op.class_name == "optional<int*>"
    assert op.value == "{value=" + values["a"].address + "}"
    assert (value_member.name, value_member.type, value_member.value) == ("value", "int*", values["a"].address)
    assert {
        (edge.source_address, edge.target_address)
        for edge in step.edges
    } == {(value_member.address, values["a"].address)}
    assert step.heap == []


def test_debug_executor_parses_lldb_optional_variant_nested_object_member_edges():
    """optional/variant object value members should map nested pointer fields."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <optional>\n"
        "#include <variant>\n"
        "using namespace std;\n"
        "struct Node { int value; Node* next; };\n"
        "Node first{6,nullptr};\n"
        "optional<Node> maybe = Node{2,&first};\n"
        "variant<int, Node> either = Node{3,&first};\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    line = generated_lines[7]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{line}:5
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{line + 1}:1
__CXXMV_FRAME__0__{line + 1}__main
0x000000016fdfe6b0: (Node) first = {{
0x000000016fdfe6b0:   (int) value = 6
0x000000016fdfe6b8:   (Node*) next = 0x0
}}
0x000000016fdfe6c0: (std::__1::optional<Node>) maybe = {{
0x000000016fdfe6c0:   (Node) Value = {{value=2, next=0x000000016fdfe6b0 {{value=6, next=0x0000000000000000}}}}
}}
0x000000016fdfe6d0: (std::__1::variant<int, Node>) either = {{
0x000000016fdfe6d0:   (Node) Value = {{value=3, next=0x000000016fdfe6b0 {{value=6, next=0x0000000000000000}}}}
}}
"""

    trace = executor._parse_lldb_output(output, prepared)
    step = trace.steps[0]
    values = {var.name: var for var in step.stack[0].variables}
    first = values["first"]
    maybe_value = values["maybe"].members[0]
    either_value = values["either"].members[0]

    assert values["maybe"].value == "{value={value=2, next=" + first.address + "}}"
    assert values["either"].value == "{value={value=3, next=" + first.address + "}}"
    assert (maybe_value.name, maybe_value.type, maybe_value.value) == (
        "value",
        "Node",
        "{value=2, next=" + first.address + "}",
    )
    assert (either_value.name, either_value.type, either_value.value) == (
        "value",
        "Node",
        "{value=3, next=" + first.address + "}",
    )
    assert {
        (edge.source_address, edge.target_address)
        for edge in step.edges
    } == {
        (maybe_value.address, first.address),
        (either_value.address, first.address),
    }


def test_debug_executor_formats_lldb_optional_empty_state():
    """Disengaged optional values should show empty instead of raw debugger text."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <optional>\n"
        "using namespace std;\n"
        "optional<int> maybe;\n"
        "maybe = 42;\n"
        "maybe.reset();\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    line = generated_lines[5]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{line}:5
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{line + 1}:1
__CXXMV_FRAME__0__{line + 1}__main
0x000000016fdfe6b0: (std::__1::optional<int>) maybe = Has Value=false
"""

    trace = executor._parse_lldb_output(output, prepared)
    maybe = trace.steps[0].stack[0].variables[0]

    assert maybe.value == "empty"
    assert maybe.is_object is False
    assert maybe.members == []


def test_debug_executor_preserves_template_pointer_in_object_class_name():
    """Class names should keep template pointer arguments for optional/variant."""
    from app.core.debug_executor import DebugExecutor

    assert DebugExecutor._object_class_name("std::__1::optional<int *>") == "optional<int*>"
    assert DebugExecutor._object_class_name("std::__1::variant<int *, double>") == "variant<int*, double>"


def test_debug_executor_parses_vector_string_elements_from_summaries():
    """vector<string> should expand string children instead of showing only size=N."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <vector>\n"
        "#include <string>\n"
        "using namespace std;\n"
        "int main() {\n"
        '    vector<string> names = {"aa", "bb"};\n'
        '    names.push_back("cc");\n'
        "}\n"
    )
    output = """
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:5:28
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:6:5
__CXXMV_FRAME__0__6__main
0x000000016fdfe700: (std::__1::vector<std::__1::string, std::__1::allocator<std::__1::string> >) names = {
0x000000010065c6a0:   (std::__1::string) [0] = "aa"
0x000000010065c6b8:   (std::__1::string) [1] = "bb"
}
__CXXMV_BEFORE__1
frame #0: 0x2 program`main at program.cpp:6:5
__CXXMV_AFTER__1
frame #0: 0x3 program`main at program.cpp:7:1
__CXXMV_FRAME__0__7__main
0x000000016fdfe700: (std::__1::vector<std::__1::string, std::__1::allocator<std::__1::string> >) names = {
0x000000010065c6a0:   (std::__1::string) [0] = "aa"
0x000000010065c6b8:   (std::__1::string) [1] = "bb"
0x000000010065c6d0:   (std::__1::string) [2] = "cc"
}
"""

    trace = executor._parse_lldb_output(output, prepared)

    first = trace.steps[0].stack[0].variables[0]
    changed = trace.steps[1].stack[0].variables[0]
    assert first.is_array is True
    assert first.value == "{[0]=aa, [1]=bb}"
    assert [(element.index, element.value) for element in changed.elements] == [
        (0, "aa"),
        (1, "bb"),
        (2, "cc"),
    ]


def test_debug_executor_parses_map_children_as_key_value_entries():
    """map<string, int> synthetic children should render as indexed key/value rows."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <map>\n"
        "#include <string>\n"
        "using namespace std;\n"
        "int main() {\n"
        "    map<string, int> m;\n"
        '    m["a"] = 1;\n'
        '    m["b"] = 2;\n'
        '    int got = m["a"];\n'
        "}\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l7 = generated_lines[7]
    l8 = generated_lines[8]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l7}:5
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l8}:5
__CXXMV_FRAME__0__{l8}__main
0x000000016fdfe700: (std::__1::map<std::__1::string, int, std::__1::less<std::__1::string>, std::__1::allocator<std::__1::pair<const std::__1::string, int> > >) m = {{
0x000000010065c6a0:   (std::__1::pair<const std::__1::string, int>) [0] = {{first="a", second=1}}
0x000000010065c6d0:   (std::__1::pair<const std::__1::string, int>) [1] = {{first="b", second=2}}
}}
"""

    trace = executor._parse_lldb_output(output, prepared)
    state = trace.steps[0]
    m = state.stack[0].variables[0]

    assert state.line_number == 7
    assert m.name == "m"
    assert m.is_array is True
    assert m.element_count == 2
    assert m.value == '{[0]={first="a", second=1}, [1]={first="b", second=2}}'
    assert [(element.index, element.value) for element in m.elements] == [
        (0, '{first="a", second=1}'),
        (1, '{first="b", second=2}'),
    ]


def test_debug_executor_parses_lldb_map_pointer_values_as_entry_edges():
    """map<string, int*> entries should point from each entry cell to the target."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <map>\n"
        "#include <string>\n"
        "using namespace std;\n"
        "int a = 1;\n"
        "int b = 2;\n"
        "map<string, int*> m;\n"
        'm["a"] = &a;\n'
        'm["b"] = &b;\n'
        '*m["b"] = 9;\n'
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    line = generated_lines[9]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{line}:5
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{line + 1}:1
__CXXMV_FRAME__0__{line + 1}__main
0x000000016fdfe6b0: (int) a = 1
0x000000016fdfe6b4: (int) b = 9
0x000000016fdfe6c0: (std::__1::map<std::__1::string, int*, std::__1::less<std::__1::string>, std::__1::allocator<std::__1::pair<const std::__1::string, int*> > >) m = {{
0x000000010065c6a0:   (std::__1::pair<const std::__1::string, int*>) [0] = {{first="a", second=0x000000016fdfe6b0}}
0x000000010065c6d0:   (std::__1::pair<const std::__1::string, int*>) [1] = {{first="b", second=0x000000016fdfe6b4}}
}}
"""

    trace = executor._parse_lldb_output(output, prepared)
    step = trace.steps[0]
    values = {var.name: var for var in step.stack[0].variables}
    m = values["m"]

    assert values["b"].value == "9"
    assert m.is_array is True
    assert [(element.index, element.value, element.address) for element in m.elements] == [
        (0, "{first=a, second=" + values["a"].address + "}", f"{m.address}[0]"),
        (1, "{first=b, second=" + values["b"].address + "}", f"{m.address}[1]"),
    ]
    assert {
        (edge.source_address, edge.target_address)
        for edge in step.edges
    } == {
        (m.elements[0].address, values["a"].address),
        (m.elements[1].address, values["b"].address),
    }
    assert step.heap == []


def test_debug_executor_parses_lldb_vector_unique_ptr_object_heap_members():
    """vector<unique_ptr<Object>> elements should create object heap blocks with member edges."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <memory>\n"
        "#include <vector>\n"
        "using namespace std;\n"
        "struct Node { int value; Node* next; };\n"
        "Node first{1,nullptr};\n"
        "vector<unique_ptr<Node>> nodes;\n"
        "nodes.push_back(make_unique<Node>(Node{2,&first}));\n"
        "nodes[0]->next->value = 6;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    line = generated_lines[8]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{line}:5
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{line + 1}:1
__CXXMV_FRAME__0__{line + 1}__main
0x000000016fdfe6b0: (Node) first = {{
0x000000016fdfe6b0:   (int) value = 6
0x000000016fdfe6b8:   (Node*) next = 0x0
}}
0x000000016fdfe6c0: (std::__1::vector<std::__1::unique_ptr<Node, std::__1::default_delete<Node> >, std::__1::allocator<std::__1::unique_ptr<Node, std::__1::default_delete<Node> > > >) nodes = {{
0x000000010065c6a0:   (std::__1::unique_ptr<Node, std::__1::default_delete<Node> >) [0] = 0x000000010065d000 {{value=2, next=0x000000016fdfe6b0}}
}}
"""

    trace = executor._parse_lldb_output(output, prepared)
    step = trace.steps[0]
    values = {var.name: var for var in step.stack[0].variables}
    first = values["first"]
    nodes = values["nodes"]
    heap = step.heap[0]

    assert nodes.is_array is True
    assert nodes.elements[0].value == "0xH001"
    assert heap.address == "0xH001"
    assert heap.type == "Node"
    assert heap.is_object is True
    assert heap.class_name == "Node"
    assert [(member.name, member.type, member.value, member.address) for member in heap.members] == [
        ("value", "int", "2", "0xH001.value"),
        ("next", "Node*", first.address, "0xH001.next"),
    ]
    assert {
        (edge.source_address, edge.target_address, edge.is_dangling)
        for edge in step.edges
    } == {
        (nodes.elements[0].address, heap.address, False),
        ("0xH001.next", first.address, False),
    }


def test_debug_executor_parses_lldb_vector_polymorphic_unique_ptr_dynamic_heap_type():
    """vector<unique_ptr<Base>> should infer the derived heap object from debugger members."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "class Animal { public: int age; virtual int speak() { return age; } virtual ~Animal() {} };\n"
        "class Dog : public Animal { public: int bones; int speak() override { return age + bones; } };\n"
        "#include <memory>\n"
        "#include <vector>\n"
        "using namespace std;\n"
        "vector<unique_ptr<Animal>> animals;\n"
        "animals.push_back(make_unique<Dog>());\n"
        "static_cast<Dog*>(animals[0].get())->age = 3;\n"
        "static_cast<Dog*>(animals[0].get())->bones = 4;\n"
        "int sound = animals[0]->speak();\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    line = generated_lines[10]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{line}:13
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{line + 1}:1
__CXXMV_FRAME__0__{line + 1}__main
0x000000016fdfe6c0: (std::__1::vector<std::__1::unique_ptr<Animal, std::__1::default_delete<Animal> >, std::__1::allocator<std::__1::unique_ptr<Animal, std::__1::default_delete<Animal> > > >) animals = {{
0x000000010065c6a0:   (std::__1::unique_ptr<Animal, std::__1::default_delete<Animal> >) [0] = 0x000000010065d000 {{Animal={{age=3}}, bones=4}}
}}
0x000000016fdfe6fc: (int) sound = 7
"""

    trace = executor._parse_lldb_output(output, prepared)
    step = trace.steps[0]
    values = {var.name: var for var in step.stack[0].variables}
    animals = values["animals"]
    heap = step.heap[0]

    assert animals.is_array is True
    assert animals.elements[0].value == heap.address
    assert heap.type == "Dog"
    assert heap.is_object is True
    assert heap.class_name == "Dog"
    assert heap.base_classes == ["Animal"]
    assert heap.virtual_methods == ["speak()"]
    assert [(member.name, member.type, member.value) for member in heap.members] == [
        ("Animal", "Animal", "{age=3}"),
        ("bones", "int", "4"),
    ]
    assert values["sound"].value == "7"
    assert {
        (edge.source_address, edge.target_address, edge.is_dangling)
        for edge in step.edges
    } == {(animals.elements[0].address, heap.address, False)}


def test_debug_executor_preserves_nested_array_child_values():
    """Nested array child values should not be stripped to empty strings."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int grid[2][3] = {{1,2,3},{4,5,6}};\n"
        "grid[1][2] = 9;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l1 = generated_lines[1]
    l2 = generated_lines[2]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l1}:16
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l2}:1
__CXXMV_FRAME__0__{l2}__main
0x000000016fdfe6c0: (int[2][3]) grid = {{
0x000000016fdfe6c0:   (int[3]) [0] = {{[0]=1, [1]=2, [2]=3}}
0x000000016fdfe6cc:   (int[3]) [1] = {{[0]=4, [1]=5, [2]=6}}
}}
__CXXMV_BEFORE__1
frame #0: 0x2 program`main at program.cpp:{l2}:1
__CXXMV_AFTER__1
frame #0: 0x3 program`main at program.cpp:{l2 + 1}:1
__CXXMV_FRAME__0__{l2 + 1}__main
0x000000016fdfe6c0: (int[2][3]) grid = {{
0x000000016fdfe6c0:   (int[3]) [0] = {{[0]=1, [1]=2, [2]=3}}
0x000000016fdfe6cc:   (int[3]) [1] = {{[0]=4, [1]=5, [2]=9}}
}}
"""

    trace = executor._parse_lldb_output(output, prepared)
    first = trace.steps[0].stack[0].variables[0]
    changed = trace.steps[1].stack[0].variables[0]

    assert first.is_array is True
    assert first.value == "{[0]={[0]=1, [1]=2, [2]=3}, [1]={[0]=4, [1]=5, [2]=6}}"
    assert [(element.index, element.value) for element in changed.elements] == [
        (0, "{[0]=1, [1]=2, [2]=3}"),
        (1, "{[0]=4, [1]=5, [2]=9}"),
    ]


def test_debug_executor_preserves_array_of_struct_child_values():
    """Array elements that are objects should keep their member summaries."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "struct Point { int x; int y; };\n"
        "Point pts[2] = {{1,2},{3,4}};\n"
        "pts[1].x = 7;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l2 = generated_lines[2]
    l3 = generated_lines[3]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l2}:14
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l3}:1
__CXXMV_FRAME__0__{l3}__main
0x000000016fdfe6d0: (Point[2]) pts = {{
0x000000016fdfe6d0:   (Point) [0] = {{x=1, y=2}}
0x000000016fdfe6d8:   (Point) [1] = {{x=3, y=4}}
}}
__CXXMV_BEFORE__1
frame #0: 0x2 program`main at program.cpp:{l3}:1
__CXXMV_AFTER__1
frame #0: 0x3 program`main at program.cpp:{l3 + 1}:1
__CXXMV_FRAME__0__{l3 + 1}__main
0x000000016fdfe6d0: (Point[2]) pts = {{
0x000000016fdfe6d0:   (Point) [0] = {{x=1, y=2}}
0x000000016fdfe6d8:   (Point) [1] = {{x=7, y=4}}
}}
"""

    trace = executor._parse_lldb_output(output, prepared)
    first = trace.steps[0].stack[0].variables[0]
    changed = trace.steps[1].stack[0].variables[0]

    assert first.is_array is True
    assert first.value == "{[0]={x=1, y=2}, [1]={x=3, y=4}}"
    assert [(element.index, element.value) for element in changed.elements] == [
        (0, "{x=1, y=2}"),
        (1, "{x=7, y=4}"),
    ]


def test_debug_executor_parses_heap_object_members_from_pointer():
    """A pointer to a heap object should produce an object HeapBlock with members."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "struct Point { int x; double y; };\n"
        "Point* p = new Point{1, 2.5};\n"
        "p->x = 3;\n"
        "delete p;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l2 = generated_lines[2]
    l3 = generated_lines[3]
    l4 = generated_lines[4]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l2}:14
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l3}:5
0x000000016fdfe710: (Point *) p = 0x00000001006446a0 {{
0x00000001006446a0:   (int) x = 1
0x00000001006446a8:   (double) y = 2.5
}}
__CXXMV_BEFORE__1
frame #0: 0x2 program`main at program.cpp:{l3}:5
__CXXMV_AFTER__1
frame #0: 0x3 program`main at program.cpp:{l4}:10
0x000000016fdfe710: (Point *) p = 0x00000001006446a0 {{
0x00000001006446a0:   (int) x = 3
0x00000001006446a8:   (double) y = 2.5
}}
__CXXMV_BEFORE__2
frame #0: 0x3 program`main at program.cpp:{l4}:10
__CXXMV_AFTER__2
frame #0: 0x4 program`main at program.cpp:{l4 + 1}:1
0x000000016fdfe710: (Point *) p = 0x00000001006446a0
"""

    trace = executor._parse_lldb_output(output, prepared)

    first_heap = trace.steps[0].heap[0]
    changed_heap = trace.steps[1].heap[0]
    freed_heap = trace.steps[2].heap[0]
    assert trace.steps[0].stack[0].variables[0].value == "0xH001"
    assert first_heap.is_object is True
    assert first_heap.class_name == "Point"
    assert first_heap.value == "{x=1, y=2.5}"
    assert [(member.name, member.type, member.value) for member in changed_heap.members] == [
        ("x", "int", "3"),
        ("y", "double", "2.5"),
    ]
    assert freed_heap.is_freed is True
    assert freed_heap.value == "{x=3, y=2.5}"
    assert trace.steps[2].edges[0].is_dangling is True


def test_debug_executor_preserves_overwritten_heap_as_leak():
    """Overwriting a heap pointer should keep the old live heap block visible."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int* p = new int(1);\n"
        "p = new int(2);\n"
        "*p = 3;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l1 = generated_lines[1]
    l2 = generated_lines[2]
    l3 = generated_lines[3]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l1}:10
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l2}:3
__CXXMV_FRAME__0__{l2}__main
0x000000016fdfe700: (int *) p = 0x00000001006446a0 {{
0x00000001006446a0:   (int) *p = 1
}}
__CXXMV_BEFORE__1
frame #0: 0x2 program`main at program.cpp:{l2}:3
__CXXMV_AFTER__1
frame #0: 0x3 program`main at program.cpp:{l3}:3
__CXXMV_FRAME__0__{l3}__main
0x000000016fdfe700: (int *) p = 0x0000000100644700 {{
0x0000000100644700:   (int) *p = 2
}}
__CXXMV_BEFORE__2
frame #0: 0x3 program`main at program.cpp:{l3}:3
__CXXMV_AFTER__2
frame #0: 0x4 program`main at program.cpp:{l3 + 1}:3
__CXXMV_FRAME__0__{l3 + 1}__main
0x000000016fdfe700: (int *) p = 0x0000000100644700 {{
0x0000000100644700:   (int) *p = 3
}}
"""

    trace = executor._parse_lldb_output(output, prepared)
    final = trace.steps[-1]
    p = final.stack[0].variables[0]
    heaps = {block.value: block for block in final.heap}
    leaked = heaps["1"]
    current = heaps["3"]

    assert p.value != leaked.address
    assert p.value == current.address
    assert set(heaps) == {"1", "3"}
    assert leaked.is_freed is False
    assert current.is_freed is False
    assert len(final.edges) == 1
    assert final.edges[0].source_address == p.address
    assert final.edges[0].target_address == current.address
    assert final.edges[0].is_dangling is False
    assert all(edge.target_address != leaked.address for edge in final.edges)


def test_debug_executor_parses_unique_ptr_as_heap_pointer():
    """Smart pointer snapshots should render as owner pointers to heap blocks."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <memory>\n"
        "using namespace std;\n"
        "unique_ptr<int> p = make_unique<int>(5);\n"
        "*p = 8;\n"
        "p.reset();\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l3 = generated_lines[3]
    l4 = generated_lines[4]
    l5 = generated_lines[5]
    smart_type = "std::__1::unique_ptr<int, std::__1::default_delete<int> >"
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l3}:21
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l4}:2
__CXXMV_FRAME__0__{l4}__main
0x000000016fdfe700: ({smart_type}) p = 0x00000001006446a0 {{
0x00000001006446a0:   (int) *p = 5
}}
__CXXMV_BEFORE__1
frame #0: 0x2 program`main at program.cpp:{l4}:2
__CXXMV_AFTER__1
frame #0: 0x3 program`main at program.cpp:{l5}:2
__CXXMV_FRAME__0__{l5}__main
0x000000016fdfe700: ({smart_type}) p = 0x00000001006446a0 {{
0x00000001006446a0:   (int) *p = 8
}}
__CXXMV_BEFORE__2
frame #0: 0x3 program`main at program.cpp:{l5}:2
__CXXMV_AFTER__2
frame #0: 0x4 program`main at program.cpp:{l5 + 1}:1
__CXXMV_FRAME__0__{l5 + 1}__main
0x000000016fdfe700: ({smart_type}) p = 0x0
"""

    trace = executor._parse_lldb_output(output, prepared)
    created = trace.steps[0]
    updated = trace.steps[1]
    final = trace.steps[2]
    created_p = created.stack[0].variables[0]
    updated_p = updated.stack[0].variables[0]
    final_p = final.stack[0].variables[0]

    assert created_p.is_pointer is True
    assert created_p.value == "0xH001"
    assert created.heap[0].type == "int"
    assert created.heap[0].value == "5"
    assert updated_p.value == "0xH001"
    assert updated.heap[0].value == "8"
    assert updated.edges[0].source_address == updated_p.address
    assert updated.edges[0].target_address == "0xH001"
    assert final_p.value == "nullptr"
    assert final.heap == []
    assert final.edges == []


def test_debug_executor_marks_expired_lldb_weak_ptr_as_dangling():
    """LLDB weak_ptr should not keep a heap block live after all shared owners reset."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <memory>\n"
        "using namespace std;\n"
        "shared_ptr<int> sp = make_shared<int>(3);\n"
        "weak_ptr<int> wp = sp;\n"
        "sp.reset();\n"
        "bool gone = wp.expired();\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l3 = generated_lines[3]
    l4 = generated_lines[4]
    l5 = generated_lines[5]
    l6 = generated_lines[6]
    shared_type = "std::__1::shared_ptr<int>"
    weak_type = "std::__1::weak_ptr<int>"
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l3}:21
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l4}:1
__CXXMV_FRAME__0__{l4}__main
0x000000016fdfe700: ({shared_type}) sp = 0x00000001006446a0 {{
0x00000001006446a0:   (int) *sp = 3
}}
__CXXMV_BEFORE__1
frame #0: 0x2 program`main at program.cpp:{l4}:1
__CXXMV_AFTER__1
frame #0: 0x3 program`main at program.cpp:{l5}:1
__CXXMV_FRAME__0__{l5}__main
0x000000016fdfe700: ({shared_type}) sp = 0x00000001006446a0 {{
0x00000001006446a0:   (int) *sp = 3
}}
0x000000016fdfe710: ({weak_type}) wp = 0x00000001006446a0 {{
0x00000001006446a0:   (int) *wp = 3
}}
__CXXMV_BEFORE__2
frame #0: 0x3 program`main at program.cpp:{l5}:1
__CXXMV_AFTER__2
frame #0: 0x4 program`main at program.cpp:{l6}:11
__CXXMV_FRAME__0__{l6}__main
0x000000016fdfe700: ({shared_type}) sp = 0x0
0x000000016fdfe710: ({weak_type}) wp = 0x00000001006446a0
__CXXMV_BEFORE__3
frame #0: 0x4 program`main at program.cpp:{l6}:11
__CXXMV_AFTER__3
frame #0: 0x5 program`main at program.cpp:{l6 + 1}:1
__CXXMV_FRAME__0__{l6 + 1}__main
0x000000016fdfe700: ({shared_type}) sp = 0x0
0x000000016fdfe710: ({weak_type}) wp = 0x00000001006446a0
0x000000016fdfe720: (bool) gone = true
"""

    trace = executor._parse_lldb_output(output, prepared)
    final = trace.steps[-1]
    values = {var.name: var for var in final.stack[0].variables}
    heap = final.heap[0]

    assert values["sp"].value == "nullptr"
    assert values["wp"].value == heap.address
    assert values["gone"].value == "true"
    assert heap.value == "3"
    assert heap.is_freed is True
    assert {
        (edge.source_address, edge.target_address, edge.is_dangling)
        for edge in final.edges
    } == {(values["wp"].address, heap.address, True)}


def test_debug_executor_preserves_polymorphic_heap_pointer_address_after_delete():
    """A base pointer to a derived heap object should keep a stable stack address."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "class Animal { public: int age; virtual int speak() { return age; } virtual ~Animal() {} };\n"
        "class Dog : public Animal { public: int bones; int speak() override { return age + bones; } };\n"
        "Animal* a = new Dog();\n"
        "a->age = 3;\n"
        "static_cast<Dog*>(a)->bones = 4;\n"
        "int sound = a->speak();\n"
        "delete a;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l6 = generated_lines[6]
    l7 = generated_lines[7]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l6}:13
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l7}:8
__CXXMV_FRAME__0__{l7}__main
0xf000000000000001: (Dog *) a = 0x0000000100aa0000 {{
0x0000000100aa0000:   (Animal) Animal = {{age=3}}
0x0000000100aa0008:   (int) bones = 4
}}
0x000000016fdfe6fc: (int) sound = 7
__CXXMV_BEFORE__1
frame #0: 0x2 program`main at program.cpp:{l7}:8
__CXXMV_AFTER__1
frame #0: 0x3 program`main at program.cpp:{l7 + 1}:3
__CXXMV_FRAME__0__{l7 + 1}__main
0x000000016fdfe710: (Animal *) a = 0x0000000100aa0000
0x000000016fdfe6fc: (int) sound = 7
"""

    trace = executor._parse_lldb_output(output, prepared)
    first = trace.steps[0]
    final = trace.steps[-1]
    first_a = next(var for var in first.stack[0].variables if var.name == "a")
    final_a = next(var for var in final.stack[0].variables if var.name == "a")
    heap = final.heap[0]

    assert final_a.address == first_a.address
    assert final_a.value == heap.address
    assert heap.is_freed is True
    assert heap.class_name == "Dog"
    assert heap.base_classes == ["Animal"]
    assert heap.virtual_methods == ["speak()"]
    assert [(member.name, member.value) for member in heap.members] == [
        ("Animal", "{age=3}"),
        ("bones", "4"),
    ]
    assert final.edges[0].source_address == final_a.address
    assert final.edges[0].target_address == heap.address
    assert final.edges[0].is_dangling is True


def test_debug_executor_closes_heap_member_pointer_targets():
    """Heap member edges should also materialize their target heap blocks."""
    from app.core.debug_executor import DebugExecutor, _ClassInfo, _ParsedFrame, _ParsedMember, _ParsedVar

    executor = DebugExecutor()
    state = executor._build_state(
        original_line=1,
        source_code="Node* root = new Node{...};",
        parsed_frames=[_ParsedFrame(
            name="main",
            original_line=1,
            variables=[
                _ParsedVar(
                    actual_addr="0x1000",
                    type="Node*",
                    name="root",
                    value="0x2000",
                    pointee_addr="0x2000",
                    pointee_type="Node",
                ),
            ],
        )],
        stack_addr_map={},
        stack_name_addr_map={},
        heap_addr_map={},
        heap_values={},
        heap_array_values={},
        heap_object_values={
            "0x2000": ("Node", [
                _ParsedMember(name="value", type="int", value="1"),
                _ParsedMember(name="left", type="Node*", value="0x3000"),
                _ParsedMember(name="right", type="Node*", value="0x4000"),
            ]),
            "0x3000": ("Node", [
                _ParsedMember(name="value", type="int", value="2"),
                _ParsedMember(name="left", type="Node*", value="0x0"),
                _ParsedMember(name="right", type="Node*", value="0x0"),
            ]),
            "0x4000": ("Node", [
                _ParsedMember(name="value", type="int", value="3"),
                _ParsedMember(name="left", type="Node*", value="0x0"),
                _ParsedMember(name="right", type="Node*", value="0x0"),
            ]),
        },
        allocated_heap=set(),
        freed_heap=set(),
        class_info={"Node": _ClassInfo(member_types={"value": "int", "left": "Node*", "right": "Node*"})},
    )

    heaps = {block.address: block for block in state.heap}
    assert set(heaps) == {"0xH001", "0xH002", "0xH003"}
    assert heaps["0xH001"].value == "{value=1, left=0xH002, right=0xH003}"
    assert heaps["0xH002"].value == "{value=2, left=nullptr, right=nullptr}"
    assert heaps["0xH003"].value == "{value=3, left=nullptr, right=nullptr}"
    assert {
        (edge.source_address, edge.target_address, edge.is_dangling)
        for edge in state.edges
    } == {
        ("0xS001", "0xH001", False),
        ("0xH001.left", "0xH002", False),
        ("0xH001.right", "0xH003", False),
    }


def test_debug_executor_parses_lldb_nested_member_pointer_object_values():
    """LLDB member pointer payloads should materialize child heap objects."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "struct Node { int value; Node* left; Node* right; };\n"
        "Node* root = new Node{1, new Node{2,nullptr,nullptr}, new Node{3,nullptr,nullptr}};\n"
        "delete root;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l2 = generated_lines[2]
    l3 = generated_lines[3]
    l4 = l3 + 1
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l2}:5
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l3}:1
__CXXMV_FRAME__0__{l3}__main
0x000000016fdfe6e0: (Node *) root = 0x00000001005f91b0 {{
0x00000001005f91b0:   (int) value = 1
0x00000001005f91b8:   (Node *) left = 0x00000001005f91d0 {{value=2, left=0x0, right=0x0}}
0x00000001005f91c0:   (Node *) right = 0x00000001005f91f0 {{value=3, left=0x0, right=0x0}}
}}
__CXXMV_BEFORE__1
frame #0: 0x2 program`main at program.cpp:{l3}:1
__CXXMV_AFTER__1
frame #0: 0x3 program`main at program.cpp:{l4}:1
__CXXMV_FRAME__0__{l4}__main
0x000000016fdfe6e0: (Node *) root = 0x00000001005f91b0
"""

    trace = executor._parse_lldb_output(output, prepared)
    step = trace.steps[0]
    heaps = {block.address: block for block in step.heap}

    assert set(heaps) == {"0xH001", "0xH002", "0xH003"}
    assert heaps["0xH001"].value == "{value=1, left=0xH002, right=0xH003}"
    assert heaps["0xH002"].type == "Node"
    assert heaps["0xH002"].value == "{value=2, left=nullptr, right=nullptr}"
    assert heaps["0xH003"].type == "Node"
    assert heaps["0xH003"].value == "{value=3, left=nullptr, right=nullptr}"
    assert trace.steps[1].heap[0].is_freed is True
    assert {
        (edge.source_address, edge.target_address, edge.is_dangling)
        for edge in trace.steps[1].edges
    } == {
        ("0xS001", "0xH001", True),
        ("0xH001.left", "0xH002", False),
        ("0xH001.right", "0xH003", False),
    }


def test_debug_executor_parses_heap_array_expression_snapshots():
    """LLDB expression probes should populate heap arrays and keep delete[] state."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int* p = new int[3]{1, 2, 3};\n"
        "p[1] = 8;\n"
        "delete[] p;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l1 = generated_lines[1]
    l2 = generated_lines[2]
    l3 = generated_lines[3]
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{l1}:12
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:{l2}:3
0x000000016fdfe6c0: (int *) p = 0x000000010065c6a0 {{
0x000000010065c6a0:   (int) *p = 1
}}
__CXXMV_EXPR__0__p__0
(int) $0 = 1
__CXXMV_EXPR__0__p__1
(int) $1 = 2
__CXXMV_EXPR__0__p__2
(int) $2 = 3
__CXXMV_BEFORE__1
frame #0: 0x2 program`main at program.cpp:{l2}:3
__CXXMV_AFTER__1
frame #0: 0x3 program`main at program.cpp:{l3}:12
0x000000016fdfe6c0: (int *) p = 0x000000010065c6a0 {{
0x000000010065c6a0:   (int) *p = 1
}}
__CXXMV_EXPR__1__p__0
(int) $3 = 1
__CXXMV_EXPR__1__p__1
(int) $4 = 8
__CXXMV_EXPR__1__p__2
(int) $5 = 3
__CXXMV_BEFORE__2
frame #0: 0x3 program`main at program.cpp:{l3}:12
__CXXMV_AFTER__2
frame #0: 0x4 program`main at program.cpp:{l3 + 1}:3
0x000000016fdfe6c0: (int *) p = 0x000000010065c6a0 {{
0x000000010065c6a0:   (int) *p = 4472
}}
"""

    trace = executor._parse_lldb_output(output, prepared)

    first_heap = trace.steps[0].heap[0]
    changed_heap = trace.steps[1].heap[0]
    freed_heap = trace.steps[2].heap[0]
    assert first_heap.is_array is True
    assert first_heap.value == "{[0]=1, [1]=2, [2]=3}"
    assert changed_heap.value == "{[0]=1, [1]=8, [2]=3}"
    assert [(e.index, e.value) for e in changed_heap.elements] == [(0, "1"), (1, "8"), (2, "3")]
    assert freed_heap.is_freed is True
    assert freed_heap.value == "{[0]=1, [1]=8, [2]=3}"
    assert trace.steps[2].edges[0].is_dangling is True


def test_debug_executor_selects_lldb_backend_when_tools_exist():
    """Backend detection should choose the implemented LLDB/DWARF path."""
    from app.core.debug_executor import DebugExecutor

    def fake_which(name):
        return {
            "lldb": "/usr/bin/lldb",
            "clang++": "/usr/bin/clang++",
        }.get(name)

    with patch("app.core.debug_executor.shutil.which", side_effect=fake_which):
        assert DebugExecutor.available_backend() == DebugExecutor.LLDB_DWARF_BACKEND
        status = {s.id: s for s in DebugExecutor.backend_status()}

    assert status[DebugExecutor.LLDB_DWARF_BACKEND].available is True
    assert status[DebugExecutor.LLDB_DWARF_BACKEND].implemented is True


def test_debug_executor_msvc_pdb_backend_is_experimental_by_default():
    """PDB support should not be auto-selected until it is explicitly enabled."""
    from app.core.debug_executor import DebugExecutor

    def fake_which(name):
        return {
            "cl": "C:/VS/VC/Tools/MSVC/bin/cl.exe",
            "cdb": "C:/Windows Kits/Debuggers/x64/cdb.exe",
            "vswhere": "C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe",
        }.get(name)

    with patch.dict(os.environ, {"CXXMV_ENABLE_EXPERIMENTAL_PDB": ""}, clear=False):
        with patch("app.core.debug_executor.platform.system", return_value="Windows"):
            with patch("app.core.debug_executor.shutil.which", side_effect=fake_which):
                status = {s.id: s for s in DebugExecutor.backend_status()}
                try:
                    DebugExecutor(preferred_backend=DebugExecutor.MSVC_PDB_BACKEND)._select_backend()
                except Exception as exc:
                    message = str(exc)
                else:
                    raise AssertionError("MSVC/PDB backend should require the experimental flag")

    assert status[DebugExecutor.MSVC_PDB_BACKEND].implemented is True
    assert status[DebugExecutor.MSVC_PDB_BACKEND].available is False
    assert "experimental" in status[DebugExecutor.MSVC_PDB_BACKEND].detail
    assert "CXXMV_ENABLE_EXPERIMENTAL_PDB=1" in message


def test_debug_executor_selects_msvc_pdb_backend_when_enabled_on_windows():
    """Windows with tools and the experiment flag may select the PDB backend."""
    from app.core.debug_executor import DebugExecutor

    def fake_which(name):
        return {
            "cl": "C:/VS/VC/Tools/MSVC/bin/cl.exe",
            "cdb": "C:/Windows Kits/Debuggers/x64/cdb.exe",
            "vswhere": "C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe",
        }.get(name)

    with patch.dict(os.environ, {"CXXMV_ENABLE_EXPERIMENTAL_PDB": "1"}, clear=False):
        with patch("app.core.debug_executor.platform.system", return_value="Windows"):
            with patch("app.core.debug_executor.shutil.which", side_effect=fake_which):
                status = {s.id: s for s in DebugExecutor.backend_status()}
                assert DebugExecutor.available_backend() == DebugExecutor.MSVC_PDB_BACKEND
                selected = DebugExecutor(preferred_backend=DebugExecutor.MSVC_PDB_BACKEND)._select_backend()

    assert selected == DebugExecutor.MSVC_PDB_BACKEND
    assert status[DebugExecutor.MSVC_PDB_BACKEND].implemented is True
    assert status[DebugExecutor.MSVC_PDB_BACKEND].available is True
    assert "PDB" in status[DebugExecutor.MSVC_PDB_BACKEND].detail


def test_debug_executor_selects_msvc_pdb_backend_from_config():
    """config.yaml can enable the experimental PDB backend without an env var."""
    from app.core.debug_executor import DebugExecutor

    def fake_which(name):
        return {
            "cl": "C:/VS/VC/Tools/MSVC/bin/cl.exe",
            "cdb": "C:/Windows Kits/Debuggers/x64/cdb.exe",
            "vswhere": "C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe",
        }.get(name)

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text("debugger:\n  enable_experimental_pdb: true\n", encoding="utf-8")
        with patch.dict(os.environ, {}, clear=True):
            with patch("app.core.debug_executor.platform.system", return_value="Windows"):
                with patch("app.core.debug_executor.shutil.which", side_effect=fake_which):
                    status = {s.id: s for s in DebugExecutor.backend_status(config_path)}
                    selected = DebugExecutor(
                        preferred_backend=DebugExecutor.MSVC_PDB_BACKEND,
                        config_path=config_path,
                    )._select_backend()

    assert selected == DebugExecutor.MSVC_PDB_BACKEND
    assert status[DebugExecutor.MSVC_PDB_BACKEND].available is True


def test_debug_executor_env_can_disable_configured_pdb_backend():
    """An explicit env value can temporarily override config.yaml."""
    from app.core.debug_executor import DebugExecutor

    def fake_which(name):
        return {
            "cl": "C:/VS/VC/Tools/MSVC/bin/cl.exe",
            "cdb": "C:/Windows Kits/Debuggers/x64/cdb.exe",
        }.get(name)

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text("debugger:\n  enable_experimental_pdb: true\n", encoding="utf-8")
        with patch.dict(os.environ, {"CXXMV_ENABLE_EXPERIMENTAL_PDB": "0"}, clear=False):
            with patch("app.core.debug_executor.platform.system", return_value="Windows"):
                with patch("app.core.debug_executor.shutil.which", side_effect=fake_which):
                    status = {s.id: s for s in DebugExecutor.backend_status(config_path)}
                    try:
                        DebugExecutor(
                            preferred_backend=DebugExecutor.MSVC_PDB_BACKEND,
                            config_path=config_path,
                        )._select_backend()
                    except Exception as exc:
                        message = str(exc)
                    else:
                        raise AssertionError("env override should disable MSVC/PDB")

    assert status[DebugExecutor.MSVC_PDB_BACKEND].available is False
    assert "experimental" in message


def test_debug_executor_msvc_pdb_backend_requires_cdb():
    """cl.exe alone is not enough; the command-line debugger is required."""
    from app.core.debug_executor import DebugExecutionError, DebugExecutor

    def fake_which(name):
        return {"cl": "C:/VS/VC/Tools/MSVC/bin/cl.exe"}.get(name)

    with patch("app.core.debug_executor.platform.system", return_value="Windows"):
        with patch("app.core.debug_executor.shutil.which", side_effect=fake_which):
            status = {s.id: s for s in DebugExecutor.backend_status()}
            try:
                DebugExecutor(preferred_backend=DebugExecutor.MSVC_PDB_BACKEND)._select_backend()
            except DebugExecutionError as exc:
                assert "cdb.exe" in str(exc)
            else:
                raise AssertionError("MSVC/PDB backend should require cdb.exe")

    assert status[DebugExecutor.MSVC_PDB_BACKEND].available is False


def test_debug_executor_discovers_msvc_tools_from_vswhere_and_windows_kits():
    """Normal PowerShell can find VS Build Tools and CDB without PATH entries."""
    from types import SimpleNamespace

    from app.core.debug_executor import DebugExecutor

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        vswhere = root / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
        install = root / "VS" / "BuildTools"
        cl = install / "VC" / "Tools" / "MSVC" / "14.40.33807" / "bin" / "Hostx64" / "x64" / "cl.exe"
        vcvarsall = install / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
        cdb = root / "Windows Kits" / "10" / "Debuggers" / "x64" / "cdb.exe"
        for file_path in (vswhere, cl, vcvarsall, cdb):
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("", encoding="utf-8")

        def fake_which(name):
            return None

        def fake_run(cmd, **kwargs):
            assert str(vswhere) == cmd[0]
            assert "-property" in cmd
            return SimpleNamespace(returncode=0, stdout=str(install) + "\n")

        with patch.dict(os.environ, {
            "ProgramFiles(x86)": str(root),
            "ProgramFiles": "",
            "WindowsSdkDir": str(root / "Windows Kits" / "10"),
        }, clear=False):
            with patch("app.core.debug_executor.platform.system", return_value="Windows"):
                with patch("app.core.debug_executor.shutil.which", side_effect=fake_which):
                    with patch("app.core.debug_executor.subprocess.run", side_effect=fake_run):
                        tools = DebugExecutor._msvc_tools()

    assert tools["compiler"] == str(cl)
    assert tools["debugger"] == str(cdb)
    assert tools["vswhere"] == str(vswhere)
    assert tools["vcvarsall"] == str(vcvarsall)


def test_debug_executor_msvc_shell_command_loads_vcvarsall():
    """Auto-discovered cl.exe should run through vcvarsall.bat on Windows."""
    from app.core.debug_executor import DebugExecutor

    cmd = [
        "C:/VS/VC/Tools/MSVC/bin/Hostx64/x64/cl.exe",
        "/nologo",
        "program.cpp",
    ]
    with patch("app.core.debug_executor.platform.system", return_value="Windows"):
        wrapped = DebugExecutor._msvc_shell_command(
            cmd,
            "C:/VS/VC/Auxiliary/Build/vcvarsall.bat",
        )

    assert wrapped[:3] == ["cmd", "/s", "/c"]
    assert 'call "C:/VS/VC/Auxiliary/Build/vcvarsall.bat" x64' in wrapped[3]
    assert "cl.exe" in wrapped[3]


def test_debug_executor_skips_stdin_programs_before_lldb_run():
    """Programs that read stdin should not enter LLDB batch stepping and hang."""
    from app.core.debug_executor import DebugExecutionError, DebugExecutor

    executor = DebugExecutor()
    try:
        executor.run_code(
            "#include <iostream>\n"
            "using namespace std;\n"
            "int main() { int cases; if (!(cin >> cases)) return 0; return cases; }\n"
        )
    except DebugExecutionError as exc:
        assert "stdin" in str(exc)
    else:
        raise AssertionError("stdin program should be skipped by native debugger")


def test_debug_executor_local_capability_rejects_stdin_code():
    """Local availability alone is not enough for stdin-heavy code."""
    from app.core.debug_executor import DebugExecutor

    with patch("app.core.debug_executor.DebugExecutor.is_available", return_value=True):
        assert DebugExecutor.can_run_code_locally("int a = 1;") is True
        assert DebugExecutor.can_run_code_locally("int x; cin >> x;") is False
        assert DebugExecutor.can_run_code_locally("int x; cin >> x;", "7\n") is True


def test_debug_executor_marks_large_simulations_as_ai_preferred():
    """Large control-flow-heavy programs should avoid debugger timeout when AI is configured."""
    from app.core.debug_executor import DebugExecutor

    simple_code = "int main() {\nint a = 1;\nint b = a + 2;\n}\n"
    complex_code = (
        "int main() {\n"
        + "\n".join(
            f"for (int i{i} = 0; i{i} < 10; ++i{i}) {{ if (i{i} % 2) continue; }}"
            for i in range(24)
        )
        + "\n}\n"
    )

    assert DebugExecutor.should_prefer_ai_for_complex_code(simple_code) is False
    assert DebugExecutor.should_prefer_ai_for_complex_code(complex_code) is True


def test_debug_executor_lldb_script_sets_stdin_input_path():
    """When stdin is provided, LLDB should launch the inferior with that input file."""
    from pathlib import Path
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source("int x;\ncin >> x;\n")
    script = executor._lldb_script(prepared, input_path=Path("/tmp/cxxmv_stdin.txt"))

    assert "settings set target.input-path /tmp/cxxmv_stdin.txt" in script
    assert script.index("settings set target.input-path") < script.index("run")


def test_debug_executor_wraps_snippet_includes_outside_main():
    """Header includes in no-main snippets should not be inserted inside main()."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <deque>\n"
        "std::deque<int> q;\n"
        "q.push_back(7);\n"
        "int front = q.front();\n"
    )

    source_lines = prepared.source.splitlines()
    include_line = source_lines.index("#include <deque>") + 1
    main_line = source_lines.index("int main() {") + 1

    assert include_line < main_line
    assert "  #include <deque>" not in prepared.source
    assert prepared.line_map[main_line + 1] == 2
    assert prepared.line_map[main_line + 3] == 4


def test_debug_executor_wraps_helper_function_outside_main_and_steps_in():
    """No-main snippets can define helpers and still step into user calls."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int square(int x) {\n"
        "    int y = x * x;\n"
        "    return y;\n"
        "}\n"
        "int result = square(3);\n"
    )

    source_lines = prepared.source.splitlines()
    function_line = source_lines.index("int square(int x) {") + 1
    main_line = source_lines.index("int main() {") + 1
    call_line = main_line + 1

    assert function_line < main_line
    assert prepared.line_map[function_line + 1] == 2
    assert prepared.line_map[call_line] == 5
    assert call_line in prepared.step_in_lines


def test_debug_executor_wraps_object_construction_inside_main():
    """Constructor calls with value arguments are statements, not function prototypes."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <string>\n"
        "using namespace std;\n"
        "class Student { public: int id; double score; string name; Student(int i, double s, string n): id(i), score(s), name(n) {} };\n"
        'Student s(7, 98.5, "Ada");\n'
        "s.score = 99.0;\n"
    )

    source_lines = prepared.source.splitlines()
    main_line = source_lines.index("int main() {") + 1
    construction_line = source_lines.index('  Student s(7, 98.5, "Ada");') + 1
    mutation_line = source_lines.index("  s.score = 99.0;") + 1

    assert DebugExecutor._looks_like_function_signature("int square(int x)") is True
    assert DebugExecutor._looks_like_function_signature('Student s(7, 98.5, "Ada")') is False
    assert construction_line > main_line
    assert mutation_line > construction_line
    assert prepared.line_map[construction_line] == 4
    assert prepared.line_map[mutation_line] == 5


def test_debug_executor_msvc_compile_args_enable_pdb_symbols():
    """MSVC compile command should emit debug info and a named PDB."""
    from pathlib import Path
    from app.core.debug_executor import DebugExecutor

    args = DebugExecutor._msvc_compile_args(
        "cl.exe",
        Path("program.cpp"),
        Path("program.exe"),
        Path("program.pdb"),
    )

    assert "/Zi" in args
    assert "/Od" in args
    assert "/EHsc" in args
    assert "/Fe:program.exe" in args
    assert "/Fd:program.pdb" in args


def test_debug_executor_cdb_script_uses_source_lines_and_local_vars():
    """CDB script should break at main, line-step, stack-walk, and dump locals."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source("int a = 1;\na++;\n")
    script = executor._cdb_script(prepared)

    assert ".lines" in script
    assert "l+t" in script
    assert "bp main" in script
    assert "kP 8" in script
    assert "dv /t /v" in script
    assert "dx -r3 @$curframe.Locals" in script
    assert "__CXXMV_FRAMEV__0" in script
    assert "__CXXMV_FRAMEDX__0" in script


def test_debug_executor_steps_into_user_function_calls():
    """A main-line user function call should step in instead of running the whole function."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "void RunGame() {\n"
        "    int total = 1;\n"
        "}\n"
        "int main() {\n"
        "    RunGame();\n"
        "    return 0;\n"
        "}\n"
    )
    script = executor._lldb_script(prepared)

    assert 5 in prepared.step_in_lines
    assert "'thread step-in' if line in {5} else 'thread step-over'" in script


def test_debug_executor_steps_over_constructors_but_keeps_method_calls():
    """Constructors/destructors should not produce confusing OO trace steps."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "class Point {\n"
        "public:\n"
        "    int x;\n"
        "    Point(int v) : x(v) {}\n"
        "    ~Point() {}\n"
        "    void inc() { x++; }\n"
        "};\n"
        "int main() {\n"
        "    Point p(1);\n"
        "    p.inc();\n"
        "}\n"
    )

    assert DebugExecutor._user_function_names(prepared.source.splitlines()) == {"inc"}
    assert 9 not in prepared.step_in_lines
    assert 10 in prepared.step_in_lines


def test_debug_executor_uses_current_function_frame_name():
    """Snapshots inside user functions should show that function as the stack frame."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "void RunGame() {\n"
        "    int total = 1;\n"
        "}\n"
        "int main() {\n"
        "    RunGame();\n"
        "}\n"
    )
    output = """
__CXXMV_BEFORE__0
frame #0: 0x1 program`RunGame() at program.cpp:2:9
__CXXMV_AFTER__0
frame #0: 0x2 program`RunGame() at program.cpp:3:1
0x000000016fdfe720: (int) total = 1
"""

    trace = executor._parse_lldb_output(output, prepared)

    assert len(trace.steps) == 1
    assert trace.steps[0].line_number == 2
    assert trace.steps[0].stack[0].frame_name == "RunGame"


def test_debug_executor_skips_step_in_transition_snapshots():
    """Entering a user function should not label callee variables as the caller line."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "void RunGame() {\n"
        "    int total = 1;\n"
        "}\n"
        "int main() {\n"
        "    RunGame();\n"
        "}\n"
    )
    output = """
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:5:5
__CXXMV_AFTER__0
frame #0: 0x2 program`RunGame() at program.cpp:2:9
0x000000016fdfe720: (int) total = 1
__CXXMV_BEFORE__1
frame #0: 0x2 program`RunGame() at program.cpp:2:9
__CXXMV_AFTER__1
frame #0: 0x3 program`RunGame() at program.cpp:3:1
0x000000016fdfe720: (int) total = 1
"""

    trace = executor._parse_lldb_output(output, prepared)

    assert [step.line_number for step in trace.steps] == [2]
    assert trace.steps[0].stack[0].frame_name == "RunGame"


def test_debug_executor_keeps_caller_assignment_after_user_function_returns():
    """The caller statement should appear after a stepped-in function returns."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int square(int x) {\n"
        "    int y = x * x;\n"
        "    return y;\n"
        "}\n"
        "int result = square(3);\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    y_line = generated_lines[2]
    return_line = generated_lines[3]
    call_line = generated_lines[5]
    wrapper_return_line = call_line + 1
    output = f"""
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:{call_line}:16
__CXXMV_AFTER__0
frame #0: 0x2 program`square(int) at program.cpp:{y_line}:13
__CXXMV_FRAME__0__{y_line}__square(int)
0x000000016fdfe6c0: (int) x = 3
__CXXMV_BEFORE__1
frame #0: 0x2 program`square(int) at program.cpp:{y_line}:13
__CXXMV_AFTER__1
frame #0: 0x3 program`square(int) at program.cpp:{return_line}:12
__CXXMV_FRAME__0__{return_line}__square(int)
0x000000016fdfe6c0: (int) x = 3
0x000000016fdfe6c4: (int) y = 9
__CXXMV_FRAME__1__{call_line}__main
0x000000016fdfe6d0: (int) result = -1
__CXXMV_BEFORE__2
frame #0: 0x3 program`square(int) at program.cpp:{return_line}:12
__CXXMV_AFTER__2
frame #0: 0x4 program`main at program.cpp:{call_line}:16
__CXXMV_FRAME__0__{call_line}__main
0x000000016fdfe6d0: (int) result = -1
__CXXMV_BEFORE__3
frame #0: 0x4 program`main at program.cpp:{call_line}:16
__CXXMV_AFTER__3
frame #0: 0x5 program`main at program.cpp:{wrapper_return_line}:3
__CXXMV_FRAME__0__{wrapper_return_line}__main
0x000000016fdfe6d0: (int) result = 9
"""

    trace = executor._parse_lldb_output(output, prepared)

    assert [step.line_number for step in trace.steps] == [2, 5]
    assert trace.steps[0].stack[0].frame_name == "square"
    result = trace.steps[1].stack[0].variables[0]
    assert result.name == "result"
    assert result.value == "9"


def test_debug_executor_parses_multiple_user_stack_frames():
    """LLDB stack snapshots should preserve callee and caller frames."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "void touch(int* p) {\n"
        "    *p = 7;\n"
        "}\n"
        "int main() {\n"
        "    int a = 1;\n"
        "    touch(&a);\n"
        "}\n"
    )
    output = """
__CXXMV_BEFORE__0
frame #0: 0x1 program`touch(int*) at program.cpp:2:5
__CXXMV_AFTER__0
frame #0: 0x2 program`touch(int*) at program.cpp:3:1
__CXXMV_FRAME__0__2__touch(int*)
0x000000016fdfe700: (int *) p = 0x000000016fdfe710 {
0x000000016fdfe710:   (int) *p = 7
}
__CXXMV_FRAME__1__6__main
0x000000016fdfe710: (int) a = 7
"""

    trace = executor._parse_lldb_output(output, prepared)
    step = trace.steps[0]

    assert [frame.frame_name for frame in step.stack] == ["touch", "main"]
    assert step.stack[0].variables[0].name == "p"
    assert step.stack[1].variables[0].name == "a"
    assert step.stack[0].variables[0].value == step.stack[1].variables[0].address
    assert step.edges[0].target_address == step.stack[1].variables[0].address
    assert step.heap == []


def test_debug_executor_parses_cdb_pdb_stack_snapshots():
    """CDB/PDB output should parse into the same trace model as LLDB."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "void touch(int* p) {\n"
        "    *p = 7;\n"
        "}\n"
        "int main() {\n"
        "    int a = 1;\n"
        "    touch(&a);\n"
        "}\n"
    )
    output = r"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!touch+0x2 [C:\tmp\program.cpp @ 2]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!touch+0x9 [C:\tmp\program.cpp @ 3]
01 000000aa`0000f040 program!main+0x21 [C:\tmp\program.cpp @ 6]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int * p = 000000aa`0000efd0
__CXXMV_FRAMEV__1
000000aa`0000efd0 int a = 7
"""

    trace = executor._parse_cdb_output(output, prepared)
    step = trace.steps[0]

    assert step.line_number == 2
    assert [frame.frame_name for frame in step.stack] == ["touch", "main"]
    assert step.stack[0].variables[0].value == step.stack[1].variables[0].address
    assert step.edges[0].target_address == step.stack[1].variables[0].address
    assert step.heap == []


def test_debug_executor_parses_cdb_expired_stack_pointer_as_dangling():
    """CDB/PDB pointers to expired stack locals should not become heap blocks."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int* p = nullptr;\n"
        "{\n"
        "    int local = 5;\n"
        "    p = &local;\n"
        "}\n"
        "int after = 9;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l3 = generated_lines[3]
    l4 = generated_lines[4]
    l6 = generated_lines[6]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x10 [C:\tmp\program.cpp @ {l3}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l4}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int * p = 00000000`00000000
000000aa`0000efc8 int local = 5
__CXXMV_BEFORE__1
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l4}]
__CXXMV_AFTER__1
00 000000aa`0000f000 program!main+0x22 [C:\tmp\program.cpp @ {l6}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int * p = 000000aa`0000efc8
__CXXMV_BEFORE__2
00 000000aa`0000f000 program!main+0x22 [C:\tmp\program.cpp @ {l6}]
__CXXMV_AFTER__2
00 000000aa`0000f000 program!main+0x2a [C:\tmp\program.cpp @ {l6 + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int * p = 000000aa`0000efc8
000000aa`0000efd0 int after = 9
"""

    trace = executor._parse_cdb_output(output, prepared)
    assign_step = trace.steps[1]
    final = trace.steps[-1]
    p = next(var for var in final.stack[0].variables if var.name == "p")
    after = next(var for var in final.stack[0].variables if var.name == "after")

    assert p.value == "0xS002"
    assert after.value == "9"
    assert assign_step.heap == []
    assert final.heap == []
    assert assign_step.edges[0].target_address == "0xS002"
    assert assign_step.edges[0].is_dangling is True
    assert final.edges[0].target_address == "0xS002"
    assert final.edges[0].is_dangling is True


def test_debug_executor_parses_cdb_double_pointer_stack_edges():
    """CDB/PDB should filter future double-pointer locals and keep stack edges."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int a = 1;\n"
        "int *p = &a;\n"
        "int **pp = &p;\n"
        "**pp = 7;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l1 = generated_lines[1]
    l2 = generated_lines[2]
    l3 = generated_lines[3]
    l4 = generated_lines[4]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x10 [C:\tmp\program.cpp @ {l1}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l2}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int a = 1
000000aa`0000efc8 int * p = 000000aa`0000efc0
000000aa`0000efd0 int ** pp = 000000aa`0000efc8
__CXXMV_BEFORE__1
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l2}]
__CXXMV_AFTER__1
00 000000aa`0000f000 program!main+0x22 [C:\tmp\program.cpp @ {l3}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int a = 1
000000aa`0000efc8 int * p = 000000aa`0000efc0
000000aa`0000efd0 int ** pp = 000000aa`0000efc8
__CXXMV_BEFORE__2
00 000000aa`0000f000 program!main+0x22 [C:\tmp\program.cpp @ {l3}]
__CXXMV_AFTER__2
00 000000aa`0000f000 program!main+0x2a [C:\tmp\program.cpp @ {l4}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int a = 1
000000aa`0000efc8 int * p = 000000aa`0000efc0
000000aa`0000efd0 int ** pp = 000000aa`0000efc8
__CXXMV_BEFORE__3
00 000000aa`0000f000 program!main+0x2a [C:\tmp\program.cpp @ {l4}]
__CXXMV_AFTER__3
00 000000aa`0000f000 program!main+0x32 [C:\tmp\program.cpp @ {l4 + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int a = 7
000000aa`0000efc8 int * p = 000000aa`0000efc0
000000aa`0000efd0 int ** pp = 000000aa`0000efc8
"""

    trace = executor._parse_cdb_output(output, prepared)

    assert [var.name for var in trace.steps[0].stack[0].variables] == ["a"]
    assert [var.name for var in trace.steps[1].stack[0].variables] == ["a", "p"]
    assert [var.name for var in trace.steps[2].stack[0].variables] == ["a", "p", "pp"]
    values = {var.name: var for var in trace.steps[-1].stack[0].variables}
    assert values["a"].value == "7"
    assert values["p"].value == values["a"].address
    assert values["pp"].value == values["p"].address
    assert trace.steps[-1].heap == []
    assert {
        (edge.source_address, edge.target_address)
        for edge in trace.steps[-1].edges
    } == {
        (values["p"].address, values["a"].address),
        (values["pp"].address, values["p"].address),
    }


def test_debug_executor_parses_cdb_member_pointer_edges():
    """CDB/PDB object pointer members should become member-origin edges."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "struct Node { int value; Node* next; };\n"
        "Node first{1, nullptr};\n"
        "Node second{2, &first};\n"
        "Node* head = &second;\n"
        "head->next->value = 3;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l5 = generated_lines[5]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x10 [C:\tmp\program.cpp @ {l5}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l5 + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 Node first = {{value=3,next=0x0}}
000000aa`0000efd0 Node second = {{value=2,next=000000aa`0000efc0}}
000000aa`0000efe0 Node * head = 000000aa`0000efd0
__CXXMV_FRAMEDX__0
@$curframe.Locals
    first : {{...}} [Type: Node]
        value : 3 [Type: int]
        next : 0x0 [Type: Node *]
    second : {{...}} [Type: Node]
        value : 2 [Type: int]
        next : 000000aa`0000efc0 [Type: Node *]
"""

    trace = executor._parse_cdb_output(output, prepared)
    step = trace.steps[0]
    values = {var.name: var for var in step.stack[0].variables}
    first = values["first"]
    second = values["second"]
    head = values["head"]
    next_member = next(member for member in second.members if member.name == "next")

    assert first.members[0].value == "3"
    assert next_member.type == "Node*"
    assert next_member.value == first.address
    assert next_member.address == f"{second.address}.next"
    assert head.value == second.address
    assert {
        (edge.source_address, edge.target_address)
        for edge in step.edges
    } == {
        (head.address, second.address),
        (next_member.address, first.address),
    }
    assert step.heap == []


def test_debug_executor_parses_cdb_std_array_as_array_variable():
    """CDB/PDB std::array implementation storage should unwrap to elements."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <array>\n"
        "using namespace std;\n"
        "array<int,3> a = {1, 2, 3};\n"
        "a[1] = 8;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l4 = generated_lines[4]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x10 [C:\tmp\program.cpp @ {l4}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l4 + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 std::array<int,3> a = {{}}
__CXXMV_FRAMEDX__0
@$curframe.Locals
    a : {{...}} [Type: std::array<int,3>]
        _Elems : {{[0]=1, [1]=8, [2]=3}} [Type: int [3]]
"""

    trace = executor._parse_cdb_output(output, prepared)
    var = trace.steps[0].stack[0].variables[0]

    assert var.name == "a"
    assert var.is_array is True
    assert var.is_object is False
    assert var.element_count == 3
    assert var.value == "{[0]=1, [1]=8, [2]=3}"
    assert [(element.index, element.value) for element in var.elements] == [(0, "1"), (1, "8"), (2, "3")]
    assert var.members == []


def test_debug_executor_maps_cdb_std_array_object_member_pointer_edges():
    """CDB/PDB std::array<Node> elements should map pointer members to simulated targets."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <array>\n"
        "using namespace std;\n"
        "struct Node { int value; Node* next; };\n"
        "Node first{1, nullptr};\n"
        "Node second{2, &first};\n"
        "array<Node,2> nodes = {first, second};\n"
        "nodes[1].next->value = 5;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    line = generated_lines[7]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x10 [C:\tmp\program.cpp @ {line}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {line + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efd0 Node first = {{}}
000000aa`0000efe0 Node second = {{}}
000000aa`0000eff0 std::array<Node,2> nodes = {{}}
__CXXMV_FRAMEDX__0
@$curframe.Locals
    first : {{ value=5, next=0x0000000000000000 }} [Type: Node]
        value : 5 [Type: int]
        next : 0x0000000000000000 [Type: Node *]
    second : {{ value=2, next=0x000000aa0000efd0 }} [Type: Node]
        value : 2 [Type: int]
        next : 0x000000aa0000efd0 [Type: Node *]
    nodes : {{...}} [Type: std::array<Node,2>]
        _Elems : {{[0]={{value=1, next=0x0000000000000000}}, [1]={{value=2, next=0x000000aa0000efd0}}}} [Type: Node [2]]
"""

    trace = executor._parse_cdb_output(output, prepared)
    step = trace.steps[0]
    values = {var.name: var for var in step.stack[0].variables}
    first = values["first"]
    second = values["second"]
    nodes = values["nodes"]
    second_next = next(member for member in second.members if member.name == "next")

    assert first.members[0].value == "5"
    assert second_next.value == first.address
    assert nodes.is_array is True
    assert nodes.is_object is False
    assert [(element.index, element.type, element.value, element.address) for element in nodes.elements] == [
        (0, "Node", "{value=1, next=nullptr}", f"{nodes.address}[0]"),
        (1, "Node", "{value=2, next=" + first.address + "}", f"{nodes.address}[1]"),
    ]
    assert {
        (edge.source_address, edge.target_address)
        for edge in step.edges
    } == {
        (second_next.address, first.address),
        (nodes.elements[1].address, first.address),
    }
    assert step.heap == []


def test_debug_executor_parses_cdb_container_adapters_as_array_variables():
    """CDB/PDB stack/priority_queue adapter storage should unwrap to elements."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <stack>\n"
        "using namespace std;\n"
        "stack<int> s;\n"
        "s.push(1);\n"
        "s.push(2);\n"
        "s.pop();\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l6 = generated_lines[6]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x10 [C:\tmp\program.cpp @ {l6}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l6 + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 std::stack<int> s = {{}}
__CXXMV_FRAMEDX__0
@$curframe.Locals
    s : {{...}} [Type: std::stack<int>]
        c : {{[0]=1}} [Type: std::deque<int>]
"""

    trace = executor._parse_cdb_output(output, prepared)
    var = trace.steps[0].stack[0].variables[0]

    assert var.name == "s"
    assert var.is_array is True
    assert var.is_object is False
    assert var.value == "{[0]=1}"
    assert [(element.index, element.value) for element in var.elements] == [(0, "1")]
    assert var.members == []


def test_debug_executor_parses_cdb_vector_of_pointers_as_array_not_pointer():
    """CDB/PDB vector<int*> should keep NatVis elements instead of pointer styling."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <vector>\n"
        "using namespace std;\n"
        "int a = 1;\n"
        "int b = 2;\n"
        "vector<int*> ptrs = {&a, &b};\n"
        "*ptrs[1] = 9;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    line = generated_lines[6]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x10 [C:\tmp\program.cpp @ {line}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {line + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efd0 int a = 1
000000aa`0000efd4 int b = 9
000000aa`0000efe0 std::vector<int *> ptrs = {{}}
__CXXMV_FRAMEDX__0
@$curframe.Locals
    ptrs : {{ size=2 }} [Type: std::vector<int *>]
        [0] : 0x000000aa0000efd0 [Type: int *]
        [1] : 0x000000aa0000efd4 [Type: int *]
"""

    trace = executor._parse_cdb_output(output, prepared)
    step = trace.steps[0]
    values = {var.name: var for var in step.stack[0].variables}
    ptrs = values["ptrs"]

    assert values["b"].value == "9"
    assert ptrs.is_array is True
    assert ptrs.is_pointer is False
    assert ptrs.is_object is False
    assert [(element.index, element.type, element.value, element.address) for element in ptrs.elements] == [
        (0, "int*", values["a"].address, f"{ptrs.address}[0]"),
        (1, "int*", values["b"].address, f"{ptrs.address}[1]"),
    ]
    assert {
        (edge.source_address, edge.target_address)
        for edge in step.edges
    } == {
        (ptrs.elements[0].address, values["a"].address),
        (ptrs.elements[1].address, values["b"].address),
    }
    assert step.heap == []


def test_debug_executor_parses_cdb_optional_pointer_member_edge():
    """CDB/PDB optional<T*> should infer value_type and keep the pointer edge."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <optional>\n"
        "using namespace std;\n"
        "int a = 1;\n"
        "optional<int*> op = &a;\n"
        "*op.value() = 5;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    line = generated_lines[5]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x10 [C:\tmp\program.cpp @ {line}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {line + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efd0 int a = 5
000000aa`0000efe0 std::optional<int *> op = {{}}
__CXXMV_FRAMEDX__0
@$curframe.Locals
    op : {{ Value=0x000000aa0000efd0 }} [Type: std::optional<int *>]
        Value : 0x000000aa0000efd0 [Type: std::remove_cv_t<value_type>]
"""

    trace = executor._parse_cdb_output(output, prepared)
    step = trace.steps[0]
    values = {var.name: var for var in step.stack[0].variables}
    op = values["op"]
    value_member = op.members[0]

    assert values["a"].value == "5"
    assert op.is_object is True
    assert op.class_name == "optional<int*>"
    assert op.value == "{value=" + values["a"].address + "}"
    assert (value_member.name, value_member.type, value_member.value) == ("value", "int*", values["a"].address)
    assert {
        (edge.source_address, edge.target_address)
        for edge in step.edges
    } == {(value_member.address, values["a"].address)}
    assert step.heap == []


def test_debug_executor_parses_cdb_reference_as_non_pointer():
    """CDB/PDB references should keep reference semantics without pointer styling."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int a = 5;\n"
        "int& r = a;\n"
        "r = 9;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    ref_line = generated_lines[2]
    write_line = generated_lines[3]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x11 [C:\tmp\program.cpp @ {ref_line}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x15 [C:\tmp\program.cpp @ {write_line}]
__CXXMV_FRAMEV__0
000000aa`0000efd0 int a = 5
000000aa`0000efd8 int & r = 000000aa`0000efd0
"""

    trace = executor._parse_cdb_output(output, prepared)
    step = trace.steps[0]
    a = step.stack[0].variables[0]
    ref = step.stack[0].variables[1]

    assert ref.is_reference is True
    assert ref.is_pointer is False
    assert ref.value == a.address
    assert step.edges == []


def test_debug_executor_parses_cdb_recursive_stack_frames():
    """CDB/PDB snapshots should preserve repeated recursive frames with stable names."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int fact(int n) {\n"
        "    if (n <= 1) return 1;\n"
        "    int sub = fact(n - 1);\n"
        "    return n * sub;\n"
        "}\n"
        "int result = fact(3);\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    recursive_line = generated_lines[3]
    call_line = generated_lines[6]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!fact+0x11 [C:\tmp\program.cpp @ {recursive_line}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!fact+0x15 [C:\tmp\program.cpp @ {recursive_line}]
01 000000aa`0000f040 program!fact+0x25 [C:\tmp\program.cpp @ {recursive_line}]
02 000000aa`0000f080 program!fact+0x25 [C:\tmp\program.cpp @ {recursive_line}]
03 000000aa`0000f0c0 program!main+0x31 [C:\tmp\program.cpp @ {call_line}]
__CXXMV_FRAMEV__0
000000aa`0000ef90 int n = 1
__CXXMV_FRAMEV__1
000000aa`0000efa0 int n = 2
__CXXMV_FRAMEV__2
000000aa`0000efb0 int n = 3
__CXXMV_FRAMEV__3
000000aa`0000efc0 int result = -1
"""

    trace = executor._parse_cdb_output(output, prepared)
    step = trace.steps[0]

    assert step.line_number == 3
    assert [frame.frame_name for frame in step.stack] == ["fact", "fact(2)", "fact(3)", "main"]
    assert [frame.variables[0].value for frame in step.stack[:3]] == ["1", "2", "3"]


def test_debug_executor_parses_cdb_object_method_call_stack():
    """CDB/PDB method calls should expose this, arguments, and caller object state."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "struct Counter {\n"
        "    int value;\n"
        "    int add(int delta) {\n"
        "        value += delta;\n"
        "        return value;\n"
        "    }\n"
        "};\n"
        "Counter c{2};\n"
        "int result = c.add(5);\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    value_line = generated_lines[4]
    return_line = generated_lines[5]
    call_line = generated_lines[9]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!Counter::add+0x11 [C:\tmp\program.cpp @ {value_line}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!Counter::add+0x15 [C:\tmp\program.cpp @ {return_line}]
01 000000aa`0000f040 program!main+0x31 [C:\tmp\program.cpp @ {call_line}]
__CXXMV_FRAMEV__0
000000aa`0000ef90 Counter * this = 000000aa`0000efd0
000000aa`0000efa0 int delta = 5
__CXXMV_FRAMEV__1
000000aa`0000efd0 Counter c = {{value=7}}
000000aa`0000efe0 int result = -1
"""

    trace = executor._parse_cdb_output(output, prepared)
    step = trace.steps[0]

    assert step.line_number == 4
    assert [frame.frame_name for frame in step.stack] == ["add", "main"]
    this_var = step.stack[0].variables[0]
    delta = step.stack[0].variables[1]
    c = step.stack[1].variables[0]
    assert this_var.name == "this"
    assert this_var.is_pointer is True
    assert this_var.value == c.address
    assert delta.name == "delta"
    assert delta.value == "5"
    assert c.is_object is True
    assert c.members[0].name == "value"
    assert c.members[0].value == "7"
    assert step.edges[0].source_address == this_var.address
    assert step.edges[0].target_address == c.address


def test_debug_executor_cdb_skips_step_in_transition_snapshots():
    """CDB should not label callee variables as the caller source line."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int square(int x) {\n"
        "    int y = x * x;\n"
        "    return y;\n"
        "}\n"
        "int result = square(3);\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    y_line = generated_lines[2]
    call_line = generated_lines[5]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x11 [C:\tmp\program.cpp @ {call_line}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!square+0x2 [C:\tmp\program.cpp @ {y_line}]
01 000000aa`0000f040 program!main+0x21 [C:\tmp\program.cpp @ {call_line}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int x = 3
000000aa`0000efc4 int y = -1
__CXXMV_FRAMEV__1
000000aa`0000efd0 int result = -1
"""

    trace = executor._parse_cdb_output(output, prepared)

    assert trace.steps == []


def test_debug_executor_cdb_keeps_caller_assignment_after_user_function_returns():
    """CDB should keep the caller assignment once a stepped-in function returns."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int square(int x) {\n"
        "    int y = x * x;\n"
        "    return y;\n"
        "}\n"
        "int result = square(3);\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    y_line = generated_lines[2]
    return_line = generated_lines[3]
    call_line = generated_lines[5]
    wrapper_return_line = call_line + 1
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x11 [C:\tmp\program.cpp @ {call_line}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!square+0x2 [C:\tmp\program.cpp @ {y_line}]
01 000000aa`0000f040 program!main+0x21 [C:\tmp\program.cpp @ {call_line}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int x = 3
__CXXMV_FRAMEV__1
000000aa`0000efd0 int result = -1
__CXXMV_BEFORE__1
00 000000aa`0000f000 program!square+0x2 [C:\tmp\program.cpp @ {y_line}]
__CXXMV_AFTER__1
00 000000aa`0000f000 program!square+0x9 [C:\tmp\program.cpp @ {return_line}]
01 000000aa`0000f040 program!main+0x21 [C:\tmp\program.cpp @ {call_line}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int x = 3
000000aa`0000efc4 int y = 9
__CXXMV_FRAMEV__1
000000aa`0000efd0 int result = -1
__CXXMV_BEFORE__2
00 000000aa`0000f000 program!square+0x9 [C:\tmp\program.cpp @ {return_line}]
__CXXMV_AFTER__2
00 000000aa`0000f040 program!main+0x21 [C:\tmp\program.cpp @ {call_line}]
__CXXMV_FRAMEV__0
000000aa`0000efd0 int result = -1
__CXXMV_BEFORE__3
00 000000aa`0000f040 program!main+0x21 [C:\tmp\program.cpp @ {call_line}]
__CXXMV_AFTER__3
00 000000aa`0000f048 program!main+0x28 [C:\tmp\program.cpp @ {wrapper_return_line}]
__CXXMV_FRAMEV__0
000000aa`0000efd0 int result = 9
"""

    trace = executor._parse_cdb_output(output, prepared)

    assert [step.line_number for step in trace.steps] == [2, 5]
    assert trace.steps[0].stack[0].frame_name == "square"
    result = trace.steps[1].stack[0].variables[0]
    assert result.name == "result"
    assert result.value == "9"


def test_debug_executor_parses_cdb_arrays_and_objects():
    """CDB/PDB structured local values should become array/object model fields."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int main() {\n"
        "    int arr[3] = {1, 2, 3};\n"
        "    struct Point { int x; double y; };\n"
        "    Point pt{1, 2.5};\n"
        "    pt.x = 3;\n"
        "}\n"
    )
    output = r"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x11 [C:\tmp\program.cpp @ 5]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x18 [C:\tmp\program.cpp @ 6]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int [3] arr = {1, 2, 3}
000000aa`0000efe0 Point pt = {x=3, y=2.5}
"""

    trace = executor._parse_cdb_output(output, prepared)
    step = trace.steps[0]
    arr = step.stack[0].variables[0]
    pt = step.stack[0].variables[1]

    assert arr.is_array is True
    assert arr.value == "{[0]=1, [1]=2, [2]=3}"
    assert [(element.index, element.value) for element in arr.elements] == [
        (0, "1"),
        (1, "2"),
        (2, "3"),
    ]
    assert pt.is_object is True
    assert pt.value == "{x=3, y=2.5}"
    assert [(member.name, member.value) for member in pt.members] == [
        ("x", "3"),
        ("y", "2.5"),
    ]


def test_debug_executor_parses_cdb_dx_object_string_member_children():
    """CDB/PDB string member children should stay under their parent object."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <string>\n"
        "using namespace std;\n"
        "class Student { public: int id; double score; string name; "
        "Student(int i, double s, string n): id(i), score(s), name(n) {} };\n"
        'Student s(7, 98.5, "Ada");\n'
        "s.score = 99.0;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    line = generated_lines[5]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x20 [C:\tmp\program.cpp @ {line}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x2b [C:\tmp\program.cpp @ {line + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 Student s = {{id=7, score=99, name={{ size=3 }}}}
__CXXMV_FRAMEDX__0
@$curframe.Locals
    s : {{ id=7, score=99, name={{ size=3 }} }} [Type: Student]
        id : 7 [Type: int]
        score : 99 [Type: double]
        name : {{ size=3 }} [Type: std::string]
            [0] : 65 'A' [Type: char]
            [1] : 100 'd' [Type: char]
            [2] : 97 'a' [Type: char]
"""

    trace = executor._parse_cdb_output(output, prepared)
    s = trace.steps[0].stack[0].variables[0]
    members = {member.name: member for member in s.members}

    assert s.is_object is True
    assert s.is_array is False
    assert s.class_name == "Student"
    assert s.value == "{id=7, score=99, name=Ada}"
    assert members["id"].value == "7"
    assert members["score"].value == "99"
    assert members["name"].type == "std::string"
    assert members["name"].value == "Ada"


def test_debug_executor_parses_cdb_dx_string_variables_and_elements():
    """CDB/PDB string char children should collapse for scalars and containers."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <string>\n"
        "#include <vector>\n"
        "using namespace std;\n"
        'string s = "abc";\n'
        "vector<string> words;\n"
        'words.push_back("one");\n'
        'words.push_back("two");\n'
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    line = generated_lines[7]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x20 [C:\tmp\program.cpp @ {line}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x2b [C:\tmp\program.cpp @ {line + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efa0 std::string s = {{ size=3 }}
000000aa`0000efc0 std::vector<std::string> words = size=2
__CXXMV_FRAMEDX__0
@$curframe.Locals
    s : {{ size=3 }} [Type: std::string]
        [0] : 97 'a' [Type: char]
        [1] : 98 'b' [Type: char]
        [2] : 99 'c' [Type: char]
    words : {{ size=2 }} [Type: std::vector<std::string>]
        [0] : {{ size=3 }} [Type: std::string]
            [0] : 111 'o' [Type: char]
            [1] : 110 'n' [Type: char]
            [2] : 101 'e' [Type: char]
        [1] : {{ size=3 }} [Type: std::string]
            [0] : 116 't' [Type: char]
            [1] : 119 'w' [Type: char]
            [2] : 111 'o' [Type: char]
"""

    trace = executor._parse_cdb_output(output, prepared)
    values = {var.name: var for var in trace.steps[0].stack[0].variables}
    s = values["s"]
    words = values["words"]

    assert s.value == "abc"
    assert s.is_object is False
    assert s.is_array is False
    assert s.members == []
    assert words.is_array is True
    assert words.value == "{[0]=one, [1]=two}"
    assert [(element.index, element.type, element.value) for element in words.elements] == [
        (0, "std::string", "one"),
        (1, "std::string", "two"),
    ]


def test_debug_executor_parses_cdb_inherited_virtual_object_metadata():
    """CDB/PDB object snapshots should carry base classes and virtual methods."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "class Animal { public: int age; virtual int speak() { return age; } };\n"
        "class Dog : public Animal { public: int bones; int speak() override { return age + bones; } };\n"
        "Dog d;\n"
        "d.age = 3;\n"
        "d.bones = 4;\n"
        "Animal* a = &d;\n"
        "int sound = a->speak();\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l7 = generated_lines[7]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x30 [C:\tmp\program.cpp @ {l7}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x38 [C:\tmp\program.cpp @ {l7 + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 Dog d = {{Animal={{age=3}}, bones=4}}
000000aa`0000efd0 Dog * a = 000000aa`0000efc0
000000aa`0000efd8 int sound = 7
"""

    trace = executor._parse_cdb_output(output, prepared)
    state = trace.steps[0]
    values = {var.name: var for var in state.stack[0].variables}
    dog = values["d"]
    pointer = values["a"]

    assert dog.is_object is True
    assert dog.class_name == "Dog"
    assert dog.base_classes == ["Animal"]
    assert dog.virtual_methods == ["speak()"]
    assert [(member.name, member.value) for member in dog.members] == [
        ("Animal", "{age=3}"),
        ("bones", "4"),
    ]
    assert pointer.value == dog.address
    assert pointer.address != dog.address
    assert state.edges[0].source_address == pointer.address
    assert state.edges[0].target_address == dog.address
    assert values["sound"].value == "7"


def test_debug_executor_parses_cdb_polymorphic_heap_delete_state():
    """CDB/PDB should preserve derived heap metadata and stable base-pointer address."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "class Animal { public: int age; virtual int speak() { return age; } virtual ~Animal() {} };\n"
        "class Dog : public Animal { public: int bones; int speak() override { return age + bones; } };\n"
        "Animal* a = new Dog();\n"
        "a->age = 3;\n"
        "static_cast<Dog*>(a)->bones = 4;\n"
        "int sound = a->speak();\n"
        "delete a;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l6 = generated_lines[6]
    l7 = generated_lines[7]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x30 [C:\tmp\program.cpp @ {l6}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x38 [C:\tmp\program.cpp @ {l7}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 Dog * a = 000001df`4e700000 {{Animal={{age=3}}, bones=4}}
000000aa`0000efd0 int sound = 7
__CXXMV_BEFORE__1
00 000000aa`0000f000 program!main+0x38 [C:\tmp\program.cpp @ {l7}]
__CXXMV_AFTER__1
00 000000aa`0000f000 program!main+0x40 [C:\tmp\program.cpp @ {l7 + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efe0 Animal * a = 000001df`4e700000
000000aa`0000efd0 int sound = 7
"""

    trace = executor._parse_cdb_output(output, prepared)
    first = trace.steps[0]
    final = trace.steps[-1]
    first_a = next(var for var in first.stack[0].variables if var.name == "a")
    final_a = next(var for var in final.stack[0].variables if var.name == "a")
    heap = final.heap[0]

    assert final_a.address == first_a.address
    assert final_a.value == heap.address
    assert heap.is_freed is True
    assert heap.class_name == "Dog"
    assert heap.base_classes == ["Animal"]
    assert heap.virtual_methods == ["speak()"]
    assert [(member.name, member.value) for member in heap.members] == [
        ("Animal", "{age=3}"),
        ("bones", "4"),
    ]
    assert final.edges[0].source_address == final_a.address
    assert final.edges[0].target_address == heap.address
    assert final.edges[0].is_dangling is True
    assert next(var for var in final.stack[0].variables if var.name == "sound").value == "7"


def test_debug_executor_parses_cdb_overwritten_heap_as_leak():
    """CDB/PDB pointer overwrite should keep the old live heap block visible."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int* p = new int(1);\n"
        "p = new int(2);\n"
        "*p = 3;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l1 = generated_lines[1]
    l2 = generated_lines[2]
    l3 = generated_lines[3]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x10 [C:\tmp\program.cpp @ {l1}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l2}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int * p = 000001df`4e700000 {{1}}
__CXXMV_BEFORE__1
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l2}]
__CXXMV_AFTER__1
00 000000aa`0000f000 program!main+0x22 [C:\tmp\program.cpp @ {l3}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int * p = 000001df`4e800000 {{2}}
__CXXMV_BEFORE__2
00 000000aa`0000f000 program!main+0x22 [C:\tmp\program.cpp @ {l3}]
__CXXMV_AFTER__2
00 000000aa`0000f000 program!main+0x2a [C:\tmp\program.cpp @ {l3 + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int * p = 000001df`4e800000 {{3}}
"""

    trace = executor._parse_cdb_output(output, prepared)
    final = trace.steps[-1]
    p = final.stack[0].variables[0]
    heaps = {block.value: block for block in final.heap}
    leaked = heaps["1"]
    current = heaps["3"]

    assert set(heaps) == {"1", "3"}
    assert p.value == current.address
    assert leaked.is_freed is False
    assert current.is_freed is False
    assert {
        (edge.source_address, edge.target_address, edge.is_dangling)
        for edge in final.edges
    } == {(p.address, current.address, False)}
    assert all(edge.target_address != leaked.address for edge in final.edges)


def test_debug_executor_parses_cdb_unique_ptr_as_heap_pointer():
    """CDB/PDB smart pointer summaries should become heap owner edges."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <memory>\n"
        "using namespace std;\n"
        "std::unique_ptr<int> p(new int(5));\n"
        "*p = 8;\n"
        "p.reset();\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l3 = generated_lines[3]
    l4 = generated_lines[4]
    l5 = generated_lines[5]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x10 [C:\tmp\program.cpp @ {l3}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l4}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 std::unique_ptr<int> p = 000001df`4e700000 {{5}}
__CXXMV_BEFORE__1
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l4}]
__CXXMV_AFTER__1
00 000000aa`0000f000 program!main+0x22 [C:\tmp\program.cpp @ {l5}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 std::unique_ptr<int> p = 000001df`4e700000 {{8}}
__CXXMV_BEFORE__2
00 000000aa`0000f000 program!main+0x22 [C:\tmp\program.cpp @ {l5}]
__CXXMV_AFTER__2
00 000000aa`0000f000 program!main+0x2a [C:\tmp\program.cpp @ {l5 + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 std::unique_ptr<int> p = 00000000`00000000
"""

    trace = executor._parse_cdb_output(output, prepared)
    updated = trace.steps[1]
    final = trace.steps[2]
    p = updated.stack[0].variables[0]

    assert p.is_pointer is True
    assert p.value == "0xH001"
    assert updated.heap[0].type == "int"
    assert updated.heap[0].value == "8"
    assert updated.edges[0].source_address == p.address
    assert updated.edges[0].target_address == "0xH001"
    assert final.stack[0].variables[0].value == "nullptr"
    assert final.heap == []
    assert final.edges == []


def test_debug_executor_marks_expired_cdb_weak_ptr_as_dangling():
    """CDB/PDB weak_ptr should not keep a heap block live after all shared owners reset."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <memory>\n"
        "using namespace std;\n"
        "std::shared_ptr<int> sp = std::make_shared<int>(3);\n"
        "std::weak_ptr<int> wp = sp;\n"
        "sp.reset();\n"
        "bool gone = wp.expired();\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l3 = generated_lines[3]
    l4 = generated_lines[4]
    l5 = generated_lines[5]
    l6 = generated_lines[6]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x10 [C:\tmp\program.cpp @ {l3}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l4}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 std::shared_ptr<int> sp = 000001df`4e700000 {{3}}
__CXXMV_BEFORE__1
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l4}]
__CXXMV_AFTER__1
00 000000aa`0000f000 program!main+0x22 [C:\tmp\program.cpp @ {l5}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 std::shared_ptr<int> sp = 000001df`4e700000 {{3}}
000000aa`0000efd0 std::weak_ptr<int> wp = 000001df`4e700000 {{3}}
__CXXMV_BEFORE__2
00 000000aa`0000f000 program!main+0x22 [C:\tmp\program.cpp @ {l5}]
__CXXMV_AFTER__2
00 000000aa`0000f000 program!main+0x2a [C:\tmp\program.cpp @ {l6}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 std::shared_ptr<int> sp = 00000000`00000000
000000aa`0000efd0 std::weak_ptr<int> wp = 000001df`4e700000 {{3}}
__CXXMV_BEFORE__3
00 000000aa`0000f000 program!main+0x2a [C:\tmp\program.cpp @ {l6}]
__CXXMV_AFTER__3
00 000000aa`0000f000 program!main+0x32 [C:\tmp\program.cpp @ {l6 + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 std::shared_ptr<int> sp = 00000000`00000000
000000aa`0000efd0 std::weak_ptr<int> wp = 000001df`4e700000 {{3}}
000000aa`0000efe0 bool gone = true
"""

    trace = executor._parse_cdb_output(output, prepared)
    final = trace.steps[-1]
    values = {var.name: var for var in final.stack[0].variables}
    heap = final.heap[0]

    assert values["sp"].value == "nullptr"
    assert values["wp"].value == heap.address
    assert values["gone"].value == "true"
    assert heap.value == "3"
    assert heap.is_freed is True
    assert {
        (edge.source_address, edge.target_address, edge.is_dangling)
        for edge in final.edges
    } == {(values["wp"].address, heap.address, True)}


def test_debug_executor_parses_cdb_shared_ptr_owners_to_same_heap():
    """CDB/PDB shared_ptr summaries should keep multiple owner edges to one heap block."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <memory>\n"
        "using namespace std;\n"
        "std::shared_ptr<int> a = std::make_shared<int>(5);\n"
        "std::shared_ptr<int> b = a;\n"
        "*b = 9;\n"
        "a.reset();\n"
        "*b = 11;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l3 = generated_lines[3]
    l4 = generated_lines[4]
    l5 = generated_lines[5]
    l6 = generated_lines[6]
    l7 = generated_lines[7]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x10 [C:\tmp\program.cpp @ {l3}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l4}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 std::shared_ptr<int> a = 000001df`4e700000 {{5}}
__CXXMV_BEFORE__1
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l4}]
__CXXMV_AFTER__1
00 000000aa`0000f000 program!main+0x22 [C:\tmp\program.cpp @ {l5}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 std::shared_ptr<int> a = 000001df`4e700000 {{5}}
000000aa`0000efd0 std::shared_ptr<int> b = 000001df`4e700000 {{5}}
__CXXMV_BEFORE__2
00 000000aa`0000f000 program!main+0x22 [C:\tmp\program.cpp @ {l5}]
__CXXMV_AFTER__2
00 000000aa`0000f000 program!main+0x2a [C:\tmp\program.cpp @ {l6}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 std::shared_ptr<int> a = 000001df`4e700000 {{9}}
000000aa`0000efd0 std::shared_ptr<int> b = 000001df`4e700000 {{9}}
__CXXMV_BEFORE__3
00 000000aa`0000f000 program!main+0x2a [C:\tmp\program.cpp @ {l6}]
__CXXMV_AFTER__3
00 000000aa`0000f000 program!main+0x32 [C:\tmp\program.cpp @ {l7}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 std::shared_ptr<int> a = 00000000`00000000
000000aa`0000efd0 std::shared_ptr<int> b = 000001df`4e700000 {{9}}
__CXXMV_BEFORE__4
00 000000aa`0000f000 program!main+0x32 [C:\tmp\program.cpp @ {l7}]
__CXXMV_AFTER__4
00 000000aa`0000f000 program!main+0x3a [C:\tmp\program.cpp @ {l7 + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 std::shared_ptr<int> a = 00000000`00000000
000000aa`0000efd0 std::shared_ptr<int> b = 000001df`4e700000 {{11}}
"""

    trace = executor._parse_cdb_output(output, prepared)
    shared = trace.steps[1]
    after_reset = trace.steps[3]
    final = trace.steps[-1]
    shared_values = {var.name: var for var in shared.stack[0].variables}
    reset_values = {var.name: var for var in after_reset.stack[0].variables}

    assert shared_values["a"].value == "0xH001"
    assert shared_values["b"].value == "0xH001"
    assert shared.heap[0].value == "5"
    assert {
        (edge.source_address, edge.target_address, edge.is_dangling)
        for edge in shared.edges
    } == {
        (shared_values["a"].address, "0xH001", False),
        (shared_values["b"].address, "0xH001", False),
    }
    assert reset_values["a"].value == "nullptr"
    assert reset_values["b"].value == "0xH001"
    assert {
        (edge.source_address, edge.target_address, edge.is_dangling)
        for edge in after_reset.edges
    } == {(reset_values["b"].address, "0xH001", False)}
    assert final.heap[0].value == "11"


def test_debug_executor_parses_cdb_dx_vector_shared_ptr_as_container_edges():
    """CDB/PDB vector<shared_ptr<T>> should stay a container with element edges."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <memory>\n"
        "#include <vector>\n"
        "using namespace std;\n"
        "shared_ptr<int> alias = make_shared<int>(5);\n"
        "vector<shared_ptr<int>> xs = {alias};\n"
        "*xs[0] = 8;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    line = generated_lines[6]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x20 [C:\tmp\program.cpp @ {line}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x2b [C:\tmp\program.cpp @ {line + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 std::shared_ptr<int> alias = 000001df`4e700000 {{8}}
000000aa`0000efe0 std::vector<std::shared_ptr<int>> xs = size=1
__CXXMV_FRAMEDX__0
@$curframe.Locals
    xs : {{ size=1 }} [Type: std::vector<std::shared_ptr<int>>]
        [0] : 000001df`4e700000 {{8}} [Type: std::shared_ptr<int>]
"""

    trace = executor._parse_cdb_output(output, prepared)
    step = trace.steps[0]
    values = {var.name: var for var in step.stack[0].variables}
    alias = values["alias"]
    xs = values["xs"]

    assert alias.is_pointer is True
    assert alias.value == "0xH001"
    assert xs.is_pointer is False
    assert xs.is_array is True
    assert xs.element_count == 1
    assert xs.elements[0].type == "std::shared_ptr<int>"
    assert xs.elements[0].value == alias.value
    assert step.heap[0].value == "8"
    assert {
        (edge.source_address, edge.target_address, edge.is_dangling)
        for edge in step.edges
    } == {
        (alias.address, alias.value, False),
        (xs.elements[0].address, alias.value, False),
    }


def test_debug_executor_parses_cdb_control_flow_loop_scope():
    """CDB/PDB loop snapshots should follow branch path and drop loop locals after scope exit."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int sum = 0;\n"
        "int parity = 0;\n"
        "for (int i = 1; i <= 4; ++i) {\n"
        "    if (i % 2 == 0) {\n"
        "        parity += i;\n"
        "    }\n"
        "    sum += i;\n"
        "}\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l1 = generated_lines[1]
    l2 = generated_lines[2]
    l3 = generated_lines[3]
    l4 = generated_lines[4]
    l5 = generated_lines[5]
    l7 = generated_lines[7]
    l8 = generated_lines[8]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x10 [C:\tmp\program.cpp @ {l1}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l2}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int sum = 0
__CXXMV_BEFORE__1
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l2}]
__CXXMV_AFTER__1
00 000000aa`0000f000 program!main+0x22 [C:\tmp\program.cpp @ {l3}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int sum = 0
000000aa`0000efc4 int parity = 0
__CXXMV_BEFORE__2
00 000000aa`0000f000 program!main+0x22 [C:\tmp\program.cpp @ {l3}]
__CXXMV_AFTER__2
00 000000aa`0000f000 program!main+0x2a [C:\tmp\program.cpp @ {l4}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int sum = 0
000000aa`0000efc4 int parity = 0
000000aa`0000efc8 int i = 1
__CXXMV_BEFORE__3
00 000000aa`0000f000 program!main+0x2a [C:\tmp\program.cpp @ {l4}]
__CXXMV_AFTER__3
00 000000aa`0000f000 program!main+0x32 [C:\tmp\program.cpp @ {l7}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int sum = 0
000000aa`0000efc4 int parity = 0
000000aa`0000efc8 int i = 1
__CXXMV_BEFORE__4
00 000000aa`0000f000 program!main+0x32 [C:\tmp\program.cpp @ {l7}]
__CXXMV_AFTER__4
00 000000aa`0000f000 program!main+0x3a [C:\tmp\program.cpp @ {l8}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int sum = 1
000000aa`0000efc4 int parity = 0
000000aa`0000efc8 int i = 1
__CXXMV_BEFORE__5
00 000000aa`0000f000 program!main+0x3a [C:\tmp\program.cpp @ {l3}]
__CXXMV_AFTER__5
00 000000aa`0000f000 program!main+0x42 [C:\tmp\program.cpp @ {l4}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int sum = 1
000000aa`0000efc4 int parity = 0
000000aa`0000efc8 int i = 2
__CXXMV_BEFORE__6
00 000000aa`0000f000 program!main+0x42 [C:\tmp\program.cpp @ {l4}]
__CXXMV_AFTER__6
00 000000aa`0000f000 program!main+0x4a [C:\tmp\program.cpp @ {l5}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int sum = 1
000000aa`0000efc4 int parity = 0
000000aa`0000efc8 int i = 2
__CXXMV_BEFORE__7
00 000000aa`0000f000 program!main+0x4a [C:\tmp\program.cpp @ {l5}]
__CXXMV_AFTER__7
00 000000aa`0000f000 program!main+0x52 [C:\tmp\program.cpp @ {l7}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int sum = 1
000000aa`0000efc4 int parity = 2
000000aa`0000efc8 int i = 2
__CXXMV_BEFORE__8
00 000000aa`0000f000 program!main+0x52 [C:\tmp\program.cpp @ {l7}]
__CXXMV_AFTER__8
00 000000aa`0000f000 program!main+0x5a [C:\tmp\program.cpp @ {l8}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int sum = 3
000000aa`0000efc4 int parity = 2
000000aa`0000efc8 int i = 2
__CXXMV_BEFORE__9
00 000000aa`0000f000 program!main+0x5a [C:\tmp\program.cpp @ {l3}]
__CXXMV_AFTER__9
00 000000aa`0000f000 program!main+0x62 [C:\tmp\program.cpp @ {l3 + 6}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int sum = 10
000000aa`0000efc4 int parity = 6
"""

    trace = executor._parse_cdb_output(output, prepared)
    final = trace.steps[-1]
    final_values = {var.name: var.value for var in final.stack[0].variables}
    if_steps = [
        state for state in trace.steps
        if state.source_code.strip().startswith("if ")
    ]

    assert final_values == {"sum": "10", "parity": "6"}
    assert "i" not in final_values
    assert [state.stack[0].variables[-1].value for state in if_steps] == ["1", "2"]


def test_debug_executor_parses_cdb_lambda_captures_as_function_object():
    """CDB/PDB lambda closure children should become LambdaCapture rows."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int base = 3;\n"
        "int factor = 4;\n"
        "auto f = [base, &factor](int x) { return base + factor + x; };\n"
        "factor = 7;\n"
        "int result = f(6);\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l3 = generated_lines[3]
    l4 = generated_lines[4]
    l5 = generated_lines[5]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x10 [C:\tmp\program.cpp @ {l3}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l4}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int base = 3
000000aa`0000efc4 int factor = 4
000000aa`0000efd0 main::<lambda_1> f = {{}}
__CXXMV_FRAMEDX__0
@$curframe.Locals
    f : {{...}} [Type: main::<lambda_1>]
        base : 3 [Type: int]
        factor : 000000aa`0000efc4 [Type: int &]
__CXXMV_BEFORE__1
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l4}]
__CXXMV_AFTER__1
00 000000aa`0000f000 program!main+0x22 [C:\tmp\program.cpp @ {l5}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int base = 3
000000aa`0000efc4 int factor = 7
000000aa`0000efd0 main::<lambda_1> f = {{}}
__CXXMV_FRAMEDX__0
@$curframe.Locals
    f : {{...}} [Type: main::<lambda_1>]
        base : 3 [Type: int]
        factor : 000000aa`0000efc4 [Type: int &]
__CXXMV_BEFORE__2
00 000000aa`0000f000 program!main+0x22 [C:\tmp\program.cpp @ {l5}]
__CXXMV_AFTER__2
00 000000aa`0000f000 program!main+0x2a [C:\tmp\program.cpp @ {l5 + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int base = 3
000000aa`0000efc4 int factor = 7
000000aa`0000efd0 main::<lambda_1> f = {{}}
000000aa`0000efe0 int result = 16
__CXXMV_FRAMEDX__0
@$curframe.Locals
    f : {{...}} [Type: main::<lambda_1>]
        base : 3 [Type: int]
        factor : 000000aa`0000efc4 [Type: int &]
"""

    trace = executor._parse_cdb_output(output, prepared)
    final = trace.steps[-1]
    values = {var.name: var for var in final.stack[0].variables}
    fn = values["f"]

    assert fn.type == "lambda"
    assert fn.value == "<lambda>"
    assert fn.is_function_object is True
    assert fn.is_object is False
    assert [(capture.name, capture.type, capture.value, capture.by_ref) for capture in fn.captures] == [
        ("base", "int", "3", False),
        ("factor", "int&", values["factor"].address, True),
    ]
    assert values["result"].value == "16"


def test_debug_executor_parses_cdb_updated_stack_array():
    """CDB/PDB should keep stack array elements after an indexed assignment."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int nums[3] = {1, 2, 3};\n"
        "nums[1] = 8;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    line = generated_lines[2]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x11 [C:\tmp\program.cpp @ {line}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x18 [C:\tmp\program.cpp @ {line + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int [3] nums = {{1, 8, 3}}
"""

    trace = executor._parse_cdb_output(output, prepared)
    nums = trace.steps[0].stack[0].variables[0]

    assert nums.name == "nums"
    assert nums.is_array is True
    assert nums.is_pointer is False
    assert nums.value == "{[0]=1, [1]=8, [2]=3}"
    assert [(element.index, element.value) for element in nums.elements] == [
        (0, "1"),
        (1, "8"),
        (2, "3"),
    ]


def test_debug_executor_parses_cdb_heap_object_from_pointer_summary():
    """A PDB pointer summary with members should render as a heap object block."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "struct Point { int x; double y; };\n"
        "int main() {\n"
        "    Point* hp = new Point{4, 5.5};\n"
        "    hp->y = 6.5;\n"
        "}\n"
    )
    output = r"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x20 [C:\tmp\program.cpp @ 4]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x2b [C:\tmp\program.cpp @ 5]
__CXXMV_FRAMEV__0
000000aa`0000efc0 Point * hp = 000001df`4e700000 {x=4, y=6.5}
"""

    trace = executor._parse_cdb_output(output, prepared)
    step = trace.steps[0]
    pointer = step.stack[0].variables[0]
    heap = step.heap[0]

    assert pointer.value == "0xH001"
    assert heap.is_object is True
    assert heap.type == "Point"
    assert heap.value == "{x=4, y=6.5}"
    assert [(member.name, member.value) for member in heap.members] == [
        ("x", "4"),
        ("y", "6.5"),
    ]
    assert step.edges[0].target_address == "0xH001"


def test_debug_executor_parses_cdb_heap_array_from_pointer_summary():
    """A PDB pointer summary with elements should render as a heap array block."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int main() {\n"
        "    int* hp = new int[3]{1, 2, 3};\n"
        "    hp[1] = 8;\n"
        "}\n"
    )
    output = r"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x20 [C:\tmp\program.cpp @ 3]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x2b [C:\tmp\program.cpp @ 4]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int * hp = 000001df`4e700000 {1, 8, 3}
"""

    trace = executor._parse_cdb_output(output, prepared)
    step = trace.steps[0]
    pointer = step.stack[0].variables[0]
    heap = step.heap[0]

    assert pointer.value == "0xH001"
    assert heap.is_array is True
    assert heap.type == "int[]"
    assert heap.value == "{[0]=1, [1]=8, [2]=3}"
    assert [(element.index, element.value) for element in heap.elements] == [
        (0, "1"),
        (1, "8"),
        (2, "3"),
    ]
    assert step.edges[0].target_address == "0xH001"


def test_debug_executor_parses_cdb_heap_array_delete_state():
    """CDB/PDB should keep freed heap arrays and dangling edges after delete[]."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int* arr = new int[3]{1, 2, 3};\n"
        "arr[1] = 9;\n"
        "delete[] arr;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l1 = generated_lines[1]
    l2 = generated_lines[2]
    l3 = generated_lines[3]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x10 [C:\tmp\program.cpp @ {l1}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l2}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int * arr = 000001df`4e700000 {{1, 2, 3}}
__CXXMV_BEFORE__1
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l2}]
__CXXMV_AFTER__1
00 000000aa`0000f000 program!main+0x22 [C:\tmp\program.cpp @ {l3}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int * arr = 000001df`4e700000 {{1, 9, 3}}
__CXXMV_BEFORE__2
00 000000aa`0000f000 program!main+0x22 [C:\tmp\program.cpp @ {l3}]
__CXXMV_AFTER__2
00 000000aa`0000f000 program!main+0x2a [C:\tmp\program.cpp @ {l3 + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int * arr = 000001df`4e700000
"""

    trace = executor._parse_cdb_output(output, prepared)
    final = trace.steps[-1]
    arr = final.stack[0].variables[0]
    heap = final.heap[0]

    assert arr.name == "arr"
    assert arr.value == heap.address
    assert heap.is_array is True
    assert heap.is_freed is True
    assert heap.type == "int[]"
    assert [(element.index, element.value) for element in heap.elements] == [
        (0, "1"),
        (1, "9"),
        (2, "3"),
    ]
    assert final.edges[0].is_dangling is True


def test_debug_executor_parses_cdb_pointer_reset_null_state():
    """CDB/PDB should remove dangling edges when a deleted pointer is reset."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int* p = new int(5);\n"
        "delete p;\n"
        "p = nullptr;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    l1 = generated_lines[1]
    l2 = generated_lines[2]
    l3 = generated_lines[3]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x10 [C:\tmp\program.cpp @ {l1}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l2}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int * p = 000001df`4e700000 {{5}}
__CXXMV_BEFORE__1
00 000000aa`0000f000 program!main+0x1a [C:\tmp\program.cpp @ {l2}]
__CXXMV_AFTER__1
00 000000aa`0000f000 program!main+0x22 [C:\tmp\program.cpp @ {l3}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int * p = 000001df`4e700000 {{5}}
__CXXMV_BEFORE__2
00 000000aa`0000f000 program!main+0x22 [C:\tmp\program.cpp @ {l3}]
__CXXMV_AFTER__2
00 000000aa`0000f000 program!main+0x2a [C:\tmp\program.cpp @ {l3 + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int * p = 00000000`00000000
"""

    trace = executor._parse_cdb_output(output, prepared)
    delete_step = trace.steps[1]
    final = trace.steps[-1]
    p = final.stack[0].variables[0]

    assert any(block.is_freed for block in delete_step.heap)
    assert any(edge.is_dangling for edge in delete_step.edges)
    assert p.name == "p"
    assert p.value == "nullptr"
    assert final.heap == []
    assert final.edges == []


def test_debug_executor_parses_cdb_dx_heap_object_children_from_pointer():
    """CDB dx child rows under a pointer should become pointee object members."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "struct Point { int x; double y; };\n"
        "int main() {\n"
        "    Point* hp = new Point{4, 5.5};\n"
        "    hp->y = 6.5;\n"
        "}\n"
    )
    output = r"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x20 [C:\tmp\program.cpp @ 4]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x2b [C:\tmp\program.cpp @ 5]
__CXXMV_FRAMEV__0
000000aa`0000efc0 Point * hp = 000001df`4e700000
__CXXMV_FRAMEDX__0
@$curframe.Locals
    hp : 0x000001df4e700000 [Type: Point *]
        x : 4 [Type: int]
        y : 6.5 [Type: double]
"""

    trace = executor._parse_cdb_output(output, prepared)
    step = trace.steps[0]
    pointer = step.stack[0].variables[0]
    heap = step.heap[0]

    assert pointer.value == "0xH001"
    assert pointer.is_object is False
    assert heap.is_object is True
    assert heap.type == "Point"
    assert heap.value == "{x=4, y=6.5}"
    assert [(member.name, member.value) for member in heap.members] == [
        ("x", "4"),
        ("y", "6.5"),
    ]


def test_debug_executor_parses_cdb_dx_nested_member_pointer_object_values():
    """CDB/PDB dx -r3 should materialize child objects under member pointers."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "struct Node { int value; Node* left; Node* right; };\n"
        "int main() {\n"
        "    Node* root = new Node{1, new Node{2,nullptr,nullptr}, new Node{3,nullptr,nullptr}};\n"
        "    delete root;\n"
        "    int after = 9;\n"
        "}\n"
    )
    output = r"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x10 [C:\tmp\program.cpp @ 3]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x20 [C:\tmp\program.cpp @ 4]
__CXXMV_FRAMEV__0
000000aa`0000efc0 Node * root = 000001df`4e700000
__CXXMV_FRAMEDX__0
@$curframe.Locals
    root : 0x000001df4e700000 [Type: Node *]
        value : 1 [Type: int]
        left : 0x000001df4e700020 [Type: Node *]
            value : 2 [Type: int]
            left : 0x0000000000000000 [Type: Node *]
            right : 0x0000000000000000 [Type: Node *]
        right : 0x000001df4e700040 [Type: Node *]
            value : 3 [Type: int]
            left : 0x0000000000000000 [Type: Node *]
            right : 0x0000000000000000 [Type: Node *]
__CXXMV_BEFORE__1
00 000000aa`0000f000 program!main+0x20 [C:\tmp\program.cpp @ 4]
__CXXMV_AFTER__1
00 000000aa`0000f000 program!main+0x34 [C:\tmp\program.cpp @ 5]
__CXXMV_FRAMEV__0
000000aa`0000efc0 Node * root = 000001df`4e700000
__CXXMV_FRAMEDX__0
@$curframe.Locals
    root : 0x000001df4e700000 [Type: Node *]
        value : 1 [Type: int]
        left : 0x000001df4e700020 [Type: Node *]
            value : 2 [Type: int]
            left : 0x0000000000000000 [Type: Node *]
            right : 0x0000000000000000 [Type: Node *]
        right : 0x000001df4e700040 [Type: Node *]
            value : 3 [Type: int]
            left : 0x0000000000000000 [Type: Node *]
            right : 0x0000000000000000 [Type: Node *]
"""

    trace = executor._parse_cdb_output(output, prepared)
    alloc_step, delete_step = trace.steps
    alloc_heaps = {block.address: block for block in alloc_step.heap}
    delete_heaps = {block.address: block for block in delete_step.heap}

    assert alloc_heaps["0xH001"].value == "{value=1, left=0xH002, right=0xH003}"
    assert alloc_heaps["0xH002"].type == "Node"
    assert alloc_heaps["0xH002"].value == "{value=2, left=nullptr, right=nullptr}"
    assert alloc_heaps["0xH003"].type == "Node"
    assert alloc_heaps["0xH003"].value == "{value=3, left=nullptr, right=nullptr}"
    assert delete_heaps["0xH001"].is_freed is True
    assert delete_heaps["0xH002"].is_freed is False
    assert delete_heaps["0xH003"].is_freed is False
    assert {
        (edge.source_address, edge.target_address, edge.is_dangling)
        for edge in delete_step.edges
    } == {
        ("0xS001", "0xH001", True),
        ("0xH001.left", "0xH002", False),
        ("0xH001.right", "0xH003", False),
    }


def test_debug_executor_parses_cdb_dx_heap_array_children_from_pointer():
    """CDB dx indexed child rows under a pointer should become a heap array."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int main() {\n"
        "    int* hp = new int[3]{1, 2, 3};\n"
        "    hp[1] = 8;\n"
        "}\n"
    )
    output = r"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x20 [C:\tmp\program.cpp @ 3]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x2b [C:\tmp\program.cpp @ 4]
__CXXMV_FRAMEV__0
000000aa`0000efc0 int * hp = 000001df`4e700000
__CXXMV_FRAMEDX__0
@$curframe.Locals
    hp : 0x000001df4e700000 [Type: int *]
        [0] : 1 [Type: int]
        [1] : 8 [Type: int]
        [2] : 3 [Type: int]
"""

    trace = executor._parse_cdb_output(output, prepared)
    step = trace.steps[0]
    heap = step.heap[0]

    assert heap.is_array is True
    assert heap.type == "int[]"
    assert heap.value == "{[0]=1, [1]=8, [2]=3}"
    assert [(element.index, element.value) for element in heap.elements] == [
        (0, "1"),
        (1, "8"),
        (2, "3"),
    ]


def test_debug_executor_parses_cdb_dx_vector_object_children():
    """CDB dx/NatVis vector object elements should keep nested member values."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <vector>\n"
        "using namespace std;\n"
        "struct Node { int id; double weight; };\n"
        "vector<Node> nodes = {{1, 1.5}, {2, 2.5}};\n"
        "nodes[1].weight = 4.5;\n"
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    line = generated_lines[5]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x20 [C:\tmp\program.cpp @ {line}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x2b [C:\tmp\program.cpp @ {line + 1}]
__CXXMV_FRAMEV__0
__CXXMV_FRAMEDX__0
@$curframe.Locals
    nodes : {{ size=2 }} [Type: std::vector<Node>]
        [0] : {{id=1, weight=1.5}} [Type: Node]
            id : 1 [Type: int]
            weight : 1.5 [Type: double]
        [1] : {{id=2, weight=4.5}} [Type: Node]
            id : 2 [Type: int]
            weight : 4.5 [Type: double]
"""

    trace = executor._parse_cdb_output(output, prepared)
    nodes = trace.steps[0].stack[0].variables[0]

    assert nodes.name == "nodes"
    assert nodes.is_array is True
    assert nodes.element_count == 2
    assert [(element.index, element.value) for element in nodes.elements] == [
        (0, "{id=1, weight=1.5}"),
        (1, "{id=2, weight=4.5}"),
    ]
    assert nodes.value == "{[0]={id=1, weight=1.5}, [1]={id=2, weight=4.5}}"


def test_debug_executor_parses_cdb_dx_map_children_as_key_value_entries():
    """CDB dx/NatVis container children should merge into the dv local variable."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <map>\n"
        "#include <string>\n"
        "using namespace std;\n"
        "int main() {\n"
        "    map<string, int> m;\n"
        '    m["a"] = 1;\n'
        '    m["b"] = 2;\n'
        '    int got = m["a"];\n'
        "}\n"
    )
    output = r"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x20 [C:\tmp\program.cpp @ 7]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x2b [C:\tmp\program.cpp @ 8]
__CXXMV_FRAMEV__0
000000aa`0000efc0 std::map<std::string,int> m = size=2
__CXXMV_FRAMEDX__0
@$curframe.Locals
    m : { size=2 } [Type: std::map<std::string,int>]
        [0] : {first="a", second=1} [Type: std::pair<const std::string,int>]
        [1] : {first="b", second=2} [Type: std::pair<const std::string,int>]
"""

    trace = executor._parse_cdb_output(output, prepared)
    step = trace.steps[0]
    m = step.stack[0].variables[0]

    assert step.line_number == 7
    assert m.name == "m"
    assert m.is_array is True
    assert m.element_count == 2
    assert m.value == '{[0]={first="a", second=1}, [1]={first="b", second=2}}'
    assert [(element.index, element.value) for element in m.elements] == [
        (0, '{first="a", second=1}'),
        (1, '{first="b", second=2}'),
    ]


def test_debug_executor_parses_cdb_dx_map_pointer_values_as_entry_edges():
    """CDB/PDB map<string, int*> entries should point from entry cells to targets."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <map>\n"
        "#include <string>\n"
        "using namespace std;\n"
        "int a = 1;\n"
        "int b = 2;\n"
        "map<string, int*> m;\n"
        'm["a"] = &a;\n'
        'm["b"] = &b;\n'
        '*m["b"] = 9;\n'
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    line = generated_lines[9]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x20 [C:\tmp\program.cpp @ {line}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x2b [C:\tmp\program.cpp @ {line + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efd0 int a = 1
000000aa`0000efd4 int b = 9
000000aa`0000efe0 std::map<std::string,int *> m = size=2
__CXXMV_FRAMEDX__0
@$curframe.Locals
    m : {{ size=2 }} [Type: std::map<std::string,int *>]
        [0] : {{first="a", second=0x000000aa0000efd0}} [Type: std::pair<const std::string,int *>]
            first : "a" [Type: std::string]
            second : 0x000000aa0000efd0 [Type: int *]
        [1] : {{first="b", second=0x000000aa0000efd4}} [Type: std::pair<const std::string,int *>]
            first : "b" [Type: std::string]
            second : 0x000000aa0000efd4 [Type: int *]
"""

    trace = executor._parse_cdb_output(output, prepared)
    step = trace.steps[0]
    values = {var.name: var for var in step.stack[0].variables}
    m = values["m"]

    assert values["b"].value == "9"
    assert m.is_array is True
    assert [(element.index, element.value, element.address) for element in m.elements] == [
        (0, "{first=a, second=" + values["a"].address + "}", f"{m.address}[0]"),
        (1, "{first=b, second=" + values["b"].address + "}", f"{m.address}[1]"),
    ]
    assert {
        (edge.source_address, edge.target_address)
        for edge in step.edges
    } == {
        (m.elements[0].address, values["a"].address),
        (m.elements[1].address, values["b"].address),
    }
    assert step.heap == []


def test_debug_executor_parses_cdb_dx_map_unique_ptr_values_as_heap_entries():
    """CDB/PDB map<string, unique_ptr<T>> entries should create valued heap blocks."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <map>\n"
        "#include <memory>\n"
        "#include <string>\n"
        "using namespace std;\n"
        "map<string, unique_ptr<int>> m;\n"
        'm["a"] = unique_ptr<int>(new int(5));\n'
        '*m["a"] = 8;\n'
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    line = generated_lines[7]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x20 [C:\tmp\program.cpp @ {line}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x2b [C:\tmp\program.cpp @ {line + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efe0 std::map<std::string,std::unique_ptr<int>> m = size=1
__CXXMV_FRAMEDX__0
@$curframe.Locals
    m : {{ size=1 }} [Type: std::map<std::string,std::unique_ptr<int>>]
        [0] : {{first="a", second=000001df`4e700000 {{8}}}} [Type: std::pair<const std::string,std::unique_ptr<int>>]
            first : "a" [Type: std::string]
            second : 000001df`4e700000 {{8}} [Type: std::unique_ptr<int>]
"""

    trace = executor._parse_cdb_output(output, prepared)
    step = trace.steps[0]
    m = step.stack[0].variables[0]

    assert m.is_array is True
    assert m.elements[0].value == "{first=a, second=0xH001}"
    assert step.heap[0].type == "int"
    assert step.heap[0].value == "8"
    assert {
        (edge.source_address, edge.target_address, edge.is_dangling)
        for edge in step.edges
    } == {(m.elements[0].address, "0xH001", False)}


def test_debug_executor_parses_cdb_dx_map_unique_ptr_object_heap_members():
    """CDB/PDB map<string, unique_ptr<Object>> entries should create object heap blocks."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <map>\n"
        "#include <memory>\n"
        "#include <string>\n"
        "using namespace std;\n"
        "struct Node { int value; Node* next; };\n"
        "Node first{1,nullptr};\n"
        "map<string, unique_ptr<Node>> m;\n"
        'm["n"] = make_unique<Node>(Node{2,&first});\n'
        'm["n"]->next->value = 6;\n'
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    line = generated_lines[9]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x20 [C:\tmp\program.cpp @ {line}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x2b [C:\tmp\program.cpp @ {line + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efd0 Node first = {{value=6, next=0x0000000000000000}}
000000aa`0000efe0 std::map<std::string,std::unique_ptr<Node>> m = size=1
__CXXMV_FRAMEDX__0
@$curframe.Locals
    first : {{value=6, next=0x0000000000000000}} [Type: Node]
        value : 6 [Type: int]
        next : 0x0000000000000000 [Type: Node *]
    m : {{ size=1 }} [Type: std::map<std::string,std::unique_ptr<Node>>]
        [0] : {{first="n", second=000001df`4e700000 {{value=2, next=000000aa`0000efd0}}}} [Type: std::pair<const std::string,std::unique_ptr<Node>>]
            first : "n" [Type: std::string]
            second : 000001df`4e700000 {{value=2, next=000000aa`0000efd0}} [Type: std::unique_ptr<Node>]
"""

    trace = executor._parse_cdb_output(output, prepared)
    step = trace.steps[0]
    values = {var.name: var for var in step.stack[0].variables}
    first = values["first"]
    m = values["m"]
    heap = step.heap[0]

    assert first.value == "{value=6, next=nullptr}"
    assert m.is_array is True
    assert m.elements[0].value == "{first=n, second=0xH001}"
    assert heap.address == "0xH001"
    assert heap.type == "Node"
    assert heap.is_object is True
    assert heap.class_name == "Node"
    assert [(member.name, member.type, member.value, member.address) for member in heap.members] == [
        ("value", "int", "2", "0xH001.value"),
        ("next", "Node*", first.address, "0xH001.next"),
    ]
    assert {
        (edge.source_address, edge.target_address, edge.is_dangling)
        for edge in step.edges
    } == {
        (m.elements[0].address, heap.address, False),
        ("0xH001.next", first.address, False),
    }


def test_debug_executor_parses_cdb_dx_map_polymorphic_shared_ptr_dynamic_heap_type():
    """CDB/PDB map<string, shared_ptr<Base>> should infer derived heap metadata."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <map>\n"
        "#include <memory>\n"
        "#include <string>\n"
        "using namespace std;\n"
        "class Animal { public: int age; virtual int speak() { return age; } virtual ~Animal() {} };\n"
        "class Dog : public Animal { public: int bones; int speak() override { return age + bones; } };\n"
        "map<string, shared_ptr<Animal>> animals;\n"
        'animals["dog"] = make_shared<Dog>();\n'
        'static_cast<Dog*>(animals["dog"].get())->age = 3;\n'
        'static_cast<Dog*>(animals["dog"].get())->bones = 4;\n'
        'int sound = animals["dog"]->speak();\n'
    )
    generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
    line = generated_lines[11]
    output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x20 [C:\tmp\program.cpp @ {line}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x2b [C:\tmp\program.cpp @ {line + 1}]
__CXXMV_FRAMEV__0
000000aa`0000efe0 std::map<std::string,std::shared_ptr<Animal>> animals = size=1
000000aa`0000efd0 int sound = 7
__CXXMV_FRAMEDX__0
@$curframe.Locals
    animals : {{ size=1 }} [Type: std::map<std::string,std::shared_ptr<Animal>>]
        [0] : {{first="dog", second=000001df`4e700000 {{Animal={{age=3}}, bones=4}}}} [Type: std::pair<const std::string,std::shared_ptr<Animal>>]
            first : "dog" [Type: std::string]
            second : 000001df`4e700000 {{Animal={{age=3}}, bones=4}} [Type: std::shared_ptr<Animal>]
    sound : 7 [Type: int]
"""

    trace = executor._parse_cdb_output(output, prepared)
    step = trace.steps[0]
    values = {var.name: var for var in step.stack[0].variables}
    animals = values["animals"]
    heap = step.heap[0]

    assert animals.is_array is True
    assert animals.elements[0].value == "{first=dog, second=0xH001}"
    assert heap.type == "Dog"
    assert heap.is_object is True
    assert heap.class_name == "Dog"
    assert heap.base_classes == ["Animal"]
    assert heap.virtual_methods == ["speak()"]
    assert [(member.name, member.type, member.value) for member in heap.members] == [
        ("Animal", "Animal", "{age=3}"),
        ("bones", "int", "4"),
    ]
    assert values["sound"].value == "7"
    assert {
        (edge.source_address, edge.target_address, edge.is_dangling)
        for edge in step.edges
    } == {(animals.elements[0].address, heap.address, False)}


def test_debug_executor_parses_cdb_dx_nested_map_pair_children():
    """Nested CDB dx pair rows should be folded into map array element values."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "#include <map>\n"
        "#include <string>\n"
        "using namespace std;\n"
        "int main() {\n"
        "    map<string, int> m;\n"
        '    m["a"] = 1;\n'
        '    m["b"] = 2;\n'
        '    int got = m["a"];\n'
        "}\n"
    )
    output = r"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x20 [C:\tmp\program.cpp @ 7]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x2b [C:\tmp\program.cpp @ 8]
__CXXMV_FRAMEV__0
000000aa`0000efc0 std::map<std::string,int> m = size=2
__CXXMV_FRAMEDX__0
@$curframe.Locals
    m : { size=2 } [Type: std::map<std::string,int>]
        [0] :  [Type: std::pair<const std::string,int>]
            first : "a" [Type: std::string]
            second : 1 [Type: int]
        [1] :  [Type: std::pair<const std::string,int>]
            first : "b" [Type: std::string]
            second : 2 [Type: int]
"""

    trace = executor._parse_cdb_output(output, prepared)
    m = trace.steps[0].stack[0].variables[0]

    assert m.is_array is True
    assert m.element_count == 2
    assert m.value == "{[0]={first=a, second=1}, [1]={first=b, second=2}}"
    assert [(element.index, element.value) for element in m.elements] == [
        (0, "{first=a, second=1}"),
        (1, "{first=b, second=2}"),
    ]


def test_debug_executor_parses_cdb_dx_stl_container_breadth():
    """CDB/PDB dx output should cover common STL sequence/set/hash containers."""
    from app.core.debug_executor import DebugExecutor

    def parse_step(code: str, original_line: int, framev: str, dx_rows: str):
        executor = DebugExecutor()
        prepared = executor._prepare_source(code)
        generated_lines = {orig: generated for generated, orig in prepared.line_map.items()}
        line = generated_lines[original_line]
        output = rf"""
__CXXMV_BEFORE__0
00 000000aa`0000f000 program!main+0x20 [C:\tmp\program.cpp @ {line}]
__CXXMV_AFTER__0
00 000000aa`0000f000 program!main+0x2b [C:\tmp\program.cpp @ {line + 1}]
__CXXMV_FRAMEV__0
{framev}
__CXXMV_FRAMEDX__0
@$curframe.Locals
{dx_rows}
"""
        return executor._parse_cdb_output(output, prepared).steps[0]

    deque_step = parse_step(
        "#include <deque>\n"
        "using namespace std;\n"
        "deque<int> xs;\n"
        "xs.push_back(1);\n"
        "xs.push_back(2);\n"
        "xs.push_front(0);\n"
        "xs[2] = 8;\n",
        7,
        "000000aa`0000efe0 std::deque<int> xs = size=3",
        "    xs : { size=3 } [Type: std::deque<int>]\n"
        "        [0] : 0 [Type: int]\n"
        "        [1] : 1 [Type: int]\n"
        "        [2] : 8 [Type: int]",
    )
    deque = deque_step.stack[0].variables[0]
    assert deque.name == "xs"
    assert deque.is_array is True
    assert deque.value == "{[0]=0, [1]=1, [2]=8}"
    assert [(element.index, element.type, element.value) for element in deque.elements] == [
        (0, "int", "0"),
        (1, "int", "1"),
        (2, "int", "8"),
    ]

    list_step = parse_step(
        "#include <list>\n"
        "using namespace std;\n"
        "int a = 1;\n"
        "int b = 2;\n"
        "list<int*> xs;\n"
        "xs.push_back(&a);\n"
        "xs.push_back(&b);\n"
        "auto it = xs.begin();\n"
        "++it;\n"
        "**it = 9;\n",
        10,
        "000000aa`0000efd0 int a = 1\n"
        "000000aa`0000efd4 int b = 9\n"
        "000000aa`0000efe0 std::list<int *> xs = size=2",
        "    xs : { size=2 } [Type: std::list<int *>]\n"
        "        [0] : 0x000000aa0000efd0 [Type: int *]\n"
        "        [1] : 0x000000aa0000efd4 [Type: int *]",
    )
    list_values = {var.name: var for var in list_step.stack[0].variables}
    list_xs = list_values["xs"]
    assert list_values["b"].value == "9"
    assert list_xs.is_array is True
    assert [(element.index, element.value) for element in list_xs.elements] == [
        (0, list_values["a"].address),
        (1, list_values["b"].address),
    ]
    assert {
        (edge.source_address, edge.target_address)
        for edge in list_step.edges
    } == {
        (list_xs.elements[0].address, list_values["a"].address),
        (list_xs.elements[1].address, list_values["b"].address),
    }

    set_step = parse_step(
        "#include <set>\n"
        "using namespace std;\n"
        "int a = 1;\n"
        "int b = 2;\n"
        "set<int*> xs;\n"
        "xs.insert(&a);\n"
        "xs.insert(&b);\n"
        "int count = xs.size();\n",
        8,
        "000000aa`0000efd0 int a = 1\n"
        "000000aa`0000efd4 int b = 2\n"
        "000000aa`0000efe0 std::set<int *> xs = size=2\n"
        "000000aa`0000efe8 int count = 2",
        "    xs : { size=2 } [Type: std::set<int *>]\n"
        "        [0] : 0x000000aa0000efd4 [Type: int *]\n"
        "        [1] : 0x000000aa0000efd0 [Type: int *]",
    )
    set_values = {var.name: var for var in set_step.stack[0].variables}
    set_xs = set_values["xs"]
    assert set_values["count"].value == "2"
    assert set_xs.is_array is True
    assert {element.value for element in set_xs.elements} == {
        set_values["a"].address,
        set_values["b"].address,
    }
    assert {
        (edge.source_address, edge.target_address)
        for edge in set_step.edges
    } == {
        (element.address, element.value)
        for element in set_xs.elements
    }

    unordered_step = parse_step(
        "#include <string>\n"
        "#include <unordered_map>\n"
        "using namespace std;\n"
        "int a = 1;\n"
        "int b = 2;\n"
        "unordered_map<string, int*> m;\n"
        'm["a"] = &a;\n'
        'm["b"] = &b;\n'
        '*m["b"] = 9;\n',
        9,
        "000000aa`0000efd0 int a = 1\n"
        "000000aa`0000efd4 int b = 9\n"
        "000000aa`0000efe0 std::unordered_map<std::string,int *> m = size=2",
        "    m : { size=2 } [Type: std::unordered_map<std::string,int *>]\n"
        "        [0] : {first=\"b\", second=0x000000aa0000efd4} [Type: std::pair<const std::string,int *>]\n"
        "            first : \"b\" [Type: std::string]\n"
        "            second : 0x000000aa0000efd4 [Type: int *]\n"
        "        [1] : {first=\"a\", second=0x000000aa0000efd0} [Type: std::pair<const std::string,int *>]\n"
        "            first : \"a\" [Type: std::string]\n"
        "            second : 0x000000aa0000efd0 [Type: int *]",
    )
    unordered_values = {var.name: var for var in unordered_step.stack[0].variables}
    unordered_m = unordered_values["m"]
    assert unordered_values["b"].value == "9"
    assert unordered_m.is_array is True
    assert [(element.index, element.value) for element in unordered_m.elements] == [
        (0, "{first=b, second=" + unordered_values["b"].address + "}"),
        (1, "{first=a, second=" + unordered_values["a"].address + "}"),
    ]
    assert {
        (edge.source_address, edge.target_address)
        for edge in unordered_step.edges
    } == {
        (unordered_m.elements[0].address, unordered_values["b"].address),
        (unordered_m.elements[1].address, unordered_values["a"].address),
    }


def test_debug_executor_filters_future_locals_from_stack_snapshots():
    """Future loop/call locals should not appear before their source line completes."""
    from app.core.debug_executor import DebugExecutor

    executor = DebugExecutor()
    prepared = executor._prepare_source(
        "int RunGame() {\n"
        "    int score = 0;\n"
        "    return score;\n"
        "}\n"
        "int main() {\n"
        "    int cases;\n"
        "    cin >> cases;\n"
        "    for (int c = 0; c < cases; ++c) {\n"
        "        int ans = RunGame();\n"
        "    }\n"
        "}\n"
    )

    before_for_output = """
__CXXMV_BEFORE__0
frame #0: 0x1 program`main at program.cpp:7:5
__CXXMV_AFTER__0
frame #0: 0x2 program`main at program.cpp:8:10
__CXXMV_FRAME__0__8__main
0x000000016fdfe700: (int) cases = 1
0x000000016fdfe704: (int) c = 0
"""
    before_call_output = """
__CXXMV_BEFORE__0
frame #0: 0x1 program`RunGame() at program.cpp:2:9
__CXXMV_AFTER__0
frame #0: 0x2 program`RunGame() at program.cpp:3:12
__CXXMV_FRAME__0__2__RunGame()
0x000000016fdfe710: (int) score = 0
__CXXMV_FRAME__1__9__main
0x000000016fdfe700: (int) cases = 1
0x000000016fdfe704: (int) c = 0
0x000000016fdfe708: (int) ans = 32767
"""

    before_for = executor._parse_lldb_output(before_for_output, prepared).steps[0]
    before_call = executor._parse_lldb_output(before_call_output, prepared).steps[0]

    assert [v.name for v in before_for.stack[0].variables] == ["cases"]
    assert [v.name for v in before_call.stack[1].variables] == ["cases", "c"]


def test_ai_executor_falls_back_to_ai_for_stdin_programs():
    """stdin-heavy OJ programs should take the existing AI path instead of timing out."""
    import asyncio

    class FakeAIService:
        async def chat_json(self, *args, **kwargs):
            return '{"steps":[]}'

    with patch("app.core.ai_executor.AIService", return_value=FakeAIService()):
        from app.core.ai_executor import AIExecutor

        result = asyncio.run(AIExecutor().run_code(
            "#include <iostream>\n"
            "using namespace std;\n"
            "int main() { int cases; if (!(cin >> cases)) return 0; return cases; }\n"
        ))

    assert result.steps == []


def test_debug_executor_lldb_timeout_is_debug_execution_error():
    """Raw subprocess timeouts should become DebugExecutionError for AI fallback."""
    import subprocess
    from pathlib import Path
    from app.core.debug_executor import DebugExecutionError, DebugExecutor

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout"))

    with patch("app.core.debug_executor.subprocess.run", side_effect=fake_run):
        try:
            DebugExecutor()._run_lldb(Path("program"), Path("lldb_commands.txt"))
        except DebugExecutionError as exc:
            assert "timed out" in str(exc)
        else:
            raise AssertionError("LLDB timeout should be wrapped as DebugExecutionError")


def test_ai_executor_prefers_debug_executor_without_ai_call():
    """AIExecutor should use the native debugger path before making API calls."""
    import asyncio
    from app.core.memory_model import ExecutionTrace, MemoryState, StackFrame, Variable

    expected = ExecutionTrace(steps=[
        MemoryState(
            line_number=1,
            source_code="int a = 1;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="int", value="1", address="0xS001", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        )
    ])
    captured = {}

    class FakeDebugExecutor:
        last_backend_label = "LLDB / DWARF"

        def run_code(self, code, stdin_text=""):
            captured["code"] = code
            captured["stdin"] = stdin_text
            return expected

    class FailingAIService:
        async def chat_json(self, *args, **kwargs):
            raise AssertionError("AI service should not be called when debugger succeeds")

    with patch("app.core.ai_executor.DebugExecutor", return_value=FakeDebugExecutor()):
        with patch("app.core.ai_executor.AIService", return_value=FailingAIService()):
            from app.core.ai_executor import AIExecutor

            executor = AIExecutor()
            result = asyncio.run(executor.run_code("int a = 1;"))

    assert result is expected
    assert captured["code"] == "int a = 1;"
    assert captured["stdin"] == ""
    assert executor.execution_summary == "Native debugger: LLDB / DWARF"


def test_ai_executor_falls_back_to_ai_when_debug_executor_cannot_run():
    """Debugger failures should preserve the existing AI JSON execution path."""
    import asyncio

    class FailingDebugExecutor:
        def run_code(self, code, stdin_text=""):
            from app.core.debug_executor import DebugExecutionError

            raise DebugExecutionError("unsupported code")

    class FakeAIService:
        async def chat_json(self, *args, **kwargs):
            return '{"steps":[]}'

    with patch("app.core.ai_executor.DebugExecutor", return_value=FailingDebugExecutor()):
        with patch("app.core.ai_executor.AIService", return_value=FakeAIService()):
            from app.core.ai_executor import AIExecutor

            executor = AIExecutor()
            result = asyncio.run(executor.run_code("template <class T> T f(T x) { return x; }"))

    assert result.steps == []
    assert executor.execution_summary == "AI fallback after native debugger failed: unsupported code"


def test_ai_executor_skips_complex_native_when_ai_key_is_configured():
    """Complex programs should use AI immediately when an API key is available."""
    import asyncio

    complex_code = (
        "int main() {\n"
        + "\n".join(
            f"for (int i{i} = 0; i{i} < 10; ++i{i}) {{ if (i{i} % 2) continue; }}"
            for i in range(24)
        )
        + "\n}\n"
    )
    captured = {}

    class FailingDebugExecutor:
        def run_code(self, code, stdin_text=""):
            raise AssertionError("complex code should skip native debugger when AI key exists")

    class FakeAIService:
        api_key = "sk-test"

        async def chat_json(self, **kwargs):
            captured["user_message"] = kwargs["user_message"]
            return '{"steps":[]}'

    with patch("app.core.ai_executor.DebugExecutor", return_value=FailingDebugExecutor()):
        with patch("app.core.ai_executor.AIService", return_value=FakeAIService()):
            from app.core.ai_executor import AIExecutor

            executor = AIExecutor()
            result = asyncio.run(executor.run_code(complex_code))

    assert result.steps == []
    assert complex_code in captured["user_message"]
    assert executor.execution_summary == "AI fallback: complex code skipped native debugger"


def test_ai_executor_keeps_native_for_complex_code_without_ai_key():
    """Without an API key, complex code should still try the local debugger path."""
    import asyncio
    from app.core.memory_model import ExecutionTrace, MemoryState, StackFrame, Variable

    complex_code = (
        "int main() {\n"
        + "\n".join(
            f"for (int i{i} = 0; i{i} < 10; ++i{i}) {{ if (i{i} % 2) continue; }}"
            for i in range(24)
        )
        + "\n}\n"
    )
    expected = ExecutionTrace(steps=[
        MemoryState(
            line_number=1,
            source_code="int ok = 1;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="ok", type="int", value="1", address="0xS001", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        )
    ])
    captured = {}

    class FakeDebugExecutor:
        def run_code(self, code, stdin_text=""):
            captured["code"] = code
            return expected

    class FailingAIService:
        api_key = ""

        async def chat_json(self, **kwargs):
            raise AssertionError("AI service should not be called without a key when native succeeds")

    with patch("app.core.ai_executor.DebugExecutor", return_value=FakeDebugExecutor()):
        with patch("app.core.ai_executor.AIService", return_value=FailingAIService()):
            from app.core.ai_executor import AIExecutor

            result = asyncio.run(AIExecutor().run_code(complex_code))

    assert result is expected
    assert captured["code"] == complex_code


# ── Phase 3: HeapItem _value_label for object and array ─────────────────

def test_heap_item_object_sets_value_label():
    """_build_object() stores _value_label reference."""
    from PySide6.QtWidgets import QApplication
    import sys
    QApplication.instance() or QApplication(sys.argv)

    from app.core.memory_model import HeapBlock, StructMember
    from app.ui.canvas.heap_item import HeapItem

    block = HeapBlock(
        address="0xH001", type="MyClass", value="42",
        is_object=True, class_name="MyClass",
        members=[StructMember(name="x", type="int", value="99")],
    )
    item = HeapItem(block)
    assert item._value_label is not None, "object heap block should have _value_label"
    assert "99" in item._value_label.toPlainText()


def test_heap_item_array_sets_value_label():
    """_build_array() stores _value_label reference."""
    from PySide6.QtWidgets import QApplication
    import sys
    QApplication.instance() or QApplication(sys.argv)

    from app.core.memory_model import HeapBlock, ArrayElement
    from app.ui.canvas.heap_item import HeapItem

    block = HeapBlock(
        address="0xH002", type="int[]", value="",
        is_array=True,
        elements=[ArrayElement(index=0, value="7")],
    )
    item = HeapItem(block)
    assert item._value_label is not None, "array heap block should have _value_label"
    assert "7" in item._value_label.toPlainText()


def test_stack_item_object_draws_member_labels():
    """Stack object variables should visibly render their member rows."""
    from PySide6.QtWidgets import QApplication, QGraphicsTextItem
    import sys
    QApplication.instance() or QApplication(sys.argv)

    from app.core.memory_model import StackFrame, StructMember, Variable
    from app.ui.canvas.stack_item import StackItem

    item = StackItem(StackFrame(frame_name="main", variables=[
        Variable(
            name="c",
            type="Counter",
            value="{value=4, extra=13}",
            address="0xS001",
            is_pointer=False,
            is_object=True,
            class_name="Counter",
            members=[
                StructMember(name="value", type="int", value="4"),
                StructMember(name="extra", type="int", value="13"),
            ],
        ),
    ]))
    texts = [
        child.toPlainText()
        for child in item.childItems()
        if isinstance(child, QGraphicsTextItem)
    ]

    assert any("c: Counter = {value=4, extra=13}" in text for text in texts)
    assert any(".value: int = 4" in text for text in texts)
    assert any(".extra: int = 13" in text for text in texts)


# ── Phase 3: No double JSON serialize ──────────────────────────────────

def test_ai_service_returns_raw_string():
    """chat_json() returns LLM content directly, not re-serialized."""
    from app.services.ai_service import AIService
    import asyncio

    service = AIService()
    service.api_key = "test_key"

    class FakeResponse:
        @staticmethod
        def json():
            return {"choices": [{"message": {"content": '{"steps":[]}'}}]}
        @staticmethod
        def raise_for_status():
            pass

    class FakeClient:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        @staticmethod
        async def post(*args, **kwargs): return FakeResponse()

    async def run():
        with patch("httpx.AsyncClient", new=FakeClient):
            result = await service.chat_json("sys", "user")
            assert isinstance(result, str), f"expected str, got {type(result)}"
            assert result == '{"steps":[]}', f"expected raw JSON, got {result}"

    asyncio.run(run())


def test_ai_service_extracts_json_from_mixed_response():
    """Common fenced/prefaced model output should still normalize to JSON text."""
    from app.services.ai_service import AIService

    raw = "Here is the JSON:\n```json\n{\"steps\": []}\n```\nDone."

    assert AIService._normalize_json(raw) == '{"steps": []}'


def test_ai_service_invalid_json_error_has_context_and_raw_response():
    """Truncated JSON should not leak a bare JSONDecodeError to the UI."""
    from app.services.ai_service import AIService

    raw = '{"steps": [{"line_number": 1, "source_code": }]}'

    try:
        AIService._normalize_json(raw)
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("invalid JSON should raise RuntimeError")

    assert "AI returned invalid JSON" in message
    assert "Near JSON line" in message
    assert "---RAW RESPONSE---" in message


# ── Phase 3: C++ comments preserved ────────────────────────────────────

def test_extract_code_preserves_comments():
    """_extract_code no longer strips // comments."""
    from app.services.file_service import _extract_code
    import tempfile

    code = 'int* p = new int(5); // heap allocation\nint a = 42;'
    with tempfile.NamedTemporaryFile(mode="w", suffix=".cpp", delete=False) as f:
        f.write(code)
        tmp = f.name
    try:
        result = _extract_code(Path(tmp)).strip()
        assert "// heap allocation" in result, "comments should be preserved"
    finally:
        os.unlink(tmp)


# ── Phase 5: Graph page uses named class ───────────────────────────────

def test_graph_page_named_canvas_class():
    """knowledge_page defines _GraphCanvas as a named class."""
    from PySide6.QtWidgets import QApplication
    import sys
    QApplication.instance() or QApplication(sys.argv)

    from app.ui.pages.knowledge_page import _GraphCanvas
    assert _GraphCanvas.__name__ == "_GraphCanvas"


def test_native_debug_smoke_summarizes_and_dumps_trace():
    """Native smoke reports enough stack/heap/edge context for Windows failures."""
    from app.core.memory_model import (
        ExecutionTrace,
        HeapBlock,
        MemoryState,
        PointerEdge,
        StackFrame,
        StructMember,
        Variable,
    )
    from tools.native_debug_smoke import CASES, _trace_summary, _write_trace_dump

    trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=2,
            source_code="Point* hp = new Point{1, 2.5};",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="hp", type="Point*", value="0xH001", address="0xS001", is_pointer=True),
            ])],
            heap=[HeapBlock(
                address="0xH001",
                type="Point",
                value="{x=1, y=2.5}",
                is_object=True,
                class_name="Point",
                base_classes=["Shape"],
                virtual_methods=["area()"],
                members=[
                    StructMember(name="x", type="int", value="1"),
                    StructMember(name="y", type="double", value="2.5"),
                ],
            )],
            edges=[PointerEdge(source_address="0xS001", target_address="0xH001")],
        ),
    ])

    summary = _trace_summary(trace)
    assert summary["step_count"] == 1
    assert summary["frames"][0]["variables"][0]["name"] == "hp"
    assert summary["heap"][0]["class_name"] == "Point"
    assert summary["heap"][0]["base_classes"] == ["Shape"]
    assert summary["heap"][0]["virtual_methods"] == ["area()"]
    assert summary["heap"][0]["members"][1]["value"] == "2.5"
    assert summary["edges"][0]["target"] == "0xH001"

    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_trace_dump(Path(tmpdir), CASES["heap_object"], trace, summary)
        payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["case"] == "heap_object"
    assert payload["summary"]["heap"][0]["type"] == "Point"
    assert payload["trace"]["steps"][0]["line_number"] == 2


def test_native_debug_smoke_requires_final_freed_heap_state():
    """Heap smoke should prove delete leaves a freed block and dangling edge visible."""
    from app.core.memory_model import ExecutionTrace, HeapBlock, MemoryState, PointerEdge
    from tools.native_debug_smoke import _validate_heap_object

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=2,
            source_code="Point* hp = new Point{1, 2.5};",
            stack=[],
            heap=[HeapBlock(
                address="0xH001",
                type="Point",
                value="{x=1, y=2.5}",
                is_object=True,
            )],
            edges=[],
        ),
        MemoryState(
            line_number=3,
            source_code="delete hp;",
            stack=[],
            heap=[],
            edges=[],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=3,
            source_code="delete hp;",
            stack=[],
            heap=[HeapBlock(
                address="0xH001",
                type="Point",
                value="{x=1, y=2.5}",
                is_object=True,
                is_freed=True,
            )],
            edges=[PointerEdge(
                source_address="0xS001",
                target_address="0xH001",
                is_dangling=True,
            )],
        ),
    ])

    weak_errors = _validate_heap_object(weak_trace)
    assert "final state is missing freed heap block after delete" in weak_errors
    assert "final state is missing dangling pointer edge after delete" in weak_errors
    assert _validate_heap_object(strong_trace) == []


def test_native_debug_smoke_requires_inherited_virtual_object_state():
    """Native smoke should prove OO metadata and polymorphic stack edges are visible."""
    from app.core.memory_model import ExecutionTrace, MemoryState, PointerEdge, StackFrame, StructMember, Variable
    from tools.native_debug_smoke import _validate_inherited_virtual_object

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=7,
            source_code="int sound = a->speak();",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="d",
                    type="Dog",
                    value="{Animal={age=3}, bones=4}",
                    address="0xS001",
                    is_pointer=False,
                    is_object=True,
                    class_name="Dog",
                    members=[
                        StructMember(name="Animal", type="Animal", value="{age=3}"),
                        StructMember(name="bones", type="int", value="4"),
                    ],
                ),
                Variable(name="a", type="Animal*", value="0xS001", address="0xS001", is_pointer=True),
                Variable(name="sound", type="int", value="6", address="0xS003", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=7,
            source_code="int sound = a->speak();",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="d",
                    type="Dog",
                    value="{Animal={age=3}, bones=4}",
                    address="0xS001",
                    is_pointer=False,
                    is_object=True,
                    class_name="Dog",
                    base_classes=["Animal"],
                    virtual_methods=["speak()"],
                    members=[
                        StructMember(name="Animal", type="Animal", value="{age=3}"),
                        StructMember(name="bones", type="int", value="4"),
                    ],
                ),
                Variable(name="a", type="Animal*", value="0xS001", address="0xS002", is_pointer=True),
                Variable(name="sound", type="int", value="7", address="0xS003", is_pointer=False),
            ])],
            heap=[],
            edges=[PointerEdge(source_address="0xS002", target_address="0xS001")],
        ),
    ])

    weak_errors = _validate_inherited_virtual_object(weak_trace)
    assert any("base class" in error for error in weak_errors)
    assert any("virtual method" in error for error in weak_errors)
    assert "a pointer variable address should not collapse onto d's object address" in weak_errors
    assert "missing a -> d stack pointer edge" in weak_errors
    assert any("sound expected 7" in error for error in weak_errors)
    assert _validate_inherited_virtual_object(strong_trace) == []


def test_native_debug_smoke_requires_heap_polymorphic_delete_state():
    """Native smoke should prove polymorphic heap objects survive as freed blocks."""
    from app.core.memory_model import ExecutionTrace, HeapBlock, MemoryState, PointerEdge, StackFrame, StructMember, Variable
    from tools.native_debug_smoke import _validate_heap_polymorphic_delete

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=6,
            source_code="int sound = a->speak();",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="Animal*", value="0xH001", address="0xS001", is_pointer=True),
                Variable(name="sound", type="int", value="6", address="0xS002", is_pointer=False),
            ])],
            heap=[HeapBlock(
                address="0xH001",
                type="Dog",
                value="{Animal={age=3}, bones=4}",
                is_object=True,
                class_name="Dog",
                base_classes=["Animal"],
                virtual_methods=["speak()", "Animal()"],
                members=[
                    StructMember(name="Animal", type="Animal", value="{age=3}"),
                    StructMember(name="bones", type="int", value="4"),
                ],
            )],
            edges=[PointerEdge(source_address="0xS001", target_address="0xH001")],
        ),
        MemoryState(
            line_number=7,
            source_code="delete a;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="Animal*", value="0xH001", address="0xS003", is_pointer=True),
                Variable(name="sound", type="int", value="6", address="0xS002", is_pointer=False),
            ])],
            heap=[HeapBlock(
                address="0xH001",
                type="Dog",
                value="{Animal={age=3}, bones=4}",
                is_object=True,
                class_name="Dog",
                base_classes=["Animal"],
                virtual_methods=["speak()", "Animal()"],
                members=[
                    StructMember(name="Animal", type="Animal", value="{age=3}"),
                    StructMember(name="bones", type="int", value="4"),
                ],
            )],
            edges=[],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=7,
            source_code="delete a;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="Animal*", value="0xH001", address="0xS001", is_pointer=True),
                Variable(name="sound", type="int", value="7", address="0xS002", is_pointer=False),
            ])],
            heap=[HeapBlock(
                address="0xH001",
                type="Dog",
                value="{Animal={age=3}, bones=4}",
                is_object=True,
                class_name="Dog",
                base_classes=["Animal"],
                virtual_methods=["speak()"],
                is_freed=True,
                members=[
                    StructMember(name="Animal", type="Animal", value="{age=3}"),
                    StructMember(name="bones", type="int", value="4"),
                ],
            )],
            edges=[PointerEdge(source_address="0xS001", target_address="0xH001", is_dangling=True)],
        ),
    ])

    weak_errors = _validate_heap_polymorphic_delete(weak_trace)
    assert any("address should remain stable" in error for error in weak_errors)
    assert any("virtual_methods expected" in error for error in weak_errors)
    assert any("should remain visible as freed" in error for error in weak_errors)
    assert "final state is missing dangling pointer edge after polymorphic delete" in weak_errors
    assert any("sound expected 7" in error for error in weak_errors)
    assert _validate_heap_polymorphic_delete(strong_trace) == []


def test_native_debug_smoke_requires_heap_leak_overwrite_state():
    """Native smoke should prove overwritten heap blocks stay visible as leaks."""
    from app.core.memory_model import ExecutionTrace, HeapBlock, MemoryState, PointerEdge, StackFrame, Variable
    from tools.native_debug_smoke import _validate_heap_leak_overwrite

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=3,
            source_code="*p = 3;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="p", type="int*", value="0xH002", address="0xS001", is_pointer=True),
            ])],
            heap=[HeapBlock(address="0xH002", type="int", value="3")],
            edges=[PointerEdge(source_address="0xS001", target_address="0xH002")],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=3,
            source_code="*p = 3;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="p", type="int*", value="0xH002", address="0xS001", is_pointer=True),
            ])],
            heap=[
                HeapBlock(address="0xH002", type="int", value="3"),
                HeapBlock(address="0xH001", type="int", value="1"),
            ],
            edges=[PointerEdge(source_address="0xS001", target_address="0xH002")],
        ),
    ])

    weak_errors = _validate_heap_leak_overwrite(weak_trace)
    assert any("expected current heap plus leaked heap block" in error for error in weak_errors)
    assert any("missing overwritten leaked heap value 1" in error for error in weak_errors)
    assert _validate_heap_leak_overwrite(strong_trace) == []


def test_native_debug_smoke_requires_unique_ptr_heap_state():
    """Native smoke should prove unique_ptr owns a visible heap block."""
    from app.core.memory_model import ExecutionTrace, HeapBlock, MemoryState, PointerEdge, StackFrame, StructMember, Variable
    from tools.native_debug_smoke import _validate_unique_ptr_heap

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=4,
            source_code="*p = 8;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="p",
                    type="std::unique_ptr<int>",
                    value="{pointer=0x00000001006446a0}",
                    address="0xS001",
                    is_pointer=False,
                    is_object=True,
                    members=[StructMember(name="pointer", type="int*", value="0x00000001006446a0")],
                ),
            ])],
            heap=[],
            edges=[],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=4,
            source_code="*p = 8;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="p", type="std::unique_ptr<int>", value="0xH001", address="0xS001", is_pointer=True),
            ])],
            heap=[HeapBlock(address="0xH001", type="int", value="8")],
            edges=[PointerEdge(source_address="0xS001", target_address="0xH001")],
        ),
        MemoryState(
            line_number=5,
            source_code="p.reset();",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="p", type="std::unique_ptr<int>", value="nullptr", address="0xS001", is_pointer=True),
            ])],
            heap=[],
            edges=[],
        ),
    ])

    weak_errors = _validate_unique_ptr_heap(weak_trace)
    assert "missing unique_ptr heap state with updated value 8" in weak_errors
    assert _validate_unique_ptr_heap(strong_trace) == []


def test_native_debug_smoke_requires_shared_ptr_owner_state():
    """Native smoke should prove shared_ptr owners share one visible heap block."""
    from app.core.memory_model import ExecutionTrace, HeapBlock, MemoryState, PointerEdge, StackFrame, Variable
    from tools.native_debug_smoke import _validate_shared_ptr_owners

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=4,
            source_code="shared_ptr<int> b = a;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="std::shared_ptr<int>", value="0xH001", address="0xS001", is_pointer=True),
                Variable(name="b", type="std::shared_ptr<int>", value="0xH002", address="0xS002", is_pointer=True),
            ])],
            heap=[
                HeapBlock(address="0xH001", type="int", value="5"),
                HeapBlock(address="0xH002", type="int", value="5"),
            ],
            edges=[
                PointerEdge(source_address="0xS001", target_address="0xH001"),
                PointerEdge(source_address="0xS002", target_address="0xH002"),
            ],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=4,
            source_code="shared_ptr<int> b = a;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="std::shared_ptr<int>", value="0xH001", address="0xS001", is_pointer=True),
                Variable(name="b", type="std::shared_ptr<int>", value="0xH001", address="0xS002", is_pointer=True),
            ])],
            heap=[HeapBlock(address="0xH001", type="int", value="5")],
            edges=[
                PointerEdge(source_address="0xS001", target_address="0xH001"),
                PointerEdge(source_address="0xS002", target_address="0xH001"),
            ],
        ),
        MemoryState(
            line_number=6,
            source_code="a.reset();",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="std::shared_ptr<int>", value="nullptr", address="0xS001", is_pointer=True),
                Variable(name="b", type="std::shared_ptr<int>", value="0xH001", address="0xS002", is_pointer=True),
            ])],
            heap=[HeapBlock(address="0xH001", type="int", value="9")],
            edges=[PointerEdge(source_address="0xS002", target_address="0xH001")],
        ),
        MemoryState(
            line_number=7,
            source_code="*b = 11;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="std::shared_ptr<int>", value="nullptr", address="0xS001", is_pointer=True),
                Variable(name="b", type="std::shared_ptr<int>", value="0xH001", address="0xS002", is_pointer=True),
            ])],
            heap=[HeapBlock(address="0xH001", type="int", value="11")],
            edges=[PointerEdge(source_address="0xS002", target_address="0xH001")],
        ),
    ])

    weak_errors = _validate_shared_ptr_owners(weak_trace)
    assert any("same heap block" in error for error in weak_errors)
    assert "missing a.reset() state" in weak_errors
    assert _validate_shared_ptr_owners(strong_trace) == []


def test_native_debug_smoke_requires_weak_ptr_expired_state():
    """Native smoke should prove expired weak_ptr targets are dangling, not live owners."""
    from app.core.memory_model import ExecutionTrace, HeapBlock, MemoryState, PointerEdge, StackFrame, Variable
    from tools.native_debug_smoke import _validate_weak_ptr_expired

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=6,
            source_code="bool gone = wp.expired();",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="sp", type="std::shared_ptr<int>", value="nullptr", address="0xS001", is_pointer=True),
                Variable(name="wp", type="std::weak_ptr<int>", value="0xH001", address="0xS002", is_pointer=True),
                Variable(name="gone", type="bool", value="true", address="0xS003", is_pointer=False),
            ])],
            heap=[HeapBlock(address="0xH001", type="int", value="3")],
            edges=[PointerEdge(source_address="0xS002", target_address="0xH001")],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=6,
            source_code="bool gone = wp.expired();",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="sp", type="std::shared_ptr<int>", value="nullptr", address="0xS001", is_pointer=True),
                Variable(name="wp", type="std::weak_ptr<int>", value="0xH001", address="0xS002", is_pointer=True),
                Variable(name="gone", type="bool", value="true", address="0xS003", is_pointer=False),
            ])],
            heap=[HeapBlock(address="0xH001", type="int", value="3", is_freed=True)],
            edges=[PointerEdge(source_address="0xS002", target_address="0xH001", is_dangling=True)],
        ),
    ])

    weak_errors = _validate_weak_ptr_expired(weak_trace)
    assert "expired weak_ptr target heap should be marked freed" in weak_errors
    assert "missing dangling wp -> expired heap edge" in weak_errors
    assert _validate_weak_ptr_expired(strong_trace) == []


def test_native_debug_smoke_requires_vector_shared_ptr_container_state():
    """Native smoke should prove vector<shared_ptr<T>> stays a container."""
    from app.core.memory_model import ArrayElement, ExecutionTrace, HeapBlock, MemoryState, PointerEdge, StackFrame, Variable
    from tools.native_debug_smoke import _validate_vector_shared_ptr

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=6,
            source_code="*xs[0] = 8;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="alias", type="std::shared_ptr<int>", value="0xH001", address="0xS001", is_pointer=True),
                Variable(name="xs", type="std::vector<std::shared_ptr<int>>", value="nullptr", address="0xS002", is_pointer=True),
            ])],
            heap=[HeapBlock(address="0xH001", type="int", value="8")],
            edges=[PointerEdge(source_address="0xS001", target_address="0xH001")],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=6,
            source_code="*xs[0] = 8;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="alias", type="std::shared_ptr<int>", value="0xH001", address="0xS001", is_pointer=True),
                Variable(
                    name="xs",
                    type="std::vector<std::shared_ptr<int>>",
                    value="{[0]=0xH001}",
                    address="0xS002",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(
                            index=0,
                            type="std::shared_ptr<int>",
                            value="0xH001",
                            address="0xS002[0]",
                        ),
                    ],
                ),
            ])],
            heap=[HeapBlock(address="0xH001", type="int", value="8")],
            edges=[
                PointerEdge(source_address="0xS001", target_address="0xH001"),
                PointerEdge(source_address="0xS002[0]", target_address="0xH001"),
            ],
        ),
    ])

    weak_errors = _validate_vector_shared_ptr(weak_trace)
    assert "xs should be marked as an array/container" in weak_errors
    assert "xs should not be marked as a pointer" in weak_errors
    assert _validate_vector_shared_ptr(strong_trace) == []


def test_native_debug_smoke_requires_vector_unique_ptr_heap_state():
    """Native smoke should prove vector<unique_ptr<T>> elements own visible heap."""
    from app.core.memory_model import ArrayElement, ExecutionTrace, HeapBlock, MemoryState, PointerEdge, StackFrame, Variable
    from tools.native_debug_smoke import _validate_vector_unique_ptr

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=6,
            source_code="*xs[0] = 8;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="xs",
                    type="std::vector<std::unique_ptr<int>>",
                    value="{[0]=0xH001}",
                    address="0xS001",
                    is_pointer=False,
                    is_array=True,
                    elements=[ArrayElement(index=0, type="std::unique_ptr<int>", value="0xH001", address="0xS001[0]")],
                ),
            ])],
            heap=[],
            edges=[PointerEdge(source_address="0xS001[0]", target_address="0xH001")],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=6,
            source_code="*xs[0] = 8;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="xs",
                    type="std::vector<std::unique_ptr<int>>",
                    value="{[0]=0xH001}",
                    address="0xS001",
                    is_pointer=False,
                    is_array=True,
                    elements=[ArrayElement(index=0, type="std::unique_ptr<int>", value="0xH001", address="0xS001[0]")],
                ),
            ])],
            heap=[HeapBlock(address="0xH001", type="int", value="8")],
            edges=[PointerEdge(source_address="0xS001[0]", target_address="0xH001")],
        ),
    ])

    weak_errors = _validate_vector_unique_ptr(weak_trace)
    assert "missing heap block for vector unique_ptr target '0xH001'" in weak_errors
    assert _validate_vector_unique_ptr(strong_trace) == []


def test_native_debug_smoke_requires_vector_unique_ptr_object_heap_state():
    """Native smoke should prove vector<unique_ptr<Object>> keeps object heap members."""
    from app.core.memory_model import ArrayElement, ExecutionTrace, HeapBlock, MemoryState, PointerEdge, StackFrame, StructMember, Variable
    from tools.native_debug_smoke import _validate_vector_unique_ptr_object

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=8,
            source_code="nodes[0]->next->value = 6;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="first",
                    type="Node",
                    value="{value=6, next=nullptr}",
                    address="0xS001",
                    is_pointer=False,
                    is_object=True,
                    class_name="Node",
                    members=[
                        StructMember(name="value", type="int", value="6", address="0xS001.value"),
                        StructMember(name="next", type="Node*", value="nullptr", address="0xS001.next"),
                    ],
                ),
                Variable(
                    name="nodes",
                    type="std::vector<std::unique_ptr<Node>>",
                    value="{[0]=0xH001}",
                    address="0xS002",
                    is_pointer=False,
                    is_array=True,
                    elements=[ArrayElement(index=0, type="std::unique_ptr<Node>", value="0xH001", address="0xS002[0]")],
                ),
            ])],
            heap=[HeapBlock(address="0xH001", type="Node", value="{value=2, next=0xS001}")],
            edges=[PointerEdge(source_address="0xS002[0]", target_address="0xH001")],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=8,
            source_code="nodes[0]->next->value = 6;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="first",
                    type="Node",
                    value="{value=6, next=nullptr}",
                    address="0xS001",
                    is_pointer=False,
                    is_object=True,
                    class_name="Node",
                    members=[
                        StructMember(name="value", type="int", value="6", address="0xS001.value"),
                        StructMember(name="next", type="Node*", value="nullptr", address="0xS001.next"),
                    ],
                ),
                Variable(
                    name="nodes",
                    type="std::vector<std::unique_ptr<Node>>",
                    value="{[0]=0xH001}",
                    address="0xS002",
                    is_pointer=False,
                    is_array=True,
                    elements=[ArrayElement(index=0, type="std::unique_ptr<Node>", value="0xH001", address="0xS002[0]")],
                ),
            ])],
            heap=[HeapBlock(
                address="0xH001",
                type="Node",
                value="{value=2, next=0xS001}",
                is_object=True,
                class_name="Node",
                members=[
                    StructMember(name="value", type="int", value="2", address="0xH001.value"),
                    StructMember(name="next", type="Node*", value="0xS001", address="0xH001.next"),
                ],
            )],
            edges=[
                PointerEdge(source_address="0xS002[0]", target_address="0xH001"),
                PointerEdge(source_address="0xH001.next", target_address="0xS001"),
            ],
        ),
    ])

    weak_errors = _validate_vector_unique_ptr_object(weak_trace)
    assert any("unique_ptr target should be Node object" in error for error in weak_errors)
    assert any("heap Node.next should target first" in error for error in weak_errors)
    assert _validate_vector_unique_ptr_object(strong_trace) == []


def test_native_debug_smoke_requires_std_array_shared_ptr_edges():
    """Native smoke should prove array<shared_ptr<T>,N> uses element edges."""
    from app.core.memory_model import ArrayElement, ExecutionTrace, HeapBlock, MemoryState, PointerEdge, StackFrame, Variable
    from tools.native_debug_smoke import _validate_std_array_shared_ptr

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=6,
            source_code="*xs[0] = 8;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="alias", type="std::shared_ptr<int>", value="0xH001", address="0xS001", is_pointer=True),
                Variable(name="xs", type="std::array<std::shared_ptr<int>, 2>", value="{__elems_=nullptr}", address="0xS002", is_pointer=False, is_object=True),
            ])],
            heap=[HeapBlock(address="0xH001", type="int", value="8")],
            edges=[PointerEdge(source_address="0xS001", target_address="0xH001")],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=6,
            source_code="*xs[0] = 8;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="alias", type="std::shared_ptr<int>", value="0xH001", address="0xS001", is_pointer=True),
                Variable(
                    name="xs",
                    type="std::array<std::shared_ptr<int>, 2>",
                    value="{[0]=0xH001, [1]=nullptr}",
                    address="0xS002",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(index=0, type="std::shared_ptr<int>", value="0xH001", address="0xS002[0]"),
                        ArrayElement(index=1, type="std::shared_ptr<int>", value="nullptr", address="0xS002[1]"),
                    ],
                ),
            ])],
            heap=[HeapBlock(address="0xH001", type="int", value="8")],
            edges=[
                PointerEdge(source_address="0xS001", target_address="0xH001"),
                PointerEdge(source_address="0xS002[0]", target_address="0xH001"),
            ],
        ),
    ])

    weak_errors = _validate_std_array_shared_ptr(weak_trace)
    assert "xs should be marked as an array/container" in weak_errors
    assert "xs should not be marked as an object after element expansion" in weak_errors
    assert _validate_std_array_shared_ptr(strong_trace) == []


def test_native_debug_smoke_requires_control_flow_loop_state():
    """Native smoke should prove real debugger execution follows loop/branch paths."""
    from app.core.memory_model import ExecutionTrace, MemoryState, StackFrame, Variable
    from tools.native_debug_smoke import _validate_control_flow_loop

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=7,
            source_code="sum += i;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="sum", type="int", value="10", address="0xS001", is_pointer=False),
                Variable(name="parity", type="int", value="6", address="0xS002", is_pointer=False),
                Variable(name="i", type="int", value="4", address="0xS003", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=4,
            source_code="if (i % 2 == 0) {",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="sum", type="int", value="0", address="0xS001", is_pointer=False),
                Variable(name="parity", type="int", value="0", address="0xS002", is_pointer=False),
                Variable(name="i", type="int", value="1", address="0xS003", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
        MemoryState(
            line_number=7,
            source_code="sum += i;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="sum", type="int", value="1", address="0xS001", is_pointer=False),
                Variable(name="parity", type="int", value="0", address="0xS002", is_pointer=False),
                Variable(name="i", type="int", value="1", address="0xS003", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
        MemoryState(
            line_number=4,
            source_code="if (i % 2 == 0) {",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="sum", type="int", value="1", address="0xS001", is_pointer=False),
                Variable(name="parity", type="int", value="0", address="0xS002", is_pointer=False),
                Variable(name="i", type="int", value="2", address="0xS003", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
        MemoryState(
            line_number=5,
            source_code="parity += i;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="sum", type="int", value="1", address="0xS001", is_pointer=False),
                Variable(name="parity", type="int", value="2", address="0xS002", is_pointer=False),
                Variable(name="i", type="int", value="2", address="0xS003", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
        MemoryState(
            line_number=7,
            source_code="sum += i;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="sum", type="int", value="3", address="0xS001", is_pointer=False),
                Variable(name="parity", type="int", value="2", address="0xS002", is_pointer=False),
                Variable(name="i", type="int", value="2", address="0xS003", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
        MemoryState(
            line_number=4,
            source_code="if (i % 2 == 0) {",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="sum", type="int", value="3", address="0xS001", is_pointer=False),
                Variable(name="parity", type="int", value="2", address="0xS002", is_pointer=False),
                Variable(name="i", type="int", value="3", address="0xS003", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
        MemoryState(
            line_number=7,
            source_code="sum += i;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="sum", type="int", value="6", address="0xS001", is_pointer=False),
                Variable(name="parity", type="int", value="2", address="0xS002", is_pointer=False),
                Variable(name="i", type="int", value="3", address="0xS003", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
        MemoryState(
            line_number=4,
            source_code="if (i % 2 == 0) {",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="sum", type="int", value="6", address="0xS001", is_pointer=False),
                Variable(name="parity", type="int", value="2", address="0xS002", is_pointer=False),
                Variable(name="i", type="int", value="4", address="0xS003", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
        MemoryState(
            line_number=5,
            source_code="parity += i;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="sum", type="int", value="6", address="0xS001", is_pointer=False),
                Variable(name="parity", type="int", value="6", address="0xS002", is_pointer=False),
                Variable(name="i", type="int", value="4", address="0xS003", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
        MemoryState(
            line_number=7,
            source_code="sum += i;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="sum", type="int", value="10", address="0xS001", is_pointer=False),
                Variable(name="parity", type="int", value="6", address="0xS002", is_pointer=False),
                Variable(name="i", type="int", value="4", address="0xS003", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
        MemoryState(
            line_number=3,
            source_code="for (int i = 1; i <= 4; ++i) {",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="sum", type="int", value="10", address="0xS001", is_pointer=False),
                Variable(name="parity", type="int", value="6", address="0xS002", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
    ])

    weak_errors = _validate_control_flow_loop(weak_trace)
    assert any("if branch should observe" in error for error in weak_errors)
    assert any("loop variable i should be out of scope" in error for error in weak_errors)
    assert _validate_control_flow_loop(strong_trace) == []


def test_native_debug_smoke_requires_lambda_capture_state():
    """Native smoke should prove lambda closures expose captures instead of plain members."""
    from app.core.memory_model import ExecutionTrace, LambdaCapture, MemoryState, StackFrame, StructMember, Variable
    from tools.native_debug_smoke import _validate_lambda_capture

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=5,
            source_code="int result = f(6);",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="base", type="int", value="3", address="0xS001", is_pointer=False),
                Variable(name="factor", type="int", value="7", address="0xS002", is_pointer=False),
                Variable(
                    name="f",
                    type="(unnamed class)",
                    value="{base=3, factor=0xS002}",
                    address="0xS003",
                    is_pointer=False,
                    is_object=True,
                    members=[
                        StructMember(name="base", type="int", value="3"),
                        StructMember(name="factor", type="int&", value="0xS002"),
                    ],
                ),
                Variable(name="result", type="int", value="16", address="0xS004", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=5,
            source_code="int result = f(6);",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="base", type="int", value="3", address="0xS001", is_pointer=False),
                Variable(name="factor", type="int", value="7", address="0xS002", is_pointer=False),
                Variable(
                    name="f",
                    type="lambda",
                    value="<lambda>",
                    address="0xS003",
                    is_pointer=False,
                    is_function_object=True,
                    captures=[
                        LambdaCapture(name="base", type="int", value="3", by_ref=False),
                        LambdaCapture(name="factor", type="int&", value="0xS002", by_ref=True),
                    ],
                ),
                Variable(name="result", type="int", value="16", address="0xS004", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
    ])

    weak_errors = _validate_lambda_capture(weak_trace)
    assert "f should be marked as a function object" in weak_errors
    assert "base capture should exist by value" in weak_errors
    assert _validate_lambda_capture(strong_trace) == []


def test_native_debug_smoke_requires_heap_array_delete_state():
    """Native smoke should prove delete[] leaves array values and dangling state visible."""
    from app.core.memory_model import (
        ArrayElement,
        ExecutionTrace,
        HeapBlock,
        MemoryState,
        PointerEdge,
        StackFrame,
        Variable,
    )
    from tools.native_debug_smoke import _validate_heap_array_delete

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=3,
            source_code="delete[] arr;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="arr", type="int*", value="0xH001", address="0xS001", is_pointer=True),
            ])],
            heap=[],
            edges=[],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=3,
            source_code="delete[] arr;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="arr", type="int*", value="0xH001", address="0xS001", is_pointer=True),
            ])],
            heap=[HeapBlock(
                address="0xH001",
                type="int[]",
                value="{[0]=1, [1]=9, [2]=3}",
                is_freed=True,
                is_array=True,
                element_count=3,
                elements=[
                    ArrayElement(index=0, value="1"),
                    ArrayElement(index=1, value="9"),
                    ArrayElement(index=2, value="3"),
                ],
            )],
            edges=[PointerEdge(
                source_address="0xS001",
                target_address="0xH001",
                is_dangling=True,
            )],
        ),
    ])

    weak_errors = _validate_heap_array_delete(weak_trace)
    assert "final state is missing heap array block" in weak_errors
    assert "final state is missing dangling pointer edge after delete[]" in weak_errors
    assert _validate_heap_array_delete(strong_trace) == []


def test_native_debug_smoke_requires_pointer_reset_null_state():
    """Native smoke should prove nullptr reset clears stale heap edges."""
    from app.core.memory_model import ExecutionTrace, HeapBlock, MemoryState, PointerEdge, StackFrame, Variable
    from tools.native_debug_smoke import _validate_pointer_reset_null

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=2,
            source_code="delete p;",
            stack=[],
            heap=[],
            edges=[],
        ),
        MemoryState(
            line_number=3,
            source_code="p = nullptr;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="p", type="int*", value="nullptr", address="0xS001", is_pointer=True),
            ])],
            heap=[],
            edges=[PointerEdge(
                source_address="0xS001",
                target_address="0xH001",
                is_dangling=True,
            )],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=2,
            source_code="delete p;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="p", type="int*", value="0xH001", address="0xS001", is_pointer=True),
            ])],
            heap=[HeapBlock(address="0xH001", type="int", value="5", is_freed=True)],
            edges=[PointerEdge(
                source_address="0xS001",
                target_address="0xH001",
                is_dangling=True,
            )],
        ),
        MemoryState(
            line_number=3,
            source_code="p = nullptr;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="p", type="int*", value="nullptr", address="0xS001", is_pointer=True),
            ])],
            heap=[],
            edges=[],
        ),
    ])

    weak_errors = _validate_pointer_reset_null(weak_trace)
    assert "delete step should keep the freed heap block visible" in weak_errors
    assert "delete step should show a dangling pointer edge" in weak_errors
    assert any("final nullptr state should have no pointer edges" in error for error in weak_errors)
    assert _validate_pointer_reset_null(strong_trace) == []


def test_native_debug_smoke_requires_stack_dangling_pointer_state():
    """Native smoke should prove expired stack targets are dangling, not heap."""
    from app.core.memory_model import ExecutionTrace, HeapBlock, MemoryState, PointerEdge, StackFrame, Variable
    from tools.native_debug_smoke import _validate_stack_dangling_pointer

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=6,
            source_code="int after = 9;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="p", type="int*", value="0xH001", address="0xS001", is_pointer=True),
                Variable(name="after", type="int", value="9", address="0xS003", is_pointer=False),
            ])],
            heap=[HeapBlock(address="0xH001", type="int", value="5")],
            edges=[PointerEdge(source_address="0xS001", target_address="0xH001")],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=6,
            source_code="int after = 9;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="p", type="int*", value="0xS002", address="0xS001", is_pointer=True),
                Variable(name="after", type="int", value="9", address="0xS003", is_pointer=False),
            ])],
            heap=[],
            edges=[PointerEdge(source_address="0xS001", target_address="0xS002", is_dangling=True)],
        ),
    ])

    weak_errors = _validate_stack_dangling_pointer(weak_trace)
    assert any("should not create heap blocks" in error for error in weak_errors)
    assert any("historical stack address" in error for error in weak_errors)
    assert "missing dangling p -> expired stack variable edge" in weak_errors
    assert _validate_stack_dangling_pointer(strong_trace) == []


def test_native_debug_smoke_requires_stack_array_elements():
    """Native smoke should prove stack arrays preserve updated element cells."""
    from app.core.memory_model import ArrayElement, ExecutionTrace, MemoryState, StackFrame, Variable
    from tools.native_debug_smoke import _validate_stack_array

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=2,
            source_code="nums[1] = 8;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="nums",
                    type="int[3]",
                    value="{[0]=1, [1]=2, [2]=3}",
                    address="0xS001",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(index=0, value="1"),
                        ArrayElement(index=1, value="2"),
                        ArrayElement(index=2, value="3"),
                    ],
                ),
            ])],
            heap=[],
            edges=[],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=2,
            source_code="nums[1] = 8;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="nums",
                    type="int[3]",
                    value="{[0]=1, [1]=8, [2]=3}",
                    address="0xS001",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(index=0, value="1"),
                        ArrayElement(index=1, value="8"),
                        ArrayElement(index=2, value="3"),
                    ],
                ),
            ])],
            heap=[],
            edges=[],
        ),
    ])

    weak_errors = _validate_stack_array(weak_trace)
    assert "nums elements expected ['1', '8', '3'], got ['1', '2', '3']" in weak_errors
    assert _validate_stack_array(strong_trace) == []


def test_native_debug_smoke_requires_std_array_elements():
    """Native smoke should prove std::array unwraps into element cells."""
    from app.core.memory_model import ArrayElement, ExecutionTrace, MemoryState, StackFrame, StructMember, Variable
    from tools.native_debug_smoke import _validate_std_array

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=4,
            source_code="a[1] = 8;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="a",
                    type="std::array<int,3>",
                    value="{__elems_={[0]=1, [1]=8, [2]=3}}",
                    address="0xS001",
                    is_pointer=False,
                    is_object=True,
                    members=[
                        StructMember(name="__elems_", type="int[3]", value="{[0]=1, [1]=8, [2]=3}"),
                    ],
                ),
            ])],
            heap=[],
            edges=[],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=4,
            source_code="a[1] = 8;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="a",
                    type="std::array<int,3>",
                    value="{[0]=1, [1]=8, [2]=3}",
                    address="0xS001",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(index=0, value="1"),
                        ArrayElement(index=1, value="8"),
                        ArrayElement(index=2, value="3"),
                    ],
                ),
            ])],
            heap=[],
            edges=[],
        ),
    ])

    weak_errors = _validate_std_array(weak_trace)
    assert "std::array a should be marked as an array/container" in weak_errors
    assert "std::array should unwrap implementation storage instead of showing __elems_ as members" in weak_errors
    assert _validate_std_array(strong_trace) == []


def test_native_debug_smoke_requires_std_array_object_pointer_edges():
    """Native smoke should prove object array element pointers are mapped and linked."""
    from app.core.memory_model import ArrayElement, ExecutionTrace, MemoryState, PointerEdge, StackFrame, StructMember, Variable
    from tools.native_debug_smoke import _validate_std_array_object_pointer

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=7,
            source_code="nodes[1].next->value = 5;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="first",
                    type="Node",
                    value="{value=5, next=nullptr}",
                    address="0xS001",
                    is_pointer=False,
                    is_object=True,
                    members=[
                        StructMember(name="value", type="int", value="5", address="0xS001.value"),
                        StructMember(name="next", type="Node*", value="nullptr", address="0xS001.next"),
                    ],
                ),
                Variable(
                    name="nodes",
                    type="std::array<Node,2>",
                    value="{[0]={value=1, next=0x0000000000000000}, [1]={value=2, next=0x000000aa0000efd0}}",
                    address="0xS002",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(index=0, type="Node", value="{value=1, next=0x0000000000000000}", address="0xS002[0]"),
                        ArrayElement(index=1, type="Node", value="{value=2, next=0x000000aa0000efd0}", address="0xS002[1]"),
                    ],
                ),
            ])],
            heap=[],
            edges=[],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=7,
            source_code="nodes[1].next->value = 5;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="first",
                    type="Node",
                    value="{value=5, next=nullptr}",
                    address="0xS001",
                    is_pointer=False,
                    is_object=True,
                    members=[
                        StructMember(name="value", type="int", value="5", address="0xS001.value"),
                        StructMember(name="next", type="Node*", value="nullptr", address="0xS001.next"),
                    ],
                ),
                Variable(
                    name="nodes",
                    type="std::array<Node,2>",
                    value="{[0]={value=1, next=nullptr}, [1]={value=2, next=0xS001}}",
                    address="0xS002",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(index=0, type="Node", value="{value=1, next=nullptr}", address="0xS002[0]"),
                        ArrayElement(index=1, type="Node", value="{value=2, next=0xS001}", address="0xS002[1]"),
                    ],
                ),
            ])],
            heap=[],
            edges=[PointerEdge(source_address="0xS002[1]", target_address="0xS001")],
        ),
    ])

    weak_errors = _validate_std_array_object_pointer(weak_trace)
    assert any("nodes[1].next should map" in error for error in weak_errors)
    assert any("nodes[1] should not expose raw debugger addresses" in error for error in weak_errors)
    assert "missing nodes[1] -> first pointer edge" in weak_errors
    assert _validate_std_array_object_pointer(strong_trace) == []


def test_native_debug_smoke_requires_container_adapter_elements():
    """Native smoke should prove stack and priority_queue unwrap adapter storage."""
    from app.core.memory_model import ArrayElement, ExecutionTrace, MemoryState, StackFrame, StructMember, Variable
    from tools.native_debug_smoke import _validate_priority_queue_adapter, _validate_stack_adapter

    weak_stack = ExecutionTrace(steps=[
        MemoryState(
            line_number=6,
            source_code="s.pop();",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="s",
                    type="std::stack<int>",
                    value="{c={[0]=1}}",
                    address="0xS001",
                    is_pointer=False,
                    is_object=True,
                    members=[StructMember(name="c", type="std::deque<int>", value="{[0]=1}")],
                ),
            ])],
            heap=[],
            edges=[],
        ),
    ])
    strong_stack = ExecutionTrace(steps=[
        MemoryState(
            line_number=6,
            source_code="s.pop();",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="s",
                    type="std::stack<int>",
                    value="{[0]=1}",
                    address="0xS001",
                    is_pointer=False,
                    is_array=True,
                    elements=[ArrayElement(index=0, value="1")],
                ),
            ])],
            heap=[],
            edges=[],
        ),
    ])
    weak_pq = ExecutionTrace(steps=[
        MemoryState(
            line_number=6,
            source_code="pq.push(2);",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="pq",
                    type="std::priority_queue<int>",
                    value="{c={[0]=3, [1]=1, [2]=2}}",
                    address="0xS001",
                    is_pointer=False,
                    is_object=True,
                    members=[StructMember(name="c", type="std::vector<int>", value="{[0]=3, [1]=1, [2]=2}")],
                ),
            ])],
            heap=[],
            edges=[],
        ),
    ])
    strong_pq = ExecutionTrace(steps=[
        MemoryState(
            line_number=6,
            source_code="pq.push(2);",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="pq",
                    type="std::priority_queue<int>",
                    value="{[0]=3, [1]=1, [2]=2}",
                    address="0xS001",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(index=0, value="3"),
                        ArrayElement(index=1, value="1"),
                        ArrayElement(index=2, value="2"),
                    ],
                ),
            ])],
            heap=[],
            edges=[],
        ),
    ])

    stack_errors = _validate_stack_adapter(weak_stack)
    assert "stack s should be marked as an array/container" in stack_errors
    assert "stack should unwrap adapter storage instead of showing c as a member" in stack_errors
    assert _validate_stack_adapter(strong_stack) == []

    pq_errors = _validate_priority_queue_adapter(weak_pq)
    assert "priority_queue pq should be marked as an array/container" in pq_errors
    assert "priority_queue should unwrap adapter storage instead of showing c as a member" in pq_errors
    assert _validate_priority_queue_adapter(strong_pq) == []


def test_native_debug_smoke_requires_vector_pointer_elements_not_pointer_container():
    """Native smoke should prove vector<int*> stays a container, not a pointer var."""
    from app.core.memory_model import ArrayElement, ExecutionTrace, MemoryState, PointerEdge, StackFrame, Variable
    from tools.native_debug_smoke import _validate_vector_pointer

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=6,
            source_code="*ptrs[1] = 9;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="int", value="1", address="0xS001", is_pointer=False),
                Variable(name="b", type="int", value="9", address="0xS002", is_pointer=False),
                Variable(
                    name="ptrs",
                    type="vector<int*>",
                    value="0xH001",
                    address="0xS003",
                    is_pointer=True,
                ),
            ])],
            heap=[],
            edges=[],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=6,
            source_code="*ptrs[1] = 9;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="int", value="1", address="0xS001", is_pointer=False),
                Variable(name="b", type="int", value="9", address="0xS002", is_pointer=False),
                Variable(
                    name="ptrs",
                    type="vector<int*>",
                    value="{[0]=0xS001, [1]=0xS002}",
                    address="0xS003",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(index=0, type="int*", value="0xS001", address="0xS003[0]"),
                        ArrayElement(index=1, type="int*", value="0xS002", address="0xS003[1]"),
                    ],
                ),
            ])],
            heap=[],
            edges=[
                PointerEdge(source_address="0xS003[0]", target_address="0xS001"),
                PointerEdge(source_address="0xS003[1]", target_address="0xS002"),
            ],
        ),
    ])

    weak_errors = _validate_vector_pointer(weak_trace)
    assert "ptrs should be marked as an array/container" in weak_errors
    assert "ptrs should not be marked as a pointer" in weak_errors
    assert _validate_vector_pointer(strong_trace) == []


def test_native_debug_smoke_requires_optional_pointer_member_edge():
    """Native smoke should prove optional<T*> value members render pointer edges."""
    from app.core.memory_model import ExecutionTrace, MemoryState, PointerEdge, StackFrame, StructMember, Variable
    from tools.native_debug_smoke import _validate_optional_pointer

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=5,
            source_code="*op.value() = 5;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="int", value="5", address="0xS001", is_pointer=False),
                Variable(
                    name="op",
                    type="std::optional<int*>",
                    value="{Value=0x000000aa0000efd0}",
                    address="0xS002",
                    is_pointer=False,
                    is_object=True,
                    class_name="optional<int>",
                    members=[StructMember(name="Value", type="std::remove_cv_t<value_type>", value="0x000000aa0000efd0", address="0xS002.Value")],
                ),
            ])],
            heap=[],
            edges=[],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=5,
            source_code="*op.value() = 5;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="int", value="5", address="0xS001", is_pointer=False),
                Variable(
                    name="op",
                    type="std::optional<int*>",
                    value="{value=0xS001}",
                    address="0xS002",
                    is_pointer=False,
                    is_object=True,
                    class_name="optional<int*>",
                    members=[StructMember(name="value", type="int*", value="0xS001", address="0xS002.Value")],
                ),
            ])],
            heap=[],
            edges=[PointerEdge(source_address="0xS002.Value", target_address="0xS001")],
        ),
    ])

    weak_errors = _validate_optional_pointer(weak_trace)
    assert "op class_name expected optional<int*>, got 'optional<int>'" in weak_errors
    assert "op member name expected value, got 'Value'" in weak_errors
    assert "op value member type expected int*, got 'std::remove_cv_t<value_type>'" in weak_errors
    assert "missing op.value -> a pointer edge" in weak_errors
    assert _validate_optional_pointer(strong_trace) == []


def test_native_debug_smoke_requires_optional_variant_object_member_edges():
    """Native smoke should prove optional/variant object values expose nested pointer edges."""
    from app.core.memory_model import ExecutionTrace, MemoryState, PointerEdge, StackFrame, StructMember, Variable
    from tools.native_debug_smoke import _validate_optional_variant_object_member_pointer

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=10,
            source_code="int done = first.value + maybe->value + get<Node>(either).value;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="first",
                    type="Node",
                    value="{value=6, next=nullptr}",
                    address="0xS001",
                    is_pointer=False,
                    is_object=True,
                    members=[
                        StructMember(name="value", type="int", value="6", address="0xS001.value"),
                        StructMember(name="next", type="Node*", value="nullptr", address="0xS001.next"),
                    ],
                ),
                Variable(
                    name="maybe",
                    type="std::optional<Node>",
                    value="{value={value=2, next=0x000000016fdfe6b0}}",
                    address="0xS002",
                    is_pointer=False,
                    is_object=True,
                    members=[StructMember(name="value", type="Node", value="{value=2, next=0x000000016fdfe6b0}", address="0xS002.Value")],
                ),
                Variable(
                    name="either",
                    type="std::variant<int,Node>",
                    value="{value={value=3, next=0x000000016fdfe6b0}}",
                    address="0xS003",
                    is_pointer=False,
                    is_object=True,
                    members=[StructMember(name="value", type="Node", value="{value=3, next=0x000000016fdfe6b0}", address="0xS003.Value")],
                ),
                Variable(name="done", type="int", value="11", address="0xS004", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=10,
            source_code="int done = first.value + maybe->value + get<Node>(either).value;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="first",
                    type="Node",
                    value="{value=6, next=nullptr}",
                    address="0xS001",
                    is_pointer=False,
                    is_object=True,
                    members=[
                        StructMember(name="value", type="int", value="6", address="0xS001.value"),
                        StructMember(name="next", type="Node*", value="nullptr", address="0xS001.next"),
                    ],
                ),
                Variable(
                    name="maybe",
                    type="std::optional<Node>",
                    value="{value={value=2, next=0xS001}}",
                    address="0xS002",
                    is_pointer=False,
                    is_object=True,
                    members=[StructMember(name="value", type="Node", value="{value=2, next=0xS001}", address="0xS002.Value")],
                ),
                Variable(
                    name="either",
                    type="std::variant<int,Node>",
                    value="{value={value=3, next=0xS001}}",
                    address="0xS003",
                    is_pointer=False,
                    is_object=True,
                    members=[StructMember(name="value", type="Node", value="{value=3, next=0xS001}", address="0xS003.Value")],
                ),
                Variable(name="done", type="int", value="11", address="0xS004", is_pointer=False),
            ])],
            heap=[],
            edges=[
                PointerEdge(source_address="0xS002.Value", target_address="0xS001"),
                PointerEdge(source_address="0xS003.Value", target_address="0xS001"),
            ],
        ),
    ])

    weak_errors = _validate_optional_variant_object_member_pointer(weak_trace)
    assert "maybe.value should not expose raw debugger addresses" in weak_errors
    assert "either.value should not expose raw debugger addresses" in weak_errors
    assert "missing maybe.value -> first pointer edge" in weak_errors
    assert "missing either.value -> first pointer edge" in weak_errors
    assert _validate_optional_variant_object_member_pointer(strong_trace) == []


def test_native_debug_smoke_requires_roadshow_native_demo_state():
    """Roadshow demo smoke should prove the real demo covers native debugger strengths."""
    from app.core.demo_examples import ROADSHOW_DEMO_CODE
    from app.core.memory_model import ArrayElement, ExecutionTrace, HeapBlock, MemoryState, PointerEdge, StackFrame, StructMember, Variable
    from tools.native_debug_smoke import CASES, _validate_roadshow_native_demo

    assert CASES["roadshow_native_demo"].code == ROADSHOW_DEMO_CODE

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=23,
            source_code="int done = first.value + second.value + sound;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="total", type="int", value="52", address="0xS001", is_pointer=False),
                Variable(name="focus", type="int*", value="0xS001", address="0xS002", is_pointer=True),
                Variable(
                    name="first",
                    type="Node",
                    value="{value=9, next=nullptr}",
                    address="0xS003",
                    is_pointer=False,
                    is_object=True,
                    members=[
                        StructMember(name="value", type="int", value="9", address="0xS003.value"),
                        StructMember(name="next", type="Node*", value="nullptr", address="0xS003.next"),
                    ],
                ),
                Variable(
                    name="second",
                    type="Node",
                    value="{value=2, next=0xS003}",
                    address="0xS004",
                    is_pointer=False,
                    is_object=True,
                    members=[
                        StructMember(name="value", type="int", value="2", address="0xS004.value"),
                        StructMember(name="next", type="Node*", value="0xS003", address="0xS004.next"),
                    ],
                ),
                Variable(name="nodes", type="vector<unique_ptr<Node>>", value="{[0]=0xH001}", address="0xS005", is_pointer=False, is_array=True),
                Variable(name="pet", type="unique_ptr<Animal>", value="0xH002", address="0xS006", is_pointer=True),
                Variable(name="sound", type="int", value="10", address="0xS007", is_pointer=False),
                Variable(name="done", type="int", value="21", address="0xS008", is_pointer=False),
            ])],
            heap=[],
            edges=[PointerEdge(source_address="0xS002", target_address="0xS001")],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=23,
            source_code="int done = first.value + second.value + sound;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="total", type="int", value="52", address="0xS001", is_pointer=False),
                Variable(name="focus", type="int*", value="0xS001", address="0xS002", is_pointer=True),
                Variable(
                    name="first",
                    type="Node",
                    value="{value=9, next=nullptr}",
                    address="0xS003",
                    is_pointer=False,
                    is_object=True,
                    members=[
                        StructMember(name="value", type="int", value="9", address="0xS003.value"),
                        StructMember(name="next", type="Node*", value="nullptr", address="0xS003.next"),
                    ],
                ),
                Variable(
                    name="second",
                    type="Node",
                    value="{value=2, next=0xS003}",
                    address="0xS004",
                    is_pointer=False,
                    is_object=True,
                    members=[
                        StructMember(name="value", type="int", value="2", address="0xS004.value"),
                        StructMember(name="next", type="Node*", value="0xS003", address="0xS004.next"),
                    ],
                ),
                Variable(
                    name="nodes",
                    type="vector<unique_ptr<Node>>",
                    value="{[0]=0xH001}",
                    address="0xS005",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(index=0, type="unique_ptr<Node>", value="0xH001", address="0xS005[0]"),
                    ],
                ),
                Variable(name="pet", type="unique_ptr<Animal>", value="0xH002", address="0xS006", is_pointer=True),
                Variable(name="sound", type="int", value="10", address="0xS007", is_pointer=False),
                Variable(
                    name="maybe",
                    type="optional<Node>",
                    value="{value={value=7, next=0xS003}}",
                    address="0xS008",
                    is_pointer=False,
                    is_object=True,
                    members=[StructMember(name="value", type="Node", value="{value=7, next=0xS003}", address="0xS008.Value")],
                ),
                Variable(
                    name="either",
                    type="variant<int, Node>",
                    value="{value={value=10, next=0xS004}}",
                    address="0xS009",
                    is_pointer=False,
                    is_object=True,
                    members=[StructMember(name="value", type="Node", value="{value=10, next=0xS004}", address="0xS009.Value")],
                ),
                Variable(name="done", type="int", value="21", address="0xS010", is_pointer=False),
            ])],
            heap=[
                HeapBlock(
                    address="0xH001",
                    type="Node",
                    value="{value=3, next=0xS004}",
                    is_object=True,
                    class_name="Node",
                    members=[
                        StructMember(name="value", type="int", value="3", address="0xH001.value"),
                        StructMember(name="next", type="Node*", value="0xS004", address="0xH001.next"),
                    ],
                ),
                HeapBlock(
                    address="0xH002",
                    type="Dog",
                    value="{Animal={age=4}, bones=6}",
                    is_object=True,
                    class_name="Dog",
                    base_classes=["Animal"],
                    virtual_methods=["speak()"],
                    members=[
                        StructMember(name="Animal", type="Animal", value="{age=4}", address="0xH002.Animal"),
                        StructMember(name="bones", type="int", value="6", address="0xH002.bones"),
                    ],
                ),
            ],
            edges=[
                PointerEdge(source_address="0xS002", target_address="0xS001"),
                PointerEdge(source_address="0xS004.next", target_address="0xS003"),
                PointerEdge(source_address="0xS005[0]", target_address="0xH001"),
                PointerEdge(source_address="0xS006", target_address="0xH002"),
                PointerEdge(source_address="0xS008.Value", target_address="0xS003"),
                PointerEdge(source_address="0xS009.Value", target_address="0xS004"),
                PointerEdge(source_address="0xH001.next", target_address="0xS004"),
            ],
        ),
    ])

    weak_errors = _validate_roadshow_native_demo(weak_trace)
    assert any("nodes should expose one unique_ptr heap target" in error for error in weak_errors)
    assert "missing heap Dog for pet target 0xH002" in weak_errors
    assert "missing maybe object" in weak_errors
    assert "missing either object" in weak_errors
    assert _validate_roadshow_native_demo(strong_trace) == []


def test_native_debug_smoke_requires_stl_container_breadth():
    """Native smoke should cover common STL sequence/set/hash containers."""
    from app.core.memory_model import ArrayElement, ExecutionTrace, MemoryState, PointerEdge, StackFrame, Variable
    from tools.native_debug_smoke import (
        CASES,
        _validate_deque,
        _validate_list_pointer,
        _validate_set_pointer,
        _validate_unordered_map_pointer,
        _validate_vector_string,
    )

    for case_name in (
        "deque_int",
        "list_pointer_stack",
        "set_pointer_stack",
        "unordered_map_pointer",
        "vector_string",
    ):
        assert case_name in CASES

    weak_deque = ExecutionTrace(steps=[
        MemoryState(
            line_number=7,
            source_code="xs[2] = 8;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="xs", type="deque<int>", value="{[0]=0, [1]=1, [2]=8}", address="0xS001", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        )
    ])
    strong_deque = ExecutionTrace(steps=[
        MemoryState(
            line_number=7,
            source_code="xs[2] = 8;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="xs",
                    type="deque<int>",
                    value="{[0]=0, [1]=1, [2]=8}",
                    address="0xS001",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(index=0, type="int", value="0", address="0xS001[0]"),
                        ArrayElement(index=1, type="int", value="1", address="0xS001[1]"),
                        ArrayElement(index=2, type="int", value="8", address="0xS001[2]"),
                    ],
                ),
            ])],
            heap=[],
            edges=[],
        )
    ])
    assert "deque xs should be marked as an array/container" in _validate_deque(weak_deque)
    assert _validate_deque(strong_deque) == []

    strong_list = ExecutionTrace(steps=[
        MemoryState(
            line_number=10,
            source_code="**it = 9;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="int", value="1", address="0xS001", is_pointer=False),
                Variable(name="b", type="int", value="9", address="0xS002", is_pointer=False),
                Variable(
                    name="xs",
                    type="list<int*>",
                    value="{[0]=0xS001, [1]=0xS002}",
                    address="0xS003",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(index=0, type="int*", value="0xS001", address="0xS003[0]"),
                        ArrayElement(index=1, type="int*", value="0xS002", address="0xS003[1]"),
                    ],
                ),
            ])],
            heap=[],
            edges=[
                PointerEdge(source_address="0xS003[0]", target_address="0xS001"),
                PointerEdge(source_address="0xS003[1]", target_address="0xS002"),
            ],
        )
    ])
    weak_list = strong_list.model_copy(deep=True)
    weak_list.steps[0].edges = []
    assert any("missing list pointer element edges" in error for error in _validate_list_pointer(weak_list))
    assert _validate_list_pointer(strong_list) == []

    strong_set = ExecutionTrace(steps=[
        MemoryState(
            line_number=8,
            source_code="int count = xs.size();",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="int", value="1", address="0xS001", is_pointer=False),
                Variable(name="b", type="int", value="2", address="0xS002", is_pointer=False),
                Variable(
                    name="xs",
                    type="set<int*>",
                    value="{[0]=0xS002, [1]=0xS001}",
                    address="0xS003",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(index=0, type="int*", value="0xS002", address="0xS003[0]"),
                        ArrayElement(index=1, type="int*", value="0xS001", address="0xS003[1]"),
                    ],
                ),
            ])],
            heap=[],
            edges=[
                PointerEdge(source_address="0xS003[0]", target_address="0xS002"),
                PointerEdge(source_address="0xS003[1]", target_address="0xS001"),
            ],
        )
    ])
    weak_set = strong_set.model_copy(deep=True)
    weak_set.steps[0].stack[0].variables[-1].elements = []
    assert any("set pointer elements expected" in error for error in _validate_set_pointer(weak_set))
    assert _validate_set_pointer(strong_set) == []

    strong_unordered_map = ExecutionTrace(steps=[
        MemoryState(
            line_number=9,
            source_code='*m["b"] = 9;',
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="int", value="1", address="0xS001", is_pointer=False),
                Variable(name="b", type="int", value="9", address="0xS002", is_pointer=False),
                Variable(
                    name="m",
                    type="unordered_map<string,int*>",
                    value="{[0]={first=b, second=0xS002}, [1]={first=a, second=0xS001}}",
                    address="0xS003",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(index=0, type="pair<string,int*>", value="{first=b, second=0xS002}", address="0xS003[0]"),
                        ArrayElement(index=1, type="pair<string,int*>", value="{first=a, second=0xS001}", address="0xS003[1]"),
                    ],
                ),
            ])],
            heap=[],
            edges=[
                PointerEdge(source_address="0xS003[0]", target_address="0xS002"),
                PointerEdge(source_address="0xS003[1]", target_address="0xS001"),
            ],
        )
    ])
    weak_unordered_map = strong_unordered_map.model_copy(deep=True)
    weak_unordered_map.steps[0].edges = []
    assert any("missing unordered_map entry edge" in error for error in _validate_unordered_map_pointer(weak_unordered_map))
    assert _validate_unordered_map_pointer(strong_unordered_map) == []

    weak_vector_string = ExecutionTrace(steps=[
        MemoryState(
            line_number=8,
            source_code="int length = words[1].size();",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="words",
                    type="vector<string>",
                    value="{size=3}",
                    address="0xS001",
                    is_pointer=False,
                    is_object=True,
                    members=[],
                ),
                Variable(name="length", type="int", value="5", address="0xS002", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        )
    ])
    strong_vector_string = ExecutionTrace(steps=[
        MemoryState(
            line_number=8,
            source_code="int length = words[1].size();",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="words",
                    type="vector<string>",
                    value="{[0]=one, [1]=three, [2]=two}",
                    address="0xS001",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(index=0, type="string", value="one", address="0xS001[0]"),
                        ArrayElement(index=1, type="string", value="three", address="0xS001[1]"),
                        ArrayElement(index=2, type="string", value="two", address="0xS001[2]"),
                    ],
                ),
                Variable(name="length", type="int", value="5", address="0xS002", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        )
    ])
    weak_vector_string_errors = _validate_vector_string(weak_vector_string)
    assert "words should be marked as an array/container" in weak_vector_string_errors
    assert "words should show string elements instead of implementation members" in weak_vector_string_errors
    assert _validate_vector_string(strong_vector_string) == []


def test_native_debug_smoke_requires_map_pointer_entry_edges():
    """Native smoke should prove map<string, int*> entries render pointer edges."""
    from app.core.memory_model import ArrayElement, ExecutionTrace, MemoryState, PointerEdge, StackFrame, Variable
    from tools.native_debug_smoke import _validate_map_pointer

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=9,
            source_code='*m["b"] = 9;',
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="int", value="1", address="0xS001", is_pointer=False),
                Variable(name="b", type="int", value="9", address="0xS002", is_pointer=False),
                Variable(
                    name="m",
                    type="std::map<string,int*>",
                    value="{[0]={first=a, second=0x000000aa0000efd0}, [1]={first=b, second=0x000000aa0000efd4}}",
                    address="0xS003",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(index=0, type="std::pair<string,int*>", value="{first=a, second=0x000000aa0000efd0}", address="0xS003[0]"),
                        ArrayElement(index=1, type="std::pair<string,int*>", value="{first=b, second=0x000000aa0000efd4}", address="0xS003[1]"),
                    ],
                ),
            ])],
            heap=[],
            edges=[],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=9,
            source_code='*m["b"] = 9;',
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="int", value="1", address="0xS001", is_pointer=False),
                Variable(name="b", type="int", value="9", address="0xS002", is_pointer=False),
                Variable(
                    name="m",
                    type="std::map<string,int*>",
                    value="{[0]={first=a, second=0xS001}, [1]={first=b, second=0xS002}}",
                    address="0xS003",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(index=0, type="std::pair<string,int*>", value="{first=a, second=0xS001}", address="0xS003[0]"),
                        ArrayElement(index=1, type="std::pair<string,int*>", value="{first=b, second=0xS002}", address="0xS003[1]"),
                    ],
                ),
            ])],
            heap=[],
            edges=[
                PointerEdge(source_address="0xS003[0]", target_address="0xS001"),
                PointerEdge(source_address="0xS003[1]", target_address="0xS002"),
            ],
        ),
    ])

    weak_errors = _validate_map_pointer(weak_trace)
    assert any("m missing a pointer entry" in error for error in weak_errors)
    assert any("m missing b pointer entry" in error for error in weak_errors)
    assert any("missing map entry pointer edges" in error for error in weak_errors)
    assert _validate_map_pointer(strong_trace) == []


def test_native_debug_smoke_requires_map_unique_ptr_heap_entry():
    """Native smoke should prove map<string, unique_ptr<int>> entries render valued heap blocks."""
    from app.core.memory_model import ArrayElement, ExecutionTrace, HeapBlock, MemoryState, PointerEdge, StackFrame, Variable
    from tools.native_debug_smoke import _validate_map_unique_ptr

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=7,
            source_code='*m["a"] = 8;',
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="m",
                    type="std::map<string,unique_ptr<int>>",
                    value="{[0]={first=a, second=0xH001}}",
                    address="0xS001",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(
                            index=0,
                            type="std::pair<string,unique_ptr<int>>",
                            value="{first=a, second=0xH001}",
                            address="0xS001[0]",
                        ),
                    ],
                ),
            ])],
            heap=[],
            edges=[PointerEdge(source_address="0xS001[0]", target_address="0xH001")],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=7,
            source_code='*m["a"] = 8;',
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="m",
                    type="std::map<string,unique_ptr<int>>",
                    value="{[0]={first=a, second=0xH001}}",
                    address="0xS001",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(
                            index=0,
                            type="std::pair<string,unique_ptr<int>>",
                            value="{first=a, second=0xH001}",
                            address="0xS001[0]",
                        ),
                    ],
                ),
            ])],
            heap=[HeapBlock(address="0xH001", type="int", value="8")],
            edges=[PointerEdge(source_address="0xS001[0]", target_address="0xH001")],
        ),
    ])

    weak_errors = _validate_map_unique_ptr(weak_trace)
    assert any("missing heap block for map unique_ptr target" in error for error in weak_errors)
    assert _validate_map_unique_ptr(strong_trace) == []


def test_native_debug_smoke_requires_map_unique_ptr_object_heap_entry():
    """Native smoke should prove map<string, unique_ptr<Object>> entries render object heap blocks."""
    from app.core.memory_model import ArrayElement, ExecutionTrace, HeapBlock, MemoryState, PointerEdge, StackFrame, StructMember, Variable
    from tools.native_debug_smoke import _validate_map_unique_ptr_object

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=9,
            source_code='m["n"]->next->value = 6;',
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="first",
                    type="Node",
                    value="{value=6, next=nullptr}",
                    address="0xS001",
                    is_pointer=False,
                    is_object=True,
                    class_name="Node",
                    members=[
                        StructMember(name="value", type="int", value="6", address="0xS001.value"),
                        StructMember(name="next", type="Node*", value="nullptr", address="0xS001.next"),
                    ],
                ),
                Variable(
                    name="m",
                    type="std::map<string,unique_ptr<Node>>",
                    value="{[0]={first=n, second=0xH001}}",
                    address="0xS002",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(
                            index=0,
                            type="std::pair<string,unique_ptr<Node>>",
                            value="{first=n, second=0xH001}",
                            address="0xS002[0]",
                        ),
                    ],
                ),
            ])],
            heap=[HeapBlock(address="0xH001", type="Node", value="{value=2, next=0xS001}")],
            edges=[PointerEdge(source_address="0xS002[0]", target_address="0xH001")],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=9,
            source_code='m["n"]->next->value = 6;',
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="first",
                    type="Node",
                    value="{value=6, next=nullptr}",
                    address="0xS001",
                    is_pointer=False,
                    is_object=True,
                    class_name="Node",
                    members=[
                        StructMember(name="value", type="int", value="6", address="0xS001.value"),
                        StructMember(name="next", type="Node*", value="nullptr", address="0xS001.next"),
                    ],
                ),
                Variable(
                    name="m",
                    type="std::map<string,unique_ptr<Node>>",
                    value="{[0]={first=n, second=0xH001}}",
                    address="0xS002",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(
                            index=0,
                            type="std::pair<string,unique_ptr<Node>>",
                            value="{first=n, second=0xH001}",
                            address="0xS002[0]",
                        ),
                    ],
                ),
            ])],
            heap=[HeapBlock(
                address="0xH001",
                type="Node",
                value="{value=2, next=0xS001}",
                is_object=True,
                class_name="Node",
                members=[
                    StructMember(name="value", type="int", value="2", address="0xH001.value"),
                    StructMember(name="next", type="Node*", value="0xS001", address="0xH001.next"),
                ],
            )],
            edges=[
                PointerEdge(source_address="0xS002[0]", target_address="0xH001"),
                PointerEdge(source_address="0xH001.next", target_address="0xS001"),
            ],
        ),
    ])

    weak_errors = _validate_map_unique_ptr_object(weak_trace)
    assert any("map unique_ptr target should be Node object" in error for error in weak_errors)
    assert any("heap Node.next should target first" in error for error in weak_errors)
    assert _validate_map_unique_ptr_object(strong_trace) == []


def test_native_debug_smoke_requires_polymorphic_smart_pointer_container_heap():
    """Native smoke should prove smart pointer containers preserve derived heap metadata."""
    from app.core.memory_model import ArrayElement, ExecutionTrace, HeapBlock, MemoryState, PointerEdge, StackFrame, StructMember, Variable
    from tools.native_debug_smoke import _validate_map_polymorphic_shared_ptr, _validate_vector_polymorphic_unique_ptr

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=8,
            source_code="int sound = animals[0]->speak();",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="animals",
                    type="std::vector<std::unique_ptr<Animal>>",
                    value="{[0]=0xH001}",
                    address="0xS001",
                    is_pointer=False,
                    is_array=True,
                    elements=[ArrayElement(index=0, type="std::unique_ptr<Animal>", value="0xH001", address="0xS001[0]")],
                ),
                Variable(name="sound", type="int", value="7", address="0xS002", is_pointer=False),
            ])],
            heap=[HeapBlock(
                address="0xH001",
                type="Animal",
                value="{Animal={age=3}, bones=4}",
                is_object=True,
                class_name="Animal",
                members=[
                    StructMember(name="Animal", type="", value="{age=3}", address="0xH001.Animal"),
                    StructMember(name="bones", type="", value="4", address="0xH001.bones"),
                ],
            )],
            edges=[PointerEdge(source_address="0xS001[0]", target_address="0xH001")],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=8,
            source_code="int sound = animals[0]->speak();",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="animals",
                    type="std::vector<std::unique_ptr<Animal>>",
                    value="{[0]=0xH001}",
                    address="0xS001",
                    is_pointer=False,
                    is_array=True,
                    elements=[ArrayElement(index=0, type="std::unique_ptr<Animal>", value="0xH001", address="0xS001[0]")],
                ),
                Variable(name="sound", type="int", value="7", address="0xS002", is_pointer=False),
            ])],
            heap=[HeapBlock(
                address="0xH001",
                type="Dog",
                value="{Animal={age=3}, bones=4}",
                is_object=True,
                class_name="Dog",
                base_classes=["Animal"],
                virtual_methods=["speak()"],
                members=[
                    StructMember(name="Animal", type="Animal", value="{age=3}", address="0xH001.Animal"),
                    StructMember(name="bones", type="int", value="4", address="0xH001.bones"),
                ],
            )],
            edges=[PointerEdge(source_address="0xS001[0]", target_address="0xH001")],
        ),
    ])

    weak_errors = _validate_vector_polymorphic_unique_ptr(weak_trace)
    assert any("class_name expected Dog" in error for error in weak_errors)
    assert any("should list Animal as a base class" in error for error in weak_errors)
    assert any("should list speak() as a virtual method" in error for error in weak_errors)
    assert _validate_vector_polymorphic_unique_ptr(strong_trace) == []
    assert _validate_map_polymorphic_shared_ptr(strong_trace) == []


def test_native_debug_smoke_requires_vector_object_elements():
    """Native smoke should prove STL containers can preserve object element members."""
    from app.core.memory_model import ArrayElement, ExecutionTrace, MemoryState, StackFrame, Variable
    from tools.native_debug_smoke import _validate_vector_object

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=5,
            source_code="nodes[1].weight = 4.5;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="nodes",
                    type="vector<Node>",
                    value="{[0]=Node, [1]=Node}",
                    address="0xS001",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(index=0, value="Node"),
                        ArrayElement(index=1, value="Node"),
                    ],
                ),
            ])],
            heap=[],
            edges=[],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=5,
            source_code="nodes[1].weight = 4.5;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="nodes",
                    type="vector<Node>",
                    value="{[0]={id=1, weight=1.5}, [1]={id=2, weight=4.5}}",
                    address="0xS001",
                    is_pointer=False,
                    is_array=True,
                    elements=[
                        ArrayElement(index=0, value="{id=1, weight=1.5}"),
                        ArrayElement(index=1, value="{id=2, weight=4.5}"),
                    ],
                ),
            ])],
            heap=[],
            edges=[],
        ),
    ])

    weak_errors = _validate_vector_object(weak_trace)
    assert any("nodes missing first object element" in error for error in weak_errors)
    assert any("nodes missing updated second object element" in error for error in weak_errors)
    assert _validate_vector_object(strong_trace) == []


def test_native_debug_smoke_forwards_stdin_to_debug_executor():
    """Native smoke should validate input-aware debugger runs, not only no-stdin code."""
    from app.core.memory_model import ExecutionTrace, MemoryState, StackFrame, Variable
    from tools.native_debug_smoke import CASES, _run_case

    captured = {}

    class FakeDebugExecutor:
        def __init__(self, preferred_backend=None):
            captured["backend"] = preferred_backend

        def run_code(self, code, stdin_text=""):
            captured["code"] = code
            captured["stdin"] = stdin_text
            return ExecutionTrace(steps=[
                MemoryState(
                    line_number=6,
                    source_code="int sum = x + y;",
                    stack=[StackFrame(frame_name="main", variables=[
                        Variable(name="x", type="int", value="7", address="0xS001", is_pointer=False),
                        Variable(name="y", type="int", value="5", address="0xS002", is_pointer=False),
                        Variable(name="sum", type="int", value="12", address="0xS003", is_pointer=False),
                    ])],
                    heap=[],
                    edges=[],
                ),
            ])

    with patch("tools.native_debug_smoke.DebugExecutor", FakeDebugExecutor):
        result = _run_case(CASES["stdin_sum"], "msvc-pdb", render=False)

    assert result["ok"] is True
    assert captured["backend"] == "msvc-pdb"
    assert captured["stdin"] == "7 5\n"
    assert "cin >> x >> y" in captured["code"]


def test_native_debug_smoke_requires_call_stack_state():
    """Native smoke should prove user-function frames are visible, not only final result."""
    from app.core.memory_model import ExecutionTrace, MemoryState, StackFrame, Variable
    from tools.native_debug_smoke import _validate_call_stack

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=5,
            source_code="int result = square(3);",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="result", type="int", value="9", address="0xS001", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=2,
            source_code="int y = x * x;",
            stack=[
                StackFrame(frame_name="square", variables=[
                    Variable(name="x", type="int", value="3", address="0xS001", is_pointer=False),
                    Variable(name="y", type="int", value="9", address="0xS002", is_pointer=False),
                ]),
                StackFrame(frame_name="main", variables=[]),
            ],
            heap=[],
            edges=[],
        ),
        MemoryState(
            line_number=5,
            source_code="int result = square(3);",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="result", type="int", value="9", address="0xS003", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
    ])

    assert "missing observed square -> main call stack" in _validate_call_stack(weak_trace)
    assert _validate_call_stack(strong_trace) == []


def test_native_debug_smoke_requires_reference_and_stack_pointer_state():
    """Native smoke should distinguish references from pointers and prove stack edges."""
    from app.core.memory_model import ExecutionTrace, MemoryState, PointerEdge, StackFrame, Variable
    from tools.native_debug_smoke import _validate_reference_stack_pointer

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=5,
            source_code="*p = 11;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="int", value="11", address="0xS001", is_pointer=False),
                Variable(
                    name="r",
                    type="int&",
                    value="0xS001",
                    address="0xS002",
                    is_pointer=True,
                    is_reference=True,
                ),
                Variable(name="p", type="int*", value="0xS001", address="0xS003", is_pointer=True),
            ])],
            heap=[],
            edges=[],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=5,
            source_code="*p = 11;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="int", value="11", address="0xS001", is_pointer=False),
                Variable(
                    name="r",
                    type="int&",
                    value="0xS001",
                    address="0xS002",
                    is_pointer=False,
                    is_reference=True,
                ),
                Variable(name="p", type="int*", value="0xS001", address="0xS003", is_pointer=True),
            ])],
            heap=[],
            edges=[PointerEdge(source_address="0xS003", target_address="0xS001")],
        ),
    ])

    weak_errors = _validate_reference_stack_pointer(weak_trace)
    assert "r should not be marked as a pointer" in weak_errors
    assert "missing p -> a stack pointer edge" in weak_errors
    assert _validate_reference_stack_pointer(strong_trace) == []


def test_native_debug_smoke_requires_double_pointer_stack_state():
    """Native smoke should prove double pointers form stack-to-stack edge chains."""
    from app.core.memory_model import ExecutionTrace, MemoryState, PointerEdge, StackFrame, Variable
    from tools.native_debug_smoke import _validate_double_pointer_stack

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=1,
            source_code="int a = 1;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="int", value="1", address="0xS001", is_pointer=False),
                Variable(name="pp", type="int**", value="0xS002", address="0xS003", is_pointer=True),
            ])],
            heap=[],
            edges=[],
        ),
        MemoryState(
            line_number=4,
            source_code="**pp = 7;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="int", value="7", address="0xS001", is_pointer=False),
                Variable(name="p", type="int*", value="0xS001", address="0xS002", is_pointer=True),
                Variable(name="pp", type="int**", value="0xS002", address="0xS003", is_pointer=True),
            ])],
            heap=[],
            edges=[PointerEdge(source_address="0xS002", target_address="0xS001")],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=1,
            source_code="int a = 1;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="int", value="1", address="0xS001", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
        MemoryState(
            line_number=2,
            source_code="int *p = &a;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="int", value="1", address="0xS001", is_pointer=False),
                Variable(name="p", type="int*", value="0xS001", address="0xS002", is_pointer=True),
            ])],
            heap=[],
            edges=[PointerEdge(source_address="0xS002", target_address="0xS001")],
        ),
        MemoryState(
            line_number=4,
            source_code="**pp = 7;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="a", type="int", value="7", address="0xS001", is_pointer=False),
                Variable(name="p", type="int*", value="0xS001", address="0xS002", is_pointer=True),
                Variable(name="pp", type="int**", value="0xS002", address="0xS003", is_pointer=True),
            ])],
            heap=[],
            edges=[
                PointerEdge(source_address="0xS002", target_address="0xS001"),
                PointerEdge(source_address="0xS003", target_address="0xS002"),
            ],
        ),
    ])

    weak_errors = _validate_double_pointer_stack(weak_trace)
    assert any("future pointer appeared on int a step" in error for error in weak_errors)
    assert "missing pp -> p stack pointer edge" in weak_errors
    assert _validate_double_pointer_stack(strong_trace) == []


def test_native_debug_smoke_requires_member_pointer_linked_list_state():
    """Native smoke should prove object member pointers render as real edges."""
    from app.core.memory_model import ExecutionTrace, MemoryState, PointerEdge, StackFrame, StructMember, Variable
    from tools.native_debug_smoke import _validate_member_pointer_linked_list

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=5,
            source_code="head->next->value = 3;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="first",
                    type="Node",
                    value="{value=3, next=nullptr}",
                    address="0xS001",
                    is_pointer=False,
                    is_object=True,
                    members=[
                        StructMember(name="value", type="int", value="3"),
                        StructMember(name="next", type="Node*", value="nullptr"),
                    ],
                ),
                Variable(
                    name="second",
                    type="Node",
                    value="{value=2, next=0xS001}",
                    address="0xS002",
                    is_pointer=False,
                    is_object=True,
                    members=[
                        StructMember(name="value", type="int", value="2"),
                        StructMember(name="next", type="Node*", value="0xS001"),
                    ],
                ),
                Variable(name="head", type="Node*", value="0xS002", address="0xS003", is_pointer=True),
            ])],
            heap=[],
            edges=[PointerEdge(source_address="0xS003", target_address="0xS002")],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=5,
            source_code="head->next->value = 3;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="first",
                    type="Node",
                    value="{value=3, next=nullptr}",
                    address="0xS001",
                    is_pointer=False,
                    is_object=True,
                    members=[
                        StructMember(name="value", type="int", value="3", address="0xS001.value"),
                        StructMember(name="next", type="Node*", value="nullptr", address="0xS001.next"),
                    ],
                ),
                Variable(
                    name="second",
                    type="Node",
                    value="{value=2, next=0xS001}",
                    address="0xS002",
                    is_pointer=False,
                    is_object=True,
                    members=[
                        StructMember(name="value", type="int", value="2", address="0xS002.value"),
                        StructMember(name="next", type="Node*", value="0xS001", address="0xS002.next"),
                    ],
                ),
                Variable(name="head", type="Node*", value="0xS002", address="0xS003", is_pointer=True),
            ])],
            heap=[],
            edges=[
                PointerEdge(source_address="0xS003", target_address="0xS002"),
                PointerEdge(source_address="0xS002.next", target_address="0xS001"),
            ],
        ),
    ])

    weak_errors = _validate_member_pointer_linked_list(weak_trace)
    assert "second.next should have a member source address" in weak_errors
    assert _validate_member_pointer_linked_list(strong_trace) == []


def test_native_debug_smoke_requires_heap_member_pointer_linked_list_state():
    """Native smoke should preserve heap node member pointers across delete."""
    from app.core.memory_model import ExecutionTrace, HeapBlock, MemoryState, PointerEdge, StackFrame, StructMember, Variable
    from tools.native_debug_smoke import _validate_heap_member_pointer_linked_list

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=6,
            source_code="delete first;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="first", type="Node*", value="0xH001", address="0xS001", is_pointer=True),
                Variable(name="second", type="Node*", value="0xH002", address="0xS002", is_pointer=True),
            ])],
            heap=[
                HeapBlock(
                    address="0xH001",
                    type="Node",
                    value="{value=4, next=nullptr}",
                    is_freed=True,
                    is_object=True,
                    members=[
                        StructMember(name="value", type="int", value="4", address="0xH001.value"),
                        StructMember(name="next", type="Node*", value="nullptr", address="0xH001.next"),
                    ],
                ),
                HeapBlock(
                    address="0xH002",
                    type="Node",
                    value="{value=2, next=0xH003}",
                    is_freed=True,
                    is_object=True,
                    members=[
                        StructMember(name="value", type="int", value="2", address="0xH002.value"),
                        StructMember(name="next", type="Node*", value="0xH003", address="0xH002.next"),
                    ],
                ),
            ],
            edges=[
                PointerEdge(source_address="0xS001", target_address="0xH001", is_dangling=True),
                PointerEdge(source_address="0xS002", target_address="0xH002", is_dangling=True),
                PointerEdge(source_address="0xH002.next", target_address="0xH003", is_dangling=False),
            ],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=6,
            source_code="delete first;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="first", type="Node*", value="0xH001", address="0xS001", is_pointer=True),
                Variable(name="second", type="Node*", value="0xH002", address="0xS002", is_pointer=True),
            ])],
            heap=[
                HeapBlock(
                    address="0xH001",
                    type="Node",
                    value="{value=4, next=nullptr}",
                    is_freed=True,
                    is_object=True,
                    members=[
                        StructMember(name="value", type="int", value="4", address="0xH001.value"),
                        StructMember(name="next", type="Node*", value="nullptr", address="0xH001.next"),
                    ],
                ),
                HeapBlock(
                    address="0xH002",
                    type="Node",
                    value="{value=2, next=0xH001}",
                    is_freed=True,
                    is_object=True,
                    members=[
                        StructMember(name="value", type="int", value="2", address="0xH002.value"),
                        StructMember(name="next", type="Node*", value="0xH001", address="0xH002.next"),
                    ],
                ),
            ],
            edges=[
                PointerEdge(source_address="0xS001", target_address="0xH001", is_dangling=True),
                PointerEdge(source_address="0xS002", target_address="0xH002", is_dangling=True),
                PointerEdge(source_address="0xH002.next", target_address="0xH001", is_dangling=True),
            ],
        ),
    ])

    weak_errors = _validate_heap_member_pointer_linked_list(weak_trace)
    assert any("second heap next should still target first heap" in error for error in weak_errors)
    assert any("missing dangling second heap next -> first heap edge" in error for error in weak_errors)
    assert _validate_heap_member_pointer_linked_list(strong_trace) == []


def test_native_debug_smoke_requires_recursive_call_stack_state():
    """Native smoke should prove recursion exposes nested stack frames."""
    from app.core.memory_model import ExecutionTrace, MemoryState, StackFrame, Variable
    from tools.native_debug_smoke import _validate_recursive_call_stack

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=6,
            source_code="int result = fact(3);",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="result", type="int", value="6", address="0xS001", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=3,
            source_code="int sub = fact(n - 1);",
            stack=[
                StackFrame(frame_name="fact", variables=[
                    Variable(name="n", type="int", value="1", address="0xS001", is_pointer=False),
                ]),
                StackFrame(frame_name="fact(2)", variables=[
                    Variable(name="n", type="int", value="2", address="0xS002", is_pointer=False),
                ]),
                StackFrame(frame_name="fact(3)", variables=[
                    Variable(name="n", type="int", value="3", address="0xS003", is_pointer=False),
                ]),
                StackFrame(frame_name="main", variables=[]),
            ],
            heap=[],
            edges=[],
        ),
        MemoryState(
            line_number=6,
            source_code="int result = fact(3);",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="result", type="int", value="6", address="0xS004", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
    ])

    weak_errors = _validate_recursive_call_stack(weak_trace)
    assert "missing observed recursive fact -> fact -> fact -> main call stack" in weak_errors
    assert _validate_recursive_call_stack(strong_trace) == []


def test_native_debug_smoke_requires_recursive_tree_heap_closure():
    """Native smoke should prove recursive tree programs keep all heap child nodes visible."""
    from app.core.memory_model import ExecutionTrace, HeapBlock, MemoryState, PointerEdge, StackFrame, StructMember, Variable
    from tools.native_debug_smoke import _validate_recursive_tree_heap

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=5,
            source_code="int left = sum(n->left);",
            stack=[
                StackFrame(frame_name="sum", variables=[Variable(name="n", type="Node*", value="0xH002", address="0xS002", is_pointer=True)]),
                StackFrame(frame_name="sum(2)", variables=[Variable(name="n", type="Node*", value="0xH001", address="0xS003", is_pointer=True)]),
                StackFrame(frame_name="sum(3)", variables=[Variable(name="n", type="Node*", value="nullptr", address="0xS005", is_pointer=True)]),
                StackFrame(frame_name="main", variables=[Variable(name="root", type="Node*", value="0xH001", address="0xS001", is_pointer=True)]),
            ],
            heap=[],
            edges=[],
        ),
        MemoryState(
            line_number=10,
            source_code="int total = sum(root);",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="root", type="Node*", value="0xH001", address="0xS001", is_pointer=True),
                Variable(name="total", type="int", value="6", address="0xS004", is_pointer=False),
            ])],
            heap=[HeapBlock(
                address="0xH001",
                type="Node",
                value="{value=1, left=0xH002, right=0xH003}",
                is_object=True,
                class_name="Node",
                members=[
                    StructMember(name="value", type="int", value="1", address="0xH001.value"),
                    StructMember(name="left", type="Node*", value="0xH002", address="0xH001.left"),
                    StructMember(name="right", type="Node*", value="0xH003", address="0xH001.right"),
                ],
            )],
            edges=[
                PointerEdge(source_address="0xS001", target_address="0xH001"),
                PointerEdge(source_address="0xH001.left", target_address="0xH002"),
                PointerEdge(source_address="0xH001.right", target_address="0xH003"),
            ],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=5,
            source_code="int left = sum(n->left);",
            stack=[
                StackFrame(frame_name="sum", variables=[Variable(name="n", type="Node*", value="0xH002", address="0xS002", is_pointer=True)]),
                StackFrame(frame_name="sum(2)", variables=[Variable(name="n", type="Node*", value="0xH001", address="0xS003", is_pointer=True)]),
                StackFrame(frame_name="sum(3)", variables=[Variable(name="n", type="Node*", value="nullptr", address="0xS005", is_pointer=True)]),
                StackFrame(frame_name="main", variables=[Variable(name="root", type="Node*", value="0xH001", address="0xS001", is_pointer=True)]),
            ],
            heap=[],
            edges=[],
        ),
        MemoryState(
            line_number=10,
            source_code="int total = sum(root);",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="root", type="Node*", value="0xH001", address="0xS001", is_pointer=True),
                Variable(name="total", type="int", value="6", address="0xS004", is_pointer=False),
            ])],
            heap=[
                HeapBlock(
                    address="0xH001",
                    type="Node",
                    value="{value=1, left=0xH002, right=0xH003}",
                    is_object=True,
                    class_name="Node",
                    members=[
                        StructMember(name="value", type="int", value="1", address="0xH001.value"),
                        StructMember(name="left", type="Node*", value="0xH002", address="0xH001.left"),
                        StructMember(name="right", type="Node*", value="0xH003", address="0xH001.right"),
                    ],
                ),
                HeapBlock(
                    address="0xH002",
                    type="Node",
                    value="{value=2, left=nullptr, right=nullptr}",
                    is_object=True,
                    class_name="Node",
                    members=[
                        StructMember(name="value", type="int", value="2", address="0xH002.value"),
                        StructMember(name="left", type="Node*", value="nullptr", address="0xH002.left"),
                        StructMember(name="right", type="Node*", value="nullptr", address="0xH002.right"),
                    ],
                ),
                HeapBlock(
                    address="0xH003",
                    type="Node",
                    value="{value=3, left=nullptr, right=nullptr}",
                    is_object=True,
                    class_name="Node",
                    members=[
                        StructMember(name="value", type="int", value="3", address="0xH003.value"),
                        StructMember(name="left", type="Node*", value="nullptr", address="0xH003.left"),
                        StructMember(name="right", type="Node*", value="nullptr", address="0xH003.right"),
                    ],
                ),
            ],
            edges=[
                PointerEdge(source_address="0xS001", target_address="0xH001"),
                PointerEdge(source_address="0xH001.left", target_address="0xH002"),
                PointerEdge(source_address="0xH001.right", target_address="0xH003"),
            ],
        ),
    ])

    weak_errors = _validate_recursive_tree_heap(weak_trace)
    assert any("missing left child heap block" in error for error in weak_errors)
    assert any("missing right child heap block" in error for error in weak_errors)
    assert _validate_recursive_tree_heap(strong_trace) == []


def test_native_debug_smoke_requires_deleted_tree_child_objects():
    """Native smoke should keep leaked child objects visible after deleting a tree root."""
    from app.core.memory_model import ExecutionTrace, HeapBlock, MemoryState, PointerEdge, StackFrame, StructMember, Variable
    from tools.native_debug_smoke import _validate_deleted_tree_keeps_child_objects

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=4,
            source_code="int after = 9;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="root", type="Node*", value="0xH001", address="0xS001", is_pointer=True),
                Variable(name="after", type="int", value="9", address="0xS002", is_pointer=False),
            ])],
            heap=[
                HeapBlock(
                    address="0xH001",
                    type="Node",
                    value="{value=1, left=0xH002, right=0xH003}",
                    is_freed=True,
                    is_object=True,
                    class_name="Node",
                    members=[
                        StructMember(name="value", type="int", value="1", address="0xH001.value"),
                        StructMember(name="left", type="Node*", value="0xH002", address="0xH001.left"),
                        StructMember(name="right", type="Node*", value="0xH003", address="0xH001.right"),
                    ],
                ),
                HeapBlock(address="0xH002", type="unknown", value=""),
                HeapBlock(address="0xH003", type="unknown", value=""),
            ],
            edges=[
                PointerEdge(source_address="0xS001", target_address="0xH001", is_dangling=True),
                PointerEdge(source_address="0xH001.left", target_address="0xH002"),
                PointerEdge(source_address="0xH001.right", target_address="0xH003"),
            ],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=4,
            source_code="int after = 9;",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(name="root", type="Node*", value="0xH001", address="0xS001", is_pointer=True),
                Variable(name="after", type="int", value="9", address="0xS002", is_pointer=False),
            ])],
            heap=[
                HeapBlock(
                    address="0xH001",
                    type="Node",
                    value="{value=1, left=0xH002, right=0xH003}",
                    is_freed=True,
                    is_object=True,
                    class_name="Node",
                    members=[
                        StructMember(name="value", type="int", value="1", address="0xH001.value"),
                        StructMember(name="left", type="Node*", value="0xH002", address="0xH001.left"),
                        StructMember(name="right", type="Node*", value="0xH003", address="0xH001.right"),
                    ],
                ),
                HeapBlock(
                    address="0xH002",
                    type="Node",
                    value="{value=2, left=nullptr, right=nullptr}",
                    is_object=True,
                    class_name="Node",
                    members=[
                        StructMember(name="value", type="int", value="2", address="0xH002.value"),
                        StructMember(name="left", type="Node*", value="nullptr", address="0xH002.left"),
                        StructMember(name="right", type="Node*", value="nullptr", address="0xH002.right"),
                    ],
                ),
                HeapBlock(
                    address="0xH003",
                    type="Node",
                    value="{value=3, left=nullptr, right=nullptr}",
                    is_object=True,
                    class_name="Node",
                    members=[
                        StructMember(name="value", type="int", value="3", address="0xH003.value"),
                        StructMember(name="left", type="Node*", value="nullptr", address="0xH003.left"),
                        StructMember(name="right", type="Node*", value="nullptr", address="0xH003.right"),
                    ],
                ),
            ],
            edges=[
                PointerEdge(source_address="0xS001", target_address="0xH001", is_dangling=True),
                PointerEdge(source_address="0xH001.left", target_address="0xH002"),
                PointerEdge(source_address="0xH001.right", target_address="0xH003"),
            ],
        ),
    ])

    weak_errors = _validate_deleted_tree_keeps_child_objects(weak_trace)
    assert "left leaked child should render as Node object, got 'unknown'" in weak_errors
    assert "right leaked child should render as Node object, got 'unknown'" in weak_errors
    assert _validate_deleted_tree_keeps_child_objects(strong_trace) == []


def test_native_debug_smoke_requires_object_method_call_state():
    """Native smoke should prove object methods expose this and updated members."""
    from app.core.memory_model import ExecutionTrace, MemoryState, PointerEdge, StackFrame, StructMember, Variable
    from tools.native_debug_smoke import _validate_object_method_call

    weak_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=9,
            source_code="int result = c.add(5);",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="c",
                    type="Counter",
                    value="{value=7}",
                    address="0xS001",
                    is_pointer=False,
                    is_object=True,
                    members=[StructMember(name="value", type="int", value="7")],
                ),
                Variable(name="result", type="int", value="7", address="0xS002", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
    ])
    strong_trace = ExecutionTrace(steps=[
        MemoryState(
            line_number=4,
            source_code="value += delta;",
            stack=[
                StackFrame(frame_name="add", variables=[
                    Variable(name="this", type="Counter*", value="0xS001", address="0xS003", is_pointer=True),
                    Variable(name="delta", type="int", value="5", address="0xS004", is_pointer=False),
                ]),
                StackFrame(frame_name="main", variables=[
                    Variable(
                        name="c",
                        type="Counter",
                        value="{value=7}",
                        address="0xS001",
                        is_pointer=False,
                        is_object=True,
                        members=[StructMember(name="value", type="int", value="7")],
                    ),
                ]),
            ],
            heap=[],
            edges=[PointerEdge(source_address="0xS003", target_address="0xS001")],
        ),
        MemoryState(
            line_number=9,
            source_code="int result = c.add(5);",
            stack=[StackFrame(frame_name="main", variables=[
                Variable(
                    name="c",
                    type="Counter",
                    value="{value=7}",
                    address="0xS001",
                    is_pointer=False,
                    is_object=True,
                    members=[StructMember(name="value", type="int", value="7")],
                ),
                Variable(name="result", type="int", value="7", address="0xS002", is_pointer=False),
            ])],
            heap=[],
            edges=[],
        ),
    ])

    weak_errors = _validate_object_method_call(weak_trace)
    assert "missing observed Counter::add -> main method call stack" in weak_errors
    assert _validate_object_method_call(strong_trace) == []


# ── Runner ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()

    tests = [
        test_error_store_lazy_init,
        test_error_store_atomic_write,
        test_canvas_animator_pending_guard,
        test_memory_model_normalizes_llm_nulls_and_numbers,
        test_clear_layout_recurses_nested_layouts,
        test_memory_canvas_does_not_remove_rekeyed_stack_item,
        test_memory_canvas_registers_member_pointer_edge_sources,
        test_memory_canvas_registers_array_element_pointer_edge_sources,
        test_canvas_view_uses_stable_fit_bounds,
        test_code_editor_auto_fit_defaults_to_initial_fit_only,
        test_code_editor_status_shows_execution_diagnostics,
        test_settings_dialog_saves_experimental_pdb_toggle,
        test_memory_canvas_prepares_trace_wide_fit_bounds,
        test_state_diff_detects_member_changes,
        test_oj_page_autogen_passes_empty_code_to_worker,
        test_debug_executor_parses_lldb_snapshots,
        test_debug_executor_parses_arrays_and_struct_members,
        test_debug_executor_parses_lldb_class_object_members,
        test_debug_executor_parses_lldb_inherited_virtual_object_metadata,
        test_debug_executor_formats_double_values_for_display,
        test_debug_executor_filters_future_long_long_locals,
        test_debug_executor_filters_future_double_pointer_locals,
        test_debug_executor_parses_nullptr_pointer_value,
        test_debug_executor_parses_c_string_pointer_summary,
        test_debug_executor_keeps_locals_on_wrapped_snippet_last_line,
        test_debug_executor_parses_reference_target_address,
        test_debug_executor_marks_expired_stack_pointer_dangling,
        test_debug_executor_formats_std_string_summary_as_scalar,
        test_debug_executor_lldb_script_expands_string_keyed_containers,
        test_debug_executor_lldb_script_expands_smart_pointers,
        test_debug_executor_lldb_script_uses_top_level_pointer_checks,
        test_debug_executor_smart_pointer_checks_are_top_level_only,
        test_debug_executor_detects_std_array_declarations_with_nested_templates,
        test_debug_executor_parses_lambda_captures_as_function_object,
        test_debug_executor_parses_lldb_member_pointer_edges,
        test_debug_executor_parses_lldb_std_array_as_array_variable,
        test_debug_executor_maps_lldb_std_array_object_member_pointer_edges,
        test_debug_executor_parses_lldb_container_adapters_as_array_variables,
        test_debug_executor_parses_vector_elements_as_array_variable,
        test_debug_executor_parses_lldb_vector_of_pointers_as_array_not_pointer,
        test_debug_executor_parses_lldb_optional_pointer_member_edge,
        test_debug_executor_parses_lldb_optional_variant_nested_object_member_edges,
        test_debug_executor_formats_lldb_optional_empty_state,
        test_debug_executor_preserves_template_pointer_in_object_class_name,
        test_debug_executor_parses_vector_string_elements_from_summaries,
        test_debug_executor_parses_map_children_as_key_value_entries,
        test_debug_executor_parses_lldb_map_pointer_values_as_entry_edges,
        test_debug_executor_parses_lldb_vector_unique_ptr_object_heap_members,
        test_debug_executor_parses_lldb_vector_polymorphic_unique_ptr_dynamic_heap_type,
        test_debug_executor_preserves_nested_array_child_values,
        test_debug_executor_preserves_array_of_struct_child_values,
        test_debug_executor_parses_heap_object_members_from_pointer,
        test_debug_executor_preserves_overwritten_heap_as_leak,
        test_debug_executor_parses_unique_ptr_as_heap_pointer,
        test_debug_executor_marks_expired_lldb_weak_ptr_as_dangling,
        test_debug_executor_preserves_polymorphic_heap_pointer_address_after_delete,
        test_debug_executor_closes_heap_member_pointer_targets,
        test_debug_executor_parses_lldb_nested_member_pointer_object_values,
        test_debug_executor_parses_heap_array_expression_snapshots,
        test_debug_executor_selects_lldb_backend_when_tools_exist,
        test_debug_executor_msvc_pdb_backend_is_experimental_by_default,
        test_debug_executor_selects_msvc_pdb_backend_when_enabled_on_windows,
        test_debug_executor_selects_msvc_pdb_backend_from_config,
        test_debug_executor_env_can_disable_configured_pdb_backend,
        test_debug_executor_msvc_pdb_backend_requires_cdb,
        test_debug_executor_discovers_msvc_tools_from_vswhere_and_windows_kits,
        test_debug_executor_msvc_shell_command_loads_vcvarsall,
        test_debug_executor_skips_stdin_programs_before_lldb_run,
        test_debug_executor_local_capability_rejects_stdin_code,
        test_debug_executor_marks_large_simulations_as_ai_preferred,
        test_debug_executor_lldb_script_sets_stdin_input_path,
        test_debug_executor_wraps_snippet_includes_outside_main,
        test_debug_executor_wraps_helper_function_outside_main_and_steps_in,
        test_debug_executor_wraps_object_construction_inside_main,
        test_debug_executor_msvc_compile_args_enable_pdb_symbols,
        test_debug_executor_cdb_script_uses_source_lines_and_local_vars,
        test_debug_executor_steps_into_user_function_calls,
        test_debug_executor_steps_over_constructors_but_keeps_method_calls,
        test_debug_executor_uses_current_function_frame_name,
        test_debug_executor_skips_step_in_transition_snapshots,
        test_debug_executor_keeps_caller_assignment_after_user_function_returns,
        test_debug_executor_parses_multiple_user_stack_frames,
        test_debug_executor_parses_cdb_pdb_stack_snapshots,
        test_debug_executor_parses_cdb_expired_stack_pointer_as_dangling,
        test_debug_executor_parses_cdb_double_pointer_stack_edges,
        test_debug_executor_parses_cdb_member_pointer_edges,
        test_debug_executor_parses_cdb_std_array_as_array_variable,
        test_debug_executor_maps_cdb_std_array_object_member_pointer_edges,
        test_debug_executor_parses_cdb_container_adapters_as_array_variables,
        test_debug_executor_parses_cdb_vector_of_pointers_as_array_not_pointer,
        test_debug_executor_parses_cdb_optional_pointer_member_edge,
        test_debug_executor_parses_cdb_reference_as_non_pointer,
        test_debug_executor_parses_cdb_recursive_stack_frames,
        test_debug_executor_parses_cdb_object_method_call_stack,
        test_debug_executor_cdb_skips_step_in_transition_snapshots,
        test_debug_executor_cdb_keeps_caller_assignment_after_user_function_returns,
        test_debug_executor_parses_cdb_arrays_and_objects,
        test_debug_executor_parses_cdb_dx_object_string_member_children,
        test_debug_executor_parses_cdb_dx_string_variables_and_elements,
        test_debug_executor_parses_cdb_inherited_virtual_object_metadata,
        test_debug_executor_parses_cdb_polymorphic_heap_delete_state,
        test_debug_executor_parses_cdb_overwritten_heap_as_leak,
        test_debug_executor_parses_cdb_unique_ptr_as_heap_pointer,
        test_debug_executor_marks_expired_cdb_weak_ptr_as_dangling,
        test_debug_executor_parses_cdb_shared_ptr_owners_to_same_heap,
        test_debug_executor_parses_cdb_dx_vector_shared_ptr_as_container_edges,
        test_debug_executor_parses_cdb_control_flow_loop_scope,
        test_debug_executor_parses_cdb_lambda_captures_as_function_object,
        test_debug_executor_parses_cdb_updated_stack_array,
        test_debug_executor_parses_cdb_heap_object_from_pointer_summary,
        test_debug_executor_parses_cdb_heap_array_from_pointer_summary,
        test_debug_executor_parses_cdb_heap_array_delete_state,
        test_debug_executor_parses_cdb_pointer_reset_null_state,
        test_debug_executor_parses_cdb_dx_heap_object_children_from_pointer,
        test_debug_executor_parses_cdb_dx_nested_member_pointer_object_values,
        test_debug_executor_parses_cdb_dx_heap_array_children_from_pointer,
        test_debug_executor_parses_cdb_dx_vector_object_children,
        test_debug_executor_parses_cdb_dx_map_children_as_key_value_entries,
        test_debug_executor_parses_cdb_dx_map_pointer_values_as_entry_edges,
        test_debug_executor_parses_cdb_dx_map_unique_ptr_values_as_heap_entries,
        test_debug_executor_parses_cdb_dx_map_unique_ptr_object_heap_members,
        test_debug_executor_parses_cdb_dx_map_polymorphic_shared_ptr_dynamic_heap_type,
        test_debug_executor_parses_cdb_dx_nested_map_pair_children,
        test_debug_executor_parses_cdb_dx_stl_container_breadth,
        test_debug_executor_filters_future_locals_from_stack_snapshots,
        test_ai_executor_falls_back_to_ai_for_stdin_programs,
        test_debug_executor_lldb_timeout_is_debug_execution_error,
        test_ai_executor_prefers_debug_executor_without_ai_call,
        test_ai_executor_falls_back_to_ai_when_debug_executor_cannot_run,
        test_ai_executor_skips_complex_native_when_ai_key_is_configured,
        test_ai_executor_keeps_native_for_complex_code_without_ai_key,
        test_heap_item_object_sets_value_label,
        test_heap_item_array_sets_value_label,
        test_stack_item_object_draws_member_labels,
        test_ai_service_returns_raw_string,
        test_ai_service_extracts_json_from_mixed_response,
        test_ai_service_invalid_json_error_has_context_and_raw_response,
        test_extract_code_preserves_comments,
        test_graph_page_named_canvas_class,
        test_native_debug_smoke_summarizes_and_dumps_trace,
        test_native_debug_smoke_requires_final_freed_heap_state,
        test_native_debug_smoke_requires_inherited_virtual_object_state,
        test_native_debug_smoke_requires_heap_polymorphic_delete_state,
        test_native_debug_smoke_requires_heap_leak_overwrite_state,
        test_native_debug_smoke_requires_unique_ptr_heap_state,
        test_native_debug_smoke_requires_shared_ptr_owner_state,
        test_native_debug_smoke_requires_weak_ptr_expired_state,
        test_native_debug_smoke_requires_vector_shared_ptr_container_state,
        test_native_debug_smoke_requires_vector_unique_ptr_heap_state,
        test_native_debug_smoke_requires_vector_unique_ptr_object_heap_state,
        test_native_debug_smoke_requires_std_array_shared_ptr_edges,
        test_native_debug_smoke_requires_control_flow_loop_state,
        test_native_debug_smoke_requires_lambda_capture_state,
        test_native_debug_smoke_requires_heap_array_delete_state,
        test_native_debug_smoke_requires_pointer_reset_null_state,
        test_native_debug_smoke_requires_stack_dangling_pointer_state,
        test_native_debug_smoke_requires_stack_array_elements,
        test_native_debug_smoke_requires_std_array_elements,
        test_native_debug_smoke_requires_std_array_object_pointer_edges,
        test_native_debug_smoke_requires_container_adapter_elements,
        test_native_debug_smoke_requires_vector_pointer_elements_not_pointer_container,
        test_native_debug_smoke_requires_optional_pointer_member_edge,
        test_native_debug_smoke_requires_optional_variant_object_member_edges,
        test_native_debug_smoke_requires_roadshow_native_demo_state,
        test_native_debug_smoke_requires_stl_container_breadth,
        test_native_debug_smoke_requires_map_pointer_entry_edges,
        test_native_debug_smoke_requires_map_unique_ptr_heap_entry,
        test_native_debug_smoke_requires_map_unique_ptr_object_heap_entry,
        test_native_debug_smoke_requires_polymorphic_smart_pointer_container_heap,
        test_native_debug_smoke_requires_vector_object_elements,
        test_native_debug_smoke_forwards_stdin_to_debug_executor,
        test_native_debug_smoke_requires_call_stack_state,
        test_native_debug_smoke_requires_reference_and_stack_pointer_state,
        test_native_debug_smoke_requires_double_pointer_stack_state,
        test_native_debug_smoke_requires_member_pointer_linked_list_state,
        test_native_debug_smoke_requires_heap_member_pointer_linked_list_state,
        test_native_debug_smoke_requires_recursive_call_stack_state,
        test_native_debug_smoke_requires_recursive_tree_heap_closure,
        test_native_debug_smoke_requires_deleted_tree_child_objects,
        test_native_debug_smoke_requires_object_method_call_state,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  PASS  {test.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL  {test.__name__}: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
        except (SystemExit, KeyboardInterrupt):
            raise

    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    sys.exit(0 if failed == 0 else 1)
