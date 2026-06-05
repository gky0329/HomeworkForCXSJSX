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

To enable the experimental MSVC/PDB path for teammate testing, use one of:

- Settings -> AI Settings -> Enable experimental MSVC/PDB native debugger
- `config.yaml`: set `debugger.enable_experimental_pdb: true`
- PowerShell: set `$env:CXXMV_ENABLE_EXPERIMENTAL_PDB="1"`

An explicit environment value of `0` or empty disables the PDB backend for that
process, even if `config.yaml` enables it.

When an API key is configured, very large control-flow-heavy programs are sent
directly to the AI fallback instead of first waiting for LLDB/CDB to time out.
Small and medium visual examples still prefer the native debugger path.
After a code run, the app status bar shows the execution source, for example
`Native debugger: MSVC / PDB` or `AI fallback after native debugger failed: ...`.
Use that message when reporting Windows validation results.

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
python tools/native_debug_smoke.py --list-backends --config .\config.yaml

# Produce JSON that can be pasted into chat or an issue.
python tools/native_debug_smoke.py --backend msvc-pdb --json

# Print observed stack/heap/edge summaries and save full trace JSON files.
python tools/native_debug_smoke.py --backend msvc-pdb --config .\config.yaml --verbose --dump-traces .\pdb-smoke-traces

# Narrow a failure to one case.
python tools/native_debug_smoke.py --backend msvc-pdb --case roadshow_native_demo
python tools/native_debug_smoke.py --backend msvc-pdb --case basic_double
python tools/native_debug_smoke.py --backend msvc-pdb --case call_stack
python tools/native_debug_smoke.py --backend msvc-pdb --case recursive_factorial
python tools/native_debug_smoke.py --backend msvc-pdb --case recursive_binary_tree
python tools/native_debug_smoke.py --backend msvc-pdb --case delete_tree_root_leaks_children
python tools/native_debug_smoke.py --backend msvc-pdb --case object_method_call
python tools/native_debug_smoke.py --backend msvc-pdb --case inherited_virtual_object
python tools/native_debug_smoke.py --backend msvc-pdb --case reference_stack_pointer
python tools/native_debug_smoke.py --backend msvc-pdb --case stack_dangling_pointer
python tools/native_debug_smoke.py --backend msvc-pdb --case double_pointer_stack
python tools/native_debug_smoke.py --backend msvc-pdb --case member_pointer_linked_list
python tools/native_debug_smoke.py --backend msvc-pdb --case heap_member_pointer_linked_list
python tools/native_debug_smoke.py --backend msvc-pdb --case stack_object
python tools/native_debug_smoke.py --backend msvc-pdb --case stack_array
python tools/native_debug_smoke.py --backend msvc-pdb --case heap_object
python tools/native_debug_smoke.py --backend msvc-pdb --case deque_int
python tools/native_debug_smoke.py --backend msvc-pdb --case list_pointer_stack
python tools/native_debug_smoke.py --backend msvc-pdb --case set_pointer_stack
python tools/native_debug_smoke.py --backend msvc-pdb --case unordered_set_pointer
python tools/native_debug_smoke.py --backend msvc-pdb --case heap_polymorphic_delete
python tools/native_debug_smoke.py --backend msvc-pdb --case heap_leak_overwrite
python tools/native_debug_smoke.py --backend msvc-pdb --case unique_ptr_heap
python tools/native_debug_smoke.py --backend msvc-pdb --case shared_ptr_owners
python tools/native_debug_smoke.py --backend msvc-pdb --case vector_shared_ptr
python tools/native_debug_smoke.py --backend msvc-pdb --case vector_unique_ptr
python tools/native_debug_smoke.py --backend msvc-pdb --case vector_unique_ptr_object
python tools/native_debug_smoke.py --backend msvc-pdb --case vector_polymorphic_unique_ptr
python tools/native_debug_smoke.py --backend msvc-pdb --case std_array_shared_ptr
python tools/native_debug_smoke.py --backend msvc-pdb --case weak_ptr_expired
python tools/native_debug_smoke.py --backend msvc-pdb --case heap_array_delete
python tools/native_debug_smoke.py --backend msvc-pdb --case pointer_reset_null
python tools/native_debug_smoke.py --backend msvc-pdb --case std_array
python tools/native_debug_smoke.py --backend msvc-pdb --case std_array_object_pointer
python tools/native_debug_smoke.py --backend msvc-pdb --case stack_int
python tools/native_debug_smoke.py --backend msvc-pdb --case priority_queue_int
python tools/native_debug_smoke.py --backend msvc-pdb --case queue_pointer_stack
python tools/native_debug_smoke.py --backend msvc-pdb --case vector_int
python tools/native_debug_smoke.py --backend msvc-pdb --case vector_string
python tools/native_debug_smoke.py --backend msvc-pdb --case vector_pointer_stack
python tools/native_debug_smoke.py --backend msvc-pdb --case pair_tuple_composite
python tools/native_debug_smoke.py --backend msvc-pdb --case optional_pointer
python tools/native_debug_smoke.py --backend msvc-pdb --case optional_variant_object_member_pointer
python tools/native_debug_smoke.py --backend msvc-pdb --case vector_object
python tools/native_debug_smoke.py --backend msvc-pdb --case map_string_int
python tools/native_debug_smoke.py --backend msvc-pdb --case map_string_pointer
python tools/native_debug_smoke.py --backend msvc-pdb --case unordered_map_pointer
python tools/native_debug_smoke.py --backend msvc-pdb --case map_string_unique_ptr
python tools/native_debug_smoke.py --backend msvc-pdb --case map_string_unique_ptr_object
python tools/native_debug_smoke.py --backend msvc-pdb --case map_polymorphic_shared_ptr
python tools/native_debug_smoke.py --backend msvc-pdb --case control_flow_loop
python tools/native_debug_smoke.py --backend msvc-pdb --case lambda_capture
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
