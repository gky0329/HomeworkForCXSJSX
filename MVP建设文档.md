# MVP 建设文档 — C++ Memory Visualizer

> 本文档是工程级路线图，精确到文件、验收标准和验证命令。
> 架构和数据契约详见 `need.md` 和 `架构设计文档v2.md`。

---

## 1. MVP 范围

### 纳入

| 模块 | 产出 |
|------|------|
| 项目骨架 | PySide6 主窗口 + 深色主题 + 左右分栏（编辑器 / Canvas） |
| 数据模型 | 6 个 Pydantic V2 模型，JSON 序列化/反序列化 |
| AI 接入 | DeepSeek API 调用，System Prompt，JSON 模式返回 `ExecutionTrace` |
| Canvas 渲染 | StackItem / VarItem / HeapItem / EdgeItem，纯 QPainter 几何绘图 |
| 单步执行 | 按钮 → LLM → Canvas 动画（新增飞入 / 值修改闪烁 / delete 抖动渐隐） |

### 排除（留给后续 Sprint）

PDF 课件处理、OJ 题目解析、错题复习、知识图谱、变量追踪器、作用域进出（第 7 条语句）。

---

## 1.5 Canvas 布局铁律（QGraphicsView — 不是 DOM）

> **这些规则不可违反。**

| # | 规则 | 原因 |
|---|------|------|
| 1 | **所有坐标必须是绝对 `(x, y)`，基于 `setSceneRect`** | QGraphicsView 没有 Flexbox，百分比或相对布局会导致位置漂移 |
| 2 | **禁止内置 ScrollBar + 覆盖 `wheelEvent`** | `ScrollBarAlwaysOff` 双轴。`wheelEvent` 中仅 `Ctrl+滚轮` 触发缩放，其余全部 `accept()` 吞掉，防止触摸板双指滑动导致画布漂移 |

```python
# CanvasView 必须这样初始化
self.setSceneRect(0, 0, SCENE_W, SCENE_H)
self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
```

---

## 2. 环境准备

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

配置 API key：
```bash
export DEEPSEEK_API_KEY="sk-xxx"
# 或直接编辑 config.yaml 中的 llm.api_key
```

---

## 3. Phase 路线图

### Phase 0 — 项目骨架 (预计 0.5d)

**文件清单**：

| 文件 | 职责 |
|------|------|
| `requirements.txt` | 依赖声明 |
| `config.yaml` | 运行时配置 |
| `config.yaml.example` | 配置模板（不含真实 key） |
| `app/__init__.py` | 空 |
| `app/core/__init__.py` | 空 |
| `app/ui/__init__.py` | 空 |
| `app/ui/theme/__init__.py` | 空 |
| `app/ui/theme/colors.py` | 深色主题色板（背景 #1E1E1E，栈蓝，堆橙，箭头灰，悬空红） |
| `app/ui/theme/styles.py` | 全局 QSS 样式表 |
| `app/ui/main_window.py` | `MainWindow(QMainWindow)`，左 QPlainTextEdit + 右 QGraphicsView 分栏 |
| `main.py` | 入口：加载 config、创建 QApplication、启动 MainWindow |

**验证**：
```bash
python main.py
# 应看到黑色主题窗口，左侧可输入代码，右侧空白 Canvas
```

---

### Phase 1 — 数据模型 (预计 0.5d)

**文件清单**：

| 文件 | 职责 |
|------|------|
| `app/core/memory_model.py` | 6 个 Pydantic V2 模型 |

**模型定义**（精确字段，来自 `need.md`）：

```
Variable(name, type, value, address, is_pointer)
StackFrame(frame_name, variables: list[Variable])
HeapBlock(address, type, value, is_freed=False)
PointerEdge(source_address, target_address, is_dangling=False)
MemoryState(line_number, source_code, stack, heap, edges)
ExecutionTrace(steps: list[MemoryState])
```

**地址规则**：栈 `0xS001`，堆 `0xH001`。

