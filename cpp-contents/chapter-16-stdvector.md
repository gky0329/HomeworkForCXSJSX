# Chapter 16 — Dynamic Arrays: std::vector

## 16.1 — Introduction to containers and arrays

### The variable scalability challenge

When you need many variables of the same type, defining individual variables doesn't scale. A **container** is a data type that provides storage for a collection of unnamed objects (called **elements**). 

### Containers

The elements of a container are unnamed, so the container can have as many elements as needed without giving each a unique name. Each container provides methods to access its elements.

### Arrays

An **array** is a container data type that stores elements **contiguously** in memory. C++ has three primary array types:
- C-style arrays (inherited from C)
- `std::vector` container class (C++03)
- `std::array` container class (C++11)

---

## 16.2 — Introduction to std::vector and list constructors

### Creating a std::vector

```cpp
#include <vector>

std::vector<int> empty{};                          // empty vector
std::vector<int> primes{ 2, 3, 5, 7 };             // list construction
std::vector vowels { 'a', 'e', 'i', 'o', 'u' };    // CTAD (C++17)
```

### List constructors

Containers have a special **list constructor** that constructs from an initializer list. It:
- Ensures enough storage for all values
- Sets length to the number of initializers
- Initializes elements to the values in order

### Accessing elements with operator[]

```cpp
std::vector primes { 2, 3, 5, 7, 11 };
std::cout << primes[0] << '\n'; // first element (index 0)
```

Arrays are **zero-based** — index 0 is the first element. `operator[]` does NOT do bounds checking.

### Creating a vector of specific length

```cpp
std::vector<int> data(10); // 10 elements, value-initialized to 0
```

**Important distinction:**
- `std::vector<int> v1 { 5 };` → 1 element with value 5 (list constructor)
- `std::vector<int> v2(5);` → 5 elements value-initialized to 0 (explicit size constructor)

Non-empty initializer lists prefer list constructors. Use direct initialization when constructing with a size argument.

---

## 16.3 — std::vector and the unsigned length and subscript problem

### The container length sign problem

Standard library containers use unsigned types for lengths and indices (usually `std::size_t`). This was a design mistake but we're stuck with it.

### size_type

Each container class defines a nested typedef `size_type`, almost always an alias for `std::size_t`.

### Getting the length

```cpp
prime.size()       // member function, returns size_type
std::size(prime)   // C++17 non-member function
std::ssize(prime)  // C++20, returns signed type (usually ptrdiff_t)
```

### Accessing elements

```cpp
prime[3]           // operator[], no bounds checking
prime.at(3)        // at(), runtime bounds checking (throws exception)
prime.data()[3]    // index underlying C-style array (avoids sign issues)
```

### Indexing with constexpr vs non-constexpr

- constexpr signed index → implicit conversion to size_t is NOT narrowing (safe)
- non-constexpr signed index → conversion IS narrowing (warning/error)

---

## 16.4 — Passing std::vector

Pass `std::vector` by (const) reference to avoid expensive copies:

```cpp
void passByRef(const std::vector<int>& arr) { /* ... */ }
```

### Using function templates for different element types

```cpp
template <typename T>
void passByRef(const std::vector<T>& arr) { /* ... */ }
```

Or use a generic template:
```cpp
template <typename T>
void passByRef(const T& arr) { /* ... */ } // accepts any type with operator[]

// C++20 abbreviated function template:
void passByRef(const auto& arr) { /* ... */ }
```

Assert on array length at runtime using `assert()`.

---

## 16.5 — Returning std::vector, and an introduction to move semantics

### Copy semantics vs Move semantics

- **Copy semantics**: rules for making copies of objects
- **Move semantics**: optimization that transfers ownership of data instead of copying

Move semantics is invoked when:
1. The type supports move semantics
2. Initializing/assigning from an rvalue of the same type
3. The move isn't elided

### Return by value is OK for move-capable types

`std::vector` and `std::string` support move semantics. Return them by value — they'll be moved (inexpensive) rather than copied.

**Key rule:** Pass move-capable types by const reference, return them by value.

---

## 16.6 — Arrays and loops

### Traversal with for-loops

```cpp
std::vector testScore { 84, 92, 76, 81, 56 };
int average { 0 };
for (std::size_t index{ 0 }; index < testScore.size(); ++index)
    average += testScore[index];
average /= static_cast<int>(testScore.size());
```

### Function template for average

```cpp
template <typename T>
T calculateAverage(const std::vector<T>& arr)
{
    T average { 0 };
    for (std::size_t index{ 0 }; index < arr.size(); ++index)
        average += arr[index];
    average /= static_cast<int>(arr.size());
    return average;
}
```

### Common traversal tasks
1. Calculate new value based on elements
2. Search for an element
3. Operate on each element
4. Reorder elements

### Off-by-one errors
Use `index < length`, NOT `index <= length` — the last valid index is `length - 1`.

---

## 16.7 — Arrays, loops, and sign challenge solutions

### The problem: unsigned loop variables

```cpp
for (std::size_t index{ arr.size() - 1 }; index >= 0; --index) // NEVER terminates!
```

`index >= 0` is always true for unsigned types. When `index` is 0 and decremented, it wraps to a huge value.

