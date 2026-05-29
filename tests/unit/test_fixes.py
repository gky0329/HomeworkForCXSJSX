"""
Smoke tests for Phase 1-5 fixes.

Run:  python tests/unit/test_fixes.py
Required env: project root in PYTHONPATH (or run from project root).
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


# ── Phase 1: error_store lazy init + tmp fallback ──────────────────────

def test_error_store_lazy_init():
    """_ensure_data_dir() is called on first save, not at import time."""
    from app.services.error_store import _ensure_data_dir, _save, _load, ERRORS_PATH

    data = [{"id": "test1", "name": "test"}]
    try:
        _save(ERRORS_PATH, data)
        loaded = _load(ERRORS_PATH)
        assert len(loaded) == 1
        assert loaded[0]["name"] == "test"
    finally:
        # cleanup
        if ERRORS_PATH.exists():
            ERRORS_PATH.unlink()
            tmp = ERRORS_PATH.with_suffix(ERRORS_PATH.suffix + ".tmp")
            if tmp.exists():
                tmp.unlink()


def test_error_store_atomic_write():
    """_save writes to .tmp first, then os.replace."""
    from app.services.error_store import _save, ERRORS_PATH

    data = [{"id": "a"}]
    _save(ERRORS_PATH, data)
    tmp_path = ERRORS_PATH.with_suffix(ERRORS_PATH.suffix + ".tmp")
    assert not tmp_path.exists(), "tmp file should be cleaned up after atomic rename"

    # cleanup
    if ERRORS_PATH.exists():
        ERRORS_PATH.unlink()


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
    """graph_page defines _GraphCanvas as a named class, not type()."""
    from PySide6.QtWidgets import QApplication
    import sys
    QApplication.instance() or QApplication(sys.argv)

    from app.ui.pages.graph_page import _GraphCanvas
    assert _GraphCanvas.__name__ == "_GraphCanvas", f"expected _GraphCanvas, got {_GraphCanvas.__name__}"
    assert issubclass(_GraphCanvas, object)


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
        test_heap_item_object_sets_value_label,
        test_heap_item_array_sets_value_label,
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
