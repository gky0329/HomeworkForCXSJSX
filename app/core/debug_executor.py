import logging
import os
import platform
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from app.core.memory_model import (
    ArrayElement,
    ExecutionTrace,
    HeapBlock,
    MemoryState,
    PointerEdge,
    StackFrame,
    StructMember,
    Variable,
)

logger = logging.getLogger(__name__)


class DebugExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class DebugBackendStatus:
    id: str
    label: str
    available: bool
    implemented: bool
    detail: str


@dataclass
class _ClassInfo:
    base_classes: list[str] = field(default_factory=list)
    virtual_methods: list[str] = field(default_factory=list)


@dataclass
class _PreparedSource:
    source: str
    original_lines: list[str]
    line_map: dict[int, int]
    heap_arrays: dict[str, tuple[str, int]] = field(default_factory=dict)
    step_in_lines: set[int] = field(default_factory=set)
    class_info: dict[str, _ClassInfo] = field(default_factory=dict)
    source_path: str = ""


@dataclass
class _ParsedElement:
    index: int
    type: str
    value: str


@dataclass
class _ParsedMember:
    name: str
    type: str
    value: str


@dataclass
class _ParsedVar:
    actual_addr: str
    type: str
    name: str
    value: str
    pointee_addr: str = ""
    pointee_type: str = ""
    pointee_value: str = ""
    pointee_elements: list[_ParsedElement] = field(default_factory=list)
    pointee_members: list[_ParsedMember] = field(default_factory=list)
    elements: list[_ParsedElement] = field(default_factory=list)
    members: list[_ParsedMember] = field(default_factory=list)


@dataclass
class _ParsedFrame:
    name: str
    original_line: int
    variables: list[_ParsedVar]


@dataclass(frozen=True)
class _FrameLocation:
    file: str
    line: int
    function: str


