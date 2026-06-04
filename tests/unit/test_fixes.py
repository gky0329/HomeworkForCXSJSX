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

    scene.addRect(0, 0, 1600, 1600)
    view.zoom_fit()
    second_scale = view.transform().m11()

    assert abs(first_scale - second_scale) < 0.000001


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
    assert "if is_std_string_type(typ) and val:" in script
    assert "if val and not is_expandable_container_type(typ):" in script
    assert "'string' in typ and 'vector' not in typ" not in script


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
    assert "dx -r2 @$curframe.Locals" in script
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

            result = asyncio.run(AIExecutor().run_code("int a = 1;"))

    assert result is expected
    assert captured["code"] == "int a = 1;"
    assert captured["stdin"] == ""


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

            result = asyncio.run(AIExecutor().run_code("template <class T> T f(T x) { return x; }"))

    assert result.steps == []


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
        test_canvas_view_uses_stable_fit_bounds,
        test_memory_canvas_prepares_trace_wide_fit_bounds,
        test_state_diff_detects_member_changes,
        test_oj_page_autogen_passes_empty_code_to_worker,
        test_debug_executor_parses_lldb_snapshots,
        test_debug_executor_parses_arrays_and_struct_members,
        test_debug_executor_parses_lldb_class_object_members,
        test_debug_executor_formats_double_values_for_display,
        test_debug_executor_filters_future_long_long_locals,
        test_debug_executor_parses_nullptr_pointer_value,
        test_debug_executor_parses_c_string_pointer_summary,
        test_debug_executor_keeps_locals_on_wrapped_snippet_last_line,
        test_debug_executor_parses_reference_target_address,
        test_debug_executor_formats_std_string_summary_as_scalar,
        test_debug_executor_lldb_script_expands_string_keyed_containers,
        test_debug_executor_parses_vector_elements_as_array_variable,
        test_debug_executor_parses_vector_string_elements_from_summaries,
        test_debug_executor_parses_map_children_as_key_value_entries,
        test_debug_executor_preserves_nested_array_child_values,
        test_debug_executor_preserves_array_of_struct_child_values,
        test_debug_executor_parses_heap_object_members_from_pointer,
        test_debug_executor_parses_heap_array_expression_snapshots,
        test_debug_executor_selects_lldb_backend_when_tools_exist,
        test_debug_executor_msvc_pdb_backend_is_experimental_by_default,
        test_debug_executor_selects_msvc_pdb_backend_when_enabled_on_windows,
        test_debug_executor_msvc_pdb_backend_requires_cdb,
        test_debug_executor_discovers_msvc_tools_from_vswhere_and_windows_kits,
        test_debug_executor_msvc_shell_command_loads_vcvarsall,
        test_debug_executor_skips_stdin_programs_before_lldb_run,
        test_debug_executor_local_capability_rejects_stdin_code,
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
        test_debug_executor_parses_cdb_reference_as_non_pointer,
        test_debug_executor_parses_cdb_recursive_stack_frames,
        test_debug_executor_parses_cdb_object_method_call_stack,
        test_debug_executor_cdb_skips_step_in_transition_snapshots,
        test_debug_executor_cdb_keeps_caller_assignment_after_user_function_returns,
        test_debug_executor_parses_cdb_arrays_and_objects,
        test_debug_executor_parses_cdb_heap_object_from_pointer_summary,
        test_debug_executor_parses_cdb_heap_array_from_pointer_summary,
        test_debug_executor_parses_cdb_dx_heap_object_children_from_pointer,
        test_debug_executor_parses_cdb_dx_heap_array_children_from_pointer,
        test_debug_executor_parses_cdb_dx_map_children_as_key_value_entries,
        test_debug_executor_parses_cdb_dx_nested_map_pair_children,
        test_debug_executor_filters_future_locals_from_stack_snapshots,
        test_ai_executor_falls_back_to_ai_for_stdin_programs,
        test_debug_executor_lldb_timeout_is_debug_execution_error,
        test_ai_executor_prefers_debug_executor_without_ai_call,
        test_ai_executor_falls_back_to_ai_when_debug_executor_cannot_run,
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
        test_native_debug_smoke_forwards_stdin_to_debug_executor,
        test_native_debug_smoke_requires_call_stack_state,
        test_native_debug_smoke_requires_reference_and_stack_pointer_state,
        test_native_debug_smoke_requires_recursive_call_stack_state,
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
