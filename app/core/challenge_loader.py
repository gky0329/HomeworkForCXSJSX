from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from app.core.oop_model import OopModel
from app.core.state_diff import StateDiff
from app.core.step_executor import execute_line


def _check_class_exists(check: dict, model: OopModel) -> tuple[bool, str]:
    name = check["name"]
    ok = name in model.classes
    return ok, f"类 {name} {'存在' if ok else '不存在'}"


def _check_class_has_member(check: dict, model: OopModel) -> tuple[bool, str]:
    cd = model.get_class(check["class_name"])
    if cd is None:
        return False, f"类 {check['class_name']} 不存在"
    ok = cd.has_member(check["member_name"])
    return ok, f"成员 {check['member_name']} {'存在' if ok else '不存在'}"


def _check_instance_exists(check: dict, model: OopModel) -> tuple[bool, str]:
    inst = model.get_instance(check["var_name"])
    ok = inst is not None and inst.cls_name == check["class_name"]
    return ok, f"实例 {check['var_name']} {'存在' if ok else '不存在或类型不匹配'}"


def _check_member_value_equals(check: dict, model: OopModel) -> tuple[bool, str]:
    inst = model.get_instance(check["var_name"])
    if inst is None:
        return False, f"实例 {check['var_name']} 不存在"
    val = inst.values.get(check["member"])
    expected = check["value"]
    ok = val == expected
    return ok, f"{check['var_name']}.{check['member']} == {val}, 期望 {expected}"


def _check_instance_count(check: dict, model: OopModel) -> tuple[bool, str]:
    cls_name = check["class_name"]
    count = sum(1 for i in model.instances.values() if i.cls_name == cls_name)
    ok = count == check["count"]
    return ok, f"类 {cls_name} 实例数 = {count}, 期望 {check['count']}"


def _check_no_errors(check: dict, model: OopModel) -> tuple[bool, str]:
    return True, ""


CHECKER_REGISTRY: dict[str, Callable[[dict, OopModel], tuple[bool, str]]] = {
    "class_exists":           _check_class_exists,
    "class_has_member":       _check_class_has_member,
    "instance_exists":        _check_instance_exists,
    "member_value_equals":    _check_member_value_equals,
    "instance_count":         _check_instance_count,
    "no_errors":              _check_no_errors,
}


class ChallengeLoader:

    def __init__(self, levels_dir: str = "data/levels") -> None:
        self._dir = Path(levels_dir)

    def load_index(self) -> list[dict[str, Any]]:
        path = self._dir / "index.json"
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("levels", [])
        except (json.JSONDecodeError, OSError):
            return []

    def load(self, level_id: str) -> dict[str, Any] | None:
        path = self._dir / f"{level_id}.json"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def list_ids(self) -> list[str]:
        index = self.load_index()
        if index:
            return [entry["id"] for entry in index]
        if not self._dir.exists():
            return []
        return sorted(
            p.stem for p in self._dir.glob("*.json")
            if p.name not in ("index.json", "_template.json")
        )

    def check_goal(self, level: dict[str, Any], model: OopModel) -> tuple[bool, str]:
        goal = level.get("goal", {})
        checks = goal.get("checks", [])
        for check in checks:
            check_type = check["type"]
            checker = CHECKER_REGISTRY.get(check_type)
            if checker is None:
                return False, f"未知检查类型: {check_type}"
            ok, msg = checker(check, model)
            if not ok:
                return False, msg
        return True, "全部检查通过!"

    def run_all_steps(self, code_lines: list[str], model: OopModel) -> list[StateDiff]:
        diffs: list[StateDiff] = []
        for i, line in enumerate(code_lines):
            diff = execute_line(line, i, model)
            diffs.append(diff)
        return diffs

    def validate(self, level: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        required = ["id", "title", "type", "unit", "order", "initial_code", "blanks"]
        for field in required:
            if field not in level:
                errors.append(f"缺少必填字段: {field}")
        if "goal" not in level or "checks" not in level.get("goal", {}):
            errors.append("缺少 goal.checks")
        return errors
