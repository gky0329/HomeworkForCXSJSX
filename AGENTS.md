# AGENTS.md — C++ Memory Visualizer (C++ 内存可视化沙盒)

A PySide6 desktop app that uses DeepSeek LLM to execute C++ code line-by-line and display memory state (stack/heap/pointers) on a QGraphicsView canvas.

## Authoritative docs
- `need.md` — Agent-Ready PRD: data contracts (Pydantic V2 models), LLM prompt template, Canvas rendering specs, MVP path
- `架构设计文档v2.md` — Architecture v2: product pivot rationale, full directory tree, sprint plan, technical decisions

Always read both before writing any code. If they conflict, `need.md` takes priority for data contracts and execution flow.

## Tech stack
- **UI**: PySide6 (QGraphicsView, QGraphicsScene, QPropertyAnimation)
- **Data validation**: Pydantic V2 (BaseModel)
- **LLM**: DeepSeek API (JSON mode / Structured Output)
- **PDF**: PyMuPDF (fitz) only — no other PDF libs
- **Storage**: local JSON (`~/.cxx_visualizer/errors.json` or `./data/user/errors.json`)
- **Config**: pyyaml (`config.yaml`)

## Critical constraints (do NOT violate)
- **No AST libraries** in MVP — parse C++ with regex only (a controlled subset of 7 statement types)
- **No QPixmap/images** — all Canvas items drawn with pure QPainter geometry (rectangles, text, bezier curves)
- **No external diagram libs** — knowledge graph rendered via QGraphicsView force-directed layout, no D3.js
- **Dark theme** — VS Code Dark+ style; stack=blue rectangles, heap=orange rounded rects, pointer=gray solid arrows (red dashed when dangling)
- **API key is user-provided** — never hardcode or commit API keys
- **Thread safety** — AI calls run in Worker thread, UI updates in main thread; use signals/slots

## Canvas layout rules (QGraphicsView — no DOM, no Flexbox)
- **Absolute coordinates only**: all item positions must be (x, y) based on `setSceneRect`, never use viewport percentages or relative layout
- **No built-in ScrollBars**: `ScrollBarAlwaysOff` on both axes. Override `wheelEvent` — only Ctrl+wheel triggers zoom, all other wheel events are `accept()`ed to prevent trackpad drift. Regular two-finger trackpad scroll must produce zero visual effect

## Core data models (exact names required)
File: `app/core/memory_model.py`
- `Variable(name, type, value, address, is_pointer)`
- `StackFrame(frame_name, variables: list[Variable])`
- `HeapBlock(address, type, value, is_freed=False)`
- `PointerEdge(source_address, target_address, is_dangling=False)`
- `MemoryState(line_number, source_code, stack, heap, edges)`
- `ExecutionTrace(steps: list[MemoryState])`

Memory addresses use simulated format: stack `0xS001`, heap `0xH001`.

## Canvas item classes (exact names required)
File: `app/ui/canvas/`
- `StackItem(QGraphicsRectItem)` — stack frame container
- `VarItem(QGraphicsTextItem)` — variable, child of StackItem
- `HeapItem(QGraphicsRectItem)` — heap block with rounded corners via paint()
- `EdgeItem(QGraphicsPathItem)` — bezier-curve pointer arrow between items

## Execution flow (按钮 → LLM → Canvas)
1. UI Thread: extract code from QPlainTextEdit, show loading overlay
2. Worker Thread: call `AIExecutor.run_code(code)` → DeepSeek API
3. LLM returns JSON matching `ExecutionTrace` schema
4. Worker Thread: validate + deserialize to `ExecutionTrace`
5. Cache Manager: store `steps[]`, set `current_step_index = 0`
6. UI Thread: remove overlay, enable step buttons
7. On step: diff against previous state → animate (fly-in for new, flash for value change, shake+fade for freed)

## MVP Sprint order
1. Scaffold: PySide6 main window with left code editor + right canvas, dark theme
2. Models: Pydantic data classes
3. AI hookup: `ai_executor.py` calling DeepSeek with hardcoded test C++ code
4. Canvas: core item classes with static fake data
5. Wire: button click → LLM JSON → Canvas animation

## Directory structure (planned, create as needed)
```
CXSJSXhomework/
├── main.py
├── config.yaml
├── requirements.txt          # PySide6 + pymupdf + pyyaml + pydantic
├── app/
│   ├── core/                 # memory_model.py, step_executor.py, state_diff.py, engine.py
│   ├── ui/                   # main_window.py, pages/, canvas/, widgets/, theme/
│   └── services/             # ai_service.py, pdf_service.py, error_store.py
├── data/user/                # user data (errors, settings)
├── data/kb/                  # RAG knowledge base
└── tests/unit/
```
