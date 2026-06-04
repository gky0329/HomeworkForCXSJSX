# C++ Memory Visualizer

A PySide6 desktop app that visualizes C++ memory state (stack/heap/pointers) step by step using AI-powered code execution.

![VS Code Dark+ theme](https://img.shields.io/badge/theme-VS%20Code%20Dark%2B-blue)

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

Windows setup and native-debugger validation notes are in [`docs/windows.md`](docs/windows.md).

## Features

- **Code Execution** — Write C++ code, click Run, see memory state step by step
- **Visual Canvas** — Stack frames (blue), heap blocks (orange), pointer arrows (gray/red)
- **OJ Analysis** — Paste competitive programming problems, get AI analysis + code visualization
- **File Import** — Upload PDF/DOCX/PPTX/MD/CPP files, extract knowledge points + quizzes
- **Knowledge Base** — Browse AI-explained C++ concepts with List/Graph views
- **Spaced Repetition** — Anki-style review with SM-2 algorithm, deck-based organization
- **Multi-Provider AI** — Supports DeepSeek, OpenAI, Claude, Gemini
- **i18n** — English + 中文 (Chinese)

## Configuration

Copy `config.yaml.example` to `config.yaml` and fill in your API key.

```bash
cp config.yaml.example config.yaml
```

Set up at least one AI provider in Settings (toolbar button or tab bar corner).

Or set environment variable: `DEEPSEEK_API_KEY=sk-xxx`

## Project Structure

```
├── main.py                    # Entry point
├── app/
│   ├── core/                  # Engine, AI executor, state diff
│   ├── ui/                    # Main window, canvas, pages, widgets, theme
│   ├── services/              # AI service, file service, error store, i18n, prompts
├── data/                      # User data (gitignored)
├── tests/unit/                # Unit tests
└── docs/                      # Documentation
```

## Running Tests

```bash
python tests/unit/test_fixes.py
```

## Documentation

- `AGENTS.md` — Agent instructions and conventions
- `need.md` — Product requirements and data contracts
- `MVP建设文档.md` — Implementation roadmap (Chinese)
- `架构设计文档v2.md` — Architecture document (Chinese)
- `FUTURE_WORK.md` — Planned features
- `docs/roadshow_demo.md` — Roadshow demo code and talk track
- `docs/windows.md` — Windows setup and native-debugger validation notes
- `docs/` — Detailed feature docs

## Requirements

- Python 3.11+
- PySide6 6.6+
- See `requirements.txt` for full list
