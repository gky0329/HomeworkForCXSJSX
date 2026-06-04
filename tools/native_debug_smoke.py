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
            {
                "index": element.index,
                "type": element.type,
                "value": element.value,
                "address": element.address,
            }
            for element in var.elements[:8]
        ],
        "is_object": var.is_object,
        "class_name": var.class_name,
        "base_classes": list(var.base_classes),
        "virtual_methods": list(var.virtual_methods),
        "members": [
            {
                "name": member.name,
                "type": member.type,
                "value": member.value,
                "address": member.address,
            }
            for member in var.members[:8]
        ],
        "captures": [
            {
                "name": capture.name,
                "type": capture.type,
                "value": capture.value,
                "by_ref": capture.by_ref,
            }
            for capture in var.captures[:8]
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
                    {
                        "name": member.name,
                        "type": member.type,
                        "value": member.value,
                        "address": member.address,
                    }
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


def _validate_std_array(trace: ExecutionTrace) -> list[str]:
    match = _last_var(trace, "a")
    if match is None:
        return ["missing std::array variable a"]
    _, var = match
    errors: list[str] = []
    if not var.is_array:
        errors.append("std::array a should be marked as an array/container")
    if var.is_object:
        errors.append("std::array a should not be marked as an object after unwrapping elements")
    values = [element.value for element in var.elements]
    if values != ["1", "8", "3"]:
        errors.append(f"std::array elements expected ['1', '8', '3'], got {values!r}")
    if var.members:
        errors.append("std::array should unwrap implementation storage instead of showing __elems_ as members")
    return errors


def _validate_std_array_object_pointer(trace: ExecutionTrace) -> list[str]:
    state = _last_observed_state(trace)
    if state is None:
        return ["trace has no observed state"]
    values = {var.name: var for var in _all_variables(state)}
    first = values.get("first")
    nodes = values.get("nodes")
    errors: list[str] = []
    if first is None:
        errors.append("missing Node variable first")
    elif _member_map(first).get("value") != "5":
        errors.append(f"first.value expected 5 after nodes[1].next write, got {_member_map(first).get('value')!r}")
    if nodes is None:
        errors.append("missing std::array<Node> variable nodes")
        return errors
    if not nodes.is_array:
        errors.append("nodes should be marked as an array/container")
    if nodes.is_object:
        errors.append("nodes should not be marked as an object after element expansion")
    if nodes.members:
        errors.append("nodes should unwrap elements instead of showing implementation members")
    elements = list(nodes.elements)
    if len(elements) != 2:
        errors.append(f"nodes expected 2 elements, got {[(e.index, e.value) for e in elements]!r}")
    elif first is not None:
        second_value = elements[1].value
        if f"next={first.address}" not in second_value:
            errors.append(f"nodes[1].next should map to {first.address}, got {second_value!r}")
        if "0000" in second_value:
            errors.append(f"nodes[1] should not expose raw debugger addresses, got {second_value!r}")
        if not any(edge.source_address == elements[1].address and edge.target_address == first.address for edge in state.edges):
            errors.append("missing nodes[1] -> first pointer edge")
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


def _validate_vector_pointer(trace: ExecutionTrace) -> list[str]:
    match = _last_var(trace, "ptrs")
    if match is None:
        return ["missing vector pointer variable ptrs"]
    state, var = match
    errors: list[str] = []
    if not var.is_array:
        errors.append("ptrs should be marked as an array/container")
    if var.is_pointer:
        errors.append("ptrs should not be marked as a pointer")
    if var.is_object:
        errors.append("ptrs should not be marked as an object after element expansion")
    if var.members:
        errors.append("ptrs should show pointer elements instead of implementation members")
    elements = list(var.elements)
    values = [element.value for element in elements]
    if len(elements) != 2:
        errors.append(f"ptrs expected 2 pointer elements, got {values!r}")
    elif not all(value.startswith("0x") for value in values):
        errors.append(f"ptrs element values should be addresses, got {values!r}")
    if elements and not all(element.type.endswith("*") for element in elements):
        errors.append(f"ptrs element types should be pointer types, got {[element.type for element in elements]!r}")
    if elements and not all(element.address for element in elements):
        errors.append("ptrs elements should expose stable cell addresses")
    b_match = _last_var(trace, "b")
    a_match = _last_var(trace, "a")
    if b_match is None:
        errors.append("missing b variable after *ptrs[1] write")
    elif b_match[1].value != "9":
        errors.append(f"b expected 9 after *ptrs[1] write, got {b_match[1].value!r}")
    if any(edge.source_address == var.address for edge in state.edges):
        errors.append("ptrs container itself should not own a pointer edge")
    if a_match is not None and b_match is not None and len(elements) == 2:
        expected_edges = {
            (elements[0].address, a_match[1].address),
            (elements[1].address, b_match[1].address),
        }
        actual_edges = {
            (edge.source_address, edge.target_address)
            for edge in state.edges
        }
        missing = expected_edges - actual_edges
        if missing:
            errors.append(f"missing ptrs element pointer edges: {sorted(missing)!r}")
    return errors


def _validate_optional_pointer(trace: ExecutionTrace) -> list[str]:
    match = _last_var(trace, "op")
    if match is None:
        return ["missing optional pointer variable op"]
    state, var = match
    errors: list[str] = []
    if not var.is_object:
        errors.append("op should be marked as an object with an engaged value")
    if var.class_name != "optional<int*>":
        errors.append(f"op class_name expected optional<int*>, got {var.class_name!r}")
    if len(var.members) != 1:
        errors.append(f"op expected one value member, got {[(m.name, m.type, m.value) for m in var.members]!r}")
        return errors
    value_member = var.members[0]
    if value_member.name != "value":
        errors.append(f"op member name expected value, got {value_member.name!r}")
    if value_member.type != "int*":
        errors.append(f"op value member type expected int*, got {value_member.type!r}")
    a_match = _last_var(trace, "a")
    if a_match is None:
        errors.append("missing a variable after optional pointer write")
        return errors
    a = a_match[1]
    if a.value != "5":
        errors.append(f"a expected 5 after *op.value() write, got {a.value!r}")
    if value_member.value != a.address:
        errors.append(f"op value member should point to a, got {value_member.value!r}")
    if not any(
        edge.source_address == value_member.address and edge.target_address == a.address
        for edge in state.edges
    ):
        errors.append("missing op.value -> a pointer edge")
    return errors


def _validate_stack_adapter(trace: ExecutionTrace) -> list[str]:
    match = _last_var(trace, "s")
    if match is None:
        return ["missing stack variable s"]
    _, var = match
    errors: list[str] = []
    if not var.is_array:
        errors.append("stack s should be marked as an array/container")
    values = [element.value for element in var.elements]
    if values != ["1"]:
        errors.append(f"stack elements expected ['1'] after pop, got {values!r}")
    if var.members:
        errors.append("stack should unwrap adapter storage instead of showing c as a member")
    return errors


def _validate_priority_queue_adapter(trace: ExecutionTrace) -> list[str]:
    match = _last_var(trace, "pq")
    if match is None:
        return ["missing priority_queue variable pq"]
    _, var = match
    errors: list[str] = []
    if not var.is_array:
        errors.append("priority_queue pq should be marked as an array/container")
    values = [element.value for element in var.elements]
    if values != ["3", "1", "2"]:
        errors.append(f"priority_queue storage expected ['3', '1', '2'], got {values!r}")
    if var.members:
        errors.append("priority_queue should unwrap adapter storage instead of showing c as a member")
    return errors


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


def _validate_map_pointer(trace: ExecutionTrace) -> list[str]:
    match = _last_var(trace, "m")
    if match is None:
        return ["missing pointer map variable m"]
    state, var = match
    errors: list[str] = []
    if not var.is_array:
        errors.append("m should be marked as an array/container")
    elements = list(var.elements)
    if len(elements) != 2:
        errors.append(f"m expected 2 key/value entries, got {[element.value for element in elements]!r}")
        return errors
    a_match = _last_var(trace, "a")
    b_match = _last_var(trace, "b")
    if a_match is None or b_match is None:
        errors.append("missing a or b variable after map pointer write")
        return errors
    a = a_match[1]
    b = b_match[1]
    if b.value != "9":
        errors.append(f"b expected 9 after *m[\"b\"] write, got {b.value!r}")
    values = [element.value for element in elements]
    if not any("first=a" in value and f"second={a.address}" in value for value in values):
        errors.append(f"m missing a pointer entry: {values!r}")
    if not any("first=b" in value and f"second={b.address}" in value for value in values):
        errors.append(f"m missing b pointer entry: {values!r}")
    expected_edges = {
        (elements[0].address, a.address),
        (elements[1].address, b.address),
    }
    actual_edges = {
        (edge.source_address, edge.target_address)
        for edge in state.edges
    }
    missing = expected_edges - actual_edges
    if missing:
        errors.append(f"missing map entry pointer edges: {sorted(missing)!r}")
    return errors


def _validate_map_unique_ptr(trace: ExecutionTrace) -> list[str]:
    match = _last_var(trace, "m")
    if match is None:
        return ["missing map unique_ptr variable m"]
    state, var = match
    errors: list[str] = []
    if not var.is_array:
        errors.append("m should be marked as an array/container")
    if var.is_pointer:
        errors.append("m should not be marked as a pointer")
    elements = list(var.elements)
    if len(elements) != 1:
        errors.append(f"m expected one key/value entry, got {[element.value for element in elements]!r}")
        return errors
    element = elements[0]
    if "first=a" not in element.value or "second=0xH" not in element.value:
        errors.append(f"m missing unique_ptr entry target: {element.value!r}")
        return errors
    target = next((edge.target_address for edge in state.edges if edge.source_address == element.address), "")
    if not target:
        errors.append("missing m entry -> unique_ptr heap edge")
        return errors
    target_heap = next((block for block in state.heap if block.address == target), None)
    if target_heap is None:
        errors.append(f"missing heap block for map unique_ptr target {target!r}")
    elif target_heap.value != "8":
        errors.append(f"map unique_ptr heap value expected 8 after *m[\"a\"] write, got {target_heap.value!r}")
    return errors


def _validate_map_unique_ptr_object(trace: ExecutionTrace) -> list[str]:
    state = _last_observed_state(trace)
    if state is None:
        return ["trace has no observed state"]
    values = {var.name: var for var in _all_variables(state)}
    first = values.get("first")
    match = _last_var(trace, "m")
    if match is None:
        return ["missing map unique_ptr object variable m"]
    _, var = match
    errors: list[str] = []
    if first is None:
        errors.append("missing stack object first")
    elif _member_map(first).get("value") != "6":
        errors.append(f"first.value expected 6 after m[\"n\"]->next write, got {_member_map(first).get('value')!r}")
    if not var.is_array:
        errors.append("m should be marked as an array/container")
    elements = list(var.elements)
    if len(elements) != 1:
        errors.append(f"m expected one key/value entry, got {[element.value for element in elements]!r}")
        return errors
    element = elements[0]
    if "first=n" not in element.value or "second=0xH" not in element.value:
        errors.append(f"m missing unique_ptr object entry target: {element.value!r}")
        return errors
    target = next((edge.target_address for edge in state.edges if edge.source_address == element.address), "")
    if not target:
        errors.append("missing m entry -> unique_ptr object heap edge")
        return errors
    heap = next((block for block in state.heap if block.address == target), None)
    if heap is None:
        errors.append(f"missing heap object for map unique_ptr target {target!r}")
        return errors
    if not heap.is_object or heap.class_name != "Node":
        errors.append(f"map unique_ptr target should be Node object, got class={heap.class_name!r} object={heap.is_object}")
    members = {member.name: member for member in heap.members}
    if members.get("value") is None or members["value"].value != "2":
        errors.append(f"heap Node.value expected 2, got {members.get('value').value if members.get('value') else None!r}")
    next_member = members.get("next")
    if first is not None:
        if next_member is None or next_member.value != first.address:
            errors.append(f"heap Node.next should target first {first.address!r}, got {next_member.value if next_member else None!r}")
        elif not any(edge.source_address == next_member.address and edge.target_address == first.address for edge in state.edges):
            errors.append("missing heap Node.next -> first pointer edge")
    return errors


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


def _validate_shared_ptr_owners(trace: ExecutionTrace) -> list[str]:
    errors: list[str] = []
    shared_state = next(
        (
            state for state in trace.steps
            if {"a", "b"}.issubset({var.name for var in _all_variables(state)})
            and len([edge for edge in state.edges if not edge.is_dangling]) >= 2
        ),
        None,
    )
    if shared_state is None:
        errors.append("missing shared_ptr state with two live owners")
    else:
        values = {var.name: var for var in _all_variables(shared_state)}
        a = values.get("a")
        b = values.get("b")
        if a is None or b is None:
            errors.append("missing shared_ptr variables a and b")
        else:
            if not a.is_pointer or not b.is_pointer:
                errors.append("shared_ptr owners should be rendered as pointer-like variables")
            if a.value != b.value:
                errors.append(f"a and b should target the same heap block, got {a.value!r} and {b.value!r}")
            owner_edges = [
                edge for edge in shared_state.edges
                if edge.target_address == a.value and edge.source_address in {a.address, b.address}
            ]
            if len(owner_edges) != 2:
                errors.append(f"expected two owner edges to shared heap, got {len(owner_edges)}")

    reset_state = next(
        (
            state for state in trace.steps
            if state.source_code.strip() == "a.reset();"
        ),
        None,
    )
    if reset_state is None:
        errors.append("missing a.reset() state")
    else:
        values = {var.name: var for var in _all_variables(reset_state)}
        a = values.get("a")
        b = values.get("b")
        if a is None or b is None:
            errors.append("missing shared_ptr variables after reset")
        else:
            if a.value != "nullptr":
                errors.append(f"a expected nullptr after reset, got {a.value!r}")
            if b.value == "nullptr":
                errors.append("b should still own the heap after a.reset()")
            if not any(edge.source_address == b.address and edge.target_address == b.value for edge in reset_state.edges):
                errors.append("missing b -> heap edge after a.reset()")
            if any(edge.source_address == a.address for edge in reset_state.edges):
                errors.append("a should not keep an owner edge after reset")

    final_state = _last_observed_state(trace)
    if final_state is None:
        return errors + ["trace has no observed state"]
    final_heap_values = {block.value for block in final_state.heap if not block.is_freed}
    if "11" not in final_heap_values:
        errors.append(f"final shared heap value expected 11, got {sorted(final_heap_values)!r}")
    return errors


def _validate_vector_shared_ptr(trace: ExecutionTrace) -> list[str]:
    state = _last_observed_state(trace)
    if state is None:
        return ["trace has no observed state"]
    values = {var.name: var for var in _all_variables(state)}
    alias = values.get("alias")
    xs = values.get("xs")
    errors: list[str] = []
    if alias is None:
        errors.append("missing shared_ptr alias variable")
    elif not alias.is_pointer:
        errors.append("alias should be rendered as a pointer-like owner")
    if xs is None:
        errors.append("missing vector<shared_ptr<int>> variable xs")
        return errors
    if not xs.is_array:
        errors.append("xs should be marked as an array/container")
    if xs.is_pointer:
        errors.append("xs should not be marked as a pointer")
    if xs.is_object:
        errors.append("xs should not be marked as an object after element expansion")
    if xs.members:
        errors.append("xs should show shared_ptr elements instead of implementation members")
    elements = list(xs.elements)
    if len(elements) != 1:
        errors.append(f"xs expected one shared_ptr element, got {[element.value for element in elements]!r}")
        return errors
    element = elements[0]
    if "shared_ptr" not in element.type:
        errors.append(f"xs[0] type should be shared_ptr, got {element.type!r}")
    if alias is not None:
        if element.value != alias.value:
            errors.append(f"xs[0] should target alias heap {alias.value!r}, got {element.value!r}")
        if any(edge.source_address == xs.address for edge in state.edges):
            errors.append("xs container itself should not own a pointer edge")
        if not any(edge.source_address == element.address and edge.target_address == alias.value for edge in state.edges):
            errors.append("missing xs[0] -> alias heap edge")
        if not any(edge.source_address == alias.address and edge.target_address == alias.value for edge in state.edges):
            errors.append("missing alias -> heap edge")
        target_heap = next((block for block in state.heap if block.address == alias.value), None)
        if target_heap is None:
            errors.append(f"missing heap block for vector shared_ptr target {alias.value!r}")
        elif target_heap.value != "8":
            errors.append(f"shared heap value expected 8 after *xs[0] write, got {target_heap.value!r}")
    return errors


def _validate_vector_unique_ptr(trace: ExecutionTrace) -> list[str]:
    state = _last_observed_state(trace)
    if state is None:
        return ["trace has no observed state"]
    values = {var.name: var for var in _all_variables(state)}
    xs = values.get("xs")
    errors: list[str] = []
    if xs is None:
        return ["missing vector<unique_ptr<int>> variable xs"]
    if not xs.is_array:
        errors.append("xs should be marked as an array/container")
    if xs.is_pointer:
        errors.append("xs should not be marked as a pointer")
    elements = list(xs.elements)
    if len(elements) != 1:
        errors.append(f"xs expected one unique_ptr element, got {[element.value for element in elements]!r}")
        return errors
    element = elements[0]
    if "unique_ptr" not in element.type:
        errors.append(f"xs[0] type should be unique_ptr, got {element.type!r}")
    if not element.value.startswith("0xH"):
        errors.append(f"xs[0] should target a heap block, got {element.value!r}")
        return errors
    target_heap = next((block for block in state.heap if block.address == element.value), None)
    if target_heap is None:
        errors.append(f"missing heap block for vector unique_ptr target {element.value!r}")
    elif target_heap.value != "8":
        errors.append(f"unique_ptr heap value expected 8 after *xs[0] write, got {target_heap.value!r}")
    if not any(edge.source_address == element.address and edge.target_address == element.value for edge in state.edges):
        errors.append("missing xs[0] -> unique_ptr heap edge")
    return errors


def _validate_vector_unique_ptr_object(trace: ExecutionTrace) -> list[str]:
    state = _last_observed_state(trace)
    if state is None:
        return ["trace has no observed state"]
    values = {var.name: var for var in _all_variables(state)}
    first = values.get("first")
    nodes = values.get("nodes")
    errors: list[str] = []
    if first is None:
        errors.append("missing stack object first")
    elif _member_map(first).get("value") != "6":
        errors.append(f"first.value expected 6 after nodes[0]->next write, got {_member_map(first).get('value')!r}")
    if nodes is None:
        return errors + ["missing vector<unique_ptr<Node>> variable nodes"]
    if not nodes.is_array:
        errors.append("nodes should be marked as an array/container")
    elements = list(nodes.elements)
    if len(elements) != 1:
        errors.append(f"nodes expected one unique_ptr element, got {[element.value for element in elements]!r}")
        return errors
    element = elements[0]
    if "unique_ptr" not in element.type:
        errors.append(f"nodes[0] type should be unique_ptr, got {element.type!r}")
    target = element.value
    if not target.startswith("0xH"):
        errors.append(f"nodes[0] should target object heap, got {target!r}")
        return errors
    heap = next((block for block in state.heap if block.address == target), None)
    if heap is None:
        errors.append(f"missing heap object for vector unique_ptr target {target!r}")
        return errors
    if not heap.is_object or heap.class_name != "Node":
        errors.append(f"unique_ptr target should be Node object, got class={heap.class_name!r} object={heap.is_object}")
    members = {member.name: member for member in heap.members}
    if members.get("value") is None or members["value"].value != "2":
        errors.append(f"heap Node.value expected 2, got {members.get('value').value if members.get('value') else None!r}")
    next_member = members.get("next")
    if first is not None:
        if next_member is None or next_member.value != first.address:
            errors.append(f"heap Node.next should target first {first.address!r}, got {next_member.value if next_member else None!r}")
        elif not any(edge.source_address == next_member.address and edge.target_address == first.address for edge in state.edges):
            errors.append("missing heap Node.next -> first pointer edge")
    if not any(edge.source_address == element.address and edge.target_address == target for edge in state.edges):
        errors.append("missing nodes[0] -> object heap edge")
    return errors


def _validate_std_array_shared_ptr(trace: ExecutionTrace) -> list[str]:
    state = _last_observed_state(trace)
    if state is None:
        return ["trace has no observed state"]
    values = {var.name: var for var in _all_variables(state)}
    alias = values.get("alias")
    xs = values.get("xs")
    errors: list[str] = []
    if alias is None:
        errors.append("missing shared_ptr alias variable")
    elif not alias.is_pointer:
        errors.append("alias should be rendered as a pointer-like owner")
    if xs is None:
        return errors + ["missing array<shared_ptr<int>,2> variable xs"]
    if not xs.is_array:
        errors.append("xs should be marked as an array/container")
    if xs.is_pointer:
        errors.append("xs should not be marked as a pointer")
    if xs.is_object:
        errors.append("xs should not be marked as an object after element expansion")
    elements = list(xs.elements)
    if len(elements) != 2:
        errors.append(f"xs expected two shared_ptr elements, got {[element.value for element in elements]!r}")
        return errors
    if alias is not None:
        if elements[0].value != alias.value:
            errors.append(f"xs[0] should target alias heap {alias.value!r}, got {elements[0].value!r}")
        if elements[1].value != "nullptr":
            errors.append(f"xs[1] should be nullptr, got {elements[1].value!r}")
        if not any(edge.source_address == elements[0].address and edge.target_address == alias.value for edge in state.edges):
            errors.append("missing xs[0] -> alias heap edge")
        target_heap = next((block for block in state.heap if block.address == alias.value), None)
        if target_heap is None:
            errors.append(f"missing heap block for std::array shared_ptr target {alias.value!r}")
        elif target_heap.value != "8":
            errors.append(f"shared heap value expected 8 after *xs[0] write, got {target_heap.value!r}")
    return errors


def _validate_weak_ptr_expired(trace: ExecutionTrace) -> list[str]:
    final_state = _last_observed_state(trace)
    if final_state is None:
        return ["trace has no observed state"]
    values = {var.name: var for var in _all_variables(final_state)}
    sp = values.get("sp")
    wp = values.get("wp")
    gone = values.get("gone")
    errors: list[str] = []
    if sp is None:
        errors.append("missing shared_ptr variable sp")
    elif sp.value != "nullptr":
        errors.append(f"sp expected nullptr after reset, got {sp.value!r}")
    if wp is None:
        errors.append("missing weak_ptr variable wp")
        return errors
    if not wp.is_pointer:
        errors.append("weak_ptr wp should render as pointer-like")
    if gone is None:
        errors.append("missing gone bool from wp.expired()")
    elif gone.value != "true":
        errors.append(f"gone expected true after owner reset, got {gone.value!r}")

    target_heap = next((block for block in final_state.heap if block.address == wp.value), None)
    if target_heap is None:
        errors.append(f"missing historical heap block for expired weak_ptr target {wp.value!r}")
    else:
        if not target_heap.is_freed:
            errors.append("expired weak_ptr target heap should be marked freed")
        if target_heap.value != "3":
            errors.append(f"expired weak_ptr target value expected 3, got {target_heap.value!r}")
    dangling_edges = [
        edge for edge in final_state.edges
        if edge.source_address == wp.address and edge.target_address == wp.value and edge.is_dangling
    ]
    if not dangling_edges:
        errors.append("missing dangling wp -> expired heap edge")
    if sp is not None and any(edge.source_address == sp.address for edge in final_state.edges):
        errors.append("reset shared_ptr sp should not keep an owner edge")
    return errors


def _validate_control_flow_loop(trace: ExecutionTrace) -> list[str]:
    errors: list[str] = []
    if_state_values: list[int] = []
    body_count = 0
    parity_updates: list[str] = []
    for state in trace.steps:
        values = {var.name: var.value for var in _all_variables(state)}
        if state.source_code.strip().startswith("if ") and "i" in values:
            try:
                if_state_values.append(int(values["i"]))
            except ValueError:
                errors.append(f"loop i should be numeric, got {values['i']!r}")
        if state.source_code.strip() == "sum += i;":
            body_count += 1
        if state.source_code.strip() == "parity += i;":
            parity_updates.append(values.get("parity", ""))

    if if_state_values != [1, 2, 3, 4]:
        errors.append(f"if branch should observe i values [1, 2, 3, 4], got {if_state_values!r}")
    if body_count != 4:
        errors.append(f"sum loop body should execute 4 times, got {body_count}")
    if parity_updates != ["2", "6"]:
        errors.append(f"parity updates expected ['2', '6'], got {parity_updates!r}")

    final_state = _last_observed_state(trace)
    if final_state is None:
        return errors + ["trace has no observed state"]
    values = {var.name: var.value for var in _all_variables(final_state)}
    if values.get("sum") != "10":
        errors.append(f"final sum expected 10, got {values.get('sum')!r}")
    if values.get("parity") != "6":
        errors.append(f"final parity expected 6, got {values.get('parity')!r}")
    if "i" in values:
        errors.append("loop variable i should be out of scope in final state")
    return errors


def _validate_lambda_capture(trace: ExecutionTrace) -> list[str]:
    errors: list[str] = []
    state = _last_observed_state(trace)
    if state is None:
        return ["trace has no observed state"]
    values = {var.name: var for var in _all_variables(state)}
    fn = values.get("f")
    factor = values.get("factor")
    result = values.get("result")
    if fn is None:
        errors.append("missing lambda variable f")
    else:
        if not fn.is_function_object:
            errors.append("f should be marked as a function object")
        captures = {capture.name: capture for capture in fn.captures}
        base_capture = captures.get("base")
        factor_capture = captures.get("factor")
        if base_capture is None or base_capture.by_ref:
            errors.append("base capture should exist by value")
        elif base_capture.value != "3":
            errors.append(f"base capture expected 3, got {base_capture.value!r}")
        if factor_capture is None:
            errors.append("factor capture should exist")
        elif not factor_capture.by_ref:
            errors.append("factor capture should be by reference")
        elif factor is not None and factor_capture.value != factor.address:
            errors.append(f"factor capture should target factor address {factor.address}, got {factor_capture.value!r}")
    if factor is None:
        errors.append("missing factor variable")
    elif factor.value != "7":
        errors.append(f"factor expected 7 before lambda call, got {factor.value!r}")
    if result is None:
        errors.append("missing lambda call result")
    elif result.value != "16":
        errors.append(f"result expected 16, got {result.value!r}")
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


def _validate_member_pointer_linked_list(trace: ExecutionTrace) -> list[str]:
    errors: list[str] = []
    state = _last_observed_state(trace)
    if state is None:
        return ["trace has no observed state"]
    values = {var.name: var for var in _all_variables(state)}
    first = values.get("first")
    second = values.get("second")
    head = values.get("head")
    if first is None:
        errors.append("missing linked-list node first")
    elif _member_map(first).get("value") != "3":
        errors.append(f"first.value expected 3 after head->next write, got {_member_map(first).get('value')!r}")
    if second is None:
        errors.append("missing linked-list node second")
    else:
        next_members = [member for member in second.members if member.name == "next"]
        if not next_members:
            errors.append("second.next member should exist")
        elif first is not None:
            next_member = next_members[0]
            if next_member.value != first.address:
                errors.append(f"second.next should target first address {first.address}, got {next_member.value!r}")
            if not next_member.address:
                errors.append("second.next should have a member source address")
            elif not any(
                edge.source_address == next_member.address and edge.target_address == first.address
                for edge in state.edges
            ):
                errors.append("missing second.next -> first member pointer edge")
    if head is None:
        errors.append("missing head pointer")
    elif second is not None:
        if head.value != second.address:
            errors.append(f"head should target second address {second.address}, got {head.value!r}")
        if not any(edge.source_address == head.address and edge.target_address == second.address for edge in state.edges):
            errors.append("missing head -> second pointer edge")
    return errors


def _validate_heap_member_pointer_linked_list(trace: ExecutionTrace) -> list[str]:
    errors: list[str] = []
    state = _last_observed_state(trace)
    if state is None:
        return ["trace has no observed state"]
    values = {var.name: var for var in _all_variables(state)}
    first_ptr = values.get("first")
    second_ptr = values.get("second")
    if first_ptr is None or second_ptr is None:
        errors.append("missing heap linked-list pointer variables first and second")
        return errors
    first_heap = next((block for block in state.heap if block.address == first_ptr.value), None)
    second_heap = next((block for block in state.heap if block.address == second_ptr.value), None)
    if first_heap is None:
        errors.append(f"missing first heap node {first_ptr.value}")
    if second_heap is None:
        errors.append(f"missing second heap node {second_ptr.value}")
    if first_heap is not None:
        if _member_map(first_heap).get("value") != "4":
            errors.append(f"first heap value expected 4, got {_member_map(first_heap).get('value')!r}")
        if not first_heap.is_freed:
            errors.append("first heap node should remain visible as freed after delete first")
    if second_heap is not None:
        if not second_heap.is_freed:
            errors.append("second heap node should remain visible as freed after delete second")
        next_members = [member for member in second_heap.members if member.name == "next"]
        if not next_members:
            errors.append("second heap node should keep next member")
        elif first_heap is not None:
            next_member = next_members[0]
            if next_member.value != first_heap.address:
                errors.append(f"second heap next should still target first heap {first_heap.address}, got {next_member.value!r}")
            if not next_member.address:
                errors.append("second heap next should have a member source address")
            elif not any(
                edge.source_address == next_member.address
                and edge.target_address == first_heap.address
                and edge.is_dangling
                for edge in state.edges
            ):
                errors.append("missing dangling second heap next -> first heap edge after delete first")
    if not any(edge.source_address == first_ptr.address and edge.target_address == first_ptr.value and edge.is_dangling for edge in state.edges):
        errors.append("missing dangling first pointer edge after delete first")
    if not any(edge.source_address == second_ptr.address and edge.target_address == second_ptr.value and edge.is_dangling for edge in state.edges):
        errors.append("missing dangling second pointer edge after delete second")
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
    "std_array": SmokeCase(
        name="std_array",
        code=(
            "#include <array>\n"
            "using namespace std;\n"
            "array<int,3> a = {1, 2, 3};\n"
            "a[1] = 8;\n"
        ),
        validate=_validate_std_array,
    ),
    "std_array_object_pointer": SmokeCase(
        name="std_array_object_pointer",
        code=(
            "#include <array>\n"
            "using namespace std;\n"
            "struct Node { int value; Node* next; };\n"
            "Node first{1, nullptr};\n"
            "Node second{2, &first};\n"
            "array<Node,2> nodes = {first, second};\n"
            "nodes[1].next->value = 5;\n"
        ),
        validate=_validate_std_array_object_pointer,
    ),
    "stack_int": SmokeCase(
        name="stack_int",
        code=(
            "#include <stack>\n"
            "using namespace std;\n"
            "stack<int> s;\n"
            "s.push(1);\n"
            "s.push(2);\n"
            "s.pop();\n"
        ),
        validate=_validate_stack_adapter,
    ),
    "priority_queue_int": SmokeCase(
        name="priority_queue_int",
        code=(
            "#include <queue>\n"
            "using namespace std;\n"
            "priority_queue<int> pq;\n"
            "pq.push(1);\n"
            "pq.push(3);\n"
            "pq.push(2);\n"
        ),
        validate=_validate_priority_queue_adapter,
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
    "shared_ptr_owners": SmokeCase(
        name="shared_ptr_owners",
        code=(
            "#include <memory>\n"
            "using namespace std;\n"
            "shared_ptr<int> a = make_shared<int>(5);\n"
            "shared_ptr<int> b = a;\n"
            "*b = 9;\n"
            "a.reset();\n"
            "*b = 11;\n"
        ),
        validate=_validate_shared_ptr_owners,
    ),
    "vector_shared_ptr": SmokeCase(
        name="vector_shared_ptr",
        code=(
            "#include <memory>\n"
            "#include <vector>\n"
            "using namespace std;\n"
            "shared_ptr<int> alias = make_shared<int>(5);\n"
            "vector<shared_ptr<int>> xs = {alias};\n"
            "*xs[0] = 8;\n"
        ),
        validate=_validate_vector_shared_ptr,
    ),
    "vector_unique_ptr": SmokeCase(
        name="vector_unique_ptr",
        code=(
            "#include <memory>\n"
            "#include <vector>\n"
            "using namespace std;\n"
            "vector<unique_ptr<int>> xs;\n"
            "xs.push_back(make_unique<int>(5));\n"
            "*xs[0] = 8;\n"
        ),
        validate=_validate_vector_unique_ptr,
    ),
    "vector_unique_ptr_object": SmokeCase(
        name="vector_unique_ptr_object",
        code=(
            "#include <memory>\n"
            "#include <vector>\n"
            "using namespace std;\n"
            "struct Node { int value; Node* next; };\n"
            "Node first{1,nullptr};\n"
            "vector<unique_ptr<Node>> nodes;\n"
            "nodes.push_back(make_unique<Node>(Node{2,&first}));\n"
            "nodes[0]->next->value = 6;\n"
        ),
        validate=_validate_vector_unique_ptr_object,
    ),
    "std_array_shared_ptr": SmokeCase(
        name="std_array_shared_ptr",
        code=(
            "#include <array>\n"
            "#include <memory>\n"
            "using namespace std;\n"
            "shared_ptr<int> alias = make_shared<int>(5);\n"
            "array<shared_ptr<int>,2> xs = {alias, nullptr};\n"
            "*xs[0] = 8;\n"
        ),
        validate=_validate_std_array_shared_ptr,
    ),
    "weak_ptr_expired": SmokeCase(
        name="weak_ptr_expired",
        code=(
            "#include <memory>\n"
            "using namespace std;\n"
            "shared_ptr<int> sp = make_shared<int>(3);\n"
            "weak_ptr<int> wp = sp;\n"
            "sp.reset();\n"
            "bool gone = wp.expired();\n"
        ),
        validate=_validate_weak_ptr_expired,
    ),
    "control_flow_loop": SmokeCase(
        name="control_flow_loop",
        code=(
            "int sum = 0;\n"
            "int parity = 0;\n"
            "for (int i = 1; i <= 4; ++i) {\n"
            "    if (i % 2 == 0) {\n"
            "        parity += i;\n"
            "    }\n"
            "    sum += i;\n"
            "}\n"
        ),
        validate=_validate_control_flow_loop,
    ),
    "lambda_capture": SmokeCase(
        name="lambda_capture",
        code=(
            "int base = 3;\n"
            "int factor = 4;\n"
            "auto f = [base, &factor](int x) { return base + factor + x; };\n"
            "factor = 7;\n"
            "int result = f(6);\n"
        ),
        validate=_validate_lambda_capture,
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
    "member_pointer_linked_list": SmokeCase(
        name="member_pointer_linked_list",
        code=(
            "struct Node { int value; Node* next; };\n"
            "Node first{1, nullptr};\n"
            "Node second{2, &first};\n"
            "Node* head = &second;\n"
            "head->next->value = 3;\n"
        ),
        validate=_validate_member_pointer_linked_list,
    ),
    "heap_member_pointer_linked_list": SmokeCase(
        name="heap_member_pointer_linked_list",
        code=(
            "struct Node { int value; Node* next; };\n"
            "Node* first = new Node{1, nullptr};\n"
            "Node* second = new Node{2, first};\n"
            "second->next->value = 4;\n"
            "delete second;\n"
            "delete first;\n"
        ),
        validate=_validate_heap_member_pointer_linked_list,
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
    "vector_pointer_stack": SmokeCase(
        name="vector_pointer_stack",
        code=(
            "#include <vector>\n"
            "using namespace std;\n"
            "int a = 1;\n"
            "int b = 2;\n"
            "vector<int*> ptrs = {&a, &b};\n"
            "*ptrs[1] = 9;\n"
        ),
        validate=_validate_vector_pointer,
    ),
    "optional_pointer": SmokeCase(
        name="optional_pointer",
        code=(
            "#include <optional>\n"
            "using namespace std;\n"
            "int a = 1;\n"
            "optional<int*> op = &a;\n"
            "*op.value() = 5;\n"
        ),
        validate=_validate_optional_pointer,
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
    "map_string_pointer": SmokeCase(
        name="map_string_pointer",
        code=(
            "#include <map>\n"
            "#include <string>\n"
            "using namespace std;\n"
            "int a = 1;\n"
            "int b = 2;\n"
            "map<string, int*> m;\n"
            'm["a"] = &a;\n'
            'm["b"] = &b;\n'
            '*m["b"] = 9;\n'
        ),
        validate=_validate_map_pointer,
    ),
    "map_string_unique_ptr": SmokeCase(
        name="map_string_unique_ptr",
        code=(
            "#include <map>\n"
            "#include <memory>\n"
            "#include <string>\n"
            "using namespace std;\n"
            "map<string, unique_ptr<int>> m;\n"
            'm["a"] = make_unique<int>(5);\n'
            '*m["a"] = 8;\n'
        ),
        validate=_validate_map_unique_ptr,
    ),
    "map_string_unique_ptr_object": SmokeCase(
        name="map_string_unique_ptr_object",
        code=(
            "#include <map>\n"
            "#include <memory>\n"
            "#include <string>\n"
            "using namespace std;\n"
            "struct Node { int value; Node* next; };\n"
            "Node first{1,nullptr};\n"
            "map<string, unique_ptr<Node>> m;\n"
            'm["n"] = make_unique<Node>(Node{2,&first});\n'
            'm["n"]->next->value = 6;\n'
        ),
        validate=_validate_map_unique_ptr_object,
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
