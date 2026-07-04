# C++rafting Table

**A cross-platform desktop learning workbench for visualizing C++ memory state step by step.**

C++rafting Table combines a PySide6 desktop UI, AI-assisted execution traces, and a pure QGraphicsView memory canvas. Students can write or import C++ code, run it line by line, and inspect stack frames, heap blocks, object fields, arrays, pointers, dangling edges, and review materials in one local-first app.

## Highlights

- **Step-by-step memory canvas**: stack frames, heap blocks, arrays, structs, objects, inheritance metadata, and pointer edges rendered with Qt graphics items.
- **AI execution fallback**: DeepSeek, OpenAI, Claude, or Gemini can produce validated `ExecutionTrace` JSON when native debugging is unavailable.
- **Native debugger path**: LLDB/DWARF is available for macOS/Linux development; MSVC/PDB is present as an experimental Windows backend, disabled by default.
- **Course workflow support**: import PDF/DOCX/PPTX/Markdown/C++ files, extract knowledge points and quizzes, and send code snippets to the visualizer.
- **OJ analysis**: paste a problem statement and reference code to generate guided explanations and runnable visualizations.
- **Knowledge loop**: local JSON storage for knowledge points, spaced-repetition review, activity, scores, and graph-based concept browsing.
- **Configurable UI**: Settings supports AI provider, proxy, language, code font size, and theme selection: MC, MC End City, or Minimal Black.

## Requirements

- Python 3.11+
- PySide6 6.6+
- A C++ compiler for native debugging (`clang++`/`g++` on macOS/Linux; optional MSVC tools on Windows)
- An AI provider API key for the stable cross-platform execution path

Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Quick Start

```bash
cp config.yaml.example config.yaml
python main.py
```

Then open **Settings** and configure at least one AI provider. For DeepSeek, either fill `llm.providers.deepseek.api_key` in `config.yaml` or set:

```bash
export DEEPSEEK_API_KEY="sk-..."
python main.py
```

On Windows PowerShell:

```powershell
copy config.yaml.example config.yaml
$env:DEEPSEEK_API_KEY="sk-..."
python main.py
```

## Configuration

`config.yaml` is gitignored and should never contain committed secrets. Start from `config.yaml.example`:

```yaml
llm:
  provider: deepseek
  providers:
    deepseek:
      api_base: https://api.deepseek.com
      api_key: ""
      api_key_env: DEEPSEEK_API_KEY
      model: deepseek-chat
ui:
  language: en
  code_font_size: 16
  theme: mc  # mc | mc_end_city | minimal_dark
debugger:
  enable_experimental_pdb: false
```

Supported AI providers are `deepseek`, `openai`, `anthropic`, and `gemini`. Optional proxy settings can be configured in Settings or under `llm.proxy`.

## Usage

1. Open **Code Editor**.
2. Choose an example or paste C++ code.
3. Add stdin in **Program Input** if the code reads from `cin` or `scanf`.
4. Click **Run**.
5. Use **Next**, **Prev**, auto-play, zoom, fit, or fullscreen to inspect each memory state.
6. Use **File Import**, **OJ Analysis**, **Knowledge Base**, and **Review** to build the learning loop around the visualizer.

## Cross-Platform Notes

| Platform | Stable path | Native debugger status |
| --- | --- | --- |
| macOS | AI provider fallback | LLDB/DWARF local development path |
| Windows | AI provider fallback | MSVC/PDB experimental opt-in |
| Linux | AI provider fallback | LLDB/DWARF local development path |

Windows native debugging requires Visual Studio C++ Build Tools and Windows Debugging Tools. See [`docs/windows.md`](docs/windows.md) before enabling `debugger.enable_experimental_pdb`.

## Project Structure

```text
app/
  core/       Engine, execution worker, memory models, state diff, native debugger
  services/   AI service, file extraction, prompts, local JSON stores, i18n
  ui/         Main window, QGraphicsView canvas, pages, widgets, themes
data/user/    Local user data, gitignored
docs/         Roadshow, Windows, canvas, feature, and design notes
tests/unit/   Regression and smoke-style unit tests
tools/        Native debugger smoke runner and support scripts
```

## Development Checks

Run the main unit suite:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/unit -q
```

Run native debugger smoke tests where a local compiler/debugger is available:

```bash
python tools/native_debug_smoke.py --list-backends
python tools/native_debug_smoke.py
```

Quick import and theme check:

```bash
QT_QPA_PLATFORM=offscreen python - <<'PY'
from PySide6.QtWidgets import QApplication
from app.ui.theme.manager import ThemeManager, THEME_LABELS
app = QApplication([])
for theme in THEME_LABELS:
    ThemeManager.apply(app, theme=theme)
print("themes ok")
PY
```

## Documentation

- [`README.md`](README.md): public project overview, setup, usage, and development checks.
- [`docs/PROJECT_GUIDE.md`](docs/PROJECT_GUIDE.md): standardized Chinese project guide.
- [`docs/supported-visualizations.md`](docs/supported-visualizations.md): supported C++ visualization cases and data-shape expectations.
- [`docs/windows.md`](docs/windows.md): Windows setup and native debugger validation.
- [`docs/canvas_interaction.md`](docs/canvas_interaction.md): canvas interaction notes.
- [`FUTURE_WORK.md`](FUTURE_WORK.md): public roadmap items.

## Safety Notes

- Do not commit `config.yaml`, API keys, or `data/user/`.
- Canvas memory items must remain pure QGraphics/QPainter geometry.
- Native Windows PDB debugging is experimental until validated on a Windows machine.