**验证**：
```python
# 在 Python REPL 中执行
from app.core.memory_model import ExecutionTrace
import json

sample = json.loads('''{
  "steps": [{
    "line_number": 1,
    "source_code": "int a = 42;",
    "stack": [{"frame_name": "main", "variables": [{"name": "a", "type": "int", "value": "42", "address": "0xS001", "is_pointer": false}]}],
    "heap": [],
    "edges": []
  }]
}''')
trace = ExecutionTrace.model_validate(sample)
print(trace.model_dump_json(indent=2))
```

---

### Phase 2 — AI 接入 (预计 1d)

**文件清单**：

| 文件 | 职责 |
|------|------|
| `app/services/__init__.py` | 空 |
| `app/services/prompt_templates.py` | System Prompt 模板（来自 `need.md` 二.2 节） |
| `app/services/ai_service.py` | `AIService` 类，封装 httpx 异步调用 DeepSeek `/v1/chat/completions` |
| `app/core/ai_executor.py` | `AIExecutor.run_code(code) -> ExecutionTrace`，调用 AIService + Pydantic 校验 |

**System Prompt 要点**：
- 角色：C++ 内存执行引擎
- 逐行输出全局内存快照 JSON
- 栈地址 `0xS` 前缀，堆地址 `0xH` 前缀
- 指针 value = target_address
- delete → is_freed=true + is_dangling=true

**API 调用参数**：
```python
{
  "model": "deepseek-chat",
  "messages": [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": user_code}
  ],
  "temperature": 0.0,
  "response_format": {"type": "json_object"},
  "max_tokens": 4096
}
```

**验证**：
```bash
# 用 hardcoded C++ 测试代码调用，确认返回合法 ExecutionTrace JSON
python -c "
from app.services.ai_service import AIService
from app.core.ai_executor import AIExecutor
import asyncio

code = '''int a = 42;
int* p = new int(100);
delete p;'''

async def test():
    executor = AIExecutor()
    trace = await executor.run_code(code)
    print(f'Steps: {len(trace.steps)}')
    for s in trace.steps:
        print(f'  Line {s.line_number}: {s.source_code}')
        print(f'    Stack: {len(s.stack)} frames, Heap: {len(s.heap)} blocks, Edges: {len(s.edges)}')

asyncio.run(test())
"
```

---

### Phase 3 — Canvas 渲染 (预计 1.5d)

**文件清单**：

| 文件 | 职责 |
|------|------|
| `app/ui/canvas/__init__.py` | 空 |
| `app/ui/canvas/memory_canvas.py` | `MemoryCanvas(QGraphicsView)`，管理 Scene、布局栈/堆区域、暴露 `render_state(state: MemoryState)` |
| `app/ui/canvas/stack_item.py` | `StackItem(QGraphicsRectItem)`，蓝色矩形框 + 标题 frame_name |
| `app/ui/canvas/var_item.py` | `VarItem(QGraphicsTextItem)`，变量文本，子节点挂 StackItem |
| `app/ui/canvas/heap_item.py` | `HeapItem(QGraphicsRectItem)`，`paint()` 绘制橙色圆角矩形 |
| `app/ui/canvas/edge_item.py` | `EdgeItem(QGraphicsPathItem)`，贝塞尔曲线箭头，灰色实线 / 红色虚线 |

**Canvas 布局算法**：
- 左侧 40% 区域：栈帧纵向排列（从上到下）
- 右侧 60% 区域：堆块纵向排列
- StackItem 高度 = 标题栏 24px + N × VarItem 行高 20px
- HeapItem 固定 60×80
- EdgeItem 控制点：取 source 右边缘中点 → target 左边缘中点，贝塞尔控制点水平偏移 ±50px

**配色常量**（来自 `colors.py`）：

| 常量 | 色值 | 用途 |
|------|------|------|
| `STACK_BORDER` | `#569CD6` | 栈边框 |
| `STACK_BG` | `#1A3A5C` | 栈填充 |
| `HEAP_BORDER` | `#CE9178` | 堆边框 |
| `HEAP_BG` | `#3D2916` | 堆填充 |
| `EDGE_SOLID` | `#808080` | 正常指针 |
| `EDGE_DANGLING` | `#F44747` | 悬空指针 |
| `CANVAS_BG` | `#1E1E1E` | 画布背景 |

