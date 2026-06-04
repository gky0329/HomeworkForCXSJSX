# Windows Runbook

This project can run on Windows as a PySide6 desktop app. The AI execution path is the stable Windows path today. Native debugger execution on Windows is present as an experimental MSVC/PDB backend and must be validated on a real Windows machine before being promoted to teammates.

## Stable Windows Setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy config.yaml.example config.yaml
python main.py
```

Configure an AI provider in `config.yaml` or in Settings. For DeepSeek, either fill `llm.providers.deepseek.api_key` or set:

```powershell
$env:DEEPSEEK_API_KEY="sk-..."
python main.py
```

## Native Debugger Status

| Backend | Platforms | Status | Notes |
| --- | --- | --- | --- |
| LLDB / DWARF | macOS, Linux | In local development | Preferred local debugger path when `lldb` and `clang++`/`g++` are available. |
| MSVC / PDB | Windows | Experimental | Disabled by default. Requires Visual Studio C++ Build Tools, Windows Debugging Tools, and `CXXMV_ENABLE_EXPERIMENTAL_PDB=1`. |
| AI provider | All | Stable fallback | Used when native debugging is unavailable or unsafe. |

Do not advertise the MSVC/PDB backend as stable until the smoke tests below pass on a Windows machine.

## Experimental MSVC/PDB Validation

Install:

- Visual Studio Build Tools with C++ workload (`cl.exe`)
- Windows Debugging Tools (`cdb.exe`)
- Python 3.11+

The app first checks `PATH`, then tries to discover Visual Studio Build Tools with `vswhere.exe` and `cdb.exe` from Windows Kits. A Developer PowerShell or Developer Command Prompt is still the safest validation shell, but normal PowerShell may work if both toolchains are installed.

Run:

```powershell
$env:CXXMV_ENABLE_EXPERIMENTAL_PDB="1"
python tests/unit/test_fixes.py --verbose
```

Then run the native debugger smoke suite. This calls `DebugExecutor` and renders
each returned trace through `MemoryCanvas` in offscreen Qt, so it catches both
debugger-output bugs and canvas-rendering crashes:

```powershell
$env:CXXMV_ENABLE_EXPERIMENTAL_PDB="1"
python tools/native_debug_smoke.py --backend msvc-pdb
```

Useful variants:

```powershell
# Show detected toolchains and why a backend is unavailable.
python tools/native_debug_smoke.py --list-backends

# Produce JSON that can be pasted into chat or an issue.
python tools/native_debug_smoke.py --backend msvc-pdb --json

# Print observed stack/heap/edge summaries and save full trace JSON files.
python tools/native_debug_smoke.py --backend msvc-pdb --verbose --dump-traces .\pdb-smoke-traces

# Narrow a failure to one case.
python tools/native_debug_smoke.py --backend msvc-pdb --case basic_double
python tools/native_debug_smoke.py --backend msvc-pdb --case call_stack
python tools/native_debug_smoke.py --backend msvc-pdb --case reference_stack_pointer
python tools/native_debug_smoke.py --backend msvc-pdb --case stack_object
python tools/native_debug_smoke.py --backend msvc-pdb --case heap_object
python tools/native_debug_smoke.py --backend msvc-pdb --case vector_int
python tools/native_debug_smoke.py --backend msvc-pdb --case map_string_int
python tools/native_debug_smoke.py --backend msvc-pdb --case stdin_sum
```

Manual UI smoke cases before sharing a Windows native build:

```cpp
int a = 42;
int b = a + 10;
double pi = 3.14;
```

```cpp
struct Point { int x; double y; };
Point p{1, 2.5};
p.x = 3;
Point* hp = new Point{4, 5.5};
hp->y = 6.5;
delete hp;
```

Expected behavior:

- Basic variables keep `a`, `b`, and `pi` visible through the final step.
- Objects show class/member state, for example `{x=3, y=2.5}`.
- Heap objects remain visible after `delete` as freed/dangling blocks.
- Canvas auto-fit keeps the same scale across steps in one run.

## Packaging Note

No Windows packaging command is configured yet. Keep teammate distribution as source plus setup instructions until a Windows machine validates both app startup and the debugger smoke tests.
