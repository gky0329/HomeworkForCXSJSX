from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.oop_model import ClassDef, ObjectInstance


@dataclass
class ClassError:
    kind: str
    description: str
    class_name: str | None = None
    line: int = 0


@dataclass
class Annotation:
    kind: str
    text: str
    target: str = ""


@dataclass
class StateDiff:
    added_classes: list[ClassDef] = field(default_factory=list)
    added_instances: list[ObjectInstance] = field(default_factory=list)
    updated_instances: list[tuple[str, str, Any]] = field(default_factory=list)
    removed_instances: list[str] = field(default_factory=list)
    errors: list[ClassError] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)
    source_line: int = 0
    source_text: str = ""

    @property
    def is_empty(self) -> bool:
        return not any([
            self.added_classes,
            self.added_instances,
            self.updated_instances,
            self.removed_instances,
            self.errors,
            self.annotations,
        ])
