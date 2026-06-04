from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import List, Optional


def _empty_list_if_none(value):
    return [] if value is None else value


def _empty_string_if_none(value):
    return "" if value is None else value


def _zero_if_none(value):
    return 0 if value is None else value


class MemoryBaseModel(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)


class ArrayElement(MemoryBaseModel):
    index: int = 0
    value: str = ""

    _normalize_index = field_validator("index", mode="before")(_zero_if_none)
    _normalize_text = field_validator("value", mode="before")(_empty_string_if_none)


class StructMember(MemoryBaseModel):
    name: str = ""
    type: str = ""
    value: str = ""

    _normalize_text = field_validator("name", "type", "value", mode="before")(_empty_string_if_none)


class LambdaCapture(MemoryBaseModel):
    name: str = ""
    type: str = ""
    value: str = ""
    by_ref: bool = False

    _normalize_text = field_validator("name", "type", "value", mode="before")(_empty_string_if_none)


class Variable(MemoryBaseModel):
    name: str
    type: str
    value: str
    address: str
    is_pointer: bool
    is_array: bool = False
    element_count: Optional[int] = None
    elements: List[ArrayElement] = Field(default_factory=list)
    members: List[StructMember] = Field(default_factory=list)
    is_object: bool = False
    class_name: str = ""
    base_classes: List[str] = Field(default_factory=list)
    virtual_methods: List[str] = Field(default_factory=list)
    is_function_object: bool = False
    captures: List[LambdaCapture] = Field(default_factory=list)
    is_constructed: bool = False
    is_destroyed: bool = False
    is_reference: bool = False
    is_temporary: bool = False

    _normalize_text = field_validator("name", "type", "value", "address", mode="before")(_empty_string_if_none)
    _normalize_lists = field_validator(
        "elements", "members", "base_classes", "virtual_methods", "captures",
        mode="before",
    )(_empty_list_if_none)


class StackFrame(MemoryBaseModel):
    frame_name: str
    variables: List[Variable] = Field(default_factory=list)

    _normalize_text = field_validator("frame_name", mode="before")(_empty_string_if_none)
    _normalize_lists = field_validator("variables", mode="before")(_empty_list_if_none)


class HeapBlock(MemoryBaseModel):
    address: str
    type: str
    value: str
    is_freed: bool = False
    is_array: bool = False
    element_count: Optional[int] = None
    elements: List[ArrayElement] = Field(default_factory=list)
    members: List[StructMember] = Field(default_factory=list)
    is_object: bool = False
    class_name: str = ""
    base_classes: List[str] = Field(default_factory=list)
    virtual_methods: List[str] = Field(default_factory=list)
    container_size: Optional[int] = None
    container_capacity: Optional[int] = None
    is_constructed: bool = False
    is_destroyed: bool = False

    _normalize_text = field_validator("address", "type", "value", "class_name", mode="before")(_empty_string_if_none)
    _normalize_lists = field_validator(
        "elements", "members", "base_classes", "virtual_methods",
        mode="before",
    )(_empty_list_if_none)


class PointerEdge(MemoryBaseModel):
    source_address: str
    target_address: str
    is_dangling: bool = False

    _normalize_text = field_validator("source_address", "target_address", mode="before")(_empty_string_if_none)


class MemoryState(MemoryBaseModel):
    line_number: int
    source_code: str
    explanation: str = ""
    stack: List[StackFrame] = Field(default_factory=list)
    heap: List[HeapBlock] = Field(default_factory=list)
    edges: List[PointerEdge] = Field(default_factory=list)

    _normalize_text = field_validator("source_code", "explanation", mode="before")(_empty_string_if_none)
    _normalize_lists = field_validator("stack", "heap", "edges", mode="before")(_empty_list_if_none)


class ExecutionTrace(MemoryBaseModel):
    steps: List[MemoryState] = Field(default_factory=list)

    _normalize_lists = field_validator("steps", mode="before")(_empty_list_if_none)
