# C++ Memory Visualizer — 支持的可视化类型

> 本文档描述 LLM 执行引擎支持输出的内存状态格式，以及 Canvas 对应的渲染效果。

---

## 1. 基础类型（MVP 已实现）

### 1.1 栈变量

```json
{
  "name": "a",
  "type": "int",
  "value": "42",
  "address": "0xS001",
  "is_pointer": false
}
```

- Canvas: 蓝色栈帧内的文本行 `a: int = 42`

### 1.2 指针变量

```json
{
  "name": "p",
  "type": "int*",
  "value": "0xH001",
  "address": "0xS002",
  "is_pointer": true
}
```

- Canvas: 文本行 + 从 p 到目标地址的灰色贝塞尔箭头

### 1.3 堆内存块

```json
{
  "address": "0xH001",
  "type": "int",
  "value": "100",
  "is_freed": false
}
```

- Canvas: 橙色圆角矩形，显示地址 + 类型 + 值

### 1.4 堆内存释放 (delete)

```json
{ "address": "0xH001", "is_freed": true }
```

- Canvas: 边框变红色虚线 → 震动动画 → 渐隐消失
- 指向该块的指针箭头同时变悬空（红色虚线），随后渐隐移除

---

## 2. 数组 (is_array)

```json
{
  "name": "arr",
  "type": "int[3]",
  "value": "[10, 20, 30]",
  "address": "0xS003",
  "is_pointer": false,
  "is_array": true,
  "element_count": 3,
  "elements": [
    {"index": 0, "value": "10"},
    {"index": 1, "value": "20"},
    {"index": 2, "value": "30"}
  ]
}
```

- Canvas: 栈数组在变量名行内对每个元素值做逐个橙色高亮，矩形宽度按值文本实时计算，不再使用固定宽度或固定偏移
- VarItem 文本显示 `arr: int[3] = [10, 20, 30]`

若数组位于堆上（例如 `new int[3]{1, 2, 3}`）：
- Canvas: 堆块内部按 cell 渲染，每个 cell 中上部显示元素值 `1` / `2` / `3`，下方显示索引 `[0]` / `[1]` / `[2]`
- cell 宽度根据“元素值文本宽度”和“索引文本宽度”二者较大值自动计算
- 整个 HeapItem 宽度取“标题行宽度”和“所有 cell 总宽度”中的较大值，避免标题溢出

`std::array<T, N>` 会解包其调试器实现字段（如 `__elems_` / `_Elems`），按普通数组的 `elements` cell 渲染，而不是显示为单个对象成员。

当 `std::array` / 容器元素本身是结构体或类时，元素值中的指针成员会根据源码字段类型映射成 `0xS...` / `0xH...` 模拟地址，并从对应 element cell 画出指针箭头。例如 `std::array<Node, 2>` 中 `nodes[1].next` 指向 `first` 时，`nodes[1]` cell 会显示 `next=0xS001`，并连到 `first`。

STL 容器适配器（如 `std::stack<T>`、`std::priority_queue<T>`）会解包底层容器字段 `c`，按 `elements` cell 渲染当前存储内容，避免把实现细节当成业务成员展示。

---

## 2.1 智能指针

`std::unique_ptr<T>` / `std::shared_ptr<T>` 会按 pointer-like owner 渲染，目标对象显示为 heap block。多个 `shared_ptr` 指向同一对象时共享同一个 `0xH...` block，并分别画 owner edge。

当 `std::unique_ptr<T>` / `std::shared_ptr<T>` 出现在 `std::vector` / `std::array` / `std::map` 等容器的模板参数里时，容器本身仍按 array/container cell 渲染，不能把整个容器误判为 pointer-like owner。元素 cell 会保留智能指针目标地址，并从元素 cell 画到对应 heap block。

`std::weak_ptr<T>` 不视为 owner。只要仍有 live `shared_ptr` owner，`weak_ptr` 会显示为普通弱引用边；当所有 `shared_ptr` owner reset 后，`weak_ptr` 仍保留历史目标地址，但目标 heap 标记为 freed，边显示为 dangling，避免误导用户以为 weak_ptr 延长了对象生命周期。

```cpp
std::shared_ptr<int> sp = std::make_shared<int>(3);
std::weak_ptr<int> wp = sp;
sp.reset();
bool gone = wp.expired();
```
预期: `sp` 显示 `nullptr`，`wp` 指向历史 heap block；该 heap block 标记为 freed，`wp -> heap` 为 dangling edge，`gone = true`。

## 3. struct / class (members)

```json
{
  "name": "pt",
  "type": "struct Point",
  "value": "{x=10, y=20}",
  "address": "0xS004",
  "is_pointer": false,
  "members": [
    {"name": "x", "type": "int", "value": "10"},
    {"name": "y", "type": "int", "value": "20"}
  ]
}
```

- Canvas: 变量名行 + 下方缩进的成员行 `.x: int = 10` `.y: int = 20`（青蓝色文字）
- VarItem 文本显示 `pt: struct Point = {x=10, y=20}`

---

## 4. 递归函数调用 (多 StackFrame)

