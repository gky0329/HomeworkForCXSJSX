from dataclasses import dataclass, field


@dataclass
class MemoryError:
    kind: str
    description: str
    block_id: str | None = None
    line: int = 0


@dataclass
class Annotation:
    kind: str
    text: str
    target: str = ""


@dataclass
class StateDiff:
    added_vars: list[tuple[str, "Variable"]] = field(default_factory=list)
    added_heap: list["HeapBlock"] = field(default_factory=list)
    added_edges: list["PointerEdge"] = field(default_factory=list)
    removed_vars: list[tuple[str, str]] = field(default_factory=list)
    freed_heap: list[str] = field(default_factory=list)
    removed_edges: list[tuple[str, str]] = field(default_factory=list)
    updated_vars: list[tuple[str, "Variable"]] = field(default_factory=list)
    errors: list[MemoryError] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)
    source_line: int = 0
    source_text: str = ""

    @property
    def is_empty(self) -> bool:
        return not any([
            self.added_vars, self.added_heap, self.added_edges,
            self.removed_vars, self.freed_heap, self.removed_edges,
            self.updated_vars, self.errors, self.annotations,
        ])

    @classmethod
    def empty(cls, line: int = 0, text: str = "") -> "StateDiff":
        return cls(source_line=line, source_text=text)
