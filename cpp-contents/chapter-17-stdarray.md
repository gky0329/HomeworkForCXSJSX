# Chapter 17 — Fixed-size Arrays: std::array and C-style Arrays

## 17.1 — Introduction to std::array

### Why not always use std::vector?

- `std::vector` is slightly less performant than fixed-size arrays
- `std::vector` only supports `constexpr` in very limited contexts

**Best practice:** Use `std::array` for constexpr arrays, `std::vector` for non-constexpr arrays.

### Defining std::array

```cpp
#include <array>

std::array<int, 5> a {};  // 5 ints, value-initialized
```

`std::array` has two template arguments: element type (`int`) and length (`5`, a non-type template parameter of type `std::size_t`).

### The length must be a constant expression

```cpp
std::array<int, 7> a {};          // literal constant
constexpr int len { 8 };
std::array<int, len> b {};        // constexpr variable
std::array<int, max_colors> c {}; // enumerator
```

### Aggregate initialization

`std::array` is an aggregate (no constructors). Use aggregate initialization:

```cpp
std::array<int, 5> prime { 2, 3, 5, 7, 11 }; // list initialization (preferred)
std::array<int, 5> a{}; // value initialize (elements zero-initialized)
```

### CTAD (C++17)

```cpp
constexpr std::array a1 { 9, 7, 5, 3, 1 }; // deduces std::array<int, 5>
constexpr std::array a2 { 9.7, 7.31 };      // deduces std::array<double, 2>
```

### std::to_array (C++20)

```cpp
constexpr auto myArray { std::to_array<int>({ 9, 7, 5, 3, 1 }) }; // specify type, deduce size
```

### Const and constexpr

`std::array` has full constexpr support — define as `constexpr` whenever possible.

---

## 17.2 — std::array length and indexing

### size_type

`std::array` defines `size_type`, which is always an alias for `std::size_t`.

### Getting the length

```cpp
arr.size()      // member function, returns size_type
std::size(arr)  // C++17, returns size_type (constexpr)
std::ssize(arr) // C++20, returns signed type (constexpr)
```

All three return constexpr values (except for a language defect with reference parameters, fixed in C++23).

### Indexing options

```cpp
arr[3]           // operator[], no bounds checking
arr.at(3)        // at(), runtime bounds checking (throws std::out_of_range)
std::get<3>(arr) // compile-time bounds checking (constexpr index required)
```

### std::get() for compile-time bounds checking

```cpp
constexpr std::array prime{ 2, 3, 5, 7, 11 };
std::cout << std::get<3>(prime); // ok
std::cout << std::get<9>(prime); // compile error!
```

---

## 17.3 — Passing and returning std::array

### Passing by reference

Both element type and array length are part of the type. Use function templates:

```cpp
template <typename T, std::size_t N>
void passByRef(const std::array<T, N>& arr)
{
    static_assert(N != 0);
    std::cout << arr[0] << '\n';
}
```

**Warning:** The non-type template parameter must be `std::size_t`, NOT `int`.

### C++20 auto non-type template parameter

```cpp
template <typename T, auto N>
void passByRef(const std::array<T, N>& arr) { /* ... */ }
```

### Static asserting on array length

```cpp
template <typename T, std::size_t N>
void printElement3(const std::array<T, N>& arr)
{
    static_assert (N > 3); // compile-time precondition
    std::cout << arr[3] << '\n';
}
```

### Returning std::array

Unlike `std::vector`, `std::array` is NOT move-capable. Options:
1. **Return by value** — acceptable for small arrays with cheap-to-copy elements
2. **Out parameter** — pass by non-const reference (no copy)
3. **Return std::vector instead** — if array isn't constexpr

---

## 17.4 — std::array of class types, and brace elision

### Initializing with structs

```cpp
struct House { int number{}, stories{}, roomsPerStory{}; };

// Explicit element types (single braces OK due to brace elision):
constexpr std::array houses { House{13,1,7}, House{14,2,5}, House{15,2,4} };

// Without explicit element types (double braces required):
constexpr std::array<House, 3> houses {{
    { 13, 1, 7 },
    { 14, 2, 5 },
    { 15, 2, 4 }
}};
```

### Brace elision

Aggregates support brace elision — you can omit braces when:
- Initializing with scalar (single) values
- The type is explicitly named with each element

---

## 17.5 — Arrays of references via std::reference_wrapper

References are not objects, so you cannot make an array of references. Workaround: `std::reference_wrapper<T>` (in `<functional>`):

```cpp
#include <functional>

int x { 1 }, y { 2 }, z { 3 };
std::array<std::reference_wrapper<int>, 3> arr { x, y, z };

arr[1].get() = 5; // modify the referenced object
std::cout << y;    // prints 5
```

