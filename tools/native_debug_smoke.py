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
    stdin_text: str = ""


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
        "class_name": var.class_name,
        "base_classes": list(var.base_classes),
        "virtual_methods": list(var.virtual_methods),
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
                "class_name": block.class_name,
                "base_classes": list(block.base_classes),
                "virtual_methods": list(block.virtual_methods),
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
                "stdin": case.stdin_text,
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


def _validate_inherited_virtual_object(trace: ExecutionTrace) -> list[str]:
    errors: list[str] = []
    state = _last_observed_state(trace)
    if state is None:
        return ["trace has no observed state"]
    values = {var.name: var for var in _all_variables(state)}
    d = values.get("d")
    ptr = values.get("a")
    sound = values.get("sound")
    if d is None:
        errors.append("missing Dog object d")
    else:
        if not d.is_object:
            errors.append("d should be marked as an object")
        if d.class_name != "Dog":
            errors.append(f"d class_name expected Dog, got {d.class_name!r}")
        if "Animal" not in d.base_classes:
            errors.append(f"d should list Animal as a base class, got {d.base_classes!r}")
        if "speak()" not in d.virtual_methods:
            errors.append(f"d should list speak() as a virtual method, got {d.virtual_methods!r}")
        members = _member_map(d)
        if members.get("Animal") is None or "age=3" not in members.get("Animal", ""):
            errors.append(f"d base Animal member should include age=3, got {members.get('Animal')!r}")
        if members.get("bones") != "4":
            errors.append(f"d.bones expected 4, got {members.get('bones')!r}")
    if ptr is None:
        errors.append("missing base pointer a")
    elif d is not None:
        if not ptr.is_pointer:
            errors.append("a should be marked as a pointer")
        if ptr.value != d.address:
            errors.append(f"a should target d address {d.address}, got {ptr.value!r}")
        if ptr.address == d.address:
            errors.append("a pointer variable address should not collapse onto d's object address")
        if not any(edge.source_address == ptr.address and edge.target_address == d.address for edge in state.edges):
            errors.append("missing a -> d stack pointer edge")
    if sound is None:
        errors.append("missing virtual call result sound")
    elif sound.value != "7":
        errors.append(f"sound expected 7 from virtual call, got {sound.value!r}")
    return errors


def _validate_stack_array(trace: ExecutionTrace) -> list[str]:
    match = _last_var(trace, "nums")
    if match is None:
        return ["missing stack array variable nums"]
    _, var = match
    errors: list[str] = []
    if not var.is_array:
        errors.append("nums should be marked as an array")
    if var.is_pointer:
        errors.append("nums should not be marked as a pointer")
    values = [element.value for element in var.elements]
    if values != ["1", "8", "3"]:
        errors.append(f"nums elements expected ['1', '8', '3'], got {values!r}")
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


def _validate_vector_object(trace: ExecutionTrace) -> list[str]:
    match = _last_var(trace, "nodes")
    if match is None:
        return ["missing vector object variable nodes"]
    _, var = match
    errors: list[str] = []
    if not var.is_array:
        errors.append("nodes should be marked as an array/container")
    values = [element.value for element in var.elements]
    if len(values) != 2:
        errors.append(f"nodes expected 2 elements, got {values!r}")
    if not any("id=1" in value and "weight=1.5" in value for value in values):
        errors.append(f"nodes missing first object element: {values!r}")
    if not any("id=2" in value and "weight=4.5" in value for value in values):
        errors.append(f"nodes missing updated second object element: {values!r}")
    return errors


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


