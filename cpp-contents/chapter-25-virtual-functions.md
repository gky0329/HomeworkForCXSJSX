# Chapter 25 — Virtual Functions

## 25.1 — Pointers and references to the base class of derived objects

C++ allows us to set Base pointers and references to Derived objects:

```cpp
Derived derived{ 5 };
Base& rBase{ derived };  // legal
Base* pBase{ &derived }; // legal
```

However, because rBase and pBase are a Base reference and pointer, they can only see members of Base. They call `Base::getName()`, not `Derived::getName()`.

**Use for pointers and references to base classes**:
- Write one function that works with all classes derived from a base class
- Store different derived types in a single array of base class pointers

The problem is that the base pointer/reference calls the base version of the function rather than the derived version. This is where virtual functions come in.

## 25.2 — Virtual functions and polymorphism

A **virtual function** is a special type of member function that, when called, resolves to the most-derived version of the function for the actual type of the object being referenced or pointed to.

A derived function is considered a match if it has the same signature (name, parameter types, and whether it is const) and return type as the base version. Such functions are called **overrides**.

To make a function virtual, place the "virtual" keyword before the function declaration:

```cpp
class Base
{
public:
    virtual std::string_view getName() const { return "Base"; }
};

class Derived: public Base
{
public:
    virtual std::string_view getName() const { return "Derived"; }
};
```

**Key insight**: Virtual function resolution only works when a member function is called through a pointer or reference to a class type object.

**Polymorphism**

- **Compile-time polymorphism**: Resolved by the compiler (function overload resolution, template resolution)
- **Runtime polymorphism**: Resolved at runtime (virtual function resolution)

**Rule**: If a function is virtual, all matching overrides in derived classes are implicitly virtual.

**Return types of virtual functions**: Under normal circumstances, the return type of a virtual function and its override must match.

**Do not call virtual functions from constructors or destructors**: The derived portion of the class hasn't been created yet (or has already been destroyed), so it would call the base version instead.

**The downside of virtual functions**: 
- Resolving a virtual function call takes longer than resolving a regular one
- Each object of a class with virtual functions gets an extra pointer (vptr), increasing object size

## 25.3 — The override and final specifiers, and covariant return types

**The override specifier**: Placed at the end of a member function declaration to tell the compiler to enforce that the function is an override.

```cpp
std::string_view getName1(short x) override { return "B"; } // compile error if not an actual override
std::string_view getName3(int x) override { return "B"; }    // okay
```

**Best practice**: Use the virtual keyword on virtual functions in a base class. Use the override specifier (but not the virtual keyword) on override functions in derived classes.

**Rule**: If a member function is both `const` and an `override`, the `const` must be listed first.

**The final specifier**: Prevents overriding a virtual function or inheriting from a class:

```cpp
// Prevent function override
std::string_view getName() const override final { return "B"; }

// Prevent class inheritance
class B final : public A { ... };
```

**Covariant return types**: If the return type of a virtual function is a pointer or a reference to some class, override functions can return a pointer or a reference to a derived class:

```cpp
class Base {
public:
    virtual Base* getThis() { return this; }
};
class Derived : public Base {
public:
    Derived* getThis() override { return this; } // covariant return type
};
```

## 25.4 — Virtual destructors, virtual assignment, and overriding virtualization

**Virtual destructors**: You should *always* make your destructors virtual if you're dealing with inheritance.

```cpp
class Base
{
public:
    virtual ~Base() // note: virtual
    {
        std::cout << "Calling ~Base()\n";
    }
};
```

**Rule**: Whenever you are dealing with inheritance, you should make any explicit destructors virtual.

You can define an empty virtual destructor as: `virtual ~Base() = default;`

**Ignoring virtualization**: Use the scope resolution operator to call a specific version:

```cpp
std::cout << base.Base::getName() << '\n';
```

**Recommendations**:
- If you intend your class to be inherited from, make sure your destructor is virtual and public
- If you do not intend your class to be inherited from, mark your class as `final`

## 25.5 — Early binding and late binding

**Binding** is the process of associating names with properties. **Function binding** determines what function definition is associated with a function call.

**Early binding** (static binding): The compiler can determine which function definition should be matched to the call at compile-time. Used for direct function calls to non-member or non-virtual member functions.

**Late binding** (dynamic dispatch): The function call can't be resolved until runtime. In C++, one way to get late binding is to use function pointers. Virtual functions use a form of late binding.

Late binding is slightly less efficient since it involves an extra level of indirection, but it's more flexible because decisions about what function to call don't need to be made until runtime.

## 25.6 — The virtual table

C++ implementations typically implement virtual functions using a form of late binding known as the **virtual table** (vtable).

The **virtual table** is a lookup table of functions used to resolve function calls in a dynamic/late binding manner.

How it works:
1. Every class that uses virtual functions has a corresponding virtual table (a static array set up at compile time)
2. Each entry in this table is a function pointer that points to the most-derived function accessible by that class
3. The compiler adds a hidden pointer member (`*__vptr`) to the base class
4. When a class object is created, `*__vptr` is set to point to the virtual table for that class

When a virtual function is called through a base pointer:
1. The program uses `dPtr->__vptr` to get to the virtual table
2. It looks up which version of the function to call
3. It calls that function

Calling a virtual function is slower because: we have to use `*__vptr` to get to the virtual table, index the virtual table to find the correct function, then call the function (3 operations vs 1 for a direct call).

