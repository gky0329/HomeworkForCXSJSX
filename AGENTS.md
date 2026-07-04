# AGENTS.md — C++rafting Table

A PySide6 desktop app that uses DeepSeek LLM to execute C++ code line-by-line and display memory state (stack/heap/pointers) on a QGraphicsView canvas.

## Quick start
```bash
pip install -r requirements.txt
python main.py
QT_QPA_PLATFORM=offscreen python -m pytest tests/unit -q
```

## Authoritative docs
- `README.md` — public project overview, setup, usage, and development checks
- `docs/PROJECT_GUIDE.md` — Chinese project guide, workflow, platform status, and verification commands
- `docs/supported-visualizations.md` — supported C++ visualization cases and data-shape expectations
- `docs/windows.md` — Windows setup and experimental MSVC/PDB validation notes

Use `app/core/memory_model.py` as the source of truth for runtime data contracts. If docs conflict with code, update the docs or tests in the same change.

## Tech stack
- **UI**: PySide6 (QGraphicsView, QGraphicsScene, QTimer-based tweens for animation — NOT QPropertyAnimation)
- **Data validation**: Pydantic V2 (BaseModel)
- **LLM**: DeepSeek API (JSON mode / Structured Output) via `httpx.AsyncClient`
- **PDF**: PyMuPDF (fitz) only — no other PDF libs
- **Storage**: local JSON (`data/user/errors.json`, `data/user/knowledge.json`, etc.)
- **Config**: pyyaml (`config.yaml`; `config.yaml.example` for template)
- **Thread safety**: `shiboken6.isValid()` for animated-item lifetime checks

## Critical constraints (do NOT violate)
- **No AST libraries** in MVP — parse C++ with regex only (a controlled subset of 7 statement types)
- **Canvas stays pure QGraphics/QPainter** — memory items are drawn with geometry, text, and paths; theme image assets must stay behind `app/ui/theme/`
- **No external diagram libs** — knowledge graph rendered via QGraphicsView force-directed layout, no D3.js
- **Themes** — supported UI themes are MC and Minimal Black; do not add another theme without updating code, docs, and tests together
- **API key is user-provided** — never hardcode or commit API keys. Read from `DEEPSEEK_API_KEY` env var or `config.yaml` (gitignored).
- **Thread safety** — AI calls run in Worker thread (`ExecutionWorker` QThread), UI updates in main thread; use signals/slots and `retire_worker()` to disconnect stale worker signals before replacement.

## Canvas layout rules (QGraphicsView — no DOM, no Flexbox)
- **Absolute coordinates only**: all item positions must be (x, y) based on `setSceneRect`, never use viewport percentages or relative layout
- **No built-in ScrollBars**: `ScrollBarAlwaysOff` on both axes. Override `wheelEvent` — only Ctrl+wheel triggers zoom, all other wheel events are `accept()`ed to prevent trackpad drift. Regular two-finger trackpad scroll must produce zero visual effect
- **Item position clamping**: both `StackItem` and `HeapItem` override `itemChange()` to prevent dragging outside scene rect

## Core data models (exact names required)
File: `app/core/memory_model.py`

Sub-models: `ArrayElement`, `StructMember`, `LambdaCapture`

```python
Variable(name, type, value, address, is_pointer,
         # Extended fields (post-MVP):
         is_array=False, element_count, elements: list[ArrayElement],
         members: list[StructMember],
         is_object=False, class_name, base_classes, virtual_methods,
         is_function_object=False, captures: list[LambdaCapture],
         is_constructed=False, is_destroyed=False,
         is_reference=False, is_temporary=False)
StackFrame(frame_name, variables: list[Variable])
HeapBlock(address, type, value, is_freed=False,
          # Extended: is_array, elements, members, is_object,
          # class_name, base_classes, virtual_methods,
          # is_constructed, is_destroyed, container_size, container_capacity)
PointerEdge(source_address, target_address, is_dangling=False)
MemoryState(line_number, source_code, stack, heap, edges)
ExecutionTrace(steps: list[MemoryState])
```

Memory addresses use simulated format: stack `0xS001`, heap `0xH001`.

## Canvas item classes (exact names required)
File: `app/ui/canvas/`
- `StackItem(QGraphicsRectItem)` — stack frame container; auto-resize via `refresh_geometry()`
- `VarItem(QGraphicsTextItem)` — variable, child of StackItem
- `HeapItem(QGraphicsRectItem)` — heap block with rounded corners via `paint()`; 4 build modes: plain, array (cell grid), struct (member list), object (badges + members)
- `EdgeItem(QGraphicsPathItem)` — bezier-curve pointer arrow between items; solid gray / dashed red (dangling)
- `MemoryCanvas(QObject)` — item lifecycle management, position caching, collision-based layout
- `CanvasAnimator(QObject)` — QTimer-based tweening (16ms interval); 7 animation types; generation counter pattern prevents stale callbacks

