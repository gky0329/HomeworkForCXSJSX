from __future__ import annotations

from typing import Iterable

from app.core.memory_model import StructMember


def visible_object_members(members: Iterable[StructMember]) -> list[StructMember]:
    return [member for member in members if member.name != "_vptr"]


def base_subobjects(
    base_classes: Iterable[str],
    members: Iterable[StructMember],
) -> list[tuple[str, StructMember | None]]:
    member_list = list(members)
    subobjects: list[tuple[str, StructMember | None]] = []
    for base in base_classes:
        base_name = base.strip()
        if not base_name:
            continue
        match = next(
            (
                member for member in member_list
                if member.name == base_name or member.type == base_name
            ),
            None,
        )
        subobjects.append((base_name, match))
    return subobjects


def derived_object_members(
    base_classes: Iterable[str],
    members: Iterable[StructMember],
) -> list[StructMember]:
    base_names = {base.strip() for base in base_classes if base.strip()}
    return [
        member for member in visible_object_members(members)
        if member.name not in base_names and member.type not in base_names
    ]


def vtable_rows(
    class_name: str,
    type_name: str,
    base_classes: Iterable[str],
    virtual_methods: Iterable[str],
) -> list[str]:
    dynamic_type = class_name or type_name or "dynamic type"
    rows: list[str] = []
    for index, method in enumerate(virtual_methods):
        method_name = method.strip()
        if not method_name:
            continue
        dispatch_target = method_name if "::" in method_name else f"{dynamic_type}::{method_name}"
        rows.append(f"slot[{index}] {method_name} -> {dispatch_target}")
    base_list = [base for base in base_classes if base]
    if base_list and rows:
        rows.append(f"{base_list[0]}* dispatch uses {dynamic_type} vtable")
    return rows