```json
{
  "stack": [
    {
      "frame_name": "factorial(3)",
      "variables": [{"name": "n", "type": "int", "value": "3", "address": "0xS005", "is_pointer": false}]
    },
    {
      "frame_name": "factorial(2)",
      "variables": [{"name": "n", "type": "int", "value": "2", "address": "0xS006", "is_pointer": false}]
    },
    {
      "frame_name": "factorial(1)",
      "variables": [{"name": "n", "type": "int", "value": "1", "address": "0xS007", "is_pointer": false}]
    }
  ]
}
```

- Canvas: 多个纵向排列的栈帧，每个有独立的变量
- frame_name 清晰显示递归深度，如 `factorial(3)` → `factorial(2)` → `factorial(1)`

---

## 5. 指针操作

| 操作 | LLM 应输出 | Canvas 渲染 |
|---|---|---|
| `int* p = &a` | edge: `source=0xS00p target=0xS00a` | 灰色实线箭头从 p 指向 a |
| `*p = 100` | a 的 value 变为 "100" | a 的文字闪烁黄色 300ms |
| `p = new int(5)` | heap: `0xH001`, edge: `source=0xS00p target=0xH001` | 堆块飞入 + 箭头指向堆 |
| `delete p` | heap `is_freed=true`, edge `is_dangling=true` | 堆块抖动渐隐 + 箭头变红虚线后消失 |

---

## 6. 地址规则

- 栈地址: `0xS001`, `0xS002`, `0xS003` ... 按顺序递增
- 堆地址: `0xH001`, `0xH002`, `0xH003` ... 按顺序递增
- 指针的 value 字段填写它指向的 target_address

---

## 7. 面向对象 — 类、继承、多态 (is_object)

### 7.1 类实例化

```json
{
  "name": "a",
  "type": "class Animal",
  "value": "<Animal object>",
  "address": "0xS001",
  "is_pointer": false,
  "is_object": true,
  "class_name": "Animal",
  "virtual_methods": ["speak()"],
  "members": [
    {"name": "_vptr", "type": "vtable*", "value": "&Animal::vtable"},
    {"name": "name", "type": "string", "value": "Tom"}
  ]
}
```

- Canvas: Class header `a: Animal` → `[vtable] speak()` → `.name: string = Tom`

### 7.2 继承 (base_classes)

```json
{
  "name": "d",
  "type": "class Dog",
  "value": "<Dog object>",
  "is_object": true,
  "class_name": "Dog",
  "base_classes": ["Animal"],
  "virtual_methods": ["speak()"],
  "members": [
    {"name": "_vptr", "type": "vtable*", "value": "&Dog::vtable"},
    {"name": "name", "type": "string", "value": "Buddy"},
    {"name": "breed", "type": "string", "value": "Golden"}
  ]
}
```

- Canvas: 橙色 `⬆ extends Animal` 提示 + 所有成员（含继承的 name）

### 7.3 多态指针

基类指针 `Animal* p` 指向派生类对象 `Dog`：
- `p` 的 type 为 `"Animal*"`，value = target_address
- Edge 指向的堆块 class_name 为 `"Dog"`，包含 Dog 全部成员
- Canvas 通过观察指针箭头指向的实际 class_name 理解多态

### 7.4 对象成员指针

```json
{
  "name": "second",
  "type": "Node",
  "value": "{value=2, next=0xS001}",
  "address": "0xS002",
  "is_object": true,
  "members": [
    {"name": "value", "type": "int", "value": "2", "address": "0xS002.value"},
    {"name": "next", "type": "Node*", "value": "0xS001", "address": "0xS002.next"}
  ]
}
```

- Canvas: `.next: Node* = 0xS001` 这一行作为箭头起点，指向目标 `Node` 对象。
- 适合链表、树、图节点等课堂/OJ 高频结构，例如 `second.next -> first`。

---

## 8. Lambda / 函数对象 (is_function_object)

```json
{
  "name": "f",
  "type": "lambda",
  "value": "<lambda>",
  "address": "0xS003",
  "is_pointer": false,
  "is_function_object": true,
  "captures": [
    {"name": "x", "type": "int", "value": "10", "by_ref": false},
    {"name": "y", "type": "int", "value": "20", "by_ref": true}
  ]
}
```

- Canvas: `f: λ` → `λ [callable]` → `[capture] x: int = 10` → `[&capture] y: int = 20`

---

## 10. 面向对象进阶

### 10.1 构造函数 (is_constructed) / 析构函数 (is_destroyed)

```json
{
  "name": "f",
  "type": "class Fraction",
  "is_object": true, "class_name": "Fraction",
  "is_constructed": true, "is_destroyed": false,
  "members": [
    {"name": "m_numerator", "type": "int", "value": "1"},
    {"name": "m_denominator", "type": "int", "value": "2"}
  ]
}
```

- Canvas: `⚡ constructed` 绿色标签 → 成员列表
- 析构时 `is_destroyed=true` → `💀 destroyed` 红色标签

### 10.2 引用 (is_reference)

```json
{
  "name": "ref", "type": "int&",
  "value": "0xS001", "address": "0xS002",
  "is_reference": true
}
```