## 25.7 — Pure virtual functions, abstract base classes, and interface classes

**Pure virtual (abstract) functions** have no body -- they act as a placeholder meant to be redefined by derived classes:

```cpp
virtual int getValue() const = 0; // a pure virtual function
```

When you add a pure virtual function to a class, the class becomes an **abstract base class** and can not be instantiated. Any derived class must define a body for this function, or that derived class will also be abstract.

A pure virtual function is useful when you want to put a function in the base class, but only the derived classes know what it should return.

**Pure virtual functions with definitions**: You can create pure virtual functions that have definitions (the definition must be provided separately, not inline). This is useful when you want your base class to provide a default implementation, but still force derived classes to provide their own.

**Interface classes**: A class that has no member variables, and where *all* of the functions are pure virtual. Interface classes are often named beginning with an I.

```cpp
class IErrorLog
{
public:
    virtual bool openLog(std::string_view filename) = 0;
    virtual bool closeLog() = 0;
    virtual bool writeError(std::string_view errorMessage) = 0;
    virtual ~IErrorLog() {}
};
```

Interface classes are extremely popular because they are easy to use, easy to extend, and easy to maintain.

**A reminder**: Any class with pure virtual functions should also have a virtual destructor.

## 25.8 — Virtual base classes

**The diamond problem**: When a class multiply inherits from two classes which each inherit from a single base class, you get two copies of the base class.

**Virtual base classes**: To share a base class, insert the "virtual" keyword in the inheritance list:

```cpp
class Scanner: virtual public PoweredDevice { };
class Printer: virtual public PoweredDevice { };
class Copier: public Scanner, public Printer { };
```

Now, Copier will have only one copy of PoweredDevice that is shared by both Scanner and Printer.

Key details:
- The most derived class is responsible for constructing the virtual base class
- Virtual base classes are always created before non-virtual base classes
- All classes inheriting a virtual base class will have a virtual table

## 25.9 — Object slicing

When we assign a Derived object to a Base object, only the Base portion of the Derived object is copied. The Derived portion is "sliced off". This is called **object slicing**.

```cpp
Derived derived{ 5 };
Base base{ derived }; // slicing! Only the Base portion is copied
```

**Slicing and functions**: Slicing often occurs accidentally when function parameters are passed by value instead of by reference.

**Slicing vectors**: A `std::vector<Base>` will slice any Derived objects added to it. Solution: use a vector of pointers (`std::vector<Base*>`) or `std::reference_wrapper`.

**The Frankenobject**: Assigning a Derived to a Base reference can create an object composed of parts of multiple objects.

**Conclusion**: Make sure your function parameters are references (or pointers) and avoid pass-by-value when it comes to derived classes.

## 25.10 — Dynamic casting

**dynamic_cast** is used for converting base-class pointers into derived-class pointers (downcasting):

```cpp
Derived* d{ dynamic_cast<Derived*>(b) };
if (d) // always check for null
    std::cout << d->getName() << '\n';
```

**Rule**: Always ensure your dynamic casts actually succeeded by checking for a null pointer result.

**dynamic_cast and references**: If the dynamic_cast of a reference fails, an exception of type `std::bad_cast` is thrown.

**Downcasting with static_cast**: static_cast does no runtime type checking, making it faster but more dangerous.

**dynamic_cast vs static_cast**: Use static_cast unless you're downcasting, in which case dynamic_cast is usually a better choice.

**A warning about RTTI**: dynamic_cast leverages Run-time Type Information (RTTI). Some compilers allow turning RTTI off as an optimization, which will break dynamic_cast.

Dynamic_cast does not work with: protected/private inheritance, classes without virtual functions, and certain cases involving virtual base classes.

## 25.11 — Printing inherited classes using operator<<

The challenge: operator<< is typically a friend function, and friends can't be virtualized.

**Solution**: Have operator<< call a normal virtual member function:

```cpp
class Base
{
public:
    friend std::ostream& operator<<(std::ostream& out, const Base& b)
    {
        return b.print(out); // delegate to virtual member function
    }
    virtual std::ostream& print(std::ostream& out) const
    {
        out << "Base";
        return out;
    }
};

class Derived : public Base
{
public:
    std::ostream& print(std::ostream& out) const override
    {
        out << "Derived";
        return out;
    }
};
```

This approach:
1. Works for all derived classes without needing operator<< for each one
2. Gives the print() function access to the stream object
3. Allows printing complex member variables that have their own operator<< overloads

## 25.x — Chapter 25 summary and quiz

**Key summary**:
- Base class pointers and references can be set to derived objects
- Virtual functions resolve to the most-derived version of the function
- Use the override specifier to ensure functions are actually overrides
- Use the final specifier to prevent overrides or inheritance
- Make destructors virtual when using inheritance
- Early binding = compile-time; Late binding = runtime (via function pointers or virtual functions)
- Virtual functions use a virtual table (vtable) for dynamic dispatch
- Pure virtual functions (`= 0`) create abstract base classes that can't be instantiated
- Interface classes have no member variables and all pure virtual functions
- Virtual base classes solve the diamond problem in multiple inheritance
- Object slicing occurs when assigning a derived object to a base object by value
- dynamic_cast is used for safe downcasting
- Override operator<< by delegating to a virtual member function
