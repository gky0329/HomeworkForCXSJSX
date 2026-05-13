import re
import logging
from uuid import uuid4

from .memory_model import MemoryModel, Variable, HeapBlock, PointerEdge, StackFrame
from .state_diff import StateDiff, MemoryError

logger = logging.getLogger("cpplab.engine")


class StepExecutor:
    VAR_DECL_RE = re.compile(
        r'(int|double|float|char|bool|void)\s+(\w+)\s*(?:=\s*(.+))?\s*;?'
    )
    PTR_DECL_RE = re.compile(
        r'(int|double|float|char|bool|void)\s*\*\s*(\w+)\s*(?:=\s*(.+))?\s*;?'
    )
    ADDR_OF_RE = re.compile(r'(\w+)\s*=\s*&(\w+)\s*;?')
    DEREF_ASSIGN_RE = re.compile(r'\*(\w+)\s*=\s*(.+)\s*;?')
    NEW_EXPR_RE = re.compile(
        r'(\w+)\s*=\s*new\s+(\w+)\s*(?:\(\s*(.*?)\s*\))?\s*;?'
    )
    DELETE_EXPR_RE = re.compile(r'delete\s+(\w+)\s*;?')
    FUNC_START_RE = re.compile(r'\w+\s+(\w+)\s*\([^)]*\)\s*\{')
    SCOPE_END_RE = re.compile(r'\s*\}\s*')

    @staticmethod
    def _clean_line(line: str) -> str:
        comment_pos = line.find("//")
        if comment_pos >= 0:
            line = line[:comment_pos]
        return line.strip().rstrip(";")

    @staticmethod
    def _parse_value(value_str: str) -> object:
        value_str = value_str.strip()
        if value_str in ("nullptr", "NULL", "0"):
            return 0
        try:
            return int(value_str)
        except ValueError:
            pass
        try:
            return float(value_str)
        except ValueError:
            pass
        if value_str.startswith('"') and value_str.endswith('"'):
            return value_str[1:-1]
        return value_str

    def _handle_ptr_init(self, init_expr: str, ptr_name: str, base_type: str,
                         model: MemoryModel, diff: StateDiff, line_no: int):
        init_expr = init_expr.strip()
        frame_name = model.get_current_frame().name

        # &var — address-of initializer
        addr_match = re.match(r'&(\w+)', init_expr)
        if addr_match:
            target_name = addr_match.group(1)
            target_var = model.find_variable(target_name)
            if target_var is None:
                logger.warning("ptr init &: '%s' not found", target_name)
                return

            target_frame = model.find_frame_of(target_name)
            target_fname = target_frame.name if target_frame else frame_name

            edge = PointerEdge(
                from_var=ptr_name, from_frame=frame_name,
                to_stack_var=target_name, to_stack_frame=target_fname,
            )
            model.edges.append(edge)
            diff.added_edges.append(edge)
            ptr_var = model.find_variable(ptr_name)
            if ptr_var:
                ptr_var.value = target_var.value
            return

        # new Type(...) — heap allocation initializer
        new_match = re.match(r'new\s+(\w+)\s*(?:\(\s*(.*?)\s*\))?', init_expr)
        if new_match:
            type_name = new_match.group(1)
            value_str = new_match.group(2) or "0"
            value = self._parse_value(value_str)
            block_id = uuid4().hex[:8]
            block = HeapBlock(
                id=block_id, type_name=type_name, size=4, value=value,
                alloc_line=line_no,
            )
            model.heap.append(block)
            diff.added_heap.append(block)

            edge = PointerEdge(
                from_var=ptr_name, from_frame=frame_name, to_heap_id=block_id,
            )
            model.edges.append(edge)
            diff.added_edges.append(edge)
            ptr_var = model.find_variable(ptr_name)
            if ptr_var:
                ptr_var.value = block_id
            return

        # variable — pointer copy initializer (e.g., int* q = p;)
        rhs_var = model.find_variable(init_expr)
        if rhs_var and rhs_var.is_pointer:
            rhs_frame = model.find_frame_of(init_expr)
            rhs_fname = rhs_frame.name if rhs_frame else frame_name
            rhs_edges = model.find_edges_from(init_expr, rhs_fname)
            for re_edge in rhs_edges:
                new_edge = PointerEdge(
                    from_var=ptr_name, from_frame=frame_name,
                    to_heap_id=re_edge.to_heap_id,
                    to_stack_var=re_edge.to_stack_var,
                    to_stack_frame=re_edge.to_stack_frame,
                    is_dangling=re_edge.is_dangling,
                )
                model.edges.append(new_edge)
                diff.added_edges.append(new_edge)
            ptr_var = model.find_variable(ptr_name)
            if ptr_var:
                ptr_var.value = rhs_var.value
            return

        # nullptr / 0 — null initialization
        if init_expr in ("nullptr", "0", "NULL"):
            ptr_var = model.find_variable(ptr_name)
            if ptr_var:
                ptr_var.value = 0
            return

    def execute_line(self, line: str, model: MemoryModel, line_no: int = 0) -> StateDiff:
        clean = self._clean_line(line)
        if not clean:
            return StateDiff.empty(line=line_no, text=line)

        diff = StateDiff(source_line=line_no, source_text=line)

        # Scope enter: int main() { ... }
        func_match = self.FUNC_START_RE.match(clean)
        if func_match:
            frame_name = func_match.group(1)
            frame = StackFrame(name=frame_name)
            model.stack.append(frame)
            logger.debug("Entered scope: %s (line %d)", frame_name, line_no)
            return diff

        # Scope exit: }
        if self.SCOPE_END_RE.match(clean):
            if model.stack:
                current_frame = model.stack[-1]
                logger.debug("Scope exit check: %s (line %d)", current_frame.name, line_no)
                # Check for memory leaks without popping the frame
                for block in model.heap:
                    if not block.is_freed and not model.has_live_references(block.id):
                        diff.errors.append(MemoryError(
                            kind="leak",
                            description=f"内存泄漏: {block.type_name} 块 ({block.id[:6]}) 不再被任何指针引用",
                            block_id=block.id,
                            line=line_no,
                        ))
            return diff

        # Variable declaration: int|double|float|char|bool name [= value]
        var_match = self.VAR_DECL_RE.match(clean)
        if var_match:
            type_name = var_match.group(1)
            var_name = var_match.group(2)
            value_str = var_match.group(3)
            value = self._parse_value(value_str) if value_str else 0

            frame = model.get_current_frame()
            var = Variable(name=var_name, type_name=type_name, value=value)
            frame.variables[var_name] = var
            diff.added_vars.append((frame.name, var))
            logger.debug("Declared variable: %s %s = %s (line %d)", type_name, var_name, value, line_no)
            return diff

        # Pointer declaration: int* name [= init];
        ptr_match = self.PTR_DECL_RE.match(clean)
        if ptr_match:
            type_name = ptr_match.group(1)
            var_name = ptr_match.group(2)
            init_expr = ptr_match.group(3)

            frame = model.get_current_frame()
            var = Variable(
                name=var_name, type_name=f"{type_name}*", value=0, is_pointer=True
            )
            frame.variables[var_name] = var
            diff.added_vars.append((frame.name, var))
            logger.debug("Declared pointer: %s* %s (line %d)", type_name, var_name, line_no)

            if init_expr:
                self._handle_ptr_init(init_expr, var_name, type_name, model, diff, line_no)

            return diff

        # new expression: p = new Type(value);
        new_match = self.NEW_EXPR_RE.match(clean)
        if new_match:
            ptr_name = new_match.group(1)
            type_name = new_match.group(2)
            value_str = new_match.group(3) or "0"

            ptr_var = model.find_variable(ptr_name)
            if ptr_var is None:
                logger.warning("new: variable '%s' not found (line %d)", ptr_name, line_no)
                return diff

            value = self._parse_value(value_str)
            block_id = uuid4().hex[:8]
            block = HeapBlock(
                id=block_id, type_name=type_name, size=4, value=value,
                alloc_line=line_no,
            )
            model.heap.append(block)
            diff.added_heap.append(block)

            # Remove old edges from this pointer
            ptr_frame = model.find_frame_of(ptr_name)
            if ptr_frame:
                old_edges = model.find_edges_from(ptr_name, ptr_frame.name)
                for e in old_edges:
                    model.edges.remove(e)
                    diff.removed_edges.append((e.from_var, e.from_frame))

            # Create new edge
            frame_name = ptr_frame.name if ptr_frame else model.get_current_frame().name
            edge = PointerEdge(
                from_var=ptr_name, from_frame=frame_name, to_heap_id=block_id,
            )
            model.edges.append(edge)
            diff.added_edges.append(edge)
            ptr_var.value = block_id
            logger.debug("new: %s = new %s(%s) -> %s (line %d)",
                         ptr_name, type_name, value_str, block_id, line_no)
            return diff

        # delete expression: delete p;
        del_match = self.DELETE_EXPR_RE.match(clean)
        if del_match:
            ptr_name = del_match.group(1)
            ptr_var = model.find_variable(ptr_name)
            if ptr_var is None:
                logger.warning("delete: variable '%s' not found (line %d)", ptr_name, line_no)
                return diff

            ptr_frame = model.find_frame_of(ptr_name)
            frame_name = ptr_frame.name if ptr_frame else model.get_current_frame().name
            edges = model.find_edges_from(ptr_name, frame_name)

            if not edges:
                for block in model.heap:
                    if block.is_freed:
                        diff.errors.append(MemoryError(
                            kind="double_free",
                            description=f"双重释放: {ptr_name} 没有可释放的内存",
                            block_id=block.id,
                            line=line_no,
                        ))
                        return diff
                return diff

            for edge in list(edges):
                model.edges.remove(edge)
                diff.removed_edges.append((edge.from_var, edge.from_frame))

                if edge.to_heap_id:
                    block = model.find_heap(edge.to_heap_id)
                    if block:
                        if block.is_freed:
                            diff.errors.append(MemoryError(
                                kind="double_free",
                                description=f"双重释放: 堆块 ({block.id[:6]}) 已经被 delete 过",
                                block_id=block.id,
                                line=line_no,
                            ))
                        else:
                            block.is_freed = True
                            diff.freed_heap.append(block.id)

                            # Check dangling pointers
                            for other_edge in model.edges:
                                if other_edge.to_heap_id == block.id:
                                    other_edge.is_dangling = True
                                    diff.errors.append(MemoryError(
                                        kind="dangling",
                                        description=(
                                            f"悬挂指针: {other_edge.from_frame}::"
                                            f"{other_edge.from_var} 指向已释放的内存"
                                        ),
                                        block_id=block.id,
                                        line=line_no,
                                    ))

                ptr_var.value = 0
                diff.updated_vars.append((frame_name, ptr_var))

            logger.debug("delete: %s (line %d)", ptr_name, line_no)
            return diff

        # Address-of: p = &a;
        addr_match = self.ADDR_OF_RE.match(clean)
        if addr_match:
            ptr_name = addr_match.group(1)
            target_name = addr_match.group(2)

            ptr_var = model.find_variable(ptr_name)
            target_var = model.find_variable(target_name)
            if ptr_var is None or target_var is None:
                logger.warning("&: variable not found (%s or %s, line %d)",
                              ptr_name, target_name, line_no)
                return diff

            ptr_frame = model.find_frame_of(ptr_name)
            target_frame = model.find_frame_of(target_name)
            frame_name = ptr_frame.name if ptr_frame else model.get_current_frame().name
            target_fname = target_frame.name if target_frame else frame_name

            # Remove old edges
            old_edges = model.find_edges_from(ptr_name, frame_name)
            for e in old_edges:
                model.edges.remove(e)
                diff.removed_edges.append((e.from_var, e.from_frame))

            edge = PointerEdge(
                from_var=ptr_name, from_frame=frame_name,
                to_stack_var=target_name, to_stack_frame=target_fname,
            )
            model.edges.append(edge)
            diff.added_edges.append(edge)
            ptr_var.value = target_var.value
            logger.debug("&: %s = &%s (line %d)", ptr_name, target_name, line_no)
            return diff

        # Deref-assign: *p = value;
        deref_match = self.DEREF_ASSIGN_RE.match(clean)
        if deref_match:
            ptr_name = deref_match.group(1)
            value_str = deref_match.group(2)

            ptr_var = model.find_variable(ptr_name)
            if ptr_var is None:
                logger.warning("*=: variable '%s' not found (line %d)", ptr_name, line_no)
                return diff

            ptr_frame = model.find_frame_of(ptr_name)
            frame_name = ptr_frame.name if ptr_frame else model.get_current_frame().name
            edges = model.find_edges_from(ptr_name, frame_name)

            if not edges:
                return diff

            value = self._parse_value(value_str)
            edge = edges[0]

            if edge.is_dangling:
                diff.errors.append(MemoryError(
                    kind="dangling",
                    description=f"写入已释放的内存: {ptr_name} 是悬挂指针",
                    block_id=edge.to_heap_id,
                    line=line_no,
                ))
                return diff

            if edge.to_heap_id:
                block = model.find_heap(edge.to_heap_id)
                if block and not block.is_freed:
                    block.value = value
                    logger.debug("*=: *%s = %s -> heap[%s] (line %d)",
                                ptr_name, value_str, block.id[:6], line_no)
            elif edge.to_stack_var and edge.to_stack_frame:
                for frame in model.stack:
                    if frame.name == edge.to_stack_frame:
                        tv = frame.variables.get(edge.to_stack_var)
                        if tv:
                            tv.value = value
                            diff.updated_vars.append((edge.to_stack_frame, tv))
                            logger.debug("*=: *%s = %s -> %s::%s (line %d)",
                                        ptr_name, value_str,
                                        edge.to_stack_frame, edge.to_stack_var, line_no)

            return diff

        # General assignment: lhs = rhs (pointer copy or value copy)
        assign_match = re.match(r'(\w+)\s*=\s*(\w+)\s*;?', clean)
        if assign_match:
            lhs_name = assign_match.group(1)
            rhs_name = assign_match.group(2)

            lhs_var = model.find_variable(lhs_name)
            rhs_var = model.find_variable(rhs_name)
            if lhs_var is None or rhs_var is None:
                logger.warning("assignment: variable not found (line %d)", line_no)
                return diff

            lhs_frame = model.find_frame_of(lhs_name)
            rhs_frame = model.find_frame_of(rhs_name)
            lhs_fname = lhs_frame.name if lhs_frame else model.get_current_frame().name
            rhs_fname = rhs_frame.name if rhs_frame else model.get_current_frame().name

            if rhs_var.is_pointer:
                # Pointer copy: clone edges from rhs to lhs
                old_edges = model.find_edges_from(lhs_name, lhs_fname)
                for e in old_edges:
                    model.edges.remove(e)
                    diff.removed_edges.append((e.from_var, e.from_frame))

                rhs_edges = model.find_edges_from(rhs_name, rhs_fname)
                for re_edge in rhs_edges:
                    new_edge = PointerEdge(
                        from_var=lhs_name,
                        from_frame=lhs_fname,
                        to_heap_id=re_edge.to_heap_id,
                        to_stack_var=re_edge.to_stack_var,
                        to_stack_frame=re_edge.to_stack_frame,
                        is_dangling=re_edge.is_dangling,
                    )
                    model.edges.append(new_edge)
                    diff.added_edges.append(new_edge)

                lhs_var.value = rhs_var.value
                logger.debug("ptr copy: %s = %s (line %d)", lhs_name, rhs_name, line_no)
            else:
                lhs_var.value = rhs_var.value
                diff.updated_vars.append((lhs_fname, lhs_var))
                logger.debug("value copy: %s = %s (line %d)", lhs_name, rhs_name, line_no)

            return diff

        logger.warning("Unrecognized statement (line %d): %s", line_no, clean)
        return diff

    def execute_all(
        self, code_lines: list[str], model: MemoryModel
    ) -> list[StateDiff]:
        diffs: list[StateDiff] = []
        for i, line in enumerate(code_lines):
            diff = self.execute_line(line, model, line_no=i + 1)
            diffs.append(diff)
        return diffs