def _validate_heap_polymorphic_delete(trace: ExecutionTrace) -> list[str]:
    errors: list[str] = []
    states_with_a = [
        (state, var)
        for state in trace.steps
        for var in _all_variables(state)
        if var.name == "a"
    ]
    if not states_with_a:
        errors.append("missing base pointer a")
    else:
        addresses = {var.address for _, var in states_with_a}
        if len(addresses) != 1:
            errors.append(f"a pointer variable address should remain stable, got {sorted(addresses)!r}")

    final_state = _last_observed_state(trace)
    if final_state is None:
        return errors + ["trace has no observed state"]
    values = {var.name: var for var in _all_variables(final_state)}
    ptr = values.get("a")
    sound = values.get("sound")
    blocks = [block for block in final_state.heap if block.is_object]
    if ptr is None:
        errors.append("missing base pointer a in final state")
    elif not ptr.is_pointer:
        errors.append("a should be marked as a pointer")
    if sound is None:
        errors.append("missing virtual call result sound")
    elif sound.value != "7":
        errors.append(f"sound expected 7 from virtual call, got {sound.value!r}")
    if not blocks:
        errors.append("missing polymorphic heap object block")
    else:
        block = blocks[0]
        if block.class_name != "Dog":
            errors.append(f"heap object class_name expected Dog, got {block.class_name!r}")
        if "Animal" not in block.base_classes:
            errors.append(f"heap object should list Animal as a base class, got {block.base_classes!r}")
        if block.virtual_methods != ["speak()"]:
            errors.append(f"heap object virtual_methods expected ['speak()'], got {block.virtual_methods!r}")
        members = {member.name: member.value for member in block.members}
        if members.get("Animal") is None or "age=3" not in members.get("Animal", ""):
            errors.append(f"heap base Animal member should include age=3, got {members.get('Animal')!r}")
        if members.get("bones") != "4":
            errors.append(f"heap Dog.bones expected 4, got {members.get('bones')!r}")
        if not block.is_freed:
            errors.append("polymorphic heap object should remain visible as freed after delete")
        if ptr is not None and ptr.value != block.address:
            errors.append(f"a should target heap object {block.address}, got {ptr.value!r}")

    if not any(edge.is_dangling for edge in final_state.edges):
        errors.append("final state is missing dangling pointer edge after polymorphic delete")
    return errors


def _validate_heap_leak_overwrite(trace: ExecutionTrace) -> list[str]:
    errors: list[str] = []
    state = _last_observed_state(trace)
    if state is None:
        return ["trace has no observed state"]
    values = {var.name: var for var in _all_variables(state)}
    ptr = values.get("p")
    if ptr is None:
        errors.append("missing pointer variable p")
    elif not ptr.is_pointer:
        errors.append("p should be marked as a pointer")

    live_blocks = [block for block in state.heap if not block.is_freed]
    if len(live_blocks) < 2:
        errors.append(f"expected current heap plus leaked heap block, got {len(live_blocks)}")
    block_values = {block.value for block in live_blocks}
    if "1" not in block_values:
        errors.append(f"missing overwritten leaked heap value 1, got {sorted(block_values)!r}")
    if "3" not in block_values:
        errors.append(f"missing current heap value 3, got {sorted(block_values)!r}")
    if ptr is not None:
        if not any(edge.source_address == ptr.address and edge.target_address == ptr.value for edge in state.edges):
            errors.append("missing p -> current heap edge")
        leaked_blocks = [block for block in live_blocks if block.value == "1"]
        for block in leaked_blocks:
            if any(edge.target_address == block.address for edge in state.edges):
                errors.append(f"leaked heap block {block.address} should have no incoming pointer edge")
    return errors


def _validate_unique_ptr_heap(trace: ExecutionTrace) -> list[str]:
    errors: list[str] = []
    updated_state = next(
        (state for state in trace.steps if any(block.value == "8" for block in state.heap)),
        None,
    )
    if updated_state is None:
        errors.append("missing unique_ptr heap state with updated value 8")
    else:
        values = {var.name: var for var in _all_variables(updated_state)}
        ptr = values.get("p")
        block = next((heap for heap in updated_state.heap if heap.value == "8"), None)
        if ptr is None:
            errors.append("missing unique_ptr variable p")
        elif not ptr.is_pointer:
            errors.append("unique_ptr p should be rendered as a pointer-like owner")
        if block is None:
            errors.append("missing heap block value 8")
        elif ptr is not None:
            if ptr.value != block.address:
                errors.append(f"p should target heap block {block.address}, got {ptr.value!r}")
            if not any(edge.source_address == ptr.address and edge.target_address == block.address for edge in updated_state.edges):
                errors.append("missing p -> heap edge for unique_ptr")

    final_state = _last_observed_state(trace)
    if final_state is None:
        return errors + ["trace has no observed state"]
    final_p = next((var for var in _all_variables(final_state) if var.name == "p"), None)
    if final_p is None:
        errors.append("missing final unique_ptr variable p")
    elif final_p.value != "nullptr":
        errors.append(f"p expected nullptr after reset, got {final_p.value!r}")
    if final_state.edges:
        errors.append(f"unique_ptr reset final state should have no edges, got {len(final_state.edges)}")
    return errors


