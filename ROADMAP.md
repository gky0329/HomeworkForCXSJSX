# ROADMAP — C++ OOP 教学工具 MVP 施工路线

> 执行原则：不看旧代码、不改旧代码、只偷资产。严格按顺序推进，上一阶段不验收绝不开下一阶段。
>
> **最后更新**：2026-05-13

---

## Phase 0: 消除技术债（半天） ✅ 已完成

**原则**：旧代码是无底洞，不要试图重构。

- [x] 将 `demo/` 目录重命名为 `legacy_demo/`（冻结为只读零件库）
- [x] 按技术报告 §4.3 目录树创建全新的空文件结构：
  - `app/core/` — 引擎（`oop_model.py`, `step_executor.py`, `state_diff.py`, `challenge_loader.py`）
  - `app/ui/` — 界面（`main_window.py`, `pages/`, `canvas/`, `widgets/`, `theme/`）
  - `app/services/` — 服务（`audio_manager.py`, `storage_service.py`, `progress_service.py`）
  - `data/levels/` — 关卡 JSON
  - `tests/unit/` — 单元测试
- [x] 从旧目录**原封不动复制**以下资产到新目录：
  - `legacy_demo/textures/`
  - `legacy_demo/Minecraft Sound Pack 1.17 - Sound Effects/`
  - `legacy_demo/app/widgets/mc_button.py`
  - `legacy_demo/app/services/audio_manager.py`
- [x] 移除根目录旧 Qt 残留文件（`.pro`, `mainwindow.*`, `test1.*`）
- [x] 配置 `requirements.txt`：`PySide6>=6.6`, `pyyaml>=6.0`, `pytest`

**额外完成**：旧 quiz app 已用新架构（DI + NavManager + Config + Logger）整体重写。8 个页面（Splash/Menu/WorldSelect/CreateWorld/CreatingWorld/LessonIntro/Quiz/Result）全部翻新，功能等价于 legacy_demo，代码从 ~1860 行减至 ~1100 行。

---

## Phase 1: 纯净内核 — Sprint 1 ✅ 已完成

**原则**：完全脱离 Qt，纯 Python 开发 + pytest 护航。

### 数据模型 (`oop_model.py`) ✅
```
ClassDef(name, members: list[MemberDef])
MemberDef(name, type, access)
ObjectInstance(cls_name, var_name, values: dict)
OopModel(classes, instances, current_scope)
  ├─ get_class(name) → ClassDef
  ├─ get_instance(name) → ObjectInstance
  └─ snapshot() → deep copy（预留给 undo）
```

### 通信协议 (`state_diff.py`) ✅
```
StateDiff(added_classes, added_instances, updated_instances,
          removed_instances, errors, annotations, source_line, source_text)
ClassError(kind, description, class_name, line)
```

### 正则执行器 (`step_executor.py`) ✅
支持 5 种语句 + 成员声明解析：

| ID | 语句 | 操作 |
|----|------|------|
| 1 | `class X { ... };` | 创建 ClassDef |
| 2 | `public:` / `private:` | 切换访问控制 |
| 3 | `int name;`（类体内） | 添加 MemberDef |
| 4 | `X obj;` | 创建 ObjectInstance |
| 5 | `obj.member = value;` | 更新 values |
| 6 | `}` (作用域退出) | removed_instances |

### TDD 验收 ✅
```
pytest tests/unit/ — 23/23 passed
  test_oop_model.py ....... (7)
  test_state_diff.py ..... (5)
  test_step_executor.py ........... (11)
```
- 输入完整 C++ 片段 → 断言 StateDiff 正确
- 输入越权访问 → 断言 ClassError 被产出
- CLI demo：`python main.py` 自动运行 oop_001 + oop_002 端到端验证

---

## Phase 2: 视觉魔法 — Sprint 2（2 天）

**原则**：只用 Mock 数据驱动画布，不连输入框。

### Canvas 搭建 (`oop_canvas.py`)
- 左侧 Class 区：绿色 `ClassItem` 卡片，显示类名 + 成员列表
- 右侧 Instance 区：蓝色 `InstanceItem` 卡片，显示对象名 + 成员值表格
- 连线：从 Instance 到所属 Class 的虚线

### 动画 (`canvas_animator.py`)
- 类定义：卡片 scale 0→1 飞入
- 实例化：卡片从 Class 区飞出到 Instance 区
- 成员赋值：值文本闪烁 2 次
- 作用域退出：对象卡片渐隐消失

### Mock 验收
```python
# 手写 StateDiff 扔给 Canvas，确认卡片渲染正确
diff = StateDiff(
    added_classes=[ClassDef("Player", [MemberDef("health", "int", "public")])],
    added_instances=[ObjectInstance("Player", "p", {"health": 0})],
    ...
)
canvas.apply(diff)
```

---

## Phase 3: 组装闭环 — Sprint 3（2 天）

### NavigationManager (`nav.py`)
- 状态机替代 lambda 蛛网
- 合法跳转表：Splash → Menu → LevelSelect → Challenge

### ChallengePage (`challenge_page.py`)
- 左：代码面板（填空式 QLineEdit + 只读行）
- 右：OopCanvas
- 底部：Step / Reset / Hint 按钮

### 按钮流
```
用户填空 → 点击 Step → 拼接字符串 → StepExecutor 执行
→ 产出 StateDiff → Canvas 播放动画 → Goal Checker 判断
```

### 输入防呆
- QLineEdit 绑定 `QRegularExpressionValidator`
- 类名：`[A-Za-z_][A-Za-z0-9_]*`
- 数值：`[0-9]+`
- 关键：**禁止分号 `;` 和大括号 `{}`**，防止正则引擎崩溃

### 关卡 (`data/levels/oop_001.json`)
- 第一关：定义 Player 类并实例化
- 第二关：两个不同类的多实例

### 集成验收
```
主菜单 → 选关 → 填空 → Step → 动画播放 → 通关
```

---

## ⚠️ Golden Rules（贴在显示器上）

1. **单向数据流**：Canvas 绝不读 OopModel。`代码字符串 → Executor → OopModel → StateDiff → Canvas` 是唯一通路。
2. **不用 time.sleep()**：动画用 `QSequentialAnimationGroup.finished` 信号解锁按钮，不手动设 bool 标志。
3. **正则防崩溃**：所有模式用 `\s*` 吸空格；UI 层提前拦截非法字符。
4. **对象消亡**：走到 `}` 时，StepExecutor 必须产出 `removed_instances`，Canvas 做渐隐动画。
