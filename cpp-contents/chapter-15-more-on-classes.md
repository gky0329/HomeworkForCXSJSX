# Chapter 15 — More on Classes

## 15.1 — The hidden "this" pointer and member function chaining

### The hidden `this` pointer

Inside every member function, the keyword **this** is a const pointer that holds the address of the current implicit object.

```cpp
#include <iostream>

class Simple
{
private:
    int m_id{};

public:
    Simple(int id) : m_id{ id } { }

    int getID() const { return m_id; }
    void setID(int id) { m_id = id; }
    void print() const { std::cout << this->m_id; } // explicit use of this
};
```

When compiled, `simple.setID(2)` is rewritten as `Simple::setID(&simple, 2)`. The function definition is rewritten to include a hidden `this` parameter:
```cpp
static void setID(Simple* const this, int id) { this->m_id = id; }
```

### Returning `*this` (Member function chaining)

Have member functions return `*this` by reference to enable chaining:

```cpp
class Calc
{
private:
    int m_value{};
public:
    Calc& add(int value) { m_value += value; return *this; }
    Calc& sub(int value) { m_value -= value; return *this; }
    Calc& mult(int value) { m_value *= value; return *this; }
    int getValue() const { return m_value; }
};

int main()
{
    Calc calc{};
    calc.add(5).sub(3).mult(4); // chaining
}
```

### Resetting a class back to default state

```cpp
void reset()
{
    *this = {}; // value initialize a new object and overwrite the implicit object
}
```

### `this` and const objects

- For non-const member functions: `this` is a const pointer to a non-const value
- For const member functions: `this` is a const pointer to a const value

---

## 15.2 — Classes and header files

### Separating declaration from implementation

Member functions can be defined outside the class definition:

```cpp
class Date
{
private:
    int m_year{}, m_month{}, m_day{};
public:
    Date(int year, int month, int day); // declaration
    void print() const;                 // declaration
    int getYear() const { return m_year; }
};

Date::Date(int year, int month, int day) // definition outside
    : m_year{ year }, m_month{ month }, m_day{ day } { }

void Date::print() const { /* ... */ }
```

### Header files for classes

- Put class definitions in a header file with the same name as the class
- Trivial member functions can be defined inside the class definition
- Non-trivial member functions should be defined in a source file with the same name as the class

### Inline member functions

- Functions defined inside the class definition are implicitly inline
- Functions defined outside can be made inline using the `inline` keyword
- Template member functions defined outside the class are almost always defined in the header file

### Default arguments

Always put default arguments for member functions inside the class definition.

---

## 15.3 — Nested types (member types)

Class types support nested types (also called member types). Define the type inside the class:

```cpp
class Fruit
{
public:
    enum Type { apple, banana, cherry };
private:
    Type m_type {};
public:
    Fruit(Type type) : m_type { type } { }
    Type getType() { return m_type; }
    bool isCherry() { return m_type == cherry; } // no Fruit:: prefix needed inside
};

int main()
{
    Fruit apple { Fruit::apple }; // Fruit:: prefix needed outside
}
```

### Nested typedefs and type aliases

```cpp
class Employee
{
public:
    using IDType = int;
private:
    IDType m_id{};
public:
    IDType getId() { return m_id; }
};

Employee::IDType id { john.getId() }; // fully qualified name outside class
```

### Nested classes

A nested class does not have access to the `this` pointer of the outer class, but can access private members of the outer class that are in scope.

### Best practice

Define any nested types at the top of your class type.

---

## 15.4 — Introduction to destructors

### The cleanup problem

Classes that use resources (memory, files, database connections, network) often need cleanup before destruction.

### Destructors

A **destructor** is a special member function called automatically when an object is destroyed.

Naming rules:
1. Same name as the class, preceded by a tilde (~)
2. Cannot take arguments
3. Has no return type
4. A class can only have a single destructor

```cpp
class Simple
{
private:
    int m_id {};
public:
    Simple(int id) : m_id { id } {
        std::cout << "Constructing Simple " << m_id << '\n';
    }
    ~Simple() { // destructor
        std::cout << "Destructing Simple " << m_id << '\n';
    }
};
```

### Implicit destructor

If a non-aggregate class has no user-declared destructor, the compiler generates an implicit destructor with an empty body.

### Warning about `std::exit()`

When the program terminates immediately via `std::exit()`, local variables are not destroyed and destructors are not called.

---

## 15.5 — Class templates with member functions

