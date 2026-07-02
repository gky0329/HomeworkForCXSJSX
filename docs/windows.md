# Windows Runbook

This project runs on Windows as a PySide6 desktop app. The stable Windows
execution path is the configured AI provider. A native MSVC/PDB debugger backend
is present for validation, but it is experimental and disabled by default.

## Stable Windows Setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy config.yaml.example config.yaml
python main.py
```

Configure an AI provider in `config.yaml` or in Settings. For DeepSeek, either
fill `llm.providers.deepseek.api_key` or set:

```powershell
$env:DEEPSEEK_API_KEY="sk-..."
python main.py
```

## Backend Status

| Backend | Platforms | Status | Notes |
| --- | --- | --- | --- |
| AI provider | Windows, macOS, Linux | Stable fallback | Used when native debugging is unavailable or unsafe. |
| LLDB / DWARF | macOS, Linux | Local development | Used when `lldb` and `clang++`/`g++` are available. |
| MSVC / PDB | Windows | Experimental, opt-in | Requires Visual Studio C++ Build Tools, Windows Debugging Tools, and explicit enablement. |

On Windows, teammates should use the AI provider path for stable demos. To
validate the native PDB path, enable one of:

```powershell
$env:CXXMV_ENABLE_EXPERIMENTAL_PDB="1"
```

or in `config.yaml`:

```yaml
debugger:
  enable_experimental_pdb: true
```

The same switch is also available in Settings as **Enable experimental MSVC/PDB
native debugger**. Do not advertise this backend as stable until the smoke tests
below pass on a real Windows machine.

## Native Debugger Validation

Install:

- Visual Studio Build Tools with the C++ workload (`cl.exe`)
- Windows Debugging Tools (`cdb.exe`)
- Python 3.11+

Then run:

```powershell
$env:CXXMV_ENABLE_EXPERIMENTAL_PDB="1"
python tests/unit/test_fixes.py --verbose
python tools/native_debug_smoke.py --backend msvc-pdb --list-backends
python tools/native_debug_smoke.py --backend msvc-pdb --json
```

The smoke script exercises `DebugExecutor` and renders each returned trace
through the offscreen `MemoryCanvas`, so it catches debugger parsing issues and
canvas crashes together.

## Manual UI Smoke Cases

Before sharing a Windows source checkout, run:

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

No Windows packaging command is configured yet. Keep teammate distribution as
source plus setup instructions until a Windows machine validates app startup.
