# 画布交互说明

> Last updated: 2026-05-30

本文档记录代码可视化画布的交互行为、缩放、平移、图元越界处理和动画系统。

## 画布移动

- **中键拖动** — 平移整个画布视图
- 不修改图元绝对坐标，只改变 QGraphicsView 视口位置

## 缩放

| 操作 | 行为 |
|------|------|
| `Ctrl + 滚轮` | 缩放视图 |
| 工具栏 `-` `+` 按钮 | 缩小 / 放大 |
| `Ctrl+0` | 重置缩放 |
| `Auto Fit` 复选框 | 每次步进后自动 fit（默认开启） |
| `Fit to View` (⇅) | 按当前可见图元边界自动缩放 |

## 步骤导航

| 操作 | 行为 |
|------|------|
| `Run (F5)` | 发送代码到 AI → 渲染首步 |
| `Next Step (PageDown)` | 计算 StateDiff → 动画 → 渲染下一步 |
| `Prev Step (PageUp)` | 无动画回到上一步 |
| `Reset (F6)` | 清空 canvas + trace |
| `Auto Play` | 自动步进（200ms–2000ms 可调） |
| 大号 `< Prev Step` / `Next Step >` | Canvas 下方醒目按钮 |

## 代码行高亮

- 每一步执行时，Code Editor 中当前行的**整行背景会变绿**（`#2A4A2A`）
- 编辑器自动滚动到当前行位置
- 高亮与 Canvas 内存状态同步

## Edge 箭头路由

- **近距离**（<150px）：从左出左入，小曲度弧线，避免大斜角横跨栈区
- **远距离**（≥150px）：从右出左入，标准贝塞尔曲线
- 悬空指针 → 红色虚线带箭头的贝塞尔曲线
- 箭头 Z-order 设为 +1，确保不被 item 遮住

## 动画系统

| 动画类型 | 效果 | 时长 |
|----------|------|------|
| 新增堆块 | 飞入（从右侧 300px 滑入）+ 透明度 0→1 | 400ms |
| 值修改 | 文字颜色变黄（`#FFD700`）→ 渐回原色 | 300ms |
| 内存释放 | 6 步 x 轴抖动 → 渐隐至透明 | 600ms |
| 移除变量 | 透明度 1→0 渐隐 | 400ms |
| 移除边 | 透明度 1→0 渐隐后 removeItem | 400ms |

- **Generation counter** 模式：`stop_all()` 时递增 generation，每 tick 检查匹配，防止 stale timer 回调
- **shiboken6.isValid()** 守卫所有动画 item 操作

## 图元越界处理

- 栈图元和堆图元尺寸变化后重算宽高
- 自动夹回场景范围内（`itemChange` + `_clamp_within_scene`）
- 左键拖动也被限制在场景范围内

## 默认放置与避让策略

- 每个图元有全局唯一「布局帧号」，`main` 固定为 0 且永不避让
- 按帧号从小到大扫描：重叠时尝试右侧→下方放置
- 手动拖动不触发自动重排
- 位置缓存：重渲染前快照，新 item 从上次位置飞入
- Item 复用：按 key（frame name + index / heap address）匹配，最小化创建销毁

## 修复日志

- 2026-05-30: Edge 路由优化（近距离左出左入，Z-order=1）；Auto-play + line highlight；Auto Fit checkbox tooltip
- 2026-05-25: 渲染流程复用 + 首次自动 Fit + 堆图元 index 缓存 + Code Editor Auto Fit 选项
- 2026-05-25: 修复堆图元地址未更新 + 透明度未恢复

## 相关代码

- 视图 & fit: [app/ui/main_window.py](../app/ui/main_window.py)
- 动画系统: [app/ui/canvas/canvas_animator.py](../app/ui/canvas/canvas_animator.py)
- 栈图元: [app/ui/canvas/stack_item.py](../app/ui/canvas/stack_item.py)
- 堆图元: [app/ui/canvas/heap_item.py](../app/ui/canvas/heap_item.py)
- 边/箭头: [app/ui/canvas/edge_item.py](../app/ui/canvas/edge_item.py)
- 画布管理: [app/ui/canvas/memory_canvas.py](../app/ui/canvas/memory_canvas.py)
- 执行引擎: [app/core/engine.py](../app/core/engine.py)
