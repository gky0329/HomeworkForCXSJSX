# Windows Runbook

This project runs on Windows as a PySide6 desktop app. On `main`, the stable
Windows execution path is the configured AI provider. Native debugger execution
for Windows PDB remains on the experimental branch.

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

On Windows, teammates should use the AI provider path from `main`. Keep PDB
validation and promotion decisions on `experiment/windows-pdb-debugger`.

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