## Execution flow (按钮 → LLM → Canvas)
1. **UI Thread**: `Engine._on_run()` extracts code from QPlainTextEdit, shows loading overlay (`main_window.py:show_loading`)
2. **Worker Thread**: `ExecutionWorker.run()` creates `AIExecutor`, calls `asyncio.run(executor.run_code(code))` → DeepSeek API
3. **LLM API**: `AIService.chat_json()` POSTs to `https://api.deepseek.com/v1/chat/completions` with `response_format={type:"json_object"}`, temperature=0.0, retry with exponential backoff (max 2)
4. **Worker Thread**: validates JSON via Pydantic `ExecutionTrace.model_validate()` → emits `finished.emit(trace)` signal
5. **UI Thread** (`Engine._on_trace_ready`): stores trace, sets `current_step_index=0`, calls `canvas.render_state(steps[0])`, updates `tracker_panel.set_state()`
6. **Step forward** (`_on_next`): `StateDiffEngine.diff(prev, curr)` → `MemoryCanvas.render_state(curr)` → `CanvasAnimator.animate_diff(diff)` (fly-in for new, flash for value change, shake+fade for freed)
7. **Step backward** (`_on_prev`): re-renders without animation

## Key architectural patterns
- **Generation counter** (`CanvasAnimator._generation`): incremented on `stop_all()`, checked in every tween tick to prevent stale timer callbacks
- **shiboken6.isValid()**: guards all animated-item operations against deletion during in-flight animation
- **Item recycling**: `MemoryCanvas.render_state()` reuses existing QGraphicsItems by matching keys (frame name/index or heap address), minimizing allocation
- **Position caching**: snapshots `_position_cache` before re-render so new items fly-in from previous location
- **Atomic file writes** (`error_store._save`): writes to `.tmp` then `os.replace()` to prevent corruption on crash
- **SM-2 spaced repetition** (`error_store.schedule_review`): UCB-based queue prioritization for review scheduling
- **Lazy data dir** (`error_store._ensure_data_dir`): directory created on first write, with `/tmp` fallback on read-only filesystems

## All UI pages (files under `app/ui/pages/`)
| Page | File | Purpose |
|------|------|---------|
| Home | `home_page.py` | Welcome / dashboard |
| Code Editor | (built into `main_window.py`) | Left pane: QPlainTextEdit + right pane: QGraphicsView + TrackerPanel |
| OJ Analysis | `oj_page.py` | Paste problem + code → AI analyzes + visualizes |
| File Import | `file_import_page.py` | Import PDF/DOCX/PPTX/MD/CPP → AI extracts content |
| Review | `review_page.py` | Spaced-repetition review of errors (SM-2 algorithm) |
| Knowledge Base | `knowledge_page.py` | Browse AI-extracted C++ concepts |
| Knowledge Graph | `graph_page.py` | Force-directed knowledge graph (`_GraphCanvas`, `GraphNode`) |

## Directory structure (actual)
```
├── main.py
├── config.yaml                 # gitignored — user provides key
├── config.yaml.example         # template without secrets
├── requirements.txt            # PySide6 + pydantic + pyyaml + httpx + pymupdf + python-docx + python-pptx
├── app/
│   ├── core/                   # memory_model.py, state_diff.py, engine.py, ai_executor.py, execution_worker.py
│   ├── ui/
│   │   ├── main_window.py
│   │   ├── shortcut_registry.py
│   │   ├── canvas/             # memory_canvas.py, canvas_animator.py, stack_item.py, heap_item.py, edge_item.py, tracker_panel.py
│   │   ├── pages/              # home_page.py, oj_page.py, file_import_page.py, review_page.py, knowledge_page.py, graph_page.py
│   │   ├── widgets/            # api_key_dialog.py, error_dialog.py, helpers.py
│   │   └── theme/              # colors.py, styles.py
│   └── services/               # ai_service.py, file_service.py, error_store.py, prompt_templates.py, compile_runner.py, ai_explain_worker.py
├── data/user/                  # errors.json, knowledge.json, activity.json, scores.json, dependencies.json
├── data/kb/                    # RAG knowledge base
└── tests/unit/
```
