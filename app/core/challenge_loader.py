from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.oop_model import OopModel
from app.core.state_diff import StateDiff
from app.core.step_executor import execute_line


class ChallengeLoader:

    def __init__(self, levels_dir: str = "data/levels") -> None:
        self._dir = Path(levels_dir)

    def load(self, challenge_id: str) -> dict[str, Any] | None:
        path = self._dir / f"{challenge_id}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_ids(self) -> list[str]:
        if not self._dir.exists():
            return []
        return sorted(
            p.stem for p in self._dir.glob("*.json")
            if p.name != "index.json"
        )

    def check_goal(self, challenge_def: dict[str, Any], model: OopModel) -> tuple[bool, str]:
        goal = challenge_def.get("goal", {})
        checks = goal.get("checks", [])
        for check in checks:
            ok, msg = _run_check(check, model)
            if not ok:
                return False, msg
        return True, "全部检查通过!"

    def run_all_steps(self, code_lines: list[str], model: OopModel) -> list[StateDiff]:
        diffs: list[StateDiff] = []
        for i, line in enumerate(code_lines):
            diff = execute_line(line, i, model)
            diffs.append(diff)
        return diffs


def _run_check(check: dict, model: OopModel) -> tuple[bool, str]:
    ct = check["type"]

    if ct == "class_exists":
        name = check["name"]
        ok = name in model.classes
        return ok, f"类 {name} {'存在' if ok else '不存在'}"

    if ct == "class_has_member":
        cd = model.get_class(check["class_name"])
        if cd is None:
            return False, f"类 {check['class_name']} 不存在"
        ok = cd.has_member(check["member_name"])
        return ok, f"成员 {check['member_name']} {'存在' if ok else '不存在'}"

    if ct == "instance_exists":
        inst = model.get_instance(check["var_name"])
        ok = inst is not None and inst.cls_name == check["class_name"]
        return ok, f"实例 {check['var_name']} {'存在' if ok else '不存在或类型不匹配'}"

    if ct == "member_value_equals":
        inst = model.get_instance(check["var_name"])
        if inst is None:
            return False, f"实例 {check['var_name']} 不存在"
        val = inst.values.get(check["member"])
        expected = check["value"]
        ok = val == expected
        return ok, f"{check['var_name']}.{check['member']} == {val}, 期望 {expected}"

    if ct == "instance_count":
        cls_name = check["class_name"]
        count = sum(1 for i in model.instances.values() if i.cls_name == cls_name)
        ok = count == check["count"]
        return ok, f"类 {cls_name} 的实例数 = {count}, 期望 {check['count']}"

    if ct == "no_errors":
        return True, ""

    return False, f"未知检查类型: {ct}"