def _validate_heap_array_delete(trace: ExecutionTrace) -> list[str]:
    errors: list[str] = []
    final_state = _last_observed_state(trace)
    if final_state is None:
        return ["trace has no observed state"]

    arr = next((var for var in _all_variables(final_state) if var.name == "arr"), None)
    if arr is None:
        errors.append("missing heap array pointer arr")
    elif not arr.is_pointer:
        errors.append("arr should be marked as a pointer")

    blocks = [block for block in final_state.heap if block.is_array]
    if not blocks:
        errors.append("final state is missing heap array block")
    else:
        block = blocks[0]
        values = [element.value for element in block.elements]
        if block.type != "int[]":
            errors.append(f"heap array type expected int[], got {block.type!r}")
        if values != ["1", "9", "3"]:
            errors.append(f"heap array elements expected ['1', '9', '3'], got {values!r}")
        if not block.is_freed:
            errors.append("heap array should remain visible as freed after delete[]")
        if arr is not None and arr.value != block.address:
            errors.append(f"arr should target heap array {block.address}, got {arr.value!r}")

    if not any(edge.is_dangling for edge in final_state.edges):
        errors.append("final state is missing dangling pointer edge after delete[]")
    return errors


def _validate_pointer_reset_null(trace: ExecutionTrace) -> list[str]:
    errors: list[str] = []
    delete_state = next(
        (state for state in trace.steps if state.source_code.startswith("delete ")),
        None,
    )
    if delete_state is None:
        errors.append("missing delete step")
    else:
        if not any(block.is_freed for block in delete_state.heap):
            errors.append("delete step should keep the freed heap block visible")
        if not any(edge.is_dangling for edge in delete_state.edges):
            errors.append("delete step should show a dangling pointer edge")

    final_state = _last_observed_state(trace)
    if final_state is None:
        return errors + ["trace has no observed state"]
    p = next((var for var in _all_variables(final_state) if var.name == "p"), None)
    if p is None:
        errors.append("missing pointer variable p")
    elif p.value != "nullptr":
        errors.append(f"p expected nullptr after reset, got {p.value!r}")
    if final_state.edges:
        errors.append(f"final nullptr state should have no pointer edges, got {len(final_state.edges)}")
    if any(edge.is_dangling for edge in final_state.edges):
        errors.append("final nullptr state should not keep a dangling edge")
    return errors


def _validate_stdin_sum(trace: ExecutionTrace) -> list[str]:
    state = _last_observed_state(trace)
    if state is None:
        return ["trace has no observed state"]
    values = {var.name: var.value for var in _all_variables(state)}
    errors: list[str] = []
    for name, expected in {"x": "7", "y": "5", "sum": "12"}.items():
        if values.get(name) != expected:
            errors.append(f"{name} expected {expected}, got {values.get(name)!r}")
    return errors


def _validate_call_stack(trace: ExecutionTrace) -> list[str]:
    errors: list[str] = []
    callee_state = None
    for state in trace.steps:
        frame_names = [frame.frame_name for frame in state.stack]
        if len(frame_names) >= 2 and frame_names[0] == "square" and "main" in frame_names[1:]:
            callee_state = state
            break
    if callee_state is None:
        errors.append("missing observed square -> main call stack")
    else:
        top_values = {
            var.name: var.value
            for var in callee_state.stack[0].variables
        }
        for name, expected in {"x": "3", "y": "9"}.items():
            if top_values.get(name) != expected:
                errors.append(f"square::{name} expected {expected}, got {top_values.get(name)!r}")

    result = _last_var(trace, "result")
    if result is None:
        errors.append("missing caller result variable")
    elif result[1].value != "9":
        errors.append(f"result expected 9, got {result[1].value!r}")
    return errors


