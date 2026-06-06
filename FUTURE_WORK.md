# FUTURE WORK — C++rafting Table

> Last updated: 2026-05-30

---

## ✅ Already Done (since last update)

| Item | Status |
|------|--------|
| PageUp/PageDown/F5/F6 shortcuts | ✅ `shortcut_registry.py` + `eventFilter` |
| Loading overlay with Cancel + elapsed time | ✅ `main_window.py` |
| Error dialog with Retry + raw response | ✅ `error_dialog.py` |
| SM-2 spaced repetition | ✅ `error_store.py` — 4-button rating with interval prediction |
| OJ auto-generate Reference Code | ✅ `OJ_AUTOGEN_TEMPLATE` |
| Multi-model routing | ✅ `deepseek-chat` for code, `deepseek-reasoner` for OJ/File |
| Canvas step animation (fly-in, flash, shake+fade) | ✅ `canvas_animator.py` |
| Variable tracker with drag-drop | ✅ `tracker_panel.py` |
| Knowledge graph (force-directed) | ✅ Merged into Knowledge Base with List/Graph toggle |
| EdgeItem bezier routing (close-range left-to-left) | ✅ `edge_item.py` |
| Keyboard shortcuts | ✅ |
| AI Hint in Review | ✅ `AIExplainWorker` |
| Auto-play with speed slider | ✅ `engine.py` + `main_window.py` |
| Current line highlight in editor | ✅ `engine.py._highlight_current_line()` |
| Lazy API key prompt (on first Run, not startup) | ✅ `main.py` + `engine.py` |
| Settings dialog (API Key, Proxy, Model, Code Font Size) | ✅ `api_key_dialog.py` |
| Example code dropdown (5 scenarios) | ✅ `main_window.py` |
| Large Prev/Next buttons below canvas | ✅ |
| Markdown rendering for AI explanations | ✅ `_md_to_html` in `knowledge_page.py` |
| AI prompt standardization (no filler) | ✅ `ai_explain_worker.py`, `prompt_templates.py` |
| Graph node click → AI explanation | ✅ callback pattern |
| Global border-free QFrame/QGroupBox/QLabel | ✅ `styles.py` |
| Bottom-border underline text inputs | ✅ `styles.py` |

---

## 1. 加强各种形式的 C++ Support

### 1.1 GDB / LLDB MI 集成（替代 LLM 执行引擎）
- `gdb --interpreter=mi2` 或 `lldb -o "script ..."` 真实执行 C++ 代码
- 优势：100% 准确、零 API 成本、支持任意复杂 C++
- 输出直接构造 `ExecutionTrace`（真实地址、真实值）
- LLM 退到纯讲解角色

### 1.2 复杂 C++ 语句支持
- 见 `docs/future/complex-cpp-support.md`

### 1.3 测试用例运行增强
- 错误 diff 展示
- 性能分析（时间/内存）

### 1.4 更多可视化概念
| 概念 | 可视化方式 |
|------|-----------|
| 链表 | 链式 HeapItem + EdgeItem |
| 模板/泛型 | 类型展开 |

---

## 2. 加强各模块间的流畅度和相关性

### 2.1 统一导航与状态管理
- **现状**：Engine 和 OJPage 各自维护 step 导航逻辑（重复代码）
- **目标**：提取 `StepController` 基类

### 2.2 跨模块数据流通
- ~~OJ → Review~~ ✅、~~File → Code~~ ✅、~~Code → KB~~ ✅、~~Review → Graph~~ ✅

### 2.3 UI 体验优化
| 项目 | 状态 |
|------|------|
| ~~步骤动画可调速~~ | ✅ auto-play speed slider |
| ~~键盘快捷键~~ | ✅ |
| ~~错误弹窗 + 重试~~ | ✅ |
| ~~Loading 耗时显示~~ | ✅ |
| Canvas 截图/PNG 导出 | TODO |
| Dock/undock 面板 | TODO |

### 2.4 Canvas 增强
- Undo/Redo
- 多标签页 Canvas
- 性能：> 50 items 时使用空间索引
- Canvas 导出

### 2.5 数据持久化与同步
- 云端同步
- 历史记录：保存最近 N 次执行，一键回放
- 导出/导入习题集

### 2.6 Code Cleanup
- ~~`clear_layout()` 工具函数~~ ✅
- ~~类型注解统一~~ ✅
- ~~canvas_animator gen counter~~ ✅
- ~~error_store UUID~~ ✅
- File/OJ 知识卡片去重
