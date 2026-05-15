from pydantic import BaseModel, Field
from typing import List


class Variable(BaseModel):
    name: str
    type: str
    value: str
    address: str
    is_pointer: bool


class StackFrame(BaseModel):
    frame_name: str
    variables: List[Variable] = Field(default_factory=list)


class HeapBlock(BaseModel):
    address: str
    type: str
    value: str
    is_freed: bool = False


class PointerEdge(BaseModel):
    source_address: str
    target_address: str
    is_dangling: bool = False


class MemoryState(BaseModel):
    line_number: int
    source_code: str
    explanation: str = ""
    stack: List[StackFrame] = Field(default_factory=list)
    heap: List[HeapBlock] = Field(default_factory=list)
    edges: List[PointerEdge] = Field(default_factory=list)


class ExecutionTrace(BaseModel):
    steps: List[MemoryState] = Field(default_factory=list)
