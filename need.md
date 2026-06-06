

# 🤖 面向 Agent 的开发需求文档 (Agent-Ready PRD)

> **项目名称**: C++rafting Table
> **目标**: 构建一个基于 PySide6 的桌面端应用，利用 LLM 解析 C++ 代码并驱动 QGraphicsView 进行内存状态可视化。
> **Agent 开发指令**: 请严格遵守本文档定义的**数据结构、类名和状态流转逻辑**。在 MVP 阶段，禁止引入复杂的第三方 AST 库，严格执行“本地正则速通 + LLM 预执行缓存”双轨架构。

## 一、 核心数据契约 (Data Contracts)

> **Agent 指令**: 所有核心模块之间的数据流转必须严格基于以下 `dataclass` (建议直接转换为 Pydantic V2 模型以实现自动 JSON 校验)。

```python
from typing import List, Optional, Any
from pydantic import BaseModel

class Variable(BaseModel):
    name: str
    type: str         # 例如: "int", "int*", "int**"
    value: str        # 统一转为字符串处理，例如 "42", "0xH001"
    address: str      # 内存地址，例如 "0xS001" (栈), "0xH001" (堆)
    is_pointer: bool

class StackFrame(BaseModel):
    frame_name: str   # 例如: "main", "foo"
    variables: List[Variable]

class HeapBlock(BaseModel):
    address: str      # 例如: "0xH001"
    type: str
    value: str
    is_freed: bool = False

class PointerEdge(BaseModel):
    source_address: str  # 发出指针的变量地址
    target_address: str  # 指向的地址 (可以是 Stack 也可以是 Heap)
    is_dangling: bool = False

class MemoryState(BaseModel):
    """代表代码执行到某一行时的全局内存快照"""
    line_number: int
    source_code: str
    stack: List[StackFrame]
    heap: List[HeapBlock]
    edges: List[PointerEdge]

class ExecutionTrace(BaseModel):
    """LLM 返回的完整执行轨迹"""
    steps: List[MemoryState]

```

## 二、 核心执行引擎 (LLM as Compiler Engine)

> **Agent 指令**: 实现 `ai_executor.py` 时，严格封装对 DeepSeek API 的调用，强制开启 JSON 模式 (或使用 Structured Output API)，并注入以下 System Prompt。

### 1. 引擎执行流转状态机

当用户点击【运行】按钮时，触发以下异步流：

1. `UI Thread`: 提取 `QPlainTextEdit` 中的完整代码，显示 Loading 遮罩。
2. `Worker Thread`: 调用 `AIExecutor.run_code(code)`。
3. `LLM API`: 将代码打包发送，获取符合 `ExecutionTrace` Schema 的 JSON。
4. `Worker Thread`: 验证 JSON 格式，反序列化为 `ExecutionTrace` 对象。
5. `Cache Manager`: 存储 `steps[]` 数组，初始化 `current_step_index = 0`。
6. `UI Thread`: 移除遮罩，激活【单步执行】按钮。

### 2. 核心 Prompt 模板 (必须写入单独的 prompt_templates.py)

```text
[System Prompt]
你是一个 C++ 内存执行引擎。你需要逐行分析用户提供的 C++ 代码，并输出每执行完一行后的**全局内存状态快照**。
规则：
1. 必须输出合法的 JSON，严格匹配提供的 Schema。
2. 内存地址请使用模拟地址：栈地址以 "0xS" 开头，堆地址以 "0xH" 开头。
3. 指针变量的 value 就是它指向的 target_address。
4. 遇到 delete 操作，将对应 HeapBlock 的 is_freed 设为 true，并将指向它的 PointerEdge 的 is_dangling 设为 true。

[User Input Example]
int a = 42;
int* p = new int(100);

[Expected JSON Output Example]
{
  "steps": [
    {
      "line_number": 1,
      "source_code": "int a = 42;",
      "stack": [{"frame_name": "main", "variables": [{"name": "a", "type": "int", "value": "42", "address": "0xS001", "is_pointer": false}]}],
      "heap": [], "edges": []
    },
    {
      "line_number": 2,
      "source_code": "int* p = new int(100);",
      "stack": [/* 包含 a 和 p */],
      "heap": [{"address": "0xH001", "type": "int", "value": "100", "is_freed": false}],
      "edges": [{"source_address": "0xS002", "target_address": "0xH001", "is_dangling": false}]
    }
  ]
}

```