### Key properties:
- `operator=` reseats the reference_wrapper
- Implicitly converts to `T&`
- `get()` returns a `T&` (use for assignment to disambiguate)

### Shortcuts

```cpp
auto ref { std::ref(x) };   // creates std::reference_wrapper<int>
auto cref { std::cref(x) }; // creates std::reference_wrapper<const int>
```

---

## 17.6 — std::array and enumerations

### Static assert for initializer count

```cpp
constexpr std::array testScores { 78, 94, 66, 77 };
static_assert(std::size(testScores) == max_students); // compile-time check!
```

### Using constexpr arrays for enum I/O

Store enumerator names in a `constexpr std::array` and use it for both `operator<<` and `operator>>`:

```cpp
constexpr std::array colorName { "black"sv, "red"sv, "blue"sv };
static_assert(std::size(colorName) == max_colors);
```

### Range-based for loops over enumerations

Create a `constexpr std::array` of all enumerator values:

```cpp
constexpr std::array types { black, red, blue };
for (auto c : types)
    std::cout << c << '\n';
```

---

## 17.7 — Introduction to C-style arrays

### Declaration

```cpp
int testScore[30] {}; // 30 value-initialized ints (no #include needed)
```

C-style arrays are built into the core language. The length must be a constant expression.

### Key properties

