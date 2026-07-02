# C++ Memory Visualizer — PPT 大纲 & 讲稿

> 共 19 页，含 3 个视频插入位

---

## Slide 1 | 封面

**标题**: C++ Memory Visualizer — AI 驱动的内存可视化学习工具
**副标题**: 看代码如何操纵内存，像调试器一样学习 C++

**演讲备注**:
各位老师、同学好。我们做的是一个面向 C++ 初学者的桌面端内存可视化工具。它能把代码运行时的栈、堆、指针关系实时画出来，让你像看电影一样理解内存。不需要手动画图，AI 帮你执行代码、生成可视化轨迹。

**(右下角留 Logo 位)**

---

## Slide 2 | 问题

**标题**: 初学者学 C++ 内存的痛点
**要点**:
- 📚 教材上的内存图是「静态的」，只有最终状态
- 🧠 指针、new/delete、构造函数/析构函数…概念抽象
- ❌ 调试器门槛高，初学者不会用 GDB/LLDB

**演讲备注**:
C++ 最难的不是语法，是内存模型。教材上只有一两张示意图，告诉你 int a=42 在栈上、new 出来的在堆上。但学生看不到「当代码执行到第3行时内存长什么样」。我们想解决的就是这个 gap。

---

## Slide 3 | 解决方案

**标题**: 我们的方案 — AI 驱动的实时内存可视化
**要点**:
- 用户写 C++ 代码 → AI 逐行「执行」→ Canvas 渲染内存状态
- 每一步展示：栈帧、变量、堆块、指针箭头
- 支持步进（上一步/下一步）、自动播放、动画

**演讲备注**:
核心思路很简单。用户输入一段 C++ 代码，我们发给 DeepSeek（或其他 LLM），让它模拟代码执行，返回每一步的内存快照。然后我们用 PySide6 的 QGraphicsView 把这个快照画出来。不是真实编译执行，是 LLM 模拟——好处是零安全风险，坏处是不支持复杂控制流。但我们做的是教学工具，简单代码就够了。

---

## Slide 4 | 🎥 Demo Video ① — 整体演示

**标题**: 完整操作流程演示
**内容**: 

```
[🎬 插入视频：从启动 app → 写代码 → Run → 步进 → Canvas 动画]
```

**时长建议**: 60-90 秒
**视频内容**: 启动 app → 选择 Pointers 示例 → 点击 Run → 等待 AI 返回 → 展示 Step 1/5 的高亮代码行 + Canvas 栈帧/堆块/箭头 → PageDown 步进 → 看到值修改闪烁动画 → delete 时堆块抖动消失

---

## Slide 5 | 核心功能 ① — 代码执行引擎

**标题**: AI 作为编译器 — LLM-Powered Execution
**要点**:
- 用户输入 C++ → DeepSeek API（JSON Mode, temperature=0）
- System Prompt 定义 19 条内存模拟规则
- AI 返回 `ExecutionTrace` — 每行代码对应一个 `MemoryState`
- Pydantic V2 校验 → Worker 线程异步处理

**演讲备注**:
我们没有用 AST 解析，也没有用真实编译器。我们写了一份 200 行的 System Prompt，教会 LLM 如何「假装自己是 C++ 执行引擎」。它知道栈地址是 0xS001 递增、堆地址是 0xH001 递增、new 分配堆、delete 释放堆、指针的 value 存 target_address。JSON Mode + temperature=0 保证输出结构稳定。

**(可以放 System Prompt 摘要截图)**

---

## Slide 6 | 核心功能 ② — Memory Canvas

**标题**: QGraphicsView 画布 — 内存可视化渲染
**要点**:
- 蓝色方块 = 栈帧（含变量名/类型/值）
- 橙色圆角块 = 堆内存
- 灰色实线箭头 = 有效指针，红色虚线 = 悬空指针
- 支持缩放/拖拽、Auto Fit、动画（飞入/闪烁/抖动渐隐）

**演讲备注**:
Canvas 是全自绘的。所有图形用纯 QPainter 几何绘制——矩形、文字、贝塞尔曲线箭头，没有任何外部图片素材。栈帧用蓝色边框 + 深蓝背景，堆块用橙色边框 + 深棕背景，这是 VS Code Dark+ 配色。指针箭头是三次贝塞尔曲线，近距离（栈内指针）从左出左入避免横跨，远距离（栈到堆）从右出左入。悬空指针是红色虚线，delete 后有抖动+渐隐动画。

**(可以放 Canvas 截图)**

---

## Slide 7 | 🎥 Demo Video ② — 关键动画演示

**标题**: Canvas 动画效果
**内容**:

```
[🎬 插入视频：展示关键动画效果]
```

