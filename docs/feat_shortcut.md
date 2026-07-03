# 快捷键功能说明

> Last updated: 2026-05-30

本文档描述代码编辑页的快捷键设计、当前映射，以及如何扩展。

## 当前映射

当焦点在 Code Editor 页面及其子控件中时：

| 快捷键 | 功能 |
|--------|------|
| `F5` | Run |
| `F6` | Reset |
| `PageUp` | Prev Step |
| `PageDown` | Next Step |

全局缩放快捷键：

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+=` | 放大画布 |
| `Ctrl+-` | 缩小画布 |
| `Ctrl+0` | 重置缩放 |

Canvas 交互：

| 操作 | 行为 |
|------|------|
| `Ctrl + 滚轮` | 缩放 |
| 中键拖动 | 平移 |
| 左键拖动图元 | 移动 Stack/Heap item（夹在 scene rect 内） |

Auto-play：

| 操作 | 行为 |
|------|------|
| 工具栏 `Auto Play` 按钮 | 自动步进（可切换开关） |
| 速度滑块 | 200ms（快）– 2000ms（慢） |

## 代码所在

- 快捷键注册入口: `app/ui/main_window.py` `_setup_shortcuts()`
- 快捷键注册器: `app/ui/shortcut_registry.py`
- 应用级事件过滤器: `main_window.py` `eventFilter()` — 确保 Code Editor 不吞 PageUp/PageDown/F5/F6
- 按钮本体: `main_window.py` `_setup_toolbar()` — 快捷键调用 `.click()`，天然同步