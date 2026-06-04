#!/usr/bin/env python3
"""Native debugger smoke tests for LLDB/DWARF and experimental MSVC/PDB.

This script intentionally exercises the same DebugExecutor -> MemoryCanvas path
as the app. It is useful on Windows when validating the experimental PDB backend
before showing it to teammates.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.core.debug_executor import DebugExecutionError, DebugExecutor  # noqa: E402
from app.core.memory_model import ExecutionTrace, MemoryState, Variable  # noqa: E402


@dataclass(frozen=True)
class SmokeCase:
    name: str
    code: str
    validate: Callable[[ExecutionTrace], list[str]]


def _all_variables(state: MemoryState) -> list[Variable]:
    return [var for frame in state.stack for var in frame.variables]


def _states_with_var(trace: ExecutionTrace, name: str) -> list[tuple[MemoryState, Variable]]:
    matches: list[tuple[MemoryState, Variable]] = []
    for state in trace.steps:
        for var in _all_variables(state):
            if var.name == name:
                matches.append((state, var))
    return matches


def _last_var(trace: ExecutionTrace, name: str) -> tuple[MemoryState, Variable] | None:
    matches = _states_with_var(trace, name)
    return matches[-1] if matches else None


def _member_map(var: Variable) -> dict[str, str]:
    return {member.name: member.value for member in var.members}


def _last_observed_state(trace: ExecutionTrace) -> MemoryState | None:
    for state in reversed(trace.steps):
        if state.stack or state.heap or state.edges:
            return state
    return trace.steps[-1] if trace.steps else None


def _variable_summary(var: Variable) -> dict[str, object]:
    return {
        "name": var.name,
        "type": var.type,
        "value": var.value,
        "is_pointer": var.is_pointer,
        "is_array": var.is_array,
        "element_count": var.element_count,
        "elements": [
            {"index": element.index, "value": element.value}
            for element in var.elements[:8]
        ],
        "is_object": var.is_object,
        "members": [
            {"name": member.name, "type": member.type, "value": member.value}
            for member in var.members[:8]
        ],
    }


def _trace_summary(trace: ExecutionTrace) -> dict[str, object]:
    last_state = _last_observed_state(trace)
    if last_state is None:
        return {
            "step_count": 0,
            "last_line": None,
            "last_source": "",
            "frames": [],
            "heap": [],
            "edges": [],
        }

    return {
        "step_count": len(trace.steps),
        "last_line": last_state.line_number,
        "last_source": last_state.source_code,
        "frames": [
            {
                "name": frame.frame_name,
                "variables": [_variable_summary(var) for var in frame.variables],
            }
            for frame in last_state.stack
        ],
        "heap": [
            {
                "address": block.address,
                "type": block.type,
                "value": block.value,
                "is_freed": block.is_freed,
                "is_array": block.is_array,
                "element_count": block.element_count,
                "elements": [
                    {"index": element.index, "value": element.value}
                    for element in block.elements[:8]
                ],
                "is_object": block.is_object,
                "members": [
                    {"name": member.name, "type": member.type, "value": member.value}
                    for member in block.members[:8]
                ],
            }
            for block in last_state.heap
        ],
        "edges": [
            {
                "source": edge.source_address,
                "target": edge.target_address,
                "dangling": edge.is_dangling,
            }
            for edge in last_state.edges
        ],
    }


def _write_trace_dump(
    dump_dir: Path,
    case: SmokeCase,
    trace: ExecutionTrace,
    summary: dict[str, object],
) -> Path:
    dump_dir.mkdir(parents=True, exist_ok=True)
    path = dump_dir / f"{case.name}.json"
    path.write_text(
        json.dumps(
            {
                "case": case.name,
                "code": case.code,
                "summary": summary,
                "trace": trace.model_dump(mode="json"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def _validate_basic_double(trace: ExecutionTrace) -> list[str]:
    errors: list[str] = []
    if len(trace.steps) < 3:
        errors.append(f"expected at least 3 steps, got {len(trace.steps)}")
        return errors
    last = trace.steps[-1]
    values = {var.name: var.value for var in _all_variables(last)}
    for name, expected in {"a": "42", "b": "52", "pi": "3.14"}.items():
        if values.get(name) != expected:
            errors.append(f"{name} expected {expected}, got {values.get(name)!r}")
    return errors


def _validate_stack_object(trace: ExecutionTrace) -> list[str]:
    errors: list[str] = []
    match = _last_var(trace, "s")
    if match is None:
        return ["missing stack object variable s"]
    _, var = match
    if not var.is_object:
        errors.append("s should be marked as an object")
    members = _member_map(var)
    for name, expected in {"id": "7", "score": "99", "name": "Ada"}.items():
        if members.get(name) != expected:
            errors.append(f"s.{name} expected {expected}, got {members.get(name)!r}")
    return errors


def _validate_vector(trace: ExecutionTrace) -> list[str]:
    match = _last_var(trace, "v")
    if match is None:
        return ["missing vector variable v"]
    _, var = match
    values = [element.value for element in var.elements]
    if not var.is_array:
        return ["v should be marked as an array/container"]
    if values != ["1", "8", "3"]:
        return [f"v elements expected ['1', '8', '3'], got {values!r}"]
    return []


def _validate_map(trace: ExecutionTrace) -> list[str]:
    match = _last_var(trace, "m")
    if match is None:
        return ["missing map variable m"]
    _, var = match
    values = [element.value for element in var.elements]
    if not var.is_array:
        return ["m should be marked as an array/container"]
    has_a = 'first="a"' in var.value or "first=a" in var.value
    has_b = 'first="b"' in var.value or "first=b" in var.value
    if not (has_a and "second=1" in var.value and has_b and "second=2" in var.value):
        return [f"m value does not contain expected key/value pairs: {var.value!r}"]
    if len(values) != 2:
        return [f"m expected 2 key/value entries, got {values!r}"]
    return []


def _validate_heap_object(trace: ExecutionTrace) -> list[str]:
    errors: list[str] = []
    live_blocks = [block for step in trace.steps for block in step.heap if block.is_object]
    if not live_blocks:
        errors.append("missing object heap block")
    final_state = _last_observed_state(trace)
    final_heap = final_state.heap if final_state is not None else []
    final_edges = final_state.edges if final_state is not None else []
    freed_blocks = [block for block in final_heap if block.is_freed]
    if not freed_blocks:
        errors.append("final state is missing freed heap block after delete")
    dangling_edges = [edge for edge in final_edges if edge.is_dangling]
    if not dangling_edges:
        errors.append("final state is missing dangling pointer edge after delete")
    return errors


CASES: dict[str, SmokeCase] = {
    "basic_double": SmokeCase(
        name="basic_double",
        code="int a = 42;\nint b = a + 10;\ndouble pi = 3.14;\n",
        validate=_validate_basic_double,
    ),
    "stack_object": SmokeCase(
        name="stack_object",
        code=(
            "#include <string>\n"
            "using namespace std;\n"
            "class Student { public: int id; double score; string name; "
            "Student(int i, double s, string n): id(i), score(s), name(n) {} };\n"
            'Student s(7, 98.5, "Ada");\n'
            "s.score = 99.0;\n"
        ),
        validate=_validate_stack_object,
    ),
    "heap_object": SmokeCase(
        name="heap_object",
        code=(
            "struct Point { int x; double y; };\n"
            "Point* hp = new Point{4, 5.5};\n"
            "hp->y = 6.5;\n"
            "delete hp;\n"
        ),
        validate=_validate_heap_object,
    ),
    "vector_int": SmokeCase(
        name="vector_int",
        code=(
            "#include <vector>\n"
            "using namespace std;\n"
            "vector<int> v = {1, 2};\n"
            "v.push_back(3);\n"
            "v[1] = 8;\n"
        ),
        validate=_validate_vector,
    ),
    "map_string_int": SmokeCase(
        name="map_string_int",
        code=(
            "#include <map>\n"
            "#include <string>\n"
            "using namespace std;\n"
            "map<string, int> m;\n"
            'm["a"] = 1;\n'
            'm["b"] = 2;\n'
            'int got = m["a"];\n'
        ),
        validate=_validate_map,
    ),
}


def _render_trace(trace: ExecutionTrace) -> int:
    from PySide6.QtWidgets import QApplication, QGraphicsScene, QGraphicsView
    from app.ui.canvas.memory_canvas import MemoryCanvas

    app = QApplication.instance() or QApplication(sys.argv)
    scene = QGraphicsScene()
    scene.setSceneRect(0, 0, 1600, 1200)
    view = QGraphicsView()
    view.setScene(scene)
    canvas = MemoryCanvas(view, scene)
    canvas.prepare_trace_layout(trace.steps)
    for state in trace.steps:
        canvas.render_state(state)
        app.processEvents()
    return len(scene.items())


def _backend_status() -> list[dict[str, object]]:
    return [
        {
            "id": status.id,
            "label": status.label,
            "available": status.available,
            "implemented": status.implemented,
            "detail": status.detail,
        }
        for status in DebugExecutor.backend_status()
    ]


def _run_case(
    case: SmokeCase,
    backend: str | None,
    render: bool,
    dump_dir: Path | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "name": case.name,
        "ok": False,
        "steps": 0,
        "rendered_items": None,
        "errors": [],
        "summary": None,
        "trace_path": None,
    }
    try:
        trace = DebugExecutor(preferred_backend=backend).run_code(case.code)
        result["steps"] = len(trace.steps)
        summary = _trace_summary(trace)
        result["summary"] = summary
        if dump_dir is not None:
            result["trace_path"] = str(_write_trace_dump(dump_dir, case, trace, summary))
        errors = case.validate(trace)
        if render:
            result["rendered_items"] = _render_trace(trace)
        result["errors"] = errors
        result["ok"] = not errors
    except Exception as exc:  # noqa: BLE001 - smoke output should include any failure.
        result["errors"] = [f"{type(exc).__name__}: {exc}"]
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend",
        choices=("auto", DebugExecutor.LLDB_DWARF_BACKEND, DebugExecutor.MSVC_PDB_BACKEND),
        default="auto",
        help="Debugger backend to force. Use msvc-pdb on Windows PDB validation.",
    )
    parser.add_argument(
        "--case",
        action="append",
        choices=sorted(CASES),
        help="Case to run. Repeat to select multiple cases. Defaults to all cases.",
    )
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="Skip offscreen MemoryCanvas rendering. Not recommended for final validation.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON only.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print trace summaries for passing cases too.",
    )
    parser.add_argument(
        "--dump-traces",
        type=Path,
        help="Write each successful case trace as JSON files under this directory.",
    )
    parser.add_argument(
        "--list-backends",
        action="store_true",
        help="Print debugger backend availability and exit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    backend = None if args.backend == "auto" else args.backend
    if args.list_backends:
        payload = {"backends": _backend_status()}
        print(json.dumps(payload, indent=2))
        return 0

    selected_cases = [CASES[name] for name in (args.case or sorted(CASES))]
    results = [
        _run_case(
            case,
            backend,
            render=not args.no_render,
            dump_dir=args.dump_traces,
        )
        for case in selected_cases
    ]
    payload = {
        "backend": args.backend,
        "render": not args.no_render,
        "backends": _backend_status(),
        "results": results,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for status in payload["backends"]:
            marker = "available" if status["available"] else "unavailable"
            print(f"backend {status['id']}: {marker} - {status['detail']}")
        print()
        for result in results:
            marker = "PASS" if result["ok"] else "FAIL"
            print(
                f"{marker} {result['name']}: "
                f"{result['steps']} steps, rendered_items={result['rendered_items']}"
            )
            for error in result["errors"]:
                print(f"  - {error}")
            if args.verbose or not result["ok"]:
                summary = result.get("summary")
                if isinstance(summary, dict):
                    print(
                        "  summary: "
                        f"line={summary.get('last_line')} "
                        f"source={summary.get('last_source')!r}"
                    )
                    print(f"  frames: {json.dumps(summary.get('frames'), ensure_ascii=False)}")
                    print(f"  heap: {json.dumps(summary.get('heap'), ensure_ascii=False)}")
                    print(f"  edges: {json.dumps(summary.get('edges'), ensure_ascii=False)}")
                if result.get("trace_path"):
                    print(f"  trace: {result['trace_path']}")

    return 0 if all(result["ok"] for result in results) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DebugExecutionError as exc:
        print(f"Debugger unavailable: {exc}", file=sys.stderr)
        raise SystemExit(2)