## 三、 Canvas 渲染实现指南 (UI Layer)

> **Agent 指令**: `memory_canvas.py` 必须基于 `QGraphicsView` 和 `QGraphicsScene` 实现。禁用任何 QPixmap/图片素材，完全使用 `QPainter` API 进行几何绘制。

### 1. 基类结构映射

* **栈帧 (StackFrame)** -> 实现 `StackItem(QGraphicsRectItem)`
* **变量 (Variable)** -> 实现 `VarItem(QGraphicsTextItem)`，作为 `StackItem` 的子节点。
* **堆块 (HeapBlock)** -> 实现 `HeapItem(QGraphicsRectItem)`，需实现 `paint()` 绘制圆角。
* **指针 (PointerEdge)** -> 实现 `EdgeItem(QGraphicsPathItem)`。必须能够动态计算贝塞尔曲线（Bezier Curve）连接 Source 和 Target 的中心点。

### 2. 动画规范 (QPropertyAnimation)

当用户点击【单步执行】，`current_step_index` +1，获取新的 `MemoryState`，Canvas 需根据 Diff 执行动画：

* **新增堆块 (new)**: 触发平移+透明度动画（`pos` 从屏幕外部飞入，`opacity` 0 -> 1）。
* **值修改**: 对应 `VarItem` 或 `HeapItem` 的文字颜色闪烁（例如变黄 300ms 后恢复）。
* **内存释放 (delete)**: 对应的 `HeapItem` 边框变红虚线，播放震动动画（改变 x 坐标），然后 `opacity` 1 -> 0 销毁。
* **指针移动**: `EdgeItem` 的 `path` 属性进行补间动画，箭头平滑移动到新目标。

## 四、 其他核心服务 (Services)

> **Agent 指令**: 第三方库使用规范如下。

### 1. PDF 提取服务 (`pdf_service.py`)

* **依赖**: 必须使用 `PyMuPDF` (`fitz`)。
* **输入**: PDF 文件路径。
* **输出**: 结构化的 Markdown 文本流，自动去除页眉页脚噪音。交由 DeepSeek API 处理成 `[知识点, 代码段, 生成的单选题]` JSON。

### 2. 错题 JSON 存储 (`error_store.py`)

* **存储引擎**: 纯本地 JSON 文件。路径为 `~/.cxx_visualizer/errors.json` 或项目级 `./data/user/errors.json`。
* **操作**: 必须实现线程安全的增删改查 (CRUD) 操作。

## 五、 MVP 阶段实现路径 (Agent 执行顺序)

1. **先脚手架**: 初始化 PySide6 主窗口，搭建分栏布局（左侧 `QPlainTextEdit`，右侧 `QGraphicsView`）。
2. **定义模型**: 编写 Pydantic 数据模型。
3. **连通 AI**: 编写 `ai_executor.py`，发送硬编码的 C++ 代码，验证能否成功解析出 JSON `ExecutionTrace`。
4. **渲染引擎**: 编写 Canvas 及核心 Item 类，用假数据测试静态渲染是否符合配色规范（深色技术风）。
5. **串联流转**: 实现点击逻辑，将 LLM 返回的 JSON 驱动 Canvas 产生补间动画。

---

### 给你的建议：

当你在 Cursor 等工具中使用这份文档时，可以直接以这样的话术开头：
*"@workspace 这是一份完整的 Agent-Ready PRD。请你仔细阅读。我们将从【五、MVP阶段实现路径】的第一步开始。请先帮我搭建基于 PySide6 的 main_window.py 和 config.yaml 的基础骨架，不要写多余的业务逻辑，只需跑通黑色的深色主题界面和左右分栏布局即可。"*

通过这种方式，AI 不会乱猜，它会像一个训练有素的高级工程师一样，顺着你的架构和数据契约一步步产出极高质量的代码。