- Elements can be any object type
- Aggregate initialization works the same as `std::array`
- **No assignment support** (can't do `arr = {1,2,3}`)
- Can be `const` or `constexpr`
- `sizeof(arr)` returns total bytes (no overhead)

### Omitted length

```cpp
const int prime[] { 2, 3, 5, 7, 11 }; // compiler deduces length 5
```

### Getting the length

```cpp
std::size(arr)   // C++17 (<iterator>)
std::ssize(arr)  // C++20
```

### Indexing advantage

C-style arrays accept signed OR unsigned indices — NO sign conversion issues!

```cpp
int s { 2 };
std::cout << arr[s] << '\n'; // okay with signed index
```

---

## 17.8 — C-style array decay

### What is array decay?

When a C-style array is used in an expression, it is implicitly converted to a pointer to its first element. This loses the array's length information.

```cpp
int arr[5]{ 9, 7, 5, 3, 1 };
auto ptr{ arr }; // arr decays to int*, ptr is int*
// typeid(ptr) == typeid(int*) → true
```

### When decay does NOT happen:
1. `sizeof()` or `typeid()` argument
2. Taking address with `operator&`
3. Passed as a class member
4. Passed by reference

### Passing C-style arrays to functions

```cpp
// These are equivalent:
void printElementZero(const int* arr) { /* ... */ }
void printElementZero(const int arr[]) { /* ... */ } // preferred syntax

// C-style arrays are passed by ADDRESS, not by value!
```

### Problems with decay

- `sizeof()` on decayed array returns pointer size, not array size
- Loss of length information makes bounds checking difficult
- Easy to introduce undefined behavior

### Best practice: Avoid C-style arrays whenever practical.

Exceptions: global constexpr arrays and C-style string parameters in performance-critical code.

---

## 17.9 — Pointer arithmetic and subscripting

### Pointer arithmetic

```cpp
int x {};
const int* ptr{ &x };
ptr + 1  // address of NEXT int (4 bytes later for 4-byte ints)
ptr - 1  // address of PREVIOUS int
++ptr    // increment pointer to next object
```

### Subscripting = pointer arithmetic

`ptr[n]` is equivalent to `*((ptr) + (n))`. This is why:
- Arrays are 0-based (index 0 = first element)
- `ptr[-1]` is valid if ptr points past the first element

### Relative positioning

Array indices are RELATIVE positions based on the pointer:
```cpp
const int* ptr { &arr[3] };
ptr[0]  // element at index 3
ptr[1]  // element at index 4
ptr[-1] // element at index 2
```

### Traversal using pointers

```cpp
const int* begin{ arr };
const int* end{ arr + std::size(arr) };
for (; begin != end; ++begin)
    std::cout << *begin << ' ';
```

### Range-based for loops are implemented this way

Internally, range-based for loops use pointer arithmetic with begin/end pointers.

---

## 17.10 — C-style strings

### Definition

C-style strings are C-style arrays with element type `char` or `const char`:

```cpp
char str1[8]{};                    // 8 chars
const char str2[]{ "string" };     // 7 chars (6 + null terminator)
constexpr char str3[] { "hello" }; // 6 chars (5 + null terminator)
```

### The null terminator

C-style strings use a null character (`'\0'`) to mark the end. This is needed because decay loses length information.

### Input (safe approach)

```cpp
char rolls[255] {};
std::cin.getline(rolls, std::size(rolls)); // reads up to 254 chars
```

**Warning:** C++20 changed `operator>>` to only work on non-decayed C-style strings to prevent buffer overflow.

### Getting length

```cpp
std::strlen(str) // from <cstring>, traverses to find null terminator (slow)
std::size(str)   // only works on non-decayed arrays
```

### C-string manipulation functions (`<cstring>`)
- `strlen()` — get length
- `strcpy()` / `strncpy()` — copy
- `strcat()` / `strncat()` — concatenate
- `strcmp()` / `strncmp()` — compare (returns 0 if equal)

### Best practice

Avoid non-const C-style string objects — use `std::string` instead.

---

## 17.11 — C-style string symbolic constants

### Two ways to create C-style string constants

```cpp
const char name[] { "Alex" };        // case 1: array (makes a copy)
const char* const color{ "Orange" }; // case 2: pointer to string literal
```

Case 1 makes a copy of the string literal. Case 2 points directly to the literal (more efficient).

### Type deduction

```cpp
auto s1{ "Alex" };  // const char*
auto* s2{ "Alex" }; // const char*
auto& s3{ "Alex" }; // const char(&)[5]
```

### Output behavior

`std::cout` treats `char*` specially — prints the string, not the address:

```cpp
int narr[]{ 9, 7, 5, 3, 1 };
char carr[]{ "Hello!" };
std::cout << narr << '\n'; // prints address
std::cout << carr << '\n'; // prints "Hello!"
```

To print the address of a char pointer: `static_cast<const void*>(ptr)`

### Best practice

Avoid C-style string symbolic constants — use `constexpr std::string_view` instead.

---

## 17.12 — Multidimensional C-style Arrays

### Two-dimensional arrays

```cpp
int a[3][5]; // 3 rows, 5 columns
a[2][3] = 7; // row 2, column 3
```

### Initialization

```cpp
int array[3][5] {
  { 1, 2, 3, 4, 5 },      // row 0
  { 6, 7, 8, 9, 10 },     // row 1
  { 11, 12, 13, 14, 15 }  // row 2
};
```

Omitting the leftmost dimension is allowed: `int array[][5] { ... }`.

### Memory layout: Row-major order

Elements are stored row-by-row: `[0][0], [0][1], ..., [0][4], [1][0], ...`

### Traversal (row-major for efficiency)

```cpp
for (std::size_t row{0}; row < std::size(arr); ++row)
    for (std::size_t col{0}; col < std::size(arr[0]); ++col)
        std::cout << arr[row][col] << ' ';
```

### Cartesian coordinates vs Array indices

Cartesian {x, y} maps to array `[y][x]` — note the reversed order!

---

## 17.13 — Multidimensional std::array

### Two-dimensional std::array

```cpp
std::array<std::array<int, 4>, 3> arr {{ // double braces
    { 1, 2, 3, 4 },
    { 5, 6, 7, 8 },
    { 9, 10, 11, 12 }
}};
```

The syntax is verbose and dimensions are "backwards" from C-style arrays.

### Alias template for cleaner syntax

```cpp
template <typename T, std::size_t Row, std::size_t Col>
using Array2d = std::array<std::array<T, Col>, Row>;

Array2d<int, 3, 4> arr {{ /* ... */ }};
```

### Getting dimensional lengths

```cpp
template <typename T, std::size_t Row, std::size_t Col>
constexpr int rowLength(const Array2d<T, Row, Col>&) { return Row; }

template <typename T, std::size_t Row, std::size_t Col>
constexpr int colLength(const Array2d<T, Row, Col>&) { return Col; }
```

### Flattening approach

Store as 1D array (`Row * Col` elements) and provide a 2D view interface via `operator()` (or `operator[]` in C++23):

```cpp
// Map 2D coordinate (row, col) to 1D index:
arr[row * cols() + col]
```

### std::mdspan (C++23)

A standard library multidimensional view for contiguous sequences:

```cpp
std::mdspan mdView { arr.data(), 3, 4 };
mdView[row, col] // C++23 multi-argument operator[]
```

---

## 17.x — Chapter 17 summary and quiz

### Key terms:
- Fixed-size arrays vs dynamic arrays
- `std::array` aggregate initialization, CTAD
- Non-type template parameters, `size_type`
- `std::size()`, `std::ssize()`, `std::get()`
- Function templates for passing `std::array`
- Brace elision, double braces for struct arrays
- `std::reference_wrapper`, `std::ref()`, `std::cref()`
- C-style arrays, array decay, pointer arithmetic
- Null-terminated C-style strings
- Multidimensional arrays, row-major order, flattening
- `std::mdspan` (C++23)

### Quiz: Roscoe's Potion Emporium
A shopping game with potion types, inventory management, gold system, and input handling.

### Quiz: Blackjack
Implementation of a simplified Blackjack card game using `Card` struct, `Deck` class, player turns, and dealer logic.