### Solutions (from worst to best):

1. **Leave sign conversion warnings off** — simple but not recommended
2. **Use unsigned loop variable** — use `std::size_t` directly
3. **Use signed loop variable** — with `static_cast` for indices
4. **Use `std::ssize()` (C++20)** — returns signed length
5. **Use `data()` member** — index the underlying C-style array (no sign issues)
6. **Avoid indexing altogether** — use range-based for loops or iterators

### Best practice: Avoid array indexing with integral values whenever possible.

---

## 16.8 — Range-based for loops (for-each)

### Syntax

```cpp
for (element_declaration : array_object)
    statement;
```

### Examples

```cpp
std::vector fibonacci { 0, 1, 1, 2, 3, 5, 8 };

for (auto num : fibonacci)           // copy (cheap types)
    std::cout << num << ' ';

for (const auto& word : words)       // const reference (expensive types)
    std::cout << word << ' ';

for (auto& element : arr)            // non-const reference (modify elements)
    element *= 2;
```

### Best practices:
- `auto` when modifying copies
- `auto&` when modifying originals
- `const auto&` otherwise (most future-proof)

### Reverse iteration (C++20)

```cpp
for (const auto& word : std::views::reverse(words))
    std::cout << word << ' ';
```

---

## 16.9 — Array indexing and length using enumerators

### Using unscoped enumerators for indexing

```cpp
namespace Students
{
    enum Names { kenny, kyle, stan, butters, cartman, max_students };
}

std::vector testScores { 78, 94, 66, 77, 14 };
testScores[Students::stan] = 76; // meaningful index
```

### Count enumerator

The `max_students` enumerator automatically equals the count of preceding enumerators. Use it for array length and assertions:

```cpp
std::vector<int> testScores(Students::max_students);
assert(std::size(testScores) == max_students);
```

### Enum classes and indexing

Enum classes don't implicitly convert to integral types. Use `static_cast` or overload unary `operator+`:

```cpp
constexpr auto operator+(StudentNames a) noexcept {
    return static_cast<std::underlying_type_t<StudentNames>>(a);
}
testScores[+StudentNames::stan] = 76;
```

---

## 16.10 — std::vector resizing and capacity

### Fixed-size vs dynamic arrays

- **Fixed-size arrays**: length known at instantiation, cannot change (`std::array`, C-style arrays)
- **Dynamic arrays**: can be resized after instantiation (`std::vector`)

### Length vs Capacity

- **Length** (size): how many elements are in active use
- **Capacity**: how many elements have storage allocated

```cpp
v.size()      // returns length
v.capacity()  // returns capacity
```

### Resizing

```cpp
v.resize(5);  // changes length (and capacity if needed)
v.resize(3);  // can shrink length, but capacity usually stays
```

### reserve()

```cpp
v.reserve(6); // changes ONLY capacity (not length)
```

### Reallocation

When capacity is insufficient, the vector must reallocate (acquire new memory, copy/move elements, free old memory). This is expensive — avoid unnecessary reallocations.

### shrink_to_fit()

Requests that capacity be reduced to match length. This request is non-binding.

### Key: Valid indices are based on length, NOT capacity.

---

## 16.11 — std::vector and stack behavior

### Stack (LIFO) operations

```cpp
v.push_back(1);     // push element onto stack (increments length)
v.pop_back();       // pop element off stack (decrements length)
v.back();           // get top element (does not remove)
v.emplace_back(args); // construct element in-place (more efficient)
```

### push_back vs emplace_back

- `push_back()`: pass an existing object or temporary
- `emplace_back()`: pass constructor arguments, object constructed directly in vector (avoids copy)
- `push_back()` won't use explicit constructors; `emplace_back()` will

**Best practice:** Prefer `emplace_back()` when creating new temporaries; prefer `push_back()` otherwise.

### reserve() for stack usage

Use `reserve()` (not `resize()`) when using stack operations to pre-allocate capacity without changing length.

---

## 16.12 — std::vector\<bool\>

`std::vector<bool>` is a specialized version that compacts 8 Boolean values into a byte for space efficiency. However:

- It is NOT a proper container (not contiguous, doesn't hold `bool` values)
- Not fully compatible with the rest of the standard library
- High overhead for small numbers of values

### Recommendations:
- Use `constexpr std::bitset` for compile-time known sizes
- Use `std::vector<char>` for resizable Boolean containers
- Use `boost::dynamic_bitset` for dynamic bitset operations

**Best practice:** Avoid `std::vector<bool>`.

---

## 16.x — Chapter 16 summary and quiz

### Key terms:
- Container, elements, length, homogeneous
- List constructor, subscript operator, zero-based indexing
- `size_type`, `std::size()`, `std::ssize()`
- Copy semantics, move semantics
- Range-based for loops, traversal, iteration
- Fixed-size vs dynamic arrays
- Length vs capacity, reallocation, `reserve()`
- Stack (LIFO), `push_back()`, `pop_back()`, `emplace_back()`

### Quiz: C++man (Hangman game)
Complete implementation of a Hangman variant using `std::vector`, `std::string_view`, enums, and the `Random.h` header for random word selection.

