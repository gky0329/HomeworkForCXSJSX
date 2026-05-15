# FUTURE WORK — C++ Memory Visualizer

> Last updated: 2026-05-16

---

## 1. 加强各种形式的 C++ Support

### 1.1 GDB / LLDB MI 集成（替代 LLM 执行引擎）
- `gdb --interpreter=mi2` 或 `lldb -o "script ..."` 真实执行 C++ 代码
- 优势：100% 准确、零 API 成本、支持任意复杂 C++
- 输出直接构造 `ExecutionTrace`（真实地址、真实值）
- LLM 退到纯讲解角色

### 1.2 复杂 C++ 语句支持
- 见 `docs/future/complex-cpp-support.md`
- 循环、函数调用栈、struct/class、数组、STL 容器、引用、smart pointers

### 1.3 PPT 文件导入
- 见 `docs/future/complex-cpp-support.md` (Future File Format 节)
- `python-pptx` 提取 slide 文本，`_extract_pptx()` 注册到 `file_service.py`

### 1.4 测试用例运行（OJ 模式增强）
- 用户输入测试输入 → 编译运行 → 对比预期输出
- 错误 diff 展示
- 性能分析（时间/内存）

### 1.5 可视化更多 C++ 概念
| 概念 | 可视化方式 |
|------|-----------|
| 数组 | 连续矩形块 |
| struct 成员 | 嵌套 StackItem |
| 链表 | 链式 HeapItem + EdgeItem |
| 递归调用栈 | 多 StackFrame 动画 |

---

## 2. 加强各模块间的流畅度和相关性

### 2.1 统一导航与状态管理
- **现状**：Engine 和 OJPage 各自维护 step 导航逻辑（重复代码）
- **目标**：提取 `StepController` 基类，Engine / OJPage 继承或组合
- **连带收益**：快捷键统一、动画状态统一、undo/redo 支持

### 2.2 跨模块数据流通
- **OJ Analysis → Review**：错题自动入 Review（已部分实现）
- **File Import → Code Editor**：Visualize 已实现
- **Code Editor → Knowledge Graph**：每步执行涉及的知识点自动入库
- **Review → Knowledge Graph**：错误知识点权重驱动图谱节点大小（已实现）
- **目标**：任意模块产生的数据都能被其他模块感知和利用

### 2.3 UI 体验优化
| 项目 | 现状 | 目标 |
|------|------|------|
| 面板拖拽 | 固定分栏 | 可拖拽调整大小、dock/undock |
| 步骤动画 | 固定 400ms | 可调速 / 可跳过 |
| 键盘快捷键 | Ctrl+/- 缩放 | 空格=下一步, B=上一步, Enter=Run |
| 错误提示 | StatusBar 一行文字 | 弹窗显示原始 LLM 响应 + 重试按钮 |
| Loading 状态 | 遮罩文字 | 进度条 / 预估时间 |

### 2.4 Canvas 增强
- **Undo/Redo**：步骤回退时的 diff 反向动画
- **多标签页 Canvas**：同时观察多个程序的内存状态
- **性能**：> 50 items 时使用空间索引（R-tree）加速碰撞检测
- **导出**：当前 Canvas 截图 / SVG 导出

### 2.5 数据持久化与同步
- **云端同步**：`data/user/` JSON 可选同步到 GitHub Gist
- **历史记录**：保存最近 10 次执行记录，一键回放
- **导出/导入**：错误集、知识图谱可导出为 Markdown / JSON

### 2.6 Code Cleanup (代码质量)
- 提取 `clear_layout()` 工具函数消除重复代码
- `ai_service.py` `Optional[Path]` → `Path | None` 统一类型注解风格
- `file_import_page.py` 和 `oj_page.py` 知识卡片构建逻辑去重
- `canvas_animator.py` 定时器管理统一（已完成 gen counter）
- `error_store.py` 索引 → UUID 迁移（已完成）
