# 快捷键功能说明

本文档描述代码编辑页的新快捷键设计、当前映射，以及以后如何继续扩展。

## 目标

- 在 Code Editor 页面内，用键盘直接控制执行流程。
- 保持快捷键与按钮行为一致，避免重复写两套逻辑。
- 为后续继续增加快捷键留出统一入口。

## 当前映射

当焦点在 Code Editor 页面及其子控件中时：

- `PageUp` = 上一步按钮
- `PageDown` = 下一步按钮
- `F5` = Run 按钮
- `F6` = Reset 按钮

当前窗口仍保留缩放快捷键：

- `Ctrl+=` = 放大画布
- `Ctrl+-` = 缩小画布
- `Ctrl+0` = 重置缩放

在代码的可视化区域内：

- 按住中键拖动 = 平移所有可视化元素

## 代码放在哪里

- 快捷键注册入口在 [app/ui/main_window.py](../app/ui/main_window.py) 的 `_setup_shortcuts()`。
- 快捷键注册器在 [app/ui/shortcut_registry.py](../app/ui/shortcut_registry.py)。
- PageUp / PageDown / F5 / F6 这组键还会经过主窗口的应用级事件过滤器，确保代码编辑器自己的按键处理不会吞掉它们。
- 按钮本体仍然定义在 [app/ui/main_window.py](../app/ui/main_window.py) 的 `_setup_toolbar()`，快捷键只是调用这些按钮的 `click()`，因此按钮和快捷键天然同步。

## 设计方式

现在的实现分成两层：

- `ShortcutRegistry` 负责统一保存快捷键定义、创建 `QShortcut`、保持引用不被回收。
- `ShortcutBinding` 负责描述一个快捷键条目，包括按键、名称、说明、回调和作用域。

这样以后新增快捷键时，不需要在各处散落地写 `QShortcut(...)`，只要往同一个注册列表里加一条绑定即可。

## 如何新增快捷键

1. 打开 [app/ui/main_window.py](../app/ui/main_window.py)。
2. 找到 `_setup_shortcuts()`。
3. 按下面的模式新增一条 `ShortcutBinding`：

```python
ShortcutBinding(
    sequence="Ctrl+K",
    name="example_action",
    description="Example shortcut",
    callback=self.btn_run.click,
)
```

4. 如果这个快捷键只应该在 Code Editor 页面生效，就放进 `self._code_shortcuts`。
5. 如果这个快捷键应该全局生效，就放进 `self._global_shortcuts`。

## 作用域约定

- `self._code_shortcuts` 绑定在 Code Editor 页面容器上，所以只在代码页及其子控件聚焦时触发。
- `self._global_shortcuts` 绑定在主窗口上，用于不依赖页面的全局行为。

## 约束

- 当前测试键必须继续通过按钮执行同一套逻辑，不要在快捷键里复制业务代码。
- 如果以后要给更多按钮加快捷键，优先继续走 `ShortcutBinding` + `ShortcutRegistry` 的方式。