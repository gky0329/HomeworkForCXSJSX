from pydantic import BaseModel, Field

from app.core.memory_model import (
    Variable, HeapBlock, PointerEdge, MemoryState,
)


class VarChange(BaseModel):
    address: str
    name: str
    old_value: str
    new_value: str


class HeapChange(BaseModel):
    address: str
    old_value: str
    new_value: str


class EdgeChange(BaseModel):
    source_address: str
    target_address: str
    was_dangling: bool
    is_dangling: bool


class DiffResult(BaseModel):
    added_vars: list[Variable] = Field(default_factory=list)
    removed_vars: list[Variable] = Field(default_factory=list)
    modified_vars: list[VarChange] = Field(default_factory=list)
    added_heap: list[HeapBlock] = Field(default_factory=list)
    removed_heap: list[HeapBlock] = Field(default_factory=list)
    freed_heap: list[HeapBlock] = Field(default_factory=list)
    modified_heap: list[HeapChange] = Field(default_factory=list)
    added_edges: list[PointerEdge] = Field(default_factory=list)
    removed_edges: list[PointerEdge] = Field(default_factory=list)
    modified_edges: list[EdgeChange] = Field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return any([
            self.added_vars, self.removed_vars, self.modified_vars,
            self.added_heap, self.removed_heap, self.freed_heap, self.modified_heap,
            self.added_edges, self.removed_edges, self.modified_edges,
        ])


class StateDiffEngine:
    @staticmethod
    def _flatten_vars(state: MemoryState) -> dict[str, Variable]:
        result: dict[str, Variable] = {}
        for frame in state.stack:
            for var in frame.variables:
                result[var.address] = var
        return result

    @staticmethod
    def _build_heap_map(state: MemoryState) -> dict[str, HeapBlock]:
        return {h.address: h for h in state.heap}

    @staticmethod
    def _build_edge_map(state: MemoryState) -> dict[tuple[str, str], PointerEdge]:
        return {(e.source_address, e.target_address): e for e in state.edges}

    @staticmethod
    def _changed(prev_item, curr_item) -> bool:
        return prev_item.model_dump() != curr_item.model_dump()

    @staticmethod
    def _heap_content_changed(prev_block: HeapBlock, curr_block: HeapBlock) -> bool:
        return (
            prev_block.model_dump(exclude={"is_freed"})
            != curr_block.model_dump(exclude={"is_freed"})
        )

    def diff(self, prev: MemoryState | None, curr: MemoryState) -> DiffResult:
        if prev is None:
            return DiffResult(
                added_vars=self._all_vars(curr),
                added_heap=list(curr.heap),
                added_edges=list(curr.edges),
            )

        result = DiffResult()

        prev_vars = self._flatten_vars(prev)
        curr_vars = self._flatten_vars(curr)

        for addr, var in curr_vars.items():
            if addr not in prev_vars:
                result.added_vars.append(var)
            elif self._changed(prev_vars[addr], var):
                result.modified_vars.append(VarChange(
                    address=addr,
                    name=var.name,
                    old_value=prev_vars[addr].value,
                    new_value=var.value,
                ))

        for addr, var in prev_vars.items():
            if addr not in curr_vars:
                result.removed_vars.append(var)

        prev_heap = self._build_heap_map(prev)
        curr_heap = self._build_heap_map(curr)

        for addr, block in curr_heap.items():
            if addr not in prev_heap:
                result.added_heap.append(block)
            elif self._heap_content_changed(prev_heap[addr], block):
                result.modified_heap.append(HeapChange(
                    address=addr,
                    old_value=prev_heap[addr].value,
                    new_value=block.value,
                ))

        for addr, block in prev_heap.items():
            if addr not in curr_heap:
                result.removed_heap.append(block)
            elif not block.is_freed and curr_heap[addr].is_freed:
                result.freed_heap.append(curr_heap[addr])
                result.removed_edges.extend([
                    e for e in prev.edges
                    if e.target_address == addr
                ])

        prev_edges = self._build_edge_map(prev)
        curr_edges = self._build_edge_map(curr)

        for key, edge in curr_edges.items():
            if key not in prev_edges:
                result.added_edges.append(edge)
            elif prev_edges[key].is_dangling != edge.is_dangling:
                result.modified_edges.append(EdgeChange(
                    source_address=edge.source_address,
                    target_address=edge.target_address,
                    was_dangling=prev_edges[key].is_dangling,
                    is_dangling=edge.is_dangling,
                ))

        for key, edge in prev_edges.items():
            if key not in curr_edges:
                result.removed_edges.append(edge)

        return result

    @staticmethod
    def _all_vars(state: MemoryState) -> list[Variable]:
        result = []
        for frame in state.stack:
            result.extend(frame.variables)
        return result