**验证**：在 MainWindow 中构造假 MemoryState，调用 `canvas.render_state()`，检查静态渲染效果（配色/布局/箭头方向）。

---

### Phase 4 — 串联流转 (预计 1.5d)

**文件清单**：

| 文件 | 职责 |
|------|------|
| `app/core/state_diff.py` | `StateDiffEngine.diff(prev, curr) -> DiffResult`，输出 add/remove/modify 事件列表 |
| `app/ui/canvas/canvas_animator.py` | `CanvasAnimator`，根据 DiffResult 驱动 QPropertyAnimation |

**Diff 算法**（伪代码）：
```
diff(prev: MemoryState, curr: MemoryState) -> DiffResult:
    added_vars    = curr.variables - prev.variables     # 按 address 比较
    removed_vars  = prev.variables - curr.variables
    modified_vars = {v in both but value changed}
    added_heap    = curr.heap - prev.heap
    removed_heap  = prev.heap - curr.heap  (is_freed=true)
    modified_heap = {h in both but value changed}
    added_edges   = curr.edges - prev.edges
    modified_edges = {e in both but is_dangling changed}
```

**动画规范**（来自 `need.md` 三.2 节）：

| 事件 | 动画 |
|------|------|
| 新增变量/堆块 | `pos` 从屏幕外飞入 + `opacity` 0→1，时长 400ms |
| 值修改 | 文字颜色变亮黄 (`#FFD700`)，300ms 后恢复原色 |
| 内存释放 | 边框变红虚线 → 震动（x ±3px 往复）→ opacity 1→0 销毁，总时长 600ms |
| 指针重指向 | `EdgeItem.path` 贝塞尔控制点补间，时长 300ms |

**按钮交互**：
- 【运行】：提取代码 → 显示 Loading 遮罩 → 调用 AIExecutor → 存储 steps → 渲染 step[0]
- 【下一步】：current_step_index++ → diff → animate → render_state

**验证**：
```bash
python main.py
# 1. 在左侧输入测试代码
# 2. 点击【运行】，等待 AI 返回，应看到第一步内存状态
# 3. 点击【下一步】，观察动画效果
```

---

## 4. MVP 验收总清单

### 功能

- [ ] 窗口正常启动，深色主题生效
- [ ] 输入 C++ 代码，点击运行，Loading 遮罩显示
- [ ] AI 返回后 Canvas 渲染第一步状态
- [ ] 连续点击【下一步】，每步正确渲染栈帧/堆块/指针箭头

### 支持的 6 种语句（MVP，不含作用域）

| # | 语句 | 预期 |
|---|------|------|
| 1 | `int a = 42;` | 栈上出现 Variable a |
| 2 | `int* p;` | 栈上出现 is_pointer=true 的 p |
| 3 | `p = &a;` | 出现 EdgeItem 从 p 指向 a |
| 4 | `*p = 100;` | a 的 value 变为 100，文字闪烁 |
| 5 | `p = new int(5);` | 堆上出现 HeapBlock 0xH001 |
| 6 | `delete p;` | 堆块变红虚线、抖动、渐隐消失 |

### 视觉

- [ ] 栈区蓝色矩形，堆区橙色圆角块，指针灰色实线箭头
- [ ] 悬空指针红色虚线
- [ ] 动画流畅（飞入/闪烁/抖动渐隐）

### 边界

- [ ] 空代码输入 → 不崩溃，Canvas 保持空白
- [ ] LLM 返回格式异常 → 错误提示，不崩溃
- [ ] API key 未配置 → 提示用户配置
- [ ] 网络超时 → 重试 1 次后提示

---

## 5. 风险与对策

| 风险 | 概率 | 对策 |
|------|------|------|
| DeepSeek API 不稳定 | 中 | 内置 `mock_executor.py`，用本地预置 JSON 做 fallback |
| LLM 返回的 JSON 不符合 Schema | 中 | Pydantic 校验失败 → 重试 1 次 → 提示用户 |
| QGraphicsView 大规模绘制性能 | 低 | MVP 限制 ≤ 50 items |
