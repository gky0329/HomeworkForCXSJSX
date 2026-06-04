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


def test_stack_item_object_draws_member_summary_and_labels():
    """Stack object variables should show both an object summary and member rows."""
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
        test_heap_item_object_sets_value_label,
        test_heap_item_array_sets_value_label,
        test_stack_item_object_draws_member_summary_and_labels,
        test_ai_service_returns_raw_string,
        test_extract_code_preserves_comments,
        test_graph_page_named_canvas_class,
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
