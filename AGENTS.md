# AGENTS.md — C++ OOP 教学工具

> 施工前务必阅读 `技术报告.md`（架构设计）和 `ROADMAP.md`（施工顺序与验收标准）。

## Tech stack
- Python 3.10+ / PySide6 >= 6.6 / pytest / pyyaml
- UI: QGraphicsView for OopCanvas, QStackedWidget for page navigation
- Entry: `python main.py`

## Architecture principles
- **DI container** (`app/di.py`): `Container.resolve()` only. No `new` in page code.
- **Navigation state machine** (`app/nav.py`): `NavigationManager` emits `page_changed`. All transitions go through it. No lambda spaghetti.
- **Engine/UI separation**: `core/` is platform-free (no PySide6 imports). UI layer (`ui/`) consumes `StateDiff` objects only. Never reads `OopModel` directly.
- **Unidirectional data flow**: `代码字符串 → StepExecutor → OopModel → StateDiff → Canvas` is the only path. Canvas never queries or modifies OopModel.
- **Config**: single `config.yaml` → frozen `Config` dataclass. No hardcoded values.
- **Logging**: `app/log.py` global logger. All key paths must log.

## File roles (new architecture)

| Path | Role |
|---|---|
| `main.py` | Entry: init log, load config, bootstrap DI, create QApplication, show MainWindow |
| `config.yaml` | All tunable values: window, audio, canvas colors, paths |
| `ROADMAP.md` | Step-by-step construction order + acceptance criteria |
| `技术报告.md` | Full architecture design doc. Read first. |
| `关卡设计准则.md` | Rules for writing challenge JSON files |
| `app/di.py` | `Container` class — register/resolve services |
| `app/nav.py` | `NavigationManager(Signal)` — page transition DAG |
| `app/config.py` | `ConfigLoader` — reads yaml → frozen dataclass |
| `app/log.py` | `setup_logging(level)` — file + console |
| `app/core/oop_model.py` | `ClassDef`, `MemberDef`, `ObjectInstance`, `OopModel` |
| `app/core/step_executor.py` | `StepExecutor` — regex parses C++ subset, outputs `list[StateDiff]` |
| `app/core/state_diff.py` | `StateDiff`, `ClassError`, `Annotation` — engine→canvas protocol |
| `app/core/challenge_loader.py` | Loads JSON challenge defs, runs goal checks |
| `app/ui/main_window.py` | Shell only: QStackedWidget + nav signal subscriptions |
| `app/ui/pages/challenge_page.py` | Left code panel (fill-in-blank) + right OopCanvas + step controls |
| `app/ui/pages/main_menu_page.py` | MC-themed main menu |
| `app/ui/pages/level_select_page.py` | Challenge list |
| `app/ui/canvas/oop_canvas.py` | `QGraphicsView` — consumes `StateDiff`, drives animations |
| `app/ui/canvas/class_item.py` | `ClassItem` — QGraphicsItem for class defs (green) |
| `app/ui/canvas/instance_item.py` | `InstanceItem` — QGraphicsItem for object instances (blue) |
| `app/ui/canvas/canvas_animator.py` | Animation orchestrator via `QSequentialAnimationGroup` |
| `app/services/audio_manager.py` | Audio playback (reused from legacy_demo) |
| `app/services/storage_service.py` | Atomic JSON read/write |
| `app/services/progress_service.py` | Challenge progress tracking |
| `data/levels/*.json` | Challenge definitions (oop_001, oop_002, ...) |
| `data/saves/` | User progress storage |

## Deprecated (DO NOT modify — rewrite instead)
- `legacy_demo/` — old MC quiz app. **Read-only parts library** for textures/sounds/McButton.
- `*.cpp/*.h/*.ui/*.pro` (root) — old Qt C++ prototype.

## Gotchas

- **Regex parsing, not AST**: StepExecutor uses pattern-matching for a restricted C++ subset. Always use `\s*` to absorb whitespace. UI layer MUST use `QRegularExpressionValidator` to block `;` `{` `}` before they reach the engine.
- **Animation lifecycle**: Never `time.sleep()` or manual `bool is_animating`. Use `QSequentialAnimationGroup.finished` signal to unlock Step button.
- **Scope exit**: When StepExecutor hits `}`, produce `StateDiff.removed_instances` for all local objects. Canvas fades them out.
- **Canvas never reads OopModel**: Write mock-data test script to verify Canvas rendering before connecting real engine.
- **Construction order**: `engine (pytest) → canvas (mock data) → shell (real wiring)`. Never start Phase N+1 before Phase N passes acceptance.
- **MVP scope**: 2 challenges (oop_001, oop_002). No constructor, no inheritance, no polymorphism, no undo, no progress persistence, single-scope (main() only).
- **StepExecutor supports 5 statement types**: class def, access specifier, object instantiation, member assignment, scope exit.
- **Challenge design**: Read `关卡设计准则.md` before writing new challenges. One new concept per challenge. Theory text 150-400 words. 3-level progressive hints.
- Chinese is used throughout (docs, comments, task descriptions).
