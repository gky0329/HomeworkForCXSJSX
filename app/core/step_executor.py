from __future__ import annotations

import re

from app.core.oop_model import ClassDef, MemberDef, ObjectInstance, OopModel
from app.core.state_diff import StateDiff, ClassError, Annotation


def execute_line(code: str, line_number: int, model: OopModel) -> StateDiff:
    line = code.strip()

    if not line or line.startswith("//"):
        return StateDiff(source_line=line_number, source_text=code)

    if line == "}":
        return _handle_scope_exit(line_number, code, model)

    if model._in_class_body:
        return _handle_class_body_line(line, line_number, code, model)

    m = _RE_CLASS.match(line)
    if m:
        return _handle_class_def(m, line_number, code, model)

    m = _RE_BARE_INSTANCE.match(line)
    if m:
        return _handle_instance(m, line_number, code, model)

    m = _RE_ASSIGN.match(line)
    if m:
        return _handle_assign(m, line_number, code, model)

    return StateDiff(
        errors=[ClassError("parse", f"无法识别的语句: {line[:40]}", line=line_number)],
        source_line=line_number,
        source_text=code,
    )


_RE_CLASS = re.compile(r'class\s+(\w+)\s*\{')
_RE_ACCESS = re.compile(r'(public|private)\s*:')
_RE_MEMBER = re.compile(r'(int|float|string|bool)\s+(\w+)\s*;')
_RE_BARE_INSTANCE = re.compile(r'(\w+)\s+(\w+)\s*;')
_RE_ASSIGN = re.compile(r'(\w+)\.(\w+)\s*=\s*(.+?)\s*;')
_RE_CLASS_CLOSE = re.compile(r'\};?')


def _handle_class_body_line(line: str, line_number: int, code: str, model: OopModel) -> StateDiff:
    m = _RE_CLASS_CLOSE.match(line)
    if m:
        model._in_class_body = False
        model._current_class = None
        return StateDiff(
            annotations=[Annotation("info", f"类 {model._last_closed_class or ''} 定义结束")],
            source_line=line_number,
            source_text=code,
        )

    m = _RE_ACCESS.match(line)
    if m:
        model._current_access = m.group(1)
        model._current_class.access = m.group(1)
        return StateDiff(
            annotations=[Annotation("info", f"访问控制 → {m.group(1)}")],
            source_line=line_number,
            source_text=code,
        )

    m = _RE_MEMBER.match(line)
    if m:
        md = MemberDef(name=m.group(2), type=m.group(1), access=model._current_access)
        if model._current_class:
            model._current_class.members.append(md)
        return StateDiff(
            annotations=[Annotation("info", f"成员 {md.type} {md.name} ({md.access})")],
            source_line=line_number,
            source_text=code,
        )

    return StateDiff(source_line=line_number, source_text=code)


def _handle_class_def(match, line_number: int, code: str, model: OopModel) -> StateDiff:
    cls_name = match.group(1)
    if cls_name in model.classes:
        return StateDiff(
            errors=[ClassError("redefinition", f"类 {cls_name} 已定义", cls_name, line_number)],
            source_line=line_number,
            source_text=code,
        )

    ec = ClassDef(name=cls_name)
    model._current_class = ec
    model._in_class_body = True
    model._last_closed_class = cls_name
    model.add_class(ec)
    return StateDiff(
        added_classes=[ec],
        annotations=[Annotation("info", f"开始定义类 {cls_name}")],
        source_line=line_number,
        source_text=code,
    )


def _handle_instance(match, line_number: int, code: str, model: OopModel) -> StateDiff:
    cls_name = match.group(1)
    var_name = match.group(2)

    if cls_name in model.classes:
        pass
    else:
        return StateDiff(
            errors=[ClassError("missing_class", f"类 {cls_name} 尚未定义", cls_name, line_number)],
            source_line=line_number,
            source_text=code,
        )

    if var_name in model.instances:
        return StateDiff(
            errors=[ClassError("redefinition", f"变量 {var_name} 已存在", line=line_number)],
            source_line=line_number,
            source_text=code,
        )

    cd = model.get_class(cls_name)
    inst = ObjectInstance(cls_name=cls_name, var_name=var_name)
    for member in cd.members:
        inst.values[member.name] = 0
    model.add_instance(inst)

    return StateDiff(
        added_instances=[inst],
        source_line=line_number,
        source_text=code,
    )


def _handle_assign(match, line_number: int, code: str, model: OopModel) -> StateDiff:
    var_name = match.group(1)
    prop_name = match.group(2)
    raw_val = match.group(3).strip()

    inst = model.get_instance(var_name)
    if inst is None:
        return StateDiff(
            errors=[ClassError("missing_instance", f"对象 {var_name} 不存在", line=line_number)],
            source_line=line_number,
            source_text=code,
        )

    cd = model.get_class(inst.cls_name)
    if cd is None:
        return StateDiff(
            errors=[ClassError("missing_class", "类型信息丢失", line=line_number)],
            source_line=line_number,
            source_text=code,
        )

    member = cd.get_member(prop_name)
    if member is None:
        return StateDiff(
            errors=[ClassError("missing_member", f"类 {inst.cls_name} 没有成员 {prop_name}", inst.cls_name, line_number)],
            source_line=line_number,
            source_text=code,
        )

    if member.access == "private":
        return StateDiff(
            errors=[ClassError("access_violation", f"成员 {prop_name} 是 private 的，外部不能访问", inst.cls_name, line_number)],
            source_line=line_number,
            source_text=code,
        )

    try:
        val = int(raw_val)
    except ValueError:
        val = raw_val.strip('"').strip("'")

    inst.values[prop_name] = val
    return StateDiff(
        updated_instances=[(var_name, prop_name, val)],
        source_line=line_number,
        source_text=code,
    )


def _handle_scope_exit(line_number: int, code: str, model: OopModel) -> StateDiff:
    removed = list(model.instances.keys())
    for name in removed:
        model.remove_instance(name)
    model._in_class_body = False
    model._current_class = None
    model._current_access = "public"
    return StateDiff(
        removed_instances=removed,
        annotations=[Annotation("info", f"作用域退出，{len(removed)} 个实例被销毁")] if removed else [],
        source_line=line_number,
        source_text=code,
    )
