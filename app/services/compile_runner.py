import subprocess
import tempfile
import os
from pathlib import Path


class CompileResult:
    def __init__(self, success: bool, output: str, error: str = ""):
        self.success = success
        self.output = output
        self.error = error


class TestResult:
    def __init__(self, case_index: int, passed: bool, actual: str, expected: str):
        self.case_index = case_index
        self.passed = passed
        self.actual = actual
        self.expected = expected


def _find_compiler() -> str | None:
    for cc in ("g++", "clang++"):
        try:
            subprocess.run([cc, "--version"], capture_output=True, timeout=5)
            return cc
        except Exception:
            continue
    return None


def compile_and_run(code: str, test_cases: list[dict]) -> dict:
    compiler = _find_compiler()
    if compiler is None:
        return {
            "compile": CompileResult(
                False, "",
                "No C++ compiler found. Install g++ or clang++."
            ),
            "tests": [],
        }

    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "solution.cpp"
        binary = Path(tmpdir) / "a.out"
        src.write_text(code, encoding="utf-8")

        compile_proc = subprocess.run(
            [compiler, "-std=c++17", "-O2", str(src), "-o", str(binary)],
            capture_output=True, text=True, timeout=30,
        )

        if compile_proc.returncode != 0:
            return {
                "compile": CompileResult(
                    False, "",
                    compile_proc.stderr.strip(),
                ),
                "tests": [],
            }

        results = []
        for i, tc in enumerate(test_cases):
            stdin = tc.get("input", "")
            expected = tc.get("expected", "")
            try:
                run_proc = subprocess.run(
                    [str(binary)],
                    input=stdin,
                    capture_output=True, text=True, timeout=10,
                )
                actual = run_proc.stdout.strip()
                passed = actual == expected.strip()
                results.append(TestResult(i + 1, passed, actual, expected.strip()))
            except subprocess.TimeoutExpired:
                results.append(TestResult(i + 1, False, "(timed out)", expected.strip()))
            except Exception as e:
                results.append(TestResult(i + 1, False, f"(error: {e})", expected.strip()))

        return {
            "compile": CompileResult(True, "", ""),
            "tests": results,
        }
