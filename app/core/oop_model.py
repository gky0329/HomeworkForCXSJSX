from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemberDef:
    name: str
    type: str = "int"
    access: str = "public"


@dataclass
class ClassDef:
    name: str
    members: list[MemberDef] = field(default_factory=list)
    access: str = "public"

    def has_member(self, name: str) -> bool:
        return any(m.name == name for m in self.members)

    def get_member(self, name: str) -> MemberDef | None:
        for m in self.members:
            if m.name == name:
                return m
        return None


@dataclass
class ObjectInstance:
    cls_name: str
    var_name: str
    values: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.values:
            self.values = {}


class OopModel:

    def __init__(self) -> None:
        self.classes: dict[str, ClassDef] = {}
        self.instances: dict[str, ObjectInstance] = {}
        self.current_scope: str = "main"
        self._current_class: ClassDef | None = None
        self._current_access: str = "public"
        self._in_class_body: bool = False
        self._last_closed_class: str = ""

    def get_class(self, name: str) -> ClassDef | None:
        return self.classes.get(name)

    def get_instance(self, name: str) -> ObjectInstance | None:
        return self.instances.get(name)

    def add_class(self, cd: ClassDef) -> None:
        self.classes[cd.name] = cd

    def add_instance(self, inst: ObjectInstance) -> None:
        self.instances[inst.var_name] = inst

    def remove_instance(self, name: str) -> None:
        self.instances.pop(name, None)

    def snapshot(self) -> OopModel:
        import copy
        return copy.deepcopy(self)

    def reset(self) -> None:
        self.classes.clear()
        self.instances.clear()
        self.current_scope = "main"
