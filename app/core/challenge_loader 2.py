import json
import logging
from pathlib import Path
from dataclasses import dataclass, field

from .memory_model import MemoryModel
from .state_diff import StateDiff

logger = logging.getLogger("cpplab.challenge")


@dataclass
class BlankSpec:
    line: int
    type: str = "text_input"
    placeholder: str = "__BLANK__"
    width_chars: int = 20


@dataclass
class GoalCheck:
    type: str
    params: dict = field(default_factory=dict)


@dataclass
class ChallengeGoal:
    checks: list[GoalCheck] = field(default_factory=list)


@dataclass
class Challenge:
    id: str
    title: str = ""
    unit: int = 0
    concept: str = ""
    order: int = 0
    prerequisites: list[str] = field(default_factory=list)
    learning_objectives: list[str] = field(default_factory=list)
    theory: str = ""
    key_points: list[str] = field(default_factory=list)
    task: str = ""
    initial_code: list[str] = field(default_factory=list)
    code_line_notes: dict[str, str] = field(default_factory=dict)
    blanks: list[BlankSpec] = field(default_factory=list)
    goal: ChallengeGoal = field(default_factory=ChallengeGoal)
    hints: list[str] = field(default_factory=list)
    success_message: str = ""
    failure_guidance: str = ""
    show_code: bool = True
    is_demo: bool = False


class ChallengeLoader:
    def __init__(self, levels_dir: str = "data/levels"):
        self._levels_dir = Path(levels_dir)
        self._cache: dict[str, Challenge] = {}

    def load(self, challenge_id: str) -> Challenge:
        if challenge_id in self._cache:
            return self._cache[challenge_id]

        path = self._levels_dir / f"{challenge_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Challenge file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        goal_data = data.get("goal", {})
        goal = ChallengeGoal(
            checks=[GoalCheck(type=c["type"], params={k: v for k, v in c.items() if k != "type"})
                    for c in goal_data.get("checks", [])]
        )

        blanks = [BlankSpec(**b) for b in data.get("blanks", [])]

        code_notes = data.get("code_line_notes", {})
        if isinstance(code_notes, list):
            code_notes = {str(i): note for i, note in enumerate(code_notes)}

        challenge = Challenge(
            id=data.get("id", challenge_id),
            title=data.get("title", ""),
            unit=data.get("unit", 0),
            concept=data.get("concept", ""),
            order=data.get("order", 0),
            prerequisites=data.get("prerequisites", []),
            learning_objectives=data.get("learning_objectives", []),
            theory=data.get("theory", ""),
            key_points=data.get("key_points", []),
            task=data.get("task", ""),
            initial_code=data.get("initial_code", []),
            code_line_notes=code_notes,
            blanks=blanks,
            goal=goal,
            hints=data.get("hints", []),
            success_message=data.get("success_message", ""),
            failure_guidance=data.get("failure_guidance", ""),
            show_code=data.get("show_code", True),
            is_demo=data.get("is_demo", False),
        )

        self._cache[challenge_id] = challenge
        logger.info("Loaded challenge: %s (%s)", challenge_id, challenge.title)
        return challenge

    def load_index(self) -> list[dict]:
        index_path = self._levels_dir / "index.json"
        if not index_path.exists():
            return []

        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    @staticmethod
    def check_goal(challenge: Challenge, model: MemoryModel, diffs: list[StateDiff]) -> tuple[bool, list[str]]:
        all_errors = []
        for diff in diffs:
            all_errors.extend(diff.errors)

        passed = True
        details: list[str] = []

        for check in challenge.goal.checks:
            ok, msg = ChallengeLoader._run_check(check, model, all_errors)
            if not ok:
                passed = False
            details.append(msg)

        return passed, details

    @staticmethod
    def _run_check(check: GoalCheck, model: MemoryModel, errors: list) -> tuple[bool, str]:
        p = check.params

        if check.type == "variable_exists":
            frame_name = p.get("frame", "main")
            var_name = p.get("name", "")
            is_ptr = p.get("is_pointer", False)
            for frame in model.stack:
                if frame.name == frame_name:
                    var = frame.variables.get(var_name)
                    if var is None:
                        return False, f"变量 {var_name} 不存在于 {frame_name}"
                    if is_ptr and not var.is_pointer:
                        return False, f"变量 {var_name} 不是指针类型"
                    return True, f"变量 {var_name} 存在"
            return False, f"栈帧 {frame_name} 不存在"

        if check.type == "variable_value_equals":
            frame_name = p.get("frame", "main")
            var_name = p.get("name", "")
            expected = p.get("value")
            for frame in model.stack:
                if frame.name == frame_name:
                    var = frame.variables.get(var_name)
                    if var is None:
                        return False, f"变量 {var_name} 不存在于 {frame_name}"
                    if str(var.value) == str(expected):
                        return True, f"{var_name} = {expected}"
                    return False, f"{var_name} = {var.value}，预期 {expected}"
            return False, f"栈帧 {frame_name} 不存在"

        if check.type == "edge_exists":
            from_var = p.get("from_var", "")
            from_frame = p.get("from_frame", "main")
            to_var = p.get("to_var")
            to_heap = p.get("to_heap_id")

            for edge in model.edges:
                if edge.is_dangling:
                    continue
                if edge.from_var != from_var or edge.from_frame != from_frame:
                    continue
                if to_var and edge.to_stack_var == to_var:
                    return True, f"指针 {from_var} 正确指向栈变量 {to_var}"
                if to_heap and edge.to_heap_id and to_heap in edge.to_heap_id:
                    return True, f"指针 {from_var} 正确指向堆块"

            return False, f"指针 {from_var} 没有指向预期的目标"

        if check.type == "no_heap_blocks":
            for block in model.heap:
                if not block.is_freed:
                    return False, f"堆区仍有活跃块 ({block.id[:6]})"
            return True, "堆区无活跃块"

        if check.type == "heap_block_count":
            expected = p.get("count", 0)
            active = sum(1 for b in model.heap if not b.is_freed)
            if active == expected:
                return True, f"堆块数 = {expected}"
            return False, f"堆块数为 {active}，预期 {expected}"

        if check.type == "heap_block_exists":
            type_name = p.get("type_name", "")
            value = p.get("value")
            for block in model.heap:
                if block.is_freed:
                    continue
                if block.type_name != type_name:
                    continue
                if value is not None:
                    if str(block.value) == str(value):
                        return True, f"堆块存在 {type_name} = {value}"
                else:
                    return True, f"堆块存在 {type_name}"
            return False, f"未找到匹配的堆块 ({type_name})"

        if check.type == "no_errors":
            if errors:
                err_msgs = [e.description for e in errors]
                return False, f"存在错误: {'; '.join(err_msgs)}"
            return True, "无错误"

        if check.type == "edge_count":
            expected = p.get("count", 0)
            live = sum(1 for e in model.edges if not e.is_dangling)
            if live == expected:
                return True, f"活跃指针边数 = {expected}"
            return False, f"活跃指针边数为 {live}，预期 {expected}"

        return False, f"未知检查类型: {check.type}"