**视频内容**: 
1. Run 后首次渲染（所有图元从无到有）
2. Step forward — 新增堆块飞入动画（400ms）
3. 值修改 — 文字变黄闪烁（300ms）
4. delete — 堆块抖动 6 步 + 渐隐 + 箭头变红虚线（600ms）
5. Prev 回退 — 无动画直接还原

---

## Slide 8 | 功能 ③ — OJ 题目分析

**标题**: OJ Analysis — 竞赛题智能讲解
**要点**:
- 粘贴 OJ 题面 + 参考代码
- AI 分析 → Overview / 解题思路 / 知识点 / 复杂度 / 常见错误 / 参考答案
- 参考答案代码可一键 Visualize
- 支持编译运行 + 测试用例对比
- 知识点可 "Add to Review"

**演讲备注**:
这个模块面向刷题的学生。比如 LeetCode 或 OJ 的题目，粘贴题目描述和解答代码进去，AI 会自动分析考点、时间复杂度、常见错误，并给出多解法。每个知识点可以加入错题复习系统，每段参考代码可以一键跳转到 Code Editor 可视化运行。

**(放 OJ 页面截图)**

---

## Slide 9 | 功能 ④ — 文件导入

**标题**: File Import — 课件/代码智能处理
**要点**:
- 支持 PDF / DOCX / PPTX / Markdown / C++ 源文件
- PyMuPDF + python-docx + python-pptx 提取文本
- AI 提取知识点 + 自动生成选择题
- 选择题交互（A/B/C/D 点击判断对错）
- 错题一键 "Add to My Errors"

**演讲备注**:
学生可以把老师的课件 PDF、PPT 直接拖进去，AI 会自动提取其中的 C++ 知识点并生成选择题。选择题是交互式的——点击选项会判断对错，错了会显示正确答案和解释，并可以将错题加入复习系统。知识点卡片上的代码示例可以一键 Visualize。

**(放 File Import 页面截图)**

---

## Slide 10 | 功能 ⑤ — 知识库 + 知识图谱

**标题**: Knowledge Base — List + Graph 双视图
**要点**:
- List 视图：搜索、浏览、详情面板
- Graph 视图：力导向图，节点大小 = 错误频率
- 点击节点 → AI 讲解（Markdown 渲染，支持代码块/粗体/列表）
- Quiz Me：对知识点出 2-3 道交互选择题
- 删除/Add to Review/自动 AI 讲解

**演讲备注**:
Knowledge Base 是所有学过知识点的汇总。List 视图可以搜索浏览，每个概念点开有 32px 大标题 + AI 生成的 Markdown 解释。切换到 Graph 视图展示力导向图——错误越多的概念节点越大，点击节点可以看 AI 解释。Quiz Me 按钮让 AI 对当前知识点出题，做错了可以加入复习。

**(放 KB List + Graph 截图)**

---

## Slide 11 | 🎥 Demo Video ③ — KB 深度演示

**标题**: 知识库核心交互
**内容**:

```
[🎬 插入视频：KB List → Graph → Quiz Me → Review 卡片]
```

**视频内容**: 
1. 打开 KB → 自动 AI 讲解无解释的概念
2. 搜索框过滤 → 点击查看 Markdown 渲染的解释
3. 切换到 Graph → 力导向图动画 → 点击节点
4. Quiz Me → AI 出题 → 做错 → Add to Review
5. 切到 Review → 看到刚添加的卡片

---

## Slide 12 | 功能 ⑥ — 错题复习

**标题**: Spaced Repetition — Anki 式智能复习
**要点**:
- SM-2 间隔重复算法（4 档评分：Forgot/Hard/Good/Easy）
- 牌组系统：指针与内存 / 面向对象 / STL / 基础语法 / 其他
- AI 自动分类知识点到对应牌组
- AI Hint（不直接给答案，引导思考）
- Markdown 答案渲染（AI 解释直接展示）
- 评分按钮显示预测下次复习时间（<10m / 6d / 10d / 1.5mo）

**演讲备注**:
复习系统借鉴 Anki。卡片正面是问题（22px 大字居中），可以先点 Hint 让 AI 给提示，再点 Show Answer 看答案。答案如果是 AI 生成的 Markdown 解释，会直接渲染成格式化的 Rich Text。评分有 4 档——Forgot（立即复习）、Hard（6天后）、Good（10天后）、Easy（1.5个月后）。按钮上显示预测的下次复习时间。

**(放 Review 页面截图)**

---

## Slide 13 | 功能 ⑦ — 多 AI 供应商 + i18n

**标题**: Multi-Provider AI & 双语支持
**要点**:
- 支持 4 个 LLM 供应商：DeepSeek / OpenAI / Claude / Gemini
- 统一配置界面（Settings → Provider 切换）
- Proxy 支持（国内用户需要代理访问 API）
- 全量中文翻译：256 行 `TRANSLATIONS` 字典
- 所有 UI 文字通过 `tr()` 动态切换