- Canvas: `&ref: int& → 0xS001` — 引用变量标签，区别于指针（无箭头）

### 10.3 std::vector 容器

栈上 vector 变量（Object + members 含 _data 指针）:
```json
{
  "name": "v", "type": "std::vector<int>", "is_object": true,
  "members": [
    {"name": "_size", "type": "int", "value": "3"},
    {"name": "_capacity", "type": "int", "value": "4"},
    {"name": "_data", "type": "int*", "value": "0xH001", "is_pointer": true}
  ]
}
```

堆上 buffer（HeapBlock）:
```json
{
  "address": "0xH001", "type": "std::vector<int>::buffer",
  "is_array": true, "container_size": 3, "container_capacity": 4,
  "elements": [
    {"index":0,"value":"10"}, {"index":1,"value":"20"}, {"index":2,"value":"30"}
  ]
}
```

- Canvas: buffer 上方显示 `size=3 cap=4`，下方元素 cells + Edge 从 `_data` 指向 buffer

### 10.4 运算符重载临时对象 (is_temporary)

```json
{
  "name": "temp", "type": "class Cents",
  "is_object": true, "is_temporary": true,
  "members": [{"name":"m_cents","type":"int","value":"15"}]
}
```

- Canvas: `⏳ temporary` 黄色标签，下一行消失

---

## 11. 测试用例

### 构造函数/析构函数测试
```cpp
class Fraction {
    int m_num, m_den;
public:
    Fraction(int n, int d) : m_num(n), m_den(d) {}
    ~Fraction() {}
};
Fraction f(1, 2);
```
预期: `f: Fraction [ctor]` → 离开作用域后 `[dtor]`

### 引用测试
```cpp
int a = 42;
int& ref = a;
ref = 100;
```
预期: `&ref: int& → 0xS001`，a 的值变 100 闪烁

### std::vector 测试
```cpp
std::vector<int> v;
v.push_back(10);
v.push_back(20);
```
预期: 堆 buffer `size=2 cap=N [10][20]`，扩容时 cap 变化

### std::vector 指针元素测试
```cpp
int a = 1;
int b = 2;
std::vector<int*> ptrs = {&a, &b};
*ptrs[1] = 9;
```
预期: `ptrs` 显示为 array/container 单元格，不能把整个 `ptrs` 变量标成 pointer；`b` 的值变成 9；`ptrs[0]` / `ptrs[1]` 单元格分别画出指向 `a` / `b` 的箭头

### std::array 对象元素指针成员测试
```cpp
struct Node { int value; Node* next; };
Node first{1, nullptr};
Node second{2, &first};
std::array<Node, 2> nodes = {first, second};
nodes[1].next->value = 5;
```
预期: `nodes` 显示为 element cell，不显示 `__elems_` / `_Elems` 实现字段；`nodes[1]` 中的 `next` 映射为 `first` 的模拟地址，并从 `nodes[1]` cell 画出指向 `first` 的箭头；`first.value` 变成 5

### std::map 指针值测试
```cpp
int a = 1;
int b = 2;
std::map<std::string, int*> m;
m["a"] = &a;
m["b"] = &b;
*m["b"] = 9;
```
预期: `m` 显示为 key/value entry 单元格，entry 中的 `second` 指针值映射为 `0xS...` 模拟地址；每个 entry cell 画出指向对应栈变量的箭头，`b` 的值变成 9

### std::optional 指针值测试
```cpp
int a = 1;
std::optional<int*> op = &a;
*op.value() = 5;
```
预期: `op` 显示为 `optional<int*>` 对象，内部 `.value: int* = 0xS...` 成员行作为箭头起点指向 `a`；`a` 的值变成 5。`optional<int>` 为空时显示 `empty`，不展示 `Has Value=false` 这类调试器摘要。

### 运算符重载测试
```cpp
class Cents { int m_cents; };
Cents a{5}, b{10};
Cents sum = a + b;
```
预期: temp 对象 `[temp]` 出现后消失，sum 赋值后显示

### 继承 + 多态测试
```cpp
class Animal { virtual void speak() {} };
class Dog : public Animal { void speak() override {} };
Animal* a = new Dog();
```
预期: stack 上 `a: Animal*` 指针 → heap 上 Dog 对象，显示 `⬆ extends Animal` + `[vtable] speak()`

### Lambda 测试
```cpp
int x = 10;
auto f = [x, &y]() { return x + y; };
```
预期: stack 上 `f: λ [x=10, &y=...]`

### 数组测试
```cpp
int arr[3] = {10, 20, 30};
int* p = arr;
*(p + 1) = 50;
```
预期: 3 个数组 cell，p→arr 箭头，第 2 个 cell 值变 50 闪烁

### struct 测试
```cpp
struct Point { int x; int y; };
Point pt = {10, 20};
Point* q = &pt;
q->x = 99;
```
预期: struct frame 显示 `.x` `.y` 成员，q 箭头指向 pt，x 值变 99 闪烁

### 递归测试
```cpp
int factorial(int n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}
int result = factorial(3);
```
预期: 3 层 StackFrame `factorial(3)` `factorial(2)` `factorial(1)` 纵向排列
