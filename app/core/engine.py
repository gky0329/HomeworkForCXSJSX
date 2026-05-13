from __future__ import annotations

from app.core.oop_model import OopModel
from app.core.state_diff import StateDiff
from app.core.step_executor import execute_line


class Engine:

    def __init__(self, model: OopModel | None = None) -> None:
        self.model = model or OopModel()

    def execute(self, code_lines: list[str]) -> list[StateDiff]:
        diffs: list[StateDiff] = []
        for i, line in enumerate(code_lines):
            diff = execute_line(line, i, self.model)
            diffs.append(diff)
        return diffs

    def last_model(self) -> OopModel:
        return self.model

    def reset(self) -> None:
        self.model.reset()