### Type template parameters in member functions

```cpp
template <typename T>
class Pair
{
private:
    T m_first{}, m_second{};
public:
    Pair(const T& first, const T& second)
        : m_first{ first }, m_second{ second } { }
    bool isEqual(const Pair<T>& pair);
};

// Member function defined outside the class
template <typename T>
bool Pair<T>::isEqual(const Pair<T>& pair)
{
    return m_first == pair.m_first && m_second == pair.m_second;
}
```

### Injected class names

Within the scope of a class template, the unqualified name of the class serves as shorthand for the fully templated name.

### Where to define member functions

Any member function templates defined outside the class definition should be defined just below the class definition (in the same file/header).

---

## 15.6 — Static member variables

**Static member variables** are shared by all objects of the class. They exist even if no objects have been instantiated.

```cpp
struct Something
{
    static int s_value; // declare
};
int Something::s_value{ 1 }; // define and initialize

int main()
{
    Something::s_value = 2; // access via class name (preferred)
}
```

### Inline static members (C++17)

```cpp
class Whatever
{
public:
    static inline int s_value{ 4 }; // can be initialized inside class
    static constexpr double s_d{ 2.2 }; // constexpr members are implicitly inline
};
```

### Use case: unique ID generator

```cpp
class Something
{
private:
    static inline int s_idGenerator { 1 };
    int m_id {};
public:
    Something() : m_id { s_idGenerator++ } { }
    int getID() const { return m_id; }
};
```

### Type deduction

Only static members may use `auto` and CTAD. Non-static members may not.

---

## 15.7 — Static member functions

Static member functions can be called without an object, using the class name and scope resolution operator.

```cpp
class Something
{
private:
    static inline int s_value { 1 };
public:
    static int getValue() { return s_value; }
};

int main()
{
    std::cout << Something::getValue() << '\n';
}
```

### Key properties

- Static member functions have no `this` pointer
- Can directly access other static members, but not non-static members

### Pure static classes vs namespaces

A static class is preferable when you have static data members and/or need access controls. Otherwise, prefer a namespace.

---

## 15.8 — Friend non-member functions

A **friend function** is a function (member or non-member) that can access the private and protected members of a class.

```cpp
class Accumulator
{
private:
    int m_value { 0 };
public:
    void add(int value) { m_value += value; }
    friend void print(const Accumulator& accumulator);
};

void print(const Accumulator& accumulator)
{
    std::cout << accumulator.m_value; // friend access
}
```

### Best practices

- A friend function should prefer to use the class interface over direct access whenever possible
- Prefer non-friend functions to friend functions
- Prefer to implement a function as a non-friend when possible and reasonable

---

## 15.9 — Friend classes and friend member functions

### Friend classes

A **friend class** is a class that can access the private and protected members of another class.

```cpp
class Storage
{
private:
    int m_nValue {};
    double m_dValue {};
public:
    friend class Display; // Display is now a friend
};
```

Friendship is not reciprocal, not transitive, and not inherited.

### Friend member functions

To make a single member function a friend, the compiler must have seen the full definition of that member function's class.

The typical pattern requires:
1. Forward declaration of the class being accessed
2. Full definition of the class containing the friend function
3. Full definition of the class granting friendship
4. Definition of the friend member function

---

## 15.10 — Ref qualifiers

C++11 introduced ref-qualifiers to overload member functions based on whether the implicit object is an lvalue or rvalue:

```cpp
const std::string& getName() const &  { return m_name; } // lvalue implicit objects
std::string        getName() const && { return m_name; } // rvalue implicit objects
```

This allows returning by reference for lvalues (efficient) and by value for rvalues (safe).

**Note:** Most C++ developers are not aware of this feature, and the standard library typically does not use it. The recommendation is to always use access function results immediately rather than saving returned references.

---

## 15.x — Chapter 15 summary and quiz

### Key terms reviewed:
- **this** pointer: const pointer holding address of current implicit object
- **Method chaining**: functions returning `*this` by reference
- **Nested types (member types)**: types defined inside a class
- **Destructor**: special member function called on object destruction
- **Static member variables**: shared by all objects, exist independently
- **Static member functions**: no `this` pointer, can only access static members
- **Friend**: class/function granted full access to private/protected members

### Quiz: Random Monster Generator

Create a `Monster` class with nested `Type` enum, a `MonsterGenerator` namespace, and randomized monster generation using `Random.h`.

