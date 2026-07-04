# C++rafting Table 项目文档

## 项目简介

C++rafting Table 是一个面向 C++ 学习场景的桌面端内存可视化工具。用户可以输入 C++ 代码，应用会生成逐行执行轨迹，并在 QGraphicsView 画布中展示栈、堆、指针、数组、结构体、对象、继承关系和释放后的悬挂指针状态。

项目采用本地优先设计：用户数据、错题、知识点、活动记录均保存在本地 JSON 文件中；AI API Key 由用户自己配置，不写入仓库。

## 项目亮点

| 亮点 | 说明 |
| --- | --- |
| 逐行内存可视化 | 用栈帧、堆块、指针曲线和对象成员视图解释 C++ 运行状态。 |
| AI 执行轨迹 | DeepSeek/OpenAI/Claude/Gemini 可返回符合 Pydantic 模型的执行 JSON。 |
| 原生调试探索 | macOS/Linux 可使用 LLDB/DWARF；Windows MSVC/PDB 后端已接入但默认关闭，需验证。 |
| 文件导入学习 | 支持 PDF/DOCX/PPTX/Markdown/C++ 文件，提取知识点和选择题。 |
| OJ 题目分析 | 粘贴题面与代码后生成讲解，并可把代码送入内存画布运行。 |
| 知识闭环 | 知识库、知识图谱、错题复习和 SM-2 间隔重复形成复习流程。 |
| 可切换 UI | 设置中可选择 MC、极简黑、极简白三种界面主题。 |

## 环境要求

- Python 3.11 或更高版本
- PySide6 6.6 或更高版本
- `pip install -r requirements.txt`
- 至少配置一个 AI 供应商 API Key
- 可选：本地 C++ 编译器/调试器，用于原生调试路径

## 安装与启动

```bash
git clone https://github.com/gky0329/HomeworkForCXSJSX.git
cd HomeworkForCXSJSX
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.yaml.example config.yaml
python main.py
```

Windows PowerShell：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy config.yaml.example config.yaml
python main.py
```

## 配置说明

`config.yaml` 不应提交到 GitHub。第一次启动前复制模板：

```bash
cp config.yaml.example config.yaml
```

核心配置：

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
  language: zh
  code_font_size: 16
  theme: mc  # mc | minimal_dark
debugger:
  enable_experimental_pdb: false
```

也可以用环境变量配置 API Key：

```bash
export DEEPSEEK_API_KEY="sk-..."
```

Windows PowerShell：

```powershell
$env:DEEPSEEK_API_KEY="sk-..."
```

## 功能使用

### 代码可视化

1. 打开 Code Editor。
2. 选择内置示例，或粘贴 C++ 代码。
3. 如果代码读取输入，在 Program Input 中填写 stdin。
4. 点击 Run。
5. 使用 Next/Prev/Auto Play/Zoom/Fit/Fullscreen 查看每一步内存变化。

### OJ 分析

1. 打开 OJ Analysis。
2. 粘贴题面和参考代码。
3. 点击 Run Analysis。
4. 查看解题思路、复杂度、常见错误和测试用例。
5. 将代码发送到可视化画布或加入复习。

### 文件导入

1. 打开 File Import。
2. 上传 PDF、DOCX、PPTX、Markdown 或 C++ 源文件。
3. 提取知识点与题目。
4. 将知识点同步到知识库或错题复习。

### 复习与知识库

- Review 页面使用 SM-2 间隔重复算法安排复习。
- Knowledge Base 页面可以浏览概念、查看 AI 解释，并通过图谱观察概念关系。

### UI 主题

打开 Settings，在 UI Theme 中选择：

- MC：当前默认的像素/方块风格深色主题。
- Minimal Black：低干扰黑色极简主题。

保存后全局控件会立即套用新样式；已加载页面中少量内联颜色可能需要重启应用后完全一致。

## 跨平台状态

| 平台 | 稳定执行路径 | 原生调试路径 |
| --- | --- | --- |
| macOS | AI 供应商 fallback | LLDB/DWARF 本地开发路径 |
| Windows | AI 供应商 fallback | MSVC/PDB 实验路径，默认关闭 |
| Linux | AI 供应商 fallback | LLDB/DWARF 本地开发路径 |

Windows PDB 后端需要 Visual Studio C++ Build Tools 和 Windows Debugging Tools。启用前请阅读 `docs/windows.md`。

## 测试与验证

```bash
python -m py_compile main.py app/core/debug_executor.py app/ui/theme/manager.py
QT_QPA_PLATFORM=offscreen python -m pytest tests/unit -q
python tools/native_debug_smoke.py --list-backends
```

主题快速检查：

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

## 安全与提交规范

- 不提交 `config.yaml`、API Key 或 `data/user/`。
- 项目价值评估、私有答辩判断等本地文件使用 `*.local.md` 命名，避免进入 GitHub。
- Canvas 内存元素保持纯 QGraphics/QPainter 几何绘制，不引入图片渲染。
- Windows MSVC/PDB 后端在真实 Windows 机器通过 smoke tests 前，不作为稳定功能宣传。