class DebugExecutor:
    """Build and inspect C++ with native debug symbols before falling back to AI."""

    LLDB_DWARF_BACKEND = "lldb-dwarf"
    MSVC_PDB_BACKEND = "msvc-pdb"
    MAX_STEPS = 120
    COMPILE_TIMEOUT_SECONDS = 30
    LLDB_TIMEOUT_SECONDS = 20
    CDB_TIMEOUT_SECONDS = 25
    VSWHERE_TIMEOUT_SECONDS = 5

    def __init__(self, preferred_backend: str | None = None):
        self._preferred_backend = preferred_backend

    @staticmethod
    def is_available() -> bool:
        return DebugExecutor.available_backend() is not None

    @staticmethod
    def can_run_code_locally(code: str, stdin_text: str = "") -> bool:
        if DebugExecutor.requires_stdin(code) and not stdin_text.strip():
            return False
        return DebugExecutor.is_available()

    @staticmethod
    def available_backend() -> str | None:
        for status in DebugExecutor.backend_status():
            if status.available and status.implemented:
                return status.id
        return None

    @staticmethod
    def backend_status() -> list[DebugBackendStatus]:
        is_windows = platform.system() == "Windows"
        compiler = DebugExecutor._compiler()
        lldb = shutil.which("lldb")
        lldb_available = bool(lldb and compiler)
        if lldb_available:
            lldb_detail = f"Using {Path(lldb).name} with {Path(compiler).name} debug symbols"
        else:
            missing = []
            if not lldb:
                missing.append("lldb")
            if not compiler:
                missing.append("clang++/g++")
            lldb_detail = "Missing " + ", ".join(missing)

        msvc = DebugExecutor._msvc_tools() if is_windows else {
            "compiler": None,
            "debugger": None,
            "vswhere": None,
            "vcvarsall": None,
        }
        msvc_tools_available = is_windows and bool(msvc["compiler"] and msvc["debugger"])
        msvc_enabled = os.environ.get("CXXMV_ENABLE_EXPERIMENTAL_PDB") == "1"
        msvc_available = msvc_tools_available and msvc_enabled
        if not is_windows:
            msvc_detail = "MSVC/PDB backend is Windows-only and not active on this platform"
        elif not msvc_tools_available:
            missing = []
            if not msvc["compiler"]:
                missing.append("cl.exe")
            if not msvc["debugger"]:
                missing.append("cdb.exe")
            msvc_detail = "Missing " + ", ".join(missing)
        elif msvc_enabled:
            msvc_detail = (
                f"Using {Path(msvc['compiler']).name} with {Path(msvc['debugger']).name} "
                "and PDB debug symbols"
            )
        else:
            msvc_detail = (
                "MSVC/PDB backend is experimental and disabled until local debugger "
                "correctness is validated; set CXXMV_ENABLE_EXPERIMENTAL_PDB=1 to test it"
            )

        lldb_status = DebugBackendStatus(
            id=DebugExecutor.LLDB_DWARF_BACKEND,
            label="LLDB / DWARF",
            available=lldb_available,
            implemented=True,
            detail=lldb_detail,
        )
        msvc_status = DebugBackendStatus(
            id=DebugExecutor.MSVC_PDB_BACKEND,
            label="MSVC / PDB",
            available=msvc_available,
            implemented=True,
            detail=msvc_detail,
        )
        if is_windows:
            return [msvc_status, lldb_status]
        return [lldb_status, msvc_status]

    @staticmethod
    def _compiler() -> str | None:
        return shutil.which("clang++") or shutil.which("g++")

    @staticmethod
    def _msvc_tools() -> dict[str, str | None]:
        compiler = shutil.which("cl") or shutil.which("cl.exe")
        debugger = shutil.which("cdb") or shutil.which("cdb.exe")
        vswhere = shutil.which("vswhere") or shutil.which("vswhere.exe")
        vcvarsall = None

        if platform.system() == "Windows":
            vswhere = vswhere or DebugExecutor._default_vswhere()
            install_dir = DebugExecutor._vs_installation_path(vswhere) if vswhere else None
            if install_dir:
                compiler = compiler or DebugExecutor._find_msvc_compiler(install_dir)
                vcvarsall = DebugExecutor._existing_file(
                    Path(install_dir) / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
                )
            debugger = debugger or DebugExecutor._find_windows_cdb()

        return {
            "compiler": compiler,
            "debugger": debugger,
            "vswhere": vswhere,
            "vcvarsall": vcvarsall,
        }

    @staticmethod
    def _existing_file(path: Path | str) -> str | None:
        candidate = Path(path)
        try:
            return str(candidate) if candidate.is_file() else None
        except OSError:
            return None

    @staticmethod
    def _default_vswhere() -> str | None:
        roots = [
            os.environ.get("ProgramFiles(x86)", ""),
            os.environ.get("ProgramFiles", ""),
        ]
        for root in roots:
            if not root:
                continue
            found = DebugExecutor._existing_file(
                Path(root) / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
            )
            if found:
                return found
        return None

    @staticmethod
    def _vs_installation_path(vswhere: str) -> str | None:
        try:
            proc = subprocess.run(
                [
                    vswhere,
                    "-latest",
                    "-products",
                    "*",
                    "-requires",
                    "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                    "-property",
                    "installationPath",
                ],
                capture_output=True,
                text=True,
                timeout=DebugExecutor.VSWHERE_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if proc.returncode != 0:
            return None
        path = (proc.stdout or "").strip().splitlines()
        return path[0].strip() if path and path[0].strip() else None

    @staticmethod
    def _find_msvc_compiler(install_dir: str) -> str | None:
        tools_root = Path(install_dir) / "VC" / "Tools" / "MSVC"
        try:
            versions = sorted(tools_root.iterdir(), key=lambda path: path.name, reverse=True)
        except OSError:
            return None
        for version_dir in versions:
            for rel in (
                Path("bin") / "Hostx64" / "x64" / "cl.exe",
                Path("bin") / "Hostx86" / "x64" / "cl.exe",
                Path("bin") / "Hostx64" / "x86" / "cl.exe",
            ):
                found = DebugExecutor._existing_file(version_dir / rel)
                if found:
                    return found
        return None

    @staticmethod
    def _find_windows_cdb() -> str | None:
        roots = [
            os.environ.get("WindowsSdkDir", ""),
            os.environ.get("ProgramFiles(x86)", ""),
            os.environ.get("ProgramFiles", ""),
        ]
        candidates: list[Path] = []
        for root in roots:
            if not root:
                continue
            base = Path(root)
            if base.name.lower() == "10":
                candidates.append(base / "Debuggers" / "x64" / "cdb.exe")
            candidates.extend([
                base / "Windows Kits" / "10" / "Debuggers" / "x64" / "cdb.exe",
                base / "Windows Kits" / "10" / "Debuggers" / "x86" / "cdb.exe",
            ])
        for candidate in candidates:
            found = DebugExecutor._existing_file(candidate)
            if found:
                return found
        return None

    def run_code(self, code: str, stdin_text: str = "") -> ExecutionTrace:
        if self.requires_stdin(code) and not stdin_text.strip():
            raise DebugExecutionError(
                "Native debugger skipped code that reads from stdin; "
                "paste sample input into Program Input (stdin) to run it locally"
            )

        backend = self._select_backend()
        if backend == self.LLDB_DWARF_BACKEND:
            return self._run_lldb_dwarf(code, stdin_text)
        if backend == self.MSVC_PDB_BACKEND:
            return self._run_msvc_pdb(code, stdin_text)
        raise DebugExecutionError("No supported debugger/compiler found")

    def _select_backend(self) -> str:
        statuses = {status.id: status for status in self.backend_status()}
        if self._preferred_backend:
            status = statuses.get(self._preferred_backend)
            if status is None:
                raise DebugExecutionError(f"Unknown debugger backend: {self._preferred_backend}")
            if not status.implemented:
                raise DebugExecutionError(f"{status.label} backend is not implemented yet")
            if not status.available:
                raise DebugExecutionError(status.detail)
            return status.id

        backend = self.available_backend()
        if backend is None:
            details = "; ".join(status.detail for status in statuses.values())
            raise DebugExecutionError(f"No supported debugger/compiler found: {details}")
        return backend

    def _run_lldb_dwarf(self, code: str, stdin_text: str = "") -> ExecutionTrace:
        prepared = self._prepare_source(code)
        with tempfile.TemporaryDirectory(prefix="cxx_visualizer_debug_") as tmpdir:
            tmp = Path(tmpdir)
            src = tmp / "program.cpp"
            binary = tmp / ("program.exe" if platform.system() == "Windows" else "program")
            commands = tmp / "lldb_commands.txt"
            input_file = tmp / "stdin.txt"
            src.write_text(prepared.source, encoding="utf-8")
            prepared.source_path = str(src)
            if stdin_text.strip():
                input_file.write_text(stdin_text, encoding="utf-8")

            self._compile(src, binary)
            commands.write_text(
                self._lldb_script(
                    prepared,
                    input_path=input_file if stdin_text.strip() else None,
                ),
                encoding="utf-8",
            )
            output = self._run_lldb(binary, commands)

        trace = self._parse_lldb_output(output, prepared)
        if not trace.steps:
            raise DebugExecutionError("Debugger produced no executable snapshots")
        return trace

    def _run_msvc_pdb(self, code: str, stdin_text: str = "") -> ExecutionTrace:
        prepared = self._prepare_source(code)
        with tempfile.TemporaryDirectory(prefix="cxx_visualizer_pdb_") as tmpdir:
            tmp = Path(tmpdir)
            src = tmp / "program.cpp"
            binary = tmp / "program.exe"
            pdb = tmp / "program.pdb"
            commands = tmp / "cdb_commands.txt"
            input_file = tmp / "stdin.txt"
            src.write_text(prepared.source, encoding="utf-8")
            prepared.source_path = str(src)
            if stdin_text.strip():
                input_file.write_text(stdin_text, encoding="utf-8")

            self._compile_msvc(src, binary, pdb)
            commands.write_text(self._cdb_script(prepared), encoding="utf-8")
            output = self._run_cdb(
                binary,
                commands,
                input_path=input_file if stdin_text.strip() else None,
            )

        trace = self._parse_cdb_output(output, prepared)
        if not trace.steps:
            raise DebugExecutionError("MSVC/PDB debugger produced no executable snapshots")
        return trace

    @staticmethod
    def requires_stdin(code: str) -> bool:
        patterns = (
            r"\bcin\s*>>",
            r"\bstd::cin\s*>>",
            r"\bscanf\s*\(",
            r"\bfscanf\s*\(",
            r"\bgetline\s*\(\s*cin\s*,",
            r"\bgetline\s*\(\s*std::cin\s*,",
        )
        return any(re.search(pattern, code) for pattern in patterns)

    def _prepare_source(self, code: str) -> _PreparedSource:
        original_lines = code.splitlines()
        class_info = self._class_metadata(original_lines)
        if re.search(r"\bmain\s*\(", code):
            line_map = {i: i for i in range(1, len(original_lines) + 1)}
            return _PreparedSource(
                source=code,
                original_lines=original_lines,
                line_map=line_map,
                heap_arrays=self._heap_array_declarations(original_lines),
                step_in_lines=self._step_in_lines(original_lines, line_map),
                class_info=class_info,
            )

        source, line_map = self._wrap_snippet_source(original_lines)
        return _PreparedSource(
            source=source,
            original_lines=original_lines,
            line_map=line_map,
            heap_arrays=self._heap_array_declarations(original_lines),
            step_in_lines=self._step_in_lines(source.splitlines(), line_map),
            class_info=class_info,
        )

    def _wrap_snippet_source(self, original_lines: list[str]) -> tuple[str, dict[int, int]]:
        prefix = [
            "#include <algorithm>",
            "#include <cmath>",
            "#include <cstdlib>",
            "#include <iostream>",
            "#include <map>",
            "#include <memory>",
            "#include <set>",
            "#include <string>",
            "#include <unordered_map>",
            "#include <utility>",
            "#include <vector>",
            "using namespace std;",
        ]
        hoisted: list[tuple[int, str]] = []
        body: list[tuple[int, str]] = []

        idx = 0
        while idx < len(original_lines):
            line = original_lines[idx]
            stripped = self._strip_line_comment(line).strip()
            if self._is_hoisted_single_line(stripped):
                hoisted.append((idx + 1, line))
                idx += 1
                continue

            if self._starts_hoisted_block(original_lines, idx):
                depth = 0
                saw_brace = False
                while idx < len(original_lines):
                    block_line = original_lines[idx]
                    hoisted.append((idx + 1, block_line))
                    clean = self._strip_line_comment(block_line)
                    depth += clean.count("{") - clean.count("}")
                    saw_brace = saw_brace or "{" in clean
                    idx += 1
                    if saw_brace and depth <= 0:
                        break
                    if not saw_brace and clean.rstrip().endswith(";"):
                        break
                continue

            body.append((idx + 1, line))
            idx += 1

        generated_lines: list[str] = []
        line_map: dict[int, int] = {}

        for line in prefix:
            generated_lines.append(line)
        for original_line, line in hoisted:
            generated_lines.append(line)
            line_map[len(generated_lines)] = original_line

        generated_lines.append("int main() {")
        for original_line, line in body:
            generated_lines.append(f"  {line}")
            line_map[len(generated_lines)] = original_line
        suffix = ["  return 0;", "}"]
        generated_lines.extend(suffix)
        return "\n".join(generated_lines) + "\n", line_map

    @staticmethod
    def _is_hoisted_single_line(stripped: str) -> bool:
        if not stripped:
            return False
        return (
            stripped.startswith("#")
            or stripped.startswith("using ")
            or (
                stripped.endswith(";")
                and DebugExecutor._looks_like_function_signature(stripped[:-1].strip())
            )
        )

    @staticmethod
    def _starts_hoisted_block(lines: list[str], index: int) -> bool:
        line = DebugExecutor._strip_line_comment(lines[index]).strip()
        if not line:
            return False
        if re.match(r"^(?:template\s*<[^>]+>\s*)?(?:class|struct|enum|namespace)\b", line):
            return True
        if DebugExecutor._looks_like_function_definition_start(line):
            return True
        if (
            index + 1 < len(lines)
            and DebugExecutor._looks_like_function_signature(line)
            and DebugExecutor._strip_line_comment(lines[index + 1]).strip().startswith("{")
        ):
            return True
        return False

    @staticmethod
    def _looks_like_function_definition_start(line: str) -> bool:
        if "{" not in line or ";" in line.split("{", 1)[0]:
            return False
        return DebugExecutor._looks_like_function_signature(line.split("{", 1)[0].strip())

    @staticmethod
    def _looks_like_function_signature(line: str) -> bool:
        if not line or "=" in line:
            return False
        if re.match(r"^(?:if|for|while|switch|catch)\b", line):
            return False
        pattern = re.compile(
            r"^(?:template\s*<[^>]+>\s*)?"
            r"(?:(?:inline|static|virtual|explicit|constexpr|friend)\s+)*"
            r"(?:[A-Za-z_]\w*(?:::\w+)?|~?[A-Za-z_]\w*|operator\s*\S+)"
            r"(?:<[^;{}()]*>)?[\s*&]+"
            r"(?P<name>~?[A-Za-z_]\w*)\s*\((?P<params>[^;{}]*)\)\s*"
            r"(?:const\s*)?(?:noexcept\s*)?(?:->\s*[^:{]+)?\s*$"
        )
        match = pattern.match(line)
        return bool(
            match
            and match.group("name") not in {"if", "for", "while", "switch", "catch"}
            and DebugExecutor._looks_like_parameter_list(match.group("params"))
        )

    @staticmethod
    def _looks_like_parameter_list(params: str) -> bool:
        text = params.strip()
        if not text or text == "void":
            return True
        if any(token in text for token in ('"', "'", "{", "}", "+", "/", "%")):
            return False
        if re.search(r"(?<![A-Za-z_])\d", text):
            return False

        for part in DebugExecutor._split_parameter_list(text):
            clean = part.strip()
            if not clean or "=" in clean:
                return False
            clean = re.sub(r"\b(?:const|volatile|constexpr|typename|class)\b", "", clean).strip()
            clean = clean.lstrip("*&").strip()
            first = clean.split(None, 1)[0] if clean else ""
            first = first.lstrip("*&")
            first = first.rstrip("*&")
            if not first:
                return False
            if "<" in first or "::" in first:
                continue
            if first in {
                "auto",
                "bool",
                "char",
                "double",
                "float",
                "int",
                "long",
                "short",
                "signed",
                "size_t",
                "string",
                "unsigned",
                "wchar_t",
            }:
                continue
            if first[:1].isupper():
                continue
            return False
        return True

    @staticmethod
    def _split_parameter_list(params: str) -> list[str]:
        parts: list[str] = []
        current: list[str] = []
        angle_depth = 0
        paren_depth = 0
        for ch in params:
            if ch == "<":
                angle_depth += 1
            elif ch == ">" and angle_depth > 0:
                angle_depth -= 1
            elif ch == "(":
                paren_depth += 1
            elif ch == ")" and paren_depth > 0:
                paren_depth -= 1
            if ch == "," and angle_depth == 0 and paren_depth == 0:
                parts.append("".join(current))
                current = []
            else:
                current.append(ch)
        parts.append("".join(current))
        return parts

    def _compile(self, src: Path, binary: Path):
        compiler = self._compiler()
        if compiler is None:
            raise DebugExecutionError("No C++ compiler found")

        try:
            proc = subprocess.run(
                [compiler, "-std=c++17", "-g", "-O0", str(src), "-o", str(binary)],
                capture_output=True,
                text=True,
                timeout=self.COMPILE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as e:
            raise DebugExecutionError(
                f"Compile timed out after {self.COMPILE_TIMEOUT_SECONDS} seconds"
            ) from e
        if proc.returncode != 0:
            raise DebugExecutionError(f"Compile failed:\n{proc.stderr.strip()}")

    def _compile_msvc(self, src: Path, binary: Path, pdb: Path):
        tools = self._msvc_tools()
        compiler = tools["compiler"]
        if compiler is None:
            raise DebugExecutionError("cl.exe not found. Run from a Visual Studio Developer Command Prompt.")

        cmd = self._msvc_compile_args(compiler, src, binary, pdb)
        run_cmd = self._msvc_shell_command(cmd, tools.get("vcvarsall"))
        try:
            proc = subprocess.run(
                run_cmd,
                capture_output=True,
                text=True,
                timeout=self.COMPILE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as e:
            raise DebugExecutionError(
                f"MSVC compile timed out after {self.COMPILE_TIMEOUT_SECONDS} seconds"
            ) from e
        if proc.returncode != 0:
            output = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
            raise DebugExecutionError(f"MSVC compile failed:\n{output}")

    @staticmethod
    def _msvc_compile_args(compiler: str, src: Path, binary: Path, pdb: Path) -> list[str]:
        return [
            compiler,
            "/nologo",
            "/std:c++17",
            "/EHsc",
            "/Zi",
            "/Od",
            "/MDd",
            f"/Fe:{binary}",
            f"/Fd:{pdb}",
            str(src),
        ]

    @staticmethod
    def _msvc_shell_command(cmd: list[str], vcvarsall: str | None = None) -> list[str]:
        if platform.system() != "Windows" or not vcvarsall:
            return cmd
        return [
            "cmd",
            "/s",
            "/c",
            f'call "{vcvarsall}" x64 >nul && {subprocess.list2cmdline(cmd)}',
        ]

    def _lldb_script(self, prepared: _PreparedSource, input_path: Path | None = None) -> str:
        step_count = min(
            self.MAX_STEPS,
            max(20, len(prepared.original_lines) * 4 + 8),
        )
        commands = [
            "settings set target.process.thread.step-avoid-regexp ^std::|^__",
        ]
        if input_path is not None:
            commands.append(f"settings set target.input-path {input_path}")
        commands.extend([
            "breakpoint set --name main",
            "run",
        ])
        for i in range(step_count):
            commands.extend([
                f'script print("__CXXMV_BEFORE__{i}")',
                "frame info",
                self._lldb_step_command(
                    prepared.step_in_lines,
                    Path(prepared.source_path).name or "program.cpp",
                ),
                f'script print("__CXXMV_AFTER__{i}")',
                "frame info",
                self._lldb_stack_snapshot_command(Path(prepared.source_path).name or "program.cpp"),
            ])
            for pointer_name, (_, count) in prepared.heap_arrays.items():
                for index in range(count):
                    commands.append(self._lldb_array_probe_command(i, pointer_name, index))
        return "\n".join(commands) + "\n"

    def _run_lldb(self, binary: Path, commands: Path) -> str:
        try:
            proc = subprocess.run(
                ["lldb", "-b", "-s", str(commands), str(binary)],
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=self.LLDB_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as e:
            raise DebugExecutionError(
                f"LLDB timed out after {self.LLDB_TIMEOUT_SECONDS} seconds. Programs waiting for stdin "
                "or very long simulations should use AI fallback or a future input-aware runner."
            ) from e
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        benign_exit_after_snapshots = (
            "__CXXMV_BEFORE__" in output
            and "Process " in output
            and " exited with status" in output
            and "Command requires a process" in output
        )
        if (
            proc.returncode != 0
            and "error: process exited" not in output
            and not benign_exit_after_snapshots
        ):
            raise DebugExecutionError(f"LLDB failed:\n{output.strip()[:2000]}")
        return output

    def _cdb_script(self, prepared: _PreparedSource) -> str:
        step_count = min(
            self.MAX_STEPS,
            max(20, len(prepared.original_lines) * 4 + 8),
        )
        commands = [
            ".lines",
            "l+t",
            "bp main",
            "g",
        ]
        for i in range(step_count):
            commands.extend([
                f".echo __CXXMV_BEFORE__{i}",
                "kP 1",
                "t",
                f".echo __CXXMV_AFTER__{i}",
                "kP 8",
            ])
            for frame_idx in range(8):
                commands.extend([
                    f".echo __CXXMV_FRAMEV__{frame_idx}",
                    f".frame {frame_idx}",
                    "dv /t /v",
                    f".echo __CXXMV_FRAMEDX__{frame_idx}",
                    "dx -r2 @$curframe.Locals",
                ])
        commands.append("q")
        return "\n".join(commands) + "\n"

    def _run_cdb(
        self,
        binary: Path,
        commands: Path,
        input_path: Path | None = None,
    ) -> str:
        debugger = self._msvc_tools()["debugger"]
        if debugger is None:
            raise DebugExecutionError("cdb.exe not found. Install Windows Debugging Tools.")

        stdin_handle = None
        try:
            if input_path is not None:
                stdin_handle = open(input_path, "r", encoding="utf-8")
            proc = subprocess.run(
                [debugger, "-lines", "-cf", str(commands), str(binary)],
                capture_output=True,
                text=True,
                stdin=stdin_handle if stdin_handle is not None else subprocess.DEVNULL,
                timeout=self.CDB_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as e:
            raise DebugExecutionError(
                f"CDB timed out after {self.CDB_TIMEOUT_SECONDS} seconds"
            ) from e
        finally:
            if stdin_handle is not None:
                stdin_handle.close()

        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        benign_exit_after_snapshots = (
            "__CXXMV_BEFORE__" in output
            and ("exited with code" in output.lower() or "quit:" in output.lower())
        )
        if proc.returncode not in (0, 1) and not benign_exit_after_snapshots:
            raise DebugExecutionError(f"CDB failed:\n{output.strip()[:2000]}")
        return output

    def _parse_cdb_output(self, output: str, prepared: _PreparedSource) -> ExecutionTrace:
        marker_re = re.compile(r"^__CXXMV_BEFORE__(\d+)$", re.MULTILINE)
        matches = list(marker_re.finditer(output))
        states: list[MemoryState] = []
        stack_addr_map: dict[str, str] = {}
        stack_name_addr_map: dict[str, str] = {}
        heap_addr_map: dict[str, str] = {}
        pointer_targets: dict[str, str] = {}
        heap_values: dict[str, tuple[str, str]] = {}
        heap_array_values: dict[str, tuple[str, list[_ParsedElement]]] = {}
        heap_object_values: dict[str, tuple[str, list[_ParsedMember]]] = {}
        freed_heap: set[str] = set()
        declarations = self._declaration_lines(prepared.original_lines)

        for idx, match in enumerate(matches):
            chunk_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(output)
            chunk = output[match.end():chunk_end]
            after_match = re.search(rf"^__CXXMV_AFTER__{match.group(1)}$", chunk, re.MULTILINE)
            if after_match is None:
                continue

            before_chunk = chunk[:after_match.start()]
            after_chunk = chunk[after_match.end():]
            location = self._cdb_frame_location(before_chunk, prepared)
            if location is None:
                continue
            after_location = self._cdb_frame_location(after_chunk, prepared)
            if self._is_step_in_transition(location, after_location, prepared):
                continue
            original_line = prepared.line_map.get(location.line)
            if original_line is None:
                continue
            source_code = self._source_line(prepared.original_lines, original_line)
            if not source_code:
                continue

            delete_name = self._deleted_pointer_name(source_code)
            parsed_frames = self._parse_cdb_stack_snapshots(
                after_chunk,
                prepared,
                declarations,
                fallback_location=location,
                fallback_original_line=original_line,
            )
            parsed_vars = [var for frame in parsed_frames for var in frame.variables]
            for var in parsed_vars:
                if var.pointee_addr:
                    pointer_targets[var.name] = var.pointee_addr
                    if var.pointee_value and var.name != delete_name:
                        heap_values[var.pointee_addr] = (var.pointee_type, var.pointee_value)
                    if var.pointee_members and var.name != delete_name:
                        heap_object_values[var.pointee_addr] = (
                            var.pointee_type or self._pointee_type(var.type),
                            var.pointee_members,
                        )
                    if var.pointee_elements and var.name != delete_name:
                        element_type = var.pointee_type or self._pointee_type(var.type)
                        heap_array_values[var.pointee_addr] = (
                            element_type,
                            var.pointee_elements,
                        )
                        heap_values[var.pointee_addr] = (
                            f"{element_type}[]",
                            self._format_elements(var.pointee_elements),
                        )

            if delete_name and delete_name in pointer_targets:
                freed_heap.add(pointer_targets[delete_name])

            states.append(self._build_state(
                original_line=original_line,
                source_code=source_code,
                parsed_frames=parsed_frames,
                stack_addr_map=stack_addr_map,
                stack_name_addr_map=stack_name_addr_map,
                heap_addr_map=heap_addr_map,
                heap_values=heap_values,
                heap_array_values=heap_array_values,
                heap_object_values=heap_object_values,
                freed_heap=freed_heap,
                class_info=prepared.class_info,
            ))

        return ExecutionTrace(steps=states)

    def _parse_lldb_output(self, output: str, prepared: _PreparedSource) -> ExecutionTrace:
        marker_re = re.compile(r"^__CXXMV_BEFORE__(\d+)$", re.MULTILINE)
        matches = list(marker_re.finditer(output))
        states: list[MemoryState] = []
        stack_addr_map: dict[str, str] = {}
        stack_name_addr_map: dict[str, str] = {}
        heap_addr_map: dict[str, str] = {}
        pointer_targets: dict[str, str] = {}
        heap_values: dict[str, tuple[str, str]] = {}
        heap_array_values: dict[str, tuple[str, list[_ParsedElement]]] = {}
        heap_object_values: dict[str, tuple[str, list[_ParsedMember]]] = {}
        freed_heap: set[str] = set()
        declarations = self._declaration_lines(prepared.original_lines)

        for idx, match in enumerate(matches):
            chunk_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(output)
            chunk = output[match.end():chunk_end]
            after_match = re.search(rf"^__CXXMV_AFTER__{match.group(1)}$", chunk, re.MULTILINE)
            if after_match is None:
                continue

            before_chunk = chunk[:after_match.start()]
            after_chunk = chunk[after_match.end():]
            location = self._frame_location(before_chunk)
            if location is None:
                continue
            if prepared.source_path and Path(location.file).name != Path(prepared.source_path).name:
                continue

            after_location = self._frame_location(after_chunk)
            if self._is_step_in_transition(location, after_location, prepared):
                continue

            original_line = prepared.line_map.get(location.line)
            if original_line is None:
                continue
            source_code = self._source_line(prepared.original_lines, original_line)
            if not source_code:
                continue

            delete_name = self._deleted_pointer_name(source_code)
            parsed_frames = self._parse_stack_snapshots(
                after_chunk,
                prepared,
                declarations,
                fallback_location=location,
                fallback_original_line=original_line,
            )
            parsed_vars = [var for frame in parsed_frames for var in frame.variables]
            array_exprs = self._parse_array_expressions(after_chunk)
            for var in parsed_vars:
                if var.pointee_addr:
                    pointer_targets[var.name] = var.pointee_addr
                    if var.pointee_value and var.name != delete_name:
                        heap_values[var.pointee_addr] = (var.pointee_type, var.pointee_value)
                    if var.pointee_members and var.name != delete_name:
                        heap_object_values[var.pointee_addr] = (
                            var.pointee_type or self._pointee_type(var.type),
                            var.pointee_members,
                        )
                    if var.name in array_exprs and var.name != delete_name:
                        element_type = prepared.heap_arrays.get(var.name, (self._pointee_type(var.type), 0))[0]
                        heap_array_values[var.pointee_addr] = (element_type, array_exprs[var.name])
                        heap_values[var.pointee_addr] = (
                            f"{element_type}[]",
                            self._format_elements(array_exprs[var.name]),
                        )

            if delete_name and delete_name in pointer_targets:
                freed_heap.add(pointer_targets[delete_name])

            state = self._build_state(
                original_line=original_line,
                source_code=source_code,
                parsed_frames=parsed_frames,
                stack_addr_map=stack_addr_map,
                stack_name_addr_map=stack_name_addr_map,
                heap_addr_map=heap_addr_map,
                heap_values=heap_values,
                heap_array_values=heap_array_values,
                heap_object_values=heap_object_values,
                freed_heap=freed_heap,
                class_info=prepared.class_info,
            )
            states.append(state)

        return ExecutionTrace(steps=states)

    def _build_state(
        self,
        original_line: int,
        source_code: str,
        parsed_frames: list[_ParsedFrame],
        stack_addr_map: dict[str, str],
        stack_name_addr_map: dict[str, str],
        heap_addr_map: dict[str, str],
        heap_values: dict[str, tuple[str, str]],
        heap_array_values: dict[str, tuple[str, list[_ParsedElement]]],
        heap_object_values: dict[str, tuple[str, list[_ParsedMember]]],
        freed_heap: set[str],
        class_info: dict[str, _ClassInfo] | None = None,
    ) -> MemoryState:
        class_info = class_info or {}
        actual_stack_lookup: dict[str, str] = {}
        frame_variables: list[tuple[str, list[Variable]]] = []
        pointer_edges: list[PointerEdge] = []
        heap_blocks_by_actual: dict[str, HeapBlock] = {}

        for parsed_frame in parsed_frames:
            for parsed in parsed_frame.variables:
                logical_key = f"{parsed_frame.name}:{parsed.name}"
                if parsed.actual_addr not in stack_addr_map:
                    if logical_key in stack_name_addr_map:
                        stack_addr_map[parsed.actual_addr] = stack_name_addr_map[logical_key]
                    else:
                        stack_name_addr_map[logical_key] = self._sim_addr(
                            stack_addr_map,
                            parsed.actual_addr,
                            "S",
                        )
                actual_stack_lookup[parsed.actual_addr] = stack_addr_map[parsed.actual_addr]

        for parsed_frame in parsed_frames:
            variables: list[Variable] = []
            for parsed in parsed_frame.variables:
                stack_addr = stack_addr_map[parsed.actual_addr]
                value = parsed.value
                is_reference = "&" in parsed.type and "*" not in parsed.type
                is_pointer = "*" in parsed.type or (self._is_hex_addr(value) and not is_reference)
                if is_pointer and self._is_hex_addr(value) and not self._is_null(value):
                    value = self._target_sim_addr(value, actual_stack_lookup, heap_addr_map)
                elif is_reference and self._is_hex_addr(value) and not self._is_null(value):
                    value = self._target_sim_addr(value, actual_stack_lookup, heap_addr_map)
                elif (is_pointer or is_reference) and self._is_null(value):
                    value = "nullptr"
                elif parsed.elements:
                    value = self._format_elements(parsed.elements)
                elif parsed.members:
                    value = self._format_members(parsed.members)
                object_class = self._object_class_name(parsed.type)
                object_info = class_info.get(object_class, _ClassInfo())
                variables.append(Variable(
                    name=parsed.name,
                    type=self._clean_type(parsed.type),
                    value=value,
                    address=stack_addr,
                    is_pointer=is_pointer,
                    is_array=bool(parsed.elements),
                    element_count=len(parsed.elements) or None,
                    elements=[
                        ArrayElement(index=element.index, value=self._clean_value(element.value))
                        for element in parsed.elements
                    ],
                    members=[
                        StructMember(
                            name=member.name,
                            type=self._clean_type(member.type),
                            value=self._clean_value(member.value),
                        )
                        for member in parsed.members
                    ],
                    is_object=bool(parsed.members),
                    class_name=object_class if parsed.members else "",
                    base_classes=object_info.base_classes if parsed.members else [],
                    virtual_methods=object_info.virtual_methods if parsed.members else [],
                    is_reference=is_reference,
                ))
            frame_variables.append((parsed_frame.name, variables))

        parsed_vars = [var for parsed_frame in parsed_frames for var in parsed_frame.variables]
        for parsed in parsed_vars:
            if not parsed.pointee_addr or self._is_null(parsed.pointee_addr):
                continue
            if "&" in parsed.type and "*" not in parsed.type:
                continue
            source_addr = stack_addr_map.get(parsed.actual_addr)
            if source_addr is None:
                continue
            target_addr = self._target_sim_addr(parsed.pointee_addr, actual_stack_lookup, heap_addr_map)
            is_dangling = parsed.pointee_addr in freed_heap
            pointer_edges.append(PointerEdge(
                source_address=source_addr,
                target_address=target_addr,
                is_dangling=is_dangling,
            ))

            if parsed.pointee_addr not in actual_stack_lookup:
                heap_type, heap_value = heap_values.get(
                    parsed.pointee_addr,
                    (self._pointee_type(parsed.type), parsed.pointee_value),
                )
                array_info = heap_array_values.get(parsed.pointee_addr)
                if array_info is not None:
                    array_type, elements = array_info
                    heap_blocks_by_actual[parsed.pointee_addr] = HeapBlock(
                        address=target_addr,
                        type=f"{self._clean_type(array_type)}[]",
                        value=self._format_elements(elements),
                        is_freed=is_dangling,
                        is_array=True,
                        element_count=len(elements),
                        elements=[
                            ArrayElement(index=element.index, value=self._clean_value(element.value))
                            for element in elements
                        ],
                    )
                    continue
                object_info = heap_object_values.get(parsed.pointee_addr)
                if object_info is not None:
                    object_type, members = object_info
                    class_name = self._object_class_name(object_type or self._pointee_type(parsed.type))
                    metadata = class_info.get(class_name, _ClassInfo())
                    heap_blocks_by_actual[parsed.pointee_addr] = HeapBlock(
                        address=target_addr,
                        type=self._clean_type(object_type or self._pointee_type(parsed.type)),
                        value=self._format_members(members),
                        is_freed=is_dangling,
                        members=[
                            StructMember(
                                name=member.name,
                                type=self._clean_type(member.type),
                                value=self._clean_value(member.value),
                            )
                            for member in members
                        ],
                        is_object=True,
                        class_name=class_name,
                        base_classes=metadata.base_classes,
                        virtual_methods=metadata.virtual_methods,
                    )
                    continue
                heap_blocks_by_actual[parsed.pointee_addr] = HeapBlock(
                    address=target_addr,
                    type=self._clean_type(heap_type or self._pointee_type(parsed.type)),
                    value=self._clean_value(heap_value),
                    is_freed=is_dangling,
                )

        return MemoryState(
            line_number=original_line,
            source_code=source_code,
            stack=[
                StackFrame(frame_name=frame_name or "main", variables=variables)
                for frame_name, variables in frame_variables
            ],
            heap=list(heap_blocks_by_actual.values()),
            edges=pointer_edges,
        )

    @staticmethod
    def _frame_line(text: str) -> int | None:
        location = DebugExecutor._frame_location(text)
        return location.line if location else None

    @staticmethod
    def _frame_location(text: str) -> _FrameLocation | None:
        matches = re.findall(
            r"frame #0: .*?`(?P<function>.*?) at (?P<file>.*):(?P<line>\d+):\d+",
            text,
        )
        if not matches:
            return None
        function, file_path, line = matches[0]
        return _FrameLocation(file=file_path.strip(), line=int(line), function=function.strip())

    @staticmethod
    def _is_step_in_transition(
        before: _FrameLocation,
        after: _FrameLocation | None,
        prepared: _PreparedSource,
    ) -> bool:
        if after is None:
            return False
        if prepared.source_path and Path(after.file).name != Path(prepared.source_path).name:
            return True
        return (
            DebugExecutor._clean_frame_name(before.function)
            != DebugExecutor._clean_frame_name(after.function)
        )

    def _parse_stack_snapshots(
        self,
        text: str,
        prepared: _PreparedSource,
        declarations: dict[str, int],
        fallback_location: _FrameLocation,
        fallback_original_line: int,
    ) -> list[_ParsedFrame]:
        frame_re = re.compile(
            r"^__CXXMV_FRAME__(?P<index>\d+)__(?P<line>\d+)__(?P<name>.*)$",
            re.MULTILINE,
        )
        matches = list(frame_re.finditer(text))
        if not matches:
            variables = [
                var for var in self._parse_variables(text)
                if declarations.get(var.name, 0) <= fallback_original_line
            ]
            return [_ParsedFrame(
                name=self._clean_frame_name(fallback_location.function),
                original_line=fallback_original_line,
                variables=variables,
            )]

        frames: list[_ParsedFrame] = []
        seen_names: dict[str, int] = {}
        for idx, match in enumerate(matches):
            chunk_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            frame_chunk = text[match.end():chunk_end]
            generated_line = int(match.group("line"))
            frame_index = int(match.group("index"))
            raw_name = match.group("name").strip()
            frame_name = self._clean_frame_name(raw_name)
            fallback_name = self._clean_frame_name(fallback_location.function)
            same_top_frame = frame_index == 0 and frame_name == fallback_name
            original_line = prepared.line_map.get(generated_line)
            if original_line is None:
                if not same_top_frame:
                    continue
                original_line = fallback_original_line
            if same_top_frame:
                declaration_cutoff = fallback_original_line
            elif generated_line in prepared.step_in_lines:
                declaration_cutoff = max(0, original_line - 1)
            else:
                declaration_cutoff = original_line
            seen_names[frame_name] = seen_names.get(frame_name, 0) + 1
            if seen_names[frame_name] > 1:
                frame_name = f"{frame_name}({seen_names[frame_name]})"
            variables = [
                var for var in self._parse_variables(frame_chunk)
                if declarations.get(var.name, 0) <= declaration_cutoff
            ]
            frames.append(_ParsedFrame(
                name=frame_name,
                original_line=original_line,
                variables=variables,
            ))

        return frames or [_ParsedFrame(
            name=self._clean_frame_name(fallback_location.function),
            original_line=fallback_original_line,
            variables=[],
        )]

    def _parse_cdb_stack_snapshots(
        self,
        text: str,
        prepared: _PreparedSource,
        declarations: dict[str, int],
        fallback_location: _FrameLocation,
        fallback_original_line: int,
    ) -> list[_ParsedFrame]:
        locations = self._cdb_stack_locations(text, prepared)
        marker_re = re.compile(r"^__CXXMV_FRAMEV__(?P<index>\d+)$", re.MULTILINE)
        matches = list(marker_re.finditer(text))
        if not matches:
            variables = [
                var for var in self._parse_cdb_frame_variables(text)
                if declarations.get(var.name, 0) <= fallback_original_line
            ]
            return [_ParsedFrame(
                name=self._clean_frame_name(fallback_location.function),
                original_line=fallback_original_line,
                variables=variables,
            )]

        frames: list[_ParsedFrame] = []
        seen_names: dict[str, int] = {}
        for idx, match in enumerate(matches):
            frame_index = int(match.group("index"))
            location = locations.get(frame_index)
            if location is None:
                continue
            chunk_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            frame_chunk = text[match.end():chunk_end]

            frame_name = self._clean_frame_name(location.function)
            fallback_name = self._clean_frame_name(fallback_location.function)
            same_top_frame = frame_index == 0 and frame_name == fallback_name
            original_line = prepared.line_map.get(location.line)
            if original_line is None:
                if not same_top_frame:
                    continue
                original_line = fallback_original_line
            if same_top_frame:
                declaration_cutoff = fallback_original_line
            elif location.line in prepared.step_in_lines:
                declaration_cutoff = max(0, original_line - 1)
            else:
                declaration_cutoff = original_line

            seen_names[frame_name] = seen_names.get(frame_name, 0) + 1
            if seen_names[frame_name] > 1:
                frame_name = f"{frame_name}({seen_names[frame_name]})"
            variables = [
                var for var in self._parse_cdb_frame_variables(frame_chunk)
                if declarations.get(var.name, 0) <= declaration_cutoff
            ]
            frames.append(_ParsedFrame(
                name=frame_name,
                original_line=original_line,
                variables=variables,
            ))

        return frames or [_ParsedFrame(
            name=self._clean_frame_name(fallback_location.function),
            original_line=fallback_original_line,
            variables=[],
        )]

    @classmethod
    def _cdb_frame_location(
        cls,
        text: str,
        prepared: _PreparedSource | None = None,
    ) -> _FrameLocation | None:
        locations = cls._cdb_stack_locations(text, prepared)
        if not locations:
            return None
        return locations.get(0) or locations[min(locations)]

    @staticmethod
    def _cdb_stack_locations(
        text: str,
        prepared: _PreparedSource | None = None,
    ) -> dict[int, _FrameLocation]:
        frame_re = re.compile(
            r"^\s*(?P<index>[0-9a-fA-F]+)\s+"
            r"[0-9a-fA-F`]+\s+"
            r"(?P<symbol>.+?)\s+"
            r"\[(?P<file>.+?)\s*@\s*(?P<line>\d+)\]",
            re.MULTILINE,
        )
        locations: dict[int, _FrameLocation] = {}
        source_name = Path(prepared.source_path).name if prepared and prepared.source_path else "program.cpp"
        for match in frame_re.finditer(text):
            file_path = match.group("file").strip()
            if source_name and DebugExecutor._path_name(file_path) != source_name:
                continue
            try:
                index = int(match.group("index"), 16)
            except ValueError:
                index = int(match.group("index"))
            symbol = match.group("symbol").strip()
            locations[index] = _FrameLocation(
                file=file_path,
                line=int(match.group("line")),
                function=symbol,
            )
        return locations

    def _parse_cdb_frame_variables(self, text: str) -> list[_ParsedVar]:
        variables = self._parse_cdb_variables(text)
        dx_variables = self._parse_cdb_dx_variables(text)
        by_name = {var.name: var for var in variables}

        for dx_var in dx_variables:
            existing = by_name.get(dx_var.name)
            if existing is None:
                variables.append(dx_var)
                by_name[dx_var.name] = dx_var
                continue
            if dx_var.elements:
                existing.elements = dx_var.elements
            if dx_var.members and not dx_var.elements:
                existing.members = dx_var.members
            if dx_var.pointee_addr and not existing.pointee_addr:
                existing.pointee_addr = dx_var.pointee_addr
            if dx_var.pointee_elements:
                existing.pointee_elements = dx_var.pointee_elements
            if dx_var.pointee_members:
                existing.pointee_members = dx_var.pointee_members
            if dx_var.value and not self._is_hex_addr(existing.value):
                existing.value = dx_var.value

        return variables

    def _parse_cdb_variables(self, text: str) -> list[_ParsedVar]:
        variables: list[_ParsedVar] = []
        pattern = re.compile(
            r"^\s*(?:(?P<addr>(?:0x)?[0-9a-fA-F`]{4,})\s+)?"
            r"(?P<type>.+?)\s+"
            r"(?P<name>[*&]?[A-Za-z_]\w*)\s+=\s+"
            r"(?P<value>.+?)\s*$"
        )
        for line in text.splitlines():
            stripped = line.strip()
            if (
                not stripped
                or stripped.startswith("__CXXMV_")
                or stripped.startswith((".", "#", "Child-SP", "RetAddr"))
                or "[" in stripped and "@" in stripped
            ):
                continue
            match = pattern.match(line)
            if match is None:
                continue

            raw_addr = match.group("addr") or f"cdb:{len(variables)}:{match.group('name')}"
            raw_value_text = match.group("value")
            raw_value = self._clean_cdb_value(raw_value_text)
            value = self._normalize_cdb_addr(raw_value) if self._is_cdb_addr(raw_value) else raw_value
            clean_type = self._clean_type(match.group("type"))
            var = _ParsedVar(
                actual_addr=self._normalize_cdb_addr(raw_addr),
                type=clean_type,
                name=match.group("name").lstrip("*&"),
                value=value,
            )
            payload = self._structured_payload(raw_value_text)
            if payload:
                element_type = self._array_element_type(clean_type)
                elements = self._parse_structured_elements(payload, element_type)
                members = [] if elements else self._parse_structured_members(payload)
                if "*" in var.type and self._is_hex_addr(value) and not self._is_null(value):
                    var.pointee_type = self._pointee_type(var.type)
                    var.pointee_elements = elements
                    var.pointee_members = members
                elif elements:
                    var.elements = elements
                elif members:
                    var.members = members
            if "*" in var.type and self._is_hex_addr(value) and not self._is_null(value):
                var.pointee_addr = value
            variables.append(var)
        return variables

    def _parse_cdb_dx_variables(self, text: str) -> list[_ParsedVar]:
        variables: list[_ParsedVar] = []
        pending: _ParsedVar | None = None
        pending_indent = 0
        pending_element: _ParsedElement | None = None
        pending_element_indent = 0
        pending_element_members: list[_ParsedMember] = []
        pattern = re.compile(
            r"^(?P<indent>\s+)"
            r"(?P<name>\[\d+\]|[A-Za-z_]\w*)\s*:\s*"
            r"(?P<value>.*?)\s*"
            r"\[Type:\s*(?P<type>.*)\]\s*$"
        )

        def flush_pending_element():
            nonlocal pending_element, pending_element_members
            if pending_element is not None and pending_element_members:
                pending_element.value = self._format_members(pending_element_members)
            pending_element = None
            pending_element_members = []

        for line in text.splitlines():
            stripped = line.strip()
            if (
                not stripped
                or stripped.startswith("__CXXMV_")
                or stripped.startswith("@$curframe")
                or stripped.startswith("[<")
            ):
                continue
            match = pattern.match(line)
            if match is None:
                continue

            indent = len(match.group("indent"))
            name = match.group("name")
            raw_value = match.group("value").strip()
            clean_type = self._clean_type(match.group("type"))
            clean_value = self._clean_cdb_value(raw_value)
            if self._is_cdb_addr(clean_value):
                clean_value = self._normalize_cdb_addr(clean_value)

            if pending_element is not None and indent > pending_element_indent:
                if self._array_index(name) is None:
                    pending_element_members.append(_ParsedMember(
                        name=name,
                        type=clean_type,
                        value=self._clean_value(raw_value),
                    ))
                    pending_element.value = self._format_members(pending_element_members)
                    continue

            if pending_element is not None and indent <= pending_element_indent:
                flush_pending_element()

            if pending is not None and indent > pending_indent:
                element_index = self._array_index(name)
                if element_index is not None:
                    target_elements = (
                        pending.pointee_elements
                        if pending.pointee_addr
                        else pending.elements
                    )
                    element = _ParsedElement(
                        index=element_index,
                        type=clean_type,
                        value=self._clean_value(raw_value),
                    )
                    target_elements.append(element)
                    pending_element = element
                    pending_element_indent = indent
                    pending_element_members = []
                else:
                    target_members = (
                        pending.pointee_members
                        if pending.pointee_addr
                        else pending.members
                    )
                    target_members.append(_ParsedMember(
                        name=name,
                        type=clean_type,
                        value=self._clean_value(raw_value),
                    ))
                continue

            flush_pending_element()
            var = _ParsedVar(
                actual_addr=f"cdbdx:{len(variables)}:{name}",
                type=clean_type,
                name=name,
                value=clean_value,
            )
            elements: list[_ParsedElement] = []
            members: list[_ParsedMember] = []
            payload = self._structured_payload(raw_value)
            if payload:
                element_type = self._array_element_type(clean_type)
                elements = self._parse_structured_elements(payload, element_type)
                members = [] if elements else self._parse_structured_members(payload)
            if "*" in var.type and self._is_hex_addr(clean_value) and not self._is_null(clean_value):
                var.pointee_addr = clean_value
                var.pointee_type = self._pointee_type(var.type)
                var.pointee_elements = elements
                var.pointee_members = members
            else:
                var.elements = elements
                var.members = members
            variables.append(var)
            pending = var
            pending_indent = indent

        flush_pending_element()
        return variables

    def _parse_variables(self, text: str) -> list[_ParsedVar]:
        variables: list[_ParsedVar] = []
        pending_pointer: _ParsedVar | None = None
        pending_container: _ParsedVar | None = None

        for line in text.splitlines():
            if line.strip() == "}":
                pending_pointer = None
                pending_container = None
                continue
            match = re.match(r"^(0x[0-9a-fA-F]+):(?P<rest>.*)$", line.rstrip())
            if match is None:
                continue
            actual_addr = self._normalize_actual_addr(match.group(1))
            rest = match.group("rest")

            if rest.startswith(" " * 2):
                child = self._parse_value_rest(rest.strip())
                if child is None:
                    continue

                child_type, child_name, child_value = child
                if (
                    pending_pointer is not None
                    and actual_addr == pending_pointer.pointee_addr
                    and child_name.startswith("*")
                ):
                    pending_pointer.pointee_type = child_type
                    pending_pointer.pointee_value = self._clean_value(child_value)
                elif pending_pointer is not None:
                    pending_pointer.pointee_type = pending_pointer.pointee_type or self._pointee_type(pending_pointer.type)
                    element_index = self._array_index(child_name)
                    if element_index is not None:
                        pending_pointer.pointee_elements.append(_ParsedElement(
                            index=element_index,
                            type=self._clean_type(child_type),
                            value=self._clean_value(child_value),
                        ))
                    else:
                        pending_pointer.pointee_members.append(_ParsedMember(
                            name=child_name.lstrip("*&"),
                            type=self._clean_type(child_type),
                            value=self._clean_value(child_value),
                        ))
                elif pending_container is not None:
                    element_index = self._array_index(child_name)
                    if element_index is not None:
                        pending_container.elements.append(_ParsedElement(
                            index=element_index,
                            type=self._clean_type(child_type),
                            value=self._clean_value(child_value),
                        ))
                    else:
                        pending_container.members.append(_ParsedMember(
                            name=child_name.lstrip("*&"),
                            type=self._clean_type(child_type),
                            value=self._clean_value(child_value),
                        ))
                continue

            raw_rest = rest.strip()
            parsed = self._parse_value_rest(raw_rest)
            if parsed is None:
                pending_pointer = None
                pending_container = None
                continue

            type_text, name, raw_value = parsed
            value = self._clean_value(raw_value)
            if self._is_hex_addr(value):
                value = self._normalize_actual_addr(value)
            var = _ParsedVar(
                actual_addr=actual_addr,
                type=self._clean_type(type_text),
                name=name,
                value=value,
            )
            if self._is_hex_addr(value) and ("*" in type_text or "&" in type_text):
                var.pointee_addr = value
                pending_pointer = var
            else:
                pending_pointer = None
            pending_container = var if "{" in raw_value else None
            variables.append(var)

        return variables

    @staticmethod
    def _parse_value_rest(rest: str) -> tuple[str, str, str] | None:
        match = re.match(
            r"\((?P<type>.+?)\)\s+"
            r"(?P<name>[*&]?[A-Za-z_]\w*|\[\d+\])\s+=\s+"
            r"(?P<value>.*)$",
            rest,
        )
        if match is None:
            return None
        return match.group("type"), match.group("name"), match.group("value")

    def _parse_array_expressions(self, text: str) -> dict[str, list[_ParsedElement]]:
        arrays: dict[str, list[_ParsedElement]] = {}
        pending: tuple[str, int] | None = None
        marker_re = re.compile(r"^__CXXMV_EXPR__\d+__(?P<name>[A-Za-z_]\w*)__(?P<index>\d+)$")
        value_re = re.compile(r"^\((?P<type>.+?)\)\s+(?:\$\d+\s+=\s+)?(?P<value>.*)$")

        for raw_line in text.splitlines():
            line = raw_line.strip()
            marker = marker_re.match(line)
            if marker:
                pending = (marker.group("name"), int(marker.group("index")))
                continue
            if pending is None:
                continue
            value_match = value_re.match(line)
            if value_match is None:
                continue

            pointer_name, index = pending
            arrays.setdefault(pointer_name, []).append(_ParsedElement(
                index=index,
                type=self._clean_type(value_match.group("type")),
                value=self._clean_value(value_match.group("value")),
            ))
            pending = None

        for elements in arrays.values():
            elements.sort(key=lambda element: element.index)
        return arrays

    @staticmethod
    def _declaration_lines(lines: list[str]) -> dict[str, int]:
        declarations: dict[str, int] = {}
        scalar_type = (
            r"(?:(?:signed|unsigned)\s+)?"
            r"(?:auto|bool|char|wchar_t|char16_t|char32_t|"
            r"short(?:\s+int)?|int|long(?:\s+long)?(?:\s+int)?|"
            r"float|double|long\s+double|string|std::string|size_t|"
            r"[A-Za-z_]\w*(?:::\w+)?(?:<[^;=]+>)?)"
        )
        pattern = re.compile(
            r"^\s*(?:const\s+|static\s+|volatile\s+)*"
            rf"{scalar_type}"
            r"(?:\s+|(?=[*&]))[\s*&]*([A-Za-z_]\w*)\b"
        )
        for_pattern = re.compile(
            rf"\bfor\s*\(\s*(?:const\s+)?{scalar_type}(?:\s+|(?=[*&]))[\s*&]*([A-Za-z_]\w*)\b"
        )
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", "//", "return", "using ")):
                continue
            for_match = for_pattern.search(line)
            if for_match:
                declarations.setdefault(for_match.group(1), idx)
            match = pattern.match(line)
            if match:
                declarations.setdefault(match.group(1), idx)
        return declarations

    @staticmethod
    def _class_metadata(lines: list[str]) -> dict[str, _ClassInfo]:
        source = "\n".join(lines)
        class_re = re.compile(
            r"\b(?:class|struct)\s+"
            r"(?P<name>[A-Za-z_]\w*)"
            r"(?:\s*:\s*(?P<bases>[^{]+))?"
            r"\s*\{(?P<body>.*?)\}\s*;",
            re.DOTALL,
        )
        info: dict[str, _ClassInfo] = {}
        for match in class_re.finditer(source):
            name = match.group("name")
            bases = DebugExecutor._parse_base_classes(match.group("bases") or "")
            virtuals = DebugExecutor._parse_virtual_methods(match.group("body") or "", name)
            info[name] = _ClassInfo(base_classes=bases, virtual_methods=virtuals)

        def inherited_virtuals(class_name: str, seen: set[str] | None = None) -> list[str]:
            seen = seen or set()
            if class_name in seen:
                return []
            seen.add(class_name)
            current = info.get(class_name)
            if current is None:
                return []
            methods: list[str] = []
            for base in current.base_classes:
                for method in inherited_virtuals(base, seen):
                    if method not in methods:
                        methods.append(method)
            for method in current.virtual_methods:
                if method not in methods:
                    methods.append(method)
            return methods

        for class_name, class_info in list(info.items()):
            class_info.virtual_methods = inherited_virtuals(class_name)
        return info

    @staticmethod
    def _parse_base_classes(base_text: str) -> list[str]:
        bases: list[str] = []
        for raw in base_text.split(","):
            clean = re.sub(r"\b(?:public|protected|private|virtual)\b", "", raw).strip()
            clean = clean.split("<", 1)[0].strip() if "<" in clean else clean
            match = re.search(r"([A-Za-z_]\w*(?:::\w+)?)$", clean)
            if match:
                name = match.group(1).rsplit("::", 1)[-1]
                if name not in bases:
                    bases.append(name)
        return bases

    @staticmethod
    def _parse_virtual_methods(body: str, class_name: str = "") -> list[str]:
        methods: list[str] = []
        patterns = (
            r"\bvirtual\b[^;{}]*?\b(?P<name>[A-Za-z_]\w*)\s*\([^;{}]*\)",
            r"\b(?P<name>[A-Za-z_]\w*)\s*\([^;{}]*\)\s*(?:const\s*)?(?:override|final)\b",
        )
        for pattern in patterns:
            for match in re.finditer(pattern, body):
                name = match.group("name")
                previous = body[match.start("name") - 1] if match.start("name") > 0 else ""
                if (
                    name not in {"if", "for", "while", "switch", "return"}
                    and name != class_name
                    and previous != "~"
                ):
                    method = f"{name}()"
                    if method not in methods:
                        methods.append(method)
        return methods

    @staticmethod
    def _heap_array_declarations(lines: list[str]) -> dict[str, tuple[str, int]]:
        declarations: dict[str, tuple[str, int]] = {}
        pattern = re.compile(
            r"(?:\b(?:auto|[A-Za-z_]\w*(?:::\w+)?(?:<[^;=]+>)?\s*\*)\s+)?"
            r"(?P<name>[A-Za-z_]\w*)\s*=\s*new\s+"
            r"(?P<type>[A-Za-z_]\w*(?:::\w+)?(?:<[^;\[]+>)?)"
            r"\s*\[\s*(?P<count>\d+)\s*\]"
        )
        for line in lines:
            match = pattern.search(line)
            if not match:
                continue
            count = min(int(match.group("count")), 32)
            if count > 0:
                declarations[match.group("name")] = (
                    DebugExecutor._clean_type(match.group("type")),
                    count,
                )
        return declarations

    @staticmethod
    def _step_in_lines(lines: list[str], line_map: dict[int, int]) -> set[int]:
        function_names = DebugExecutor._user_function_names(lines)
        if not function_names:
            return set()

        step_lines: set[int] = set()
        for line_no in line_map:
            line = lines[line_no - 1] if 1 <= line_no <= len(lines) else ""
            if DebugExecutor._is_function_definition_line(line, function_names):
                continue
            if DebugExecutor._has_user_function_call(line, function_names):
                step_lines.add(line_no)
        return step_lines

    @staticmethod
    def _user_function_names(lines: list[str]) -> set[str]:
        keywords = {
            "if", "for", "while", "switch", "catch", "return", "sizeof",
            "new", "delete", "else", "do",
        }
        pattern = re.compile(
            r"^\s*(?:template\s*<[^>]+>\s*)?"
            r"(?:(?:inline|static|virtual|explicit|constexpr|friend)\s+)*"
            r"(?:(?:[A-Za-z_]\w*(?:::\w+)?|~?[A-Za-z_]\w*|operator\s*\S+)"
            r"(?:<[^;{}()]*>)?[\s*&]+)*"
            r"(?P<name>~?[A-Za-z_]\w*)\s*\([^;{}]*\)\s*"
            r"(?:const\s*)?(?:noexcept\s*)?(?:->\s*[^:{]+)?\s*(?:[:{]|$)"
        )
        names: set[str] = set()
        for raw_line in lines:
            line = DebugExecutor._strip_line_comment(raw_line).strip()
            if not line:
                continue
            match = pattern.match(line)
            if not match:
                continue
            name = match.group("name").lstrip("~")
            if name not in keywords:
                names.add(name)
        names.discard("main")
        names.difference_update(DebugExecutor._class_names(lines))
        return names

    @staticmethod
    def _class_names(lines: list[str]) -> set[str]:
        names: set[str] = set()
        pattern = re.compile(r"\b(?:class|struct)\s+([A-Za-z_]\w*)\b")
        for line in lines:
            match = pattern.search(DebugExecutor._strip_line_comment(line))
            if match:
                names.add(match.group(1))
        return names

    @staticmethod
    def _is_function_definition_line(line: str, function_names: set[str]) -> bool:
        stripped = DebugExecutor._strip_line_comment(line).strip()
        if not stripped:
            return False
        for name in function_names:
            if re.match(rf".*\b{re.escape(name)}\s*\([^;]*\)\s*(?:const\s*)?(?:noexcept\s*)?(?:[:{{]|$)", stripped):
                return True
        return False

    @staticmethod
    def _has_user_function_call(line: str, function_names: set[str]) -> bool:
        stripped = DebugExecutor._strip_line_comment(line)
        if "cout" in stripped or "std::cout" in stripped:
            return False
        for name in function_names:
            if re.search(rf"(?<![\w:~]){re.escape(name)}\s*\(", stripped):
                return True
        return False

    @staticmethod
    def _strip_line_comment(line: str) -> str:
        in_string = False
        escape = False
        for i, ch in enumerate(line):
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                return line[:i]
        return line

    @staticmethod
    def _lldb_step_command(step_in_lines: set[int], source_filename: str = "program.cpp") -> str:
        line_set = "{" + ",".join(str(line) for line in sorted(step_in_lines)) + "}"
        return (
            "script "
            "frame=lldb.debugger.GetSelectedTarget().GetProcess().GetSelectedThread().GetSelectedFrame(); "
            "entry=frame.GetLineEntry(); "
            "file=entry.GetFileSpec().GetFilename(); "
            "line=entry.GetLine(); "
            f"cmd='process continue' if file and file != {source_filename!r} else "
            f"('thread step-in' if line in {line_set} else 'thread step-over'); "
            "lldb.debugger.HandleCommand(cmd)"
        )

    @staticmethod
    def _lldb_stack_snapshot_command(source_filename: str = "program.cpp") -> str:
        script = (
            "import sys\n"
            "target=lldb.debugger.GetSelectedTarget()\n"
            "thread=target.GetProcess().GetSelectedThread()\n"
            "def synthetic_addr(name, value_idx=-1, frame_idx=-1):\n"
            "    seed=((frame_idx + 1) * 1000003 + (value_idx + 1) * 9176) & 0xfffffffffffffff\n"
            "    for ch in (name or ''):\n"
            "        seed=((seed * 131) + ord(ch)) & 0xfffffffffffffff\n"
            "    return '0xf%015x' % seed\n"
            "def addr_of(value, value_idx=-1, frame_idx=-1):\n"
            "    typ=type_of(value)\n"
            "    name=value.GetName() or ''\n"
            "    loc=value.GetLocation() or ''\n"
            "    if loc == 'scalar' and '*' in typ:\n"
            "        return synthetic_addr(name, value_idx, frame_idx)\n"
            "    if loc.startswith('0x'):\n"
            "        return loc.split()[0]\n"
            "    addr=value.GetAddress()\n"
            "    if addr.IsValid():\n"
            "        load=addr.GetLoadAddress(target)\n"
            "        if load != lldb.LLDB_INVALID_ADDRESS:\n"
            "            return '0x%x' % load\n"
            "    return loc.split()[0] if loc.startswith('0x') else '0x0'\n"
            "def val_of(value):\n"
            "    return value.GetValue() or value.GetSummary() or ''\n"
            "def type_of(value):\n"
            "    return value.GetTypeName() or 'unknown'\n"
            "def is_std_string_type(typ):\n"
            "    compact=typ.replace(' ', '')\n"
            "    return compact in ('string', 'std::string', 'std::__1::string') or compact.startswith('std::basic_string<char') or compact.startswith('std::__1::basic_string<char')\n"
            "def is_expandable_container_type(typ):\n"
            "    compact=typ.replace(' ', '')\n"
            "    tokens=('array<', 'deque<', 'list<', 'map<', 'multimap<', 'multiset<', 'pair<', 'set<', 'tuple<', 'unordered_map<', 'unordered_set<', 'vector<')\n"
            "    return any(token in compact for token in tokens)\n"
            "def flat_value(value, depth=0):\n"
            "    val=val_of(value)\n"
            "    typ=type_of(value)\n"
            "    if val and not is_expandable_container_type(typ):\n"
            "        return val\n"
            "    if depth >= 2:\n"
            "        return val\n"
            "    count=min(value.GetNumChildren(), 16)\n"
            "    parts=[]\n"
            "    for child_idx in range(count):\n"
            "        child=value.GetChildAtIndex(child_idx)\n"
            "        child_name=child.GetName() or ''\n"
            "        child_val=flat_value(child, depth + 1)\n"
            "        if child_name.startswith('['):\n"
            "            parts.append('%s=%s' % (child_name, child_val))\n"
            "        elif child_name:\n"
            "            parts.append('%s=%s' % (child_name.lstrip('*&'), child_val))\n"
            "        else:\n"
            "            parts.append(child_val)\n"
            "    if parts:\n"
            "        return '{' + ', '.join(parts) + '}'\n"
            "    if val:\n"
            "        return val\n"
            "    if 'vector' in typ:\n"
            "        summary=value.GetSummary() or ''\n"
            "        return summary\n"
            "    return ''\n"
            "def emit_child(child, name=None, frame_idx=-1):\n"
            "    print('%s:   (%s) %s = %s' % (addr_of(child, -1, frame_idx), type_of(child), name or child.GetName() or '', flat_value(child)))\n"
            "def emit_value(value, value_idx=-1, frame_idx=-1):\n"
            "    name=value.GetName() or ''\n"
            "    typ=type_of(value)\n"
            "    val=val_of(value)\n"
            "    addr=addr_of(value, value_idx, frame_idx)\n"
            "    summary=value.GetSummary() or ''\n"
            "    if is_std_string_type(typ) and val:\n"
            "        print('%s: (%s) %s = %s' % (addr, typ, name, val))\n"
            "        return\n"
            "    if '&' in typ and val and val not in ('0x0', '0x0000000000000000'):\n"
            "        print('%s: (%s) %s = %s' % (addr, typ, name, val))\n"
            "        return\n"
            "    if '*' in typ and not val:\n"
            "        raw=value.GetValueAsUnsigned(0)\n"
            "        val='0x%x' % raw\n"
            "    if '*' in typ and val in ('0x0', '0x0000000000000000'):\n"
            "        print('%s: (%s) %s = %s' % (addr, typ, name, val))\n"
            "        return\n"
            "    if '*' in typ and 'char' in typ and summary:\n"
            "        char_typ='const char[]' if 'const' in typ else 'char[]'\n"
            "        print('%s: (%s) %s = %s {' % (addr, typ, name, val))\n"
            "        print('%s:   (%s) *%s = %s' % (val, char_typ, name, summary))\n"
            "        print('}')\n"
            "        return\n"
            "    if '*' in typ and val and val not in ('0x0', '0x0000000000000000'):\n"
            "        print('%s: (%s) %s = %s {' % (addr, typ, name, val))\n"
            "        deref=value.Dereference()\n"
            "        if deref.IsValid():\n"
            "            deref_child_count=min(deref.GetNumChildren(), 32)\n"
            "            if deref_child_count > 0:\n"
            "                for child_idx in range(deref_child_count):\n"
            "                    emit_child(deref.GetChildAtIndex(child_idx), frame_idx=frame_idx)\n"
            "            else:\n"
            "                emit_child(deref, '*' + name, frame_idx=frame_idx)\n"
            "        print('}')\n"
            "        return\n"
            "    child_count=min(value.GetNumChildren(), 32)\n"
            "    if child_count > 0:\n"
            "        print('%s: (%s) %s = {' % (addr, typ, name))\n"
            "        for child_idx in range(child_count):\n"
            "            emit_child(value.GetChildAtIndex(child_idx), frame_idx=frame_idx)\n"
            "        print('}')\n"
            "        return\n"
            "    print('%s: (%s) %s = %s' % (addr, typ, name, val))\n"
            "limit=min(thread.GetNumFrames(), 8)\n"
            "for idx in range(limit):\n"
            "    frame=thread.GetFrameAtIndex(idx)\n"
            "    entry=frame.GetLineEntry()\n"
            "    file=entry.GetFileSpec().GetFilename()\n"
            f"    if file != {source_filename!r}:\n"
            "        continue\n"
            "    name=frame.GetFunctionName() or frame.GetDisplayFunctionName() or ''\n"
            "    print('__CXXMV_FRAME__%d__%d__%s' % (idx, entry.GetLine(), name))\n"
            "    sys.stdout.flush()\n"
            "    values=frame.GetVariables(True, True, False, True)\n"
            "    for value_idx in range(values.GetSize()):\n"
            "        emit_value(values.GetValueAtIndex(value_idx), value_idx, idx)\n"
        )
        return f"script exec({script!r})"

    @staticmethod
    def _lldb_array_probe_command(step: int, pointer_name: str, index: int) -> str:
        marker = f"__CXXMV_EXPR__{step}__{pointer_name}__{index}"
        expression = f"{pointer_name}[{index}]"
        return (
            "script "
            "frame=lldb.debugger.GetSelectedTarget().GetProcess().GetSelectedThread().GetSelectedFrame(); "
            f"var=frame.FindVariable('{pointer_name}'); "
            "value=var.GetValue(); "
            "ok=var.IsValid() and value and int(value, 0) != 0; "
            f"print('{marker}') if ok else None; "
            f"print(frame.EvaluateExpression('{expression}')) if ok else None"
        )

    @staticmethod
    def _source_line(lines: list[str], line_number: int) -> str:
        if 1 <= line_number <= len(lines):
            return lines[line_number - 1].strip()
        return ""

    @staticmethod
    def _deleted_pointer_name(source_code: str) -> str:
        match = re.search(r"\bdelete(?:\s*\[\s*\])?\s+([A-Za-z_]\w*)", source_code)
        return match.group(1) if match else ""

    @staticmethod
    def _sim_addr(mapping: dict[str, str], actual_addr: str, prefix: str) -> str:
        if actual_addr not in mapping:
            mapping[actual_addr] = f"0x{prefix}{len(mapping) + 1:03d}"
        return mapping[actual_addr]

    def _target_sim_addr(
        self,
        actual_addr: str,
        actual_stack_lookup: dict[str, str],
        heap_addr_map: dict[str, str],
    ) -> str:
        if actual_addr in actual_stack_lookup:
            return actual_stack_lookup[actual_addr]
        return self._sim_addr(heap_addr_map, actual_addr, "H")

    @staticmethod
    def _is_hex_addr(value: str) -> bool:
        return bool(re.fullmatch(r"0x[0-9a-fA-F]+", value.strip()))

    @staticmethod
    def _normalize_actual_addr(value: str) -> str:
        stripped = value.strip()
        if not DebugExecutor._is_hex_addr(stripped):
            return stripped
        return f"0x{int(stripped, 16):x}"

    @staticmethod
    def _is_cdb_addr(value: str) -> bool:
        stripped = value.strip().replace("`", "")
        return bool(re.fullmatch(r"(?:0x)?[0-9a-fA-F]{4,}", stripped))

    @staticmethod
    def _normalize_cdb_addr(value: str) -> str:
        stripped = value.strip().replace("`", "")
        if stripped.startswith("cdb:"):
            return stripped
        if stripped.lower().startswith("0x"):
            return DebugExecutor._normalize_actual_addr(stripped)
        if re.fullmatch(r"[0-9a-fA-F]{4,}", stripped):
            return DebugExecutor._normalize_actual_addr(f"0x{stripped}")
        return stripped

    @staticmethod
    def _path_name(path_text: str) -> str:
        return re.split(r"[\\/]", path_text.strip())[-1]

    @staticmethod
    def _structured_payload(value_text: str) -> str:
        start = value_text.find("{")
        end = value_text.rfind("}")
        if start < 0 or end <= start:
            return ""
        return value_text[start + 1:end].strip()

    @staticmethod
    def _split_structured_items(payload: str) -> list[str]:
        items: list[str] = []
        current: list[str] = []
        depth = 0
        in_string = False
        escape = False
        for ch in payload:
            if in_string:
                current.append(ch)
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
                current.append(ch)
                continue
            if ch == "{":
                depth += 1
                current.append(ch)
                continue
            if ch == "}":
                depth = max(0, depth - 1)
                current.append(ch)
                continue
            if ch == "," and depth == 0:
                item = "".join(current).strip()
                if item:
                    items.append(item)
                current = []
                continue
            current.append(ch)

        item = "".join(current).strip()
        if item:
            items.append(item)
        return items

    @staticmethod
    def _parse_structured_elements(payload: str, element_type: str = "") -> list[_ParsedElement]:
        items = DebugExecutor._split_structured_items(payload)
        elements: list[_ParsedElement] = []
        indexed = False
        for idx, item in enumerate(items):
            match = re.match(r"^\[(?P<index>\d+)\]\s*=\s*(?P<value>.*)$", item)
            if match:
                indexed = True
                elements.append(_ParsedElement(
                    index=int(match.group("index")),
                    type=element_type,
                    value=DebugExecutor._clean_value(match.group("value")),
                ))
                continue
            if indexed:
                return []
            if re.match(r"^[A-Za-z_]\w*\s*=", item):
                return []
            elements.append(_ParsedElement(
                index=idx,
                type=element_type,
                value=DebugExecutor._clean_value(item),
            ))
        return elements if elements and (indexed or len(items) > 1) else []

    @staticmethod
    def _parse_structured_members(payload: str) -> list[_ParsedMember]:
        members: list[_ParsedMember] = []
        for item in DebugExecutor._split_structured_items(payload):
            match = re.match(r"^(?:\.|this->)?(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<value>.*)$", item)
            if not match:
                return []
            members.append(_ParsedMember(
                name=match.group("name"),
                type="",
                value=DebugExecutor._clean_value(match.group("value")),
            ))
        return members

    @staticmethod
    def _array_element_type(type_text: str) -> str:
        cleaned = DebugExecutor._clean_type(type_text)
        if "[" in cleaned:
            return re.sub(r"\s*\[[^\]]*\]", "", cleaned).strip()
        return cleaned

    @staticmethod
    def _is_null(value: str) -> bool:
        stripped = value.strip().lower()
        return stripped in {"0x0", "0x0000000000000000", "nullptr", "null"}

    @staticmethod
    def _clean_type(type_text: str) -> str:
        return re.sub(r"\s+", " ", type_text.replace(" *", "*").replace(" &", "&")).strip()

    @staticmethod
    def _object_class_name(type_text: str) -> str:
        cleaned = DebugExecutor._clean_type(type_text)
        cleaned = re.sub(r"\b(?:class|struct|const|volatile)\b", "", cleaned).strip()
        cleaned = cleaned.replace("*", "").replace("&", "").strip()
        if "::" in cleaned:
            cleaned = cleaned.rsplit("::", 1)[-1]
        return cleaned

    @staticmethod
    def _clean_value(value: str) -> str:
        cleaned = value.strip()
        if cleaned == "{":
            return ""
        if "{" in cleaned and not cleaned.startswith("{"):
            cleaned = cleaned.split("{", 1)[0].strip()
        cleaned = cleaned.strip('"')
        if DebugExecutor._is_hex_addr(cleaned):
            return cleaned
        return DebugExecutor._clean_float_value(cleaned)

    @staticmethod
    def _clean_cdb_value(value: str) -> str:
        cleaned = value.strip()
        if cleaned.startswith("0n") and cleaned[2:].lstrip("-").isdigit():
            return cleaned[2:]
        return DebugExecutor._clean_value(cleaned)

    @staticmethod
    def _clean_float_value(value: str) -> str:
        if not re.fullmatch(r"[-+]?(?:(?:\d+\.\d*)|(?:\.\d+)|(?:\d+[eE][-+]?\d+))(?:[eE][-+]?\d+)?", value):
            return value
        try:
            return f"{float(value):.15g}"
        except ValueError:
            return value

    @staticmethod
    def _clean_frame_name(function: str) -> str:
        name = function.strip()
        if "!" in name:
            name = name.rsplit("!", 1)[-1]
        name = re.sub(r"\+0x[0-9a-fA-F]+$", "", name)
        name = name.split("(", 1)[0].strip()
        if "::" in name:
            name = name.rsplit("::", 1)[-1]
        return name or "main"

    @staticmethod
    def _pointee_type(pointer_type: str) -> str:
        return pointer_type.replace("*", "").strip() or "unknown"

    @staticmethod
    def _array_index(name: str) -> int | None:
        match = re.fullmatch(r"\[(\d+)\]", name)
        return int(match.group(1)) if match else None

    @staticmethod
    def _format_elements(elements: list[_ParsedElement]) -> str:
        return "{" + ", ".join(
            f"[{element.index}]={DebugExecutor._clean_value(element.value)}"
            for element in elements
        ) + "}"

    @staticmethod
    def _format_members(members: list[_ParsedMember]) -> str:
        return "{" + ", ".join(
            f"{member.name}={DebugExecutor._clean_value(member.value)}"
            for member in members
        ) + "}"