def _validate_reference_stack_pointer(trace: ExecutionTrace) -> list[str]:
    errors: list[str] = []
    state = _last_observed_state(trace)
    if state is None:
        return ["trace has no observed state"]
    values = {var.name: var for var in _all_variables(state)}
    a = values.get("a")
    ref = values.get("r")
    ptr = values.get("p")
    if a is None:
        errors.append("missing int variable a")
    elif a.value != "11":
        errors.append(f"a expected 11 after reference and pointer writes, got {a.value!r}")
    if ref is None:
        errors.append("missing reference variable r")
    elif a is not None:
        if not ref.is_reference:
            errors.append("r should be marked as a reference")
        if ref.is_pointer:
            errors.append("r should not be marked as a pointer")
        if ref.value != a.address:
            errors.append(f"r should target a address {a.address}, got {ref.value!r}")
    if ptr is None:
        errors.append("missing pointer variable p")
    elif a is not None:
        if not ptr.is_pointer:
            errors.append("p should be marked as a pointer")
        if ptr.value != a.address:
            errors.append(f"p should target a address {a.address}, got {ptr.value!r}")
    if ptr is not None and not any(edge.source_address == ptr.address and edge.target_address == ptr.value for edge in state.edges):
        errors.append("missing p -> a stack pointer edge")
    return errors


def _validate_stack_dangling_pointer(trace: ExecutionTrace) -> list[str]:
    errors: list[str] = []
    state = _last_observed_state(trace)
    if state is None:
        return ["trace has no observed state"]
    values = {var.name: var for var in _all_variables(state)}
    ptr = values.get("p")
    after = values.get("after")
    if ptr is None:
        errors.append("missing pointer variable p")
    elif not ptr.is_pointer:
        errors.append("p should be marked as a pointer")
    if after is None:
        errors.append("missing after-scope variable after")
    elif after.value != "9":
        errors.append(f"after expected 9, got {after.value!r}")
    if state.heap:
        errors.append(f"dangling stack pointer should not create heap blocks, got {len(state.heap)}")
    if ptr is not None:
        if not ptr.value.startswith("0xS"):
            errors.append(f"p should target a historical stack address, got {ptr.value!r}")
        dangling_edges = [
            edge for edge in state.edges
            if edge.source_address == ptr.address and edge.target_address == ptr.value and edge.is_dangling
        ]
        if not dangling_edges:
            errors.append("missing dangling p -> expired stack variable edge")
    return errors


def _validate_double_pointer_stack(trace: ExecutionTrace) -> list[str]:
    errors: list[str] = []
    for state in trace.steps:
        names = {var.name for var in _all_variables(state)}
        if state.source_code.startswith("int a") and ({"p", "pp"} & names):
            errors.append(f"future pointer appeared on int a step: {sorted(names)!r}")
        if state.source_code.startswith("int *p") and "pp" in names:
            errors.append(f"future double pointer appeared on p step: {sorted(names)!r}")

    state = _last_observed_state(trace)
    if state is None:
        return errors + ["trace has no observed state"]
    values = {var.name: var for var in _all_variables(state)}
    a = values.get("a")
    ptr = values.get("p")
    double_ptr = values.get("pp")
    if a is None:
        errors.append("missing int variable a")
    elif a.value != "7":
        errors.append(f"a expected 7 after **pp write, got {a.value!r}")
    if ptr is None:
        errors.append("missing pointer variable p")
    elif a is not None:
        if not ptr.is_pointer:
            errors.append("p should be marked as a pointer")
        if ptr.value != a.address:
            errors.append(f"p should target a address {a.address}, got {ptr.value!r}")
    if double_ptr is None:
        errors.append("missing double pointer variable pp")
    elif ptr is not None:
        if not double_ptr.is_pointer:
            errors.append("pp should be marked as a pointer")
        if double_ptr.value != ptr.address:
            errors.append(f"pp should target p address {ptr.address}, got {double_ptr.value!r}")
    if ptr is not None and a is not None:
        if not any(edge.source_address == ptr.address and edge.target_address == a.address for edge in state.edges):
            errors.append("missing p -> a stack pointer edge")
    if double_ptr is not None and ptr is not None:
        if not any(edge.source_address == double_ptr.address and edge.target_address == ptr.address for edge in state.edges):
            errors.append("missing pp -> p stack pointer edge")
    if state.heap:
        errors.append(f"double pointer stack case should not create heap blocks, got {len(state.heap)}")
    return errors