**演讲备注**:
Settings 里可以切换 AI 供应商。默认 DeepSeek（免费用量大），也可以用 OpenAI GPT-4.1-mini、Claude Sonnet、Gemini Flash。所有供应商通过统一的 AIService 接口调用。另外我们做了完整的中文翻译，256 条映射，所有按钮、标签、提示语都可以在 Settings 里一键切换中英文。

---

## Slide 14 | 技术架构

**标题**: Technology Stack & Architecture
**要点**:
```
┌─────────────────────────────┐
│  PySide6 QGraphicsView UI   │  ← 桌面端 GUI
├─────────────────────────────┤
│  Engine (状态管理器)          │  ← 协调 AI ↔ Canvas
├─────────────────────────────┤
│  Pydantic V2 Models          │  ← 数据契约
├─────────────────────────────┤
│  DeepSeek/OpenAI/Claude API  │  ← LLM 执行引擎
├─────────────────────────────┤
│  Local JSON (SM-2/Scores)    │  ← 数据持久化
└─────────────────────────────┘
```

**技术栈**: PySide6, Pydantic V2, httpx, PyMuPDF, python-docx, python-pptx, PyYAML

**演讲备注**:
架构分 4 层。UI 层用 PySide6 的 QGraphicsView 做 Canvas 渲染。Core 层有一个 Engine 类作为中央协调器，管理执行工作流、状态 Diff、动画。数据模型用 Pydantic V2 定义，保证 LLM 返回的 JSON 格式正确。服务层封装了 AI API 调用（httpx 异步）、文件处理（PyMuPDF 等）、本地 JSON 存储（线程安全的 CRUD + SM-2 算法）。

---

## Slide 15 | 数据流

**标题**: 端到端数据流
**要点**:
```
用户写代码 → Run → Engine._on_run()
  → ExecutionWorker (QThread) → AIExecutor
    → AIService.chat_json() → DeepSeek API
      → JSON Response → Pydantic Validation
        → ExecutionTrace.steps[]
          → MemoryCanvas.render_state()
            → StackItem / HeapItem / EdgeItem
              → CanvasAnimator.animate_diff()
```

**演讲备注**:
一条完整的数据流：用户点击 Run → Engine 创建 Worker 线程 → Worker 调用 AI Service 发 HTTP 请求到 DeepSeek → 收到 JSON 后用 Pydantic 校验 → Engine 拿到 ExecutionTrace → Canvas 渲染第一步 → 用户按 PageDown 步进 → StateDiff 计算差异 → Animator 播放动画。整个过程主线程和 Worker 线程通过 Qt Signals/Slots 通信，不会阻塞 UI。

---

## Slide 16 | 团队分工

**标题**: Team Contributions
**要点**:

| 成员 | 贡献 |
|------|------|
| **zhangjs0303** | 核心引擎、Canvas 渲染、动画系统、KB/Review 全线功能、架构设计 |
| **gky0329** | 数组/类 Canvas 修复、中文翻译系统(i18n)、快捷键、Review 滚动优化 |
| **QizhenLi-pku** | 多 AI 供应商支持(4 providers)、Settings 重构 |

---

## Slide 17 | 未来规划

**标题**: Future Roadmap
**要点**:
- 🔮 GDB/LLDB 真实执行引擎（替代 LLM 模拟）
- 🔮 复杂 C++ 语句支持（循环、条件、函数调用栈）
- 🔮 更多 STL 容器（map, set, unique_ptr）
- 🔮 Canvas 截图/PNG 导出
- 🔮 CI/CD + 单元测试覆盖
- 🔮 云端同步 + 学习数据分析

---

## Slide 18 | 总结

**标题**: What We Built
**要点**:
- ✅ 一个完整的桌面端 C++ 内存可视化工具
- ✅ AI 驱动的代码执行 + Canvas 实时渲染
- ✅ OJ 分析 + 文件导入 + 知识库 + Anki 复习
- ✅ 多 AI 供应商 + 中英双语
- ✅ ~7000 行 Python，38 个模块
- ✅ 开源、MIT 协议

---

## Slide 19 | 谢谢

**标题**: Thank You / Q&A
**副标题**: GitHub: https://github.com/gky0329/HomeworkForCXSJSX

---

## 🎬 视频位汇总

| Slide | 内容 | 建议时长 |
|-------|------|---------|
| Slide 4 | 整体操作流程（启动→Run→步进） | 60-90s |
| Slide 7 | Canvas 动画集锦（飞入/闪烁/抖动） | 30-45s |
| Slide 11 | KB 深度交互（Graph→Quiz→Review） | 45-60s |
