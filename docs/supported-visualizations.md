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

- Canvas: 变量名行 + 下方 3 个连续的小矩形块 `[0] 10  [1] 20  [2] 30`（橙色底色，和堆块同色系）
- VarItem 文本显示 `arr: int[3] = [10, 20, 30]`

---

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