def _validate_recursive_call_stack(trace: ExecutionTrace) -> list[str]:
    errors: list[str] = []
    recursive_state = None
    for state in trace.steps:
        frame_names = [frame.frame_name for frame in state.stack]
        fact_frames = [name for name in frame_names if name.startswith("fact")]
        if len(fact_frames) >= 3 and "main" in frame_names:
            recursive_state = state
            break

    if recursive_state is None:
        errors.append("missing observed recursive fact -> fact -> fact -> main call stack")
    else:
        top_values = {
            var.name: var.value
            for var in recursive_state.stack[0].variables
        }
        if top_values.get("n") != "1":
            errors.append(f"deepest fact::n expected 1, got {top_values.get('n')!r}")

    result = _last_var(trace, "result")
    if result is None:
        errors.append("missing final recursive result variable")
    elif result[1].value != "6":
        errors.append(f"recursive result expected 6, got {result[1].value!r}")
    return errors


def _validate_object_method_call(trace: ExecutionTrace) -> list[str]:
    errors: list[str] = []
    method_state = None
    for state in trace.steps:
        frame_names = [frame.frame_name for frame in state.stack]
        if frame_names and frame_names[0] == "add" and "main" in frame_names[1:]:
            method_state = state
            break

    if method_state is None:
        errors.append("missing observed Counter::add -> main method call stack")
    else:
        method_values = {var.name: var for var in method_state.stack[0].variables}
        this_var = method_values.get("this")
        delta = method_values.get("delta")
        if this_var is None or not this_var.is_pointer:
            errors.append("method frame should expose this as a pointer")
        if delta is None or delta.value != "5":
            errors.append(f"method delta expected 5, got {delta.value if delta else None!r}")
        main_frame = next((frame for frame in method_state.stack if frame.frame_name == "main"), None)
        c = next((var for var in main_frame.variables if var.name == "c"), None) if main_frame else None
        if c is None:
            errors.append("caller frame missing Counter object c during method call")
        elif not c.is_object:
            errors.append("c should be marked as an object")
        elif _member_map(c).get("value") != "7":
            errors.append(f"c.value expected 7 during method call, got {_member_map(c).get('value')!r}")
        if this_var is not None and c is not None:
            if this_var.value != c.address:
                errors.append(f"this should point at c address {c.address}, got {this_var.value!r}")
            if not any(edge.source_address == this_var.address and edge.target_address == c.address for edge in method_state.edges):
                errors.append("missing this -> c stack pointer edge")

    result = _last_var(trace, "result")
    if result is None:
        errors.append("missing final method result variable")
    elif result[1].value != "7":
        errors.append(f"method result expected 7, got {result[1].value!r}")
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
    "inherited_virtual_object": SmokeCase(
        name="inherited_virtual_object",
        code=(
            "class Animal { public: int age; virtual int speak() { return age; } };\n"
            "class Dog : public Animal { public: int bones; int speak() override { return age + bones; } };\n"
            "Dog d;\n"
            "d.age = 3;\n"
            "d.bones = 4;\n"
            "Animal* a = &d;\n"
            "int sound = a->speak();\n"
        ),
        validate=_validate_inherited_virtual_object,
    ),
    "stack_array": SmokeCase(
        name="stack_array",
        code=(
            "int nums[3] = {1, 2, 3};\n"
            "nums[1] = 8;\n"
        ),
        validate=_validate_stack_array,
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
    "heap_polymorphic_delete": SmokeCase(
        name="heap_polymorphic_delete",
        code=(
            "class Animal { public: int age; virtual int speak() { return age; } virtual ~Animal() {} };\n"
            "class Dog : public Animal { public: int bones; int speak() override { return age + bones; } };\n"
            "Animal* a = new Dog();\n"
            "a->age = 3;\n"
            "static_cast<Dog*>(a)->bones = 4;\n"
            "int sound = a->speak();\n"
            "delete a;\n"
        ),
        validate=_validate_heap_polymorphic_delete,
    ),
    "heap_leak_overwrite": SmokeCase(
        name="heap_leak_overwrite",
        code=(
            "int* p = new int(1);\n"
            "p = new int(2);\n"
            "*p = 3;\n"
        ),
        validate=_validate_heap_leak_overwrite,
    ),
    "unique_ptr_heap": SmokeCase(
        name="unique_ptr_heap",
        code=(
            "#include <memory>\n"
            "using namespace std;\n"
            "unique_ptr<int> p = make_unique<int>(5);\n"
            "*p = 8;\n"
            "p.reset();\n"
        ),
        validate=_validate_unique_ptr_heap,
    ),
    "heap_array_delete": SmokeCase(
        name="heap_array_delete",
        code=(
            "int* arr = new int[3]{1, 2, 3};\n"
            "arr[1] = 9;\n"
            "delete[] arr;\n"
        ),
        validate=_validate_heap_array_delete,
    ),
    "pointer_reset_null": SmokeCase(
        name="pointer_reset_null",
        code=(
            "int* p = new int(5);\n"
            "delete p;\n"
            "p = nullptr;\n"
        ),
        validate=_validate_pointer_reset_null,
    ),
    "call_stack": SmokeCase(
        name="call_stack",
        code=(
            "int square(int x) {\n"
            "    int y = x * x;\n"
            "    return y;\n"
            "}\n"
            "int result = square(3);\n"
        ),
        validate=_validate_call_stack,
    ),
    "reference_stack_pointer": SmokeCase(
        name="reference_stack_pointer",
        code=(
            "int a = 4;\n"
            "int& r = a;\n"
            "r = 9;\n"
            "int* p = &a;\n"
            "*p = 11;\n"
        ),
        validate=_validate_reference_stack_pointer,
    ),
    "stack_dangling_pointer": SmokeCase(
        name="stack_dangling_pointer",
        code=(
            "int* p = nullptr;\n"
            "{\n"
            "    int local = 5;\n"
            "    p = &local;\n"
            "}\n"
            "int after = 9;\n"
        ),
        validate=_validate_stack_dangling_pointer,
    ),
    "double_pointer_stack": SmokeCase(
        name="double_pointer_stack",
        code=(
            "int a = 1;\n"
            "int *p = &a;\n"
            "int **pp = &p;\n"
            "**pp = 7;\n"
        ),
        validate=_validate_double_pointer_stack,
    ),
    "recursive_factorial": SmokeCase(
        name="recursive_factorial",
        code=(
            "int fact(int n) {\n"
            "    if (n <= 1) return 1;\n"
            "    int sub = fact(n - 1);\n"
            "    return n * sub;\n"
            "}\n"
            "int result = fact(3);\n"
        ),
        validate=_validate_recursive_call_stack,
    ),
    "object_method_call": SmokeCase(
        name="object_method_call",
        code=(
            "struct Counter {\n"
            "    int value;\n"
            "    int add(int delta) {\n"
            "        value += delta;\n"
            "        return value;\n"
            "    }\n"
            "};\n"
            "Counter c{2};\n"
            "int result = c.add(5);\n"
        ),
        validate=_validate_object_method_call,
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
    "vector_object": SmokeCase(
        name="vector_object",
        code=(
            "#include <vector>\n"
            "using namespace std;\n"
            "struct Node { int id; double weight; };\n"
            "vector<Node> nodes = {{1, 1.5}, {2, 2.5}};\n"
            "nodes[1].weight = 4.5;\n"
        ),
        validate=_validate_vector_object,
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
    "stdin_sum": SmokeCase(
        name="stdin_sum",
        code=(
            "#include <iostream>\n"
            "using namespace std;\n"
            "int x = 0;\n"
            "int y = 0;\n"
            "cin >> x >> y;\n"
            "int sum = x + y;\n"
        ),
        validate=_validate_stdin_sum,
        stdin_text="7 5\n",
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
        trace = DebugExecutor(preferred_backend=backend).run_code(case.code, case.stdin_text)
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
