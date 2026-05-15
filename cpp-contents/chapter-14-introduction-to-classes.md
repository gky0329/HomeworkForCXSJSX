# Chapter 14 — Introduction to Classes

## 14.1 — Introduction to object-oriented programming

### Procedural programming

Back in lesson 1.3, we defined an object in C++ as, "a piece of memory that can be used to store values". An object with a name is called a variable. Our C++ programs have consisted of sequential lists of instructions to the computer that define data (via objects) and operations performed on that data (via functions containing statements and expressions).

Up to now, we've been doing a type of programming called procedural programming. In **procedural programming**, the focus is on creating "procedures" (which in C++ are called functions) that implement our program logic. We pass data objects to these functions, those functions perform operations on the data, and then potentially return a result to be used by the caller.

In procedural programming, the functions and the data those functions operate on are separate entities. The programmer is responsible for combining the functions and the data together to produce the desired result. This leads to code that looks like this:

```cpp
eat(you, apple);
```

### What is object-oriented programming?

In **object-oriented programming** (often abbreviated as OOP), the focus is on creating program-defined data types that contain both properties and a set of well-defined behaviors. The term "object" in OOP refers to the objects that we can instantiate from such types.

This leads to code that looks more like this:

```cpp
you.eat(apple);
```

This makes it clearer who the subject is (`you`), what behavior is being invoked (`eat()`), and what objects are accessories to that behavior (`apple`).

Because the properties and behaviors are no longer separate, objects are easier to modularize, which makes our programs easier to write and understand, and also provides a higher degree of code reusability.

### A procedural vs OOP-like example

Here's a short program written in a procedural programming style:

```cpp
enum AnimalType { cat, dog, chicken };

constexpr std::string_view animalName(AnimalType type)
{
    switch (type)
    {
    case cat: return "cat";
    case dog: return "dog";
    case chicken: return "chicken";
    default:  return "";
    }
}

constexpr int numLegs(AnimalType type)
{
    switch (type)
    {
    case cat: return 4;
    case dog: return 4;
    case chicken: return 2;
    default:  return 0;
    }
}
```

Now let's write that same program using more of an OOP mindset:

```cpp
struct Cat
{
    std::string_view name{ "cat" };
    int numLegs{ 4 };
};

struct Dog
{
    std::string_view name{ "dog" };
    int numLegs{ 4 };
};

struct Chicken
{
    std::string_view name{ "chicken" };
    int numLegs{ 2 };
};
```

OOP also brings a number of other useful concepts to the table: **inheritance**, **encapsulation**, **abstraction**, and **polymorphism**.

---

## 14.2 — Introduction to classes

### The class invariant problem

Perhaps the biggest difficulty with structs is that they do not provide an effective way to document and enforce class invariants. A **class invariant** is a condition that must be true throughout the lifetime of an object in order for the object to remain in a valid state. An object that has a violated class invariant is said to be in an **invalid state**, and unexpected or undefined behavior may result from further use of that object.

> **Key insight:** Using an object whose class invariant has been violated may result in unexpected or undefined behavior.

Consider the following struct:

```cpp
struct Fraction
{
    int numerator { 0 };
    int denominator { 1 }; // class invariant: should never be 0
};
```

We know from mathematics that a fraction with a denominator of `0` is mathematically undefined. Nothing prevents us from explicitly violating this class invariant.

### Introduction to classes

When developing C++, Bjarne Stroustrup wanted to introduce capabilities that would allow developers to create program-defined types that could be used more intuitively. He called this type a *class*.

Just like structs, a **class** is a program-defined compound type that can have many member variables with different types.

> **Key insight:** From a technical standpoint, structs and classes are almost identical -- therefore, any example that is implemented using a struct could be implemented using a class, or vice-versa. However, from a practical standpoint, we use structs and classes differently.

### Defining a class

Because a class is a program-defined data type, it must be defined before it can be used. Classes are defined similarly to structs, except we use the `class` keyword instead of `struct`:

```cpp
class Employee
{
    int m_id {};
    int m_age {};
    double m_wage {};
};
```

### Most of the C++ standard library is classes

You have already been using class objects, perhaps without knowing it. Both `std::string` and `std::string_view` are defined as classes. In fact, most of the non-aliased types in the standard library are defined as classes!

Classes are really the heart and soul of C++ -- they are so foundational that C++ was originally named "C with classes"!

---

## 14.3 — Member functions

### The separation of properties and actions

In programming, we represent properties with variables, and actions with functions. It sure would be nice if there were some way to define our properties and actions together, as a single package.

### Member functions

In addition to having member variables, class types (which includes structs, classes, and unions) can also have their own functions! Functions that belong to a class type are called **member functions**.

Functions that are not member functions are called **non-member functions** (or occasionally **free functions**) to distinguish them from member functions.

Member functions must be declared inside the class type definition, and can be defined inside or outside of the class type definition. As a reminder, a definition is also a declaration, so if we define a member function inside the class, that counts as a declaration.

### A member function example

```cpp
struct Date
{
    int year {};
    int month {};
    int day {};

    void print() // defines a member function named print
    {
        std::cout << year << '/' << month << '/' << day;
    }
};

int main()
{
    Date today { 2020, 10, 14 };
    today.day = 16;
    today.print();  // member functions accessed using member selection operator (.)
    return 0;
}
```

### Calling member functions (and the implicit object)

All (non-static) member functions must be called using an object of that class type. The object that a member function is called on is *implicitly* passed to the member function. For this reason, the object that a member function is called on is often called **the implicit object**.

In other words, when we call `today.print()`, `today` is the implicit object, and it is implicitly passed to the `print()` member function.

### Accessing members inside a member function uses the implicit object

Inside a member function, any member identifier that is not prefixed with the member selection operator (.) is associated with the implicit object.

> **Key insight:** With non-member functions, we have to explicitly pass an object to the function to work with, and members are explicitly accessed through that object. With member functions, we implicitly pass an object to the function to work with, and members are implicitly accessed through that object.

### Member variables and functions can be defined in any order

The C++ compiler normally compiles code from top to bottom. However, inside a class definition, this restriction doesn't apply: you can access member variables and member functions before they are declared. This means you can define member variables and member functions in any order you like!

### Member functions can be overloaded

Just like non-member functions, member functions can be overloaded, so long as each member function can be differentiated.

### Structs and member functions

In modern C++, it is fine for structs to have member functions. This excludes constructors, which are a special type of member function.

> **Best practice:** Member functions can be used with both structs and classes. However, structs should avoid defining constructor member functions, as doing so makes them a non-aggregate.

### Class types with no data members

> **Best practice:** If your class type has no data members, prefer using a namespace.

---

## 14.4 — Const class objects and const member functions

### Modifying the data members of const objects is disallowed

Once a const class type object has been initialized, any attempt to modify the data members of the object is disallowed, as it would violate the const-ness of the object.

```cpp
const Date today { 2020, 10, 14 }; // const
today.day += 1;        // compile error: can't modify member of const object
today.incrementDay();  // compile error: can't call member function that modifies member
```

### Const objects may not call non-const member functions

Even though `print()` does not try to modify a member variable, calling `today.print()` is still a const violation. This happens because the `print()` member function itself is not declared as const. The compiler won't let us call a non-const member function on a const object.

### Const member functions

A **const member function** is a member function that guarantees it will not modify the object or call any non-const member functions (as they may modify the object).

Making `print()` a const member function is easy -- we simply append the `const` keyword to the function prototype, after the parameter list, but before the function body:

```cpp
void print() const // now a const member function
{
    std::cout << year << '/' << month << '/' << day;
}
```

> **Key insight:** A const member function may not: modify the implicit object, call non-const member functions. A const member function may: modify objects that aren't the implicit object, call const member functions, call non-member functions.

### Const member functions may be called on non-const objects

Because const member functions can be called on both const and non-const objects, if a member function does not modify the state of the object, it should be made const.

> **Best practice:** A member function that does not (and will not ever) modify the state of the object should be made const, so that it can be called on both const and non-const objects.

### Const objects via pass by const reference

Although instantiating const local variables is one way to create const objects, a more common way to get a const object is by passing an object to a function by const reference.

### Member function const and non-const overloading

It is possible to overload a member function to have a const and non-const version of the same function. This works because the const qualifier is considered part of the function's signature, so two functions which differ only in their const-ness are considered distinct.

---

## 14.5 — Public and private members and access specifiers

### Member access

Each member of a class type has a property called an **access level** that determines who can access that member. C++ has three different access levels: *public*, *private*, and *protected*.

### The members of a struct are public by default

**Public members** are members of a class type that do not have any restrictions on how they can be accessed. Public members can be accessed by anyone (as long as they are in scope).

> **Key insight:** The members of a struct are public by default. Public members can be accessed by other members of the class type, and by the public. The term "the public" is used to refer to code that exists outside of the members of a given class type.

### The members of a class are private by default

**Private members** are members of a class type that can only be accessed by other members of the same class.

> **Key insight:** The members of a class are private by default. Private members can be accessed by other members of the class, but can not be accessed by the public. A class with private members is no longer an aggregate, and therefore can no longer use aggregate initialization.

### Naming your private member variables

In C++, it is a common convention to name private data members starting with an "m_" prefix.

> **Best practice:** Consider naming your private data members starting with an "m_" prefix to help distinguish them from the names of local variables, function parameters, and member functions.

### Setting access levels via access specifiers

We can explicitly set the access level of our members by using an **access specifier**. An access specifier sets the access level of *all members* that follow the specifier. C++ provides three access specifiers: `public:`, `private:`, and `protected:`.

### Access level summary

| Access level | Access specifier | Member access | Derived class access | Public access |
|---|---|---|---|---|
| Public | public: | yes | yes | yes |
| Protected | protected: | yes | yes | no |
| Private | private: | yes | no | no |

### Access level best practices for structs and classes

> **Best practice:** Classes should generally make member variables private (or protected), and member functions public. Structs should generally avoid using access specifiers (all members will default to public).

### Access levels work on a per-class basis

One nuance of C++ access levels is that access to members is defined on a per-class basis, not on a per-object basis. A member function can directly access the private members of ANY other object of the same class type that is in scope.

### The technical and practical difference between structs and classes

A class defaults its members to private, whereas a struct defaults its members to public. That's it.

As a rule of thumb, use a struct when all of the following are true:
- You have a simple collection of data that doesn't benefit from restricting access.
- Aggregate initialization is sufficient.
- You have no class invariants, setup needs, or cleanup needs.

Use a class otherwise.

---

## 14.6 — Access functions

### Access functions

An **access function** is a trivial public member function whose job is to retrieve or change the value of a private member variable.

Access functions come in two flavors: getters and setters. **Getters** (also sometimes called **accessors**) are public member functions that return the value of a private member variable. **Setters** (also sometimes called **mutators**) are public member functions that set the value of a private member variable.

Getters are usually made const, so they can be called on both const and non-const objects. Setters should be non-const, so they can modify the data members.

```cpp
int getYear() const { return m_year; }        // getter for year
void setYear(int year) { m_year = year; }     // setter for year
```

### Access function naming

There is no common convention for naming access functions. However, there are a few naming conventions that are more popular than others:
- Prefixed with "get" and "set"
- No prefix (e.g. `int day() const` and `void day(int day)`)
- "set" prefix only

> **Tip:** Use a "set" prefix on your setters to make it more obvious that they are changing the state of the object.

### Getters should return by value or by const lvalue reference

Getters should provide "read-only" access to data. Therefore, the best practice is that they should return by either value (if making a copy of the member is inexpensive) or by const lvalue reference (if making a copy of the member is expensive).

### Access functions concerns

- If your class has no invariants and requires a lot of access functions, consider using a struct (whose data members are public) and providing direct access to members instead.
- Prefer implementing behaviors or actions instead of access functions.
- Only provide access functions in cases where the public would reasonably need to get or set the value of an individual member.

---

## 14.7 — Member functions returning references to data members

### Returning data members by value can be expensive

While returning by value is the safest thing to do, it also means that an expensive copy will be made every time a getter is called. Since access functions tend to be called a lot, this is generally not the best choice.

### Returning data members by lvalue reference

Data members have the same lifetime as the object containing them. Since member functions are always called on an object, and that object must exist in the scope of the caller, it is generally safe for a member function to return a data member by (const) lvalue reference.

```cpp
const std::string& getName() const { return m_name; } // getter returns by const reference
```

> **Key insight:** It is okay to return a (const) lvalue reference to a data member. The implicit object (containing the data member) still exists in the scope of the caller after the function returns, so any returned references will be valid.

> **Best practice:** A member function returning a reference should return a reference of the same type as the data member being returned, to avoid unnecessary conversions.

### Rvalue implicit objects and return by reference

> **Warning:** An rvalue object is destroyed at the end of the full expression in which it is created. Any references to members of the rvalue object are left dangling at that point. A reference to a member of an rvalue object can only be safely used within the full expression where the rvalue object is created.

> **Best practice:** Prefer to use the return value of a member function that returns by reference immediately, to avoid issues with dangling references when the implicit object is an rvalue.

### Do not return non-const references to private data members

Because a reference acts just like the object being referenced, a member function that returns a non-const reference provides direct access to that member (even if the member is private).

### Const member functions can't return non-const references to data members

A const member function is not allowed to return a non-const reference to members. This makes sense -- a const member function should not be doing anything that might lead to the modification of the object.

---

## 14.8 — The benefits of data hiding (encapsulation)

### Implementation and interfaces in class types

The **interface** of a class type (also called a **class interface**) defines how a user of the class type will interact with objects of the class type. Because only public members can be accessed from outside of the class type, the public members of a class type form its interface. For this reason, an interface composed of public members is sometimes called a **public interface**.

The **implementation** of a class type consists of the code that actually makes the class behave as intended. This includes both the member variables that store data, and the bodies of the member functions that contain the program logic and manipulate the member variables.

### Data hiding

In programming, **data hiding** (also called **information hiding** or **data abstraction**) is a technique used to enforce the separation of interface and implementation by hiding (making inaccessible) the implementation of a program-defined data type from users.

The term **encapsulation** typically refers to one of two things:
- The enclosing of one or more items within a container of some kind.
- The bundling of data and functions for operating on instances of that data.

### Data hiding make classes easier to use, and reduces complexity

To use an encapsulated class, you don't need to know how it is implemented. You only need to understand its interface: what member functions are publicly available, what arguments they take, and what values they return. Not having to care about these details dramatically reduces the complexity of your programs, which in turn reduces mistakes.

### Data hiding allows us to maintain invariants

When we give users direct access to the implementation of a class, they become responsible for maintaining all invariants -- which they may not do (either correctly, or at all). Putting this burden on the user adds a lot of complexity.

### Data hiding allows us to do better error detection (and handling)

Because we're forcing the user to set members through public interface functions, we can validate inputs before assignment.

### Data hiding makes it possible to change implementation details without breaking existing programs

Data hiding gives us the ability to change how classes are implemented without breaking the programs that use them.

### Classes with interfaces are easier to debug

If a member can only be changed through a single member function, then you can simply breakpoint that single function and watch as each caller changes the value.

### Prefer non-member functions to member functions

> **Best practice:** Prefer implementing functions as non-members when possible (especially functions that contain application specific data or logic).

Here's a simplified guide on when to make a function a member vs a non-member:
- Use a member function when you have to (constructors, destructors, virtual functions, certain operators).
- Prefer a member function when the function needs access to private (or protected) data that should not be exposed.
- Prefer a non-member function otherwise (especially for functions that do not modify the state of the object).

### The order of class member declaration

> **Best practice:** Declare public members first, protected members next, and private members last. This spotlights the public interface and de-emphasizes implementation details.

---

## 14.9 — Introduction to constructors

When a class type is an aggregate, we can use aggregate initialization to initialize the class type directly:

```cpp
struct Foo // Foo is an aggregate
{
    int x {};
    int y {};
};

int main()
{
    Foo foo { 6, 7 }; // uses aggregate initialization
    return 0;
}
```

However, as soon as we make any member variables private (to hide our data), our class type is no longer an aggregate (because aggregates cannot have private members). And that means we're no longer able to use aggregate initialization.

### Constructors

A **constructor** is a special member function that is automatically called after a non-aggregate class type object is created.

When a non-aggregate class type object is defined, the compiler looks to see if it can find an accessible constructor that is a match for the initialization values provided by the caller (if any).
- If an accessible matching constructor is found, memory for the object is allocated, and then the constructor function is called.
- If no accessible matching constructor can be found, a compilation error will be generated.

> **Key insight:** Many new programmers are confused about whether constructors create the objects or not. They do not -- the compiler sets up the memory allocation for the object prior to the constructor call.

Beyond determining how an object may be created, constructors generally perform two functions:
- They typically perform initialization of any member variables (via a member initialization list)
- They may perform other setup functions (via statements in the body of the constructor)

Note that aggregates are not allowed to have constructors -- so if you add a constructor to an aggregate, it is no longer an aggregate.

### Naming constructors

- Constructors must have the same name as the class (with the same capitalization).
- Constructors have no return type (not even `void`).

Because constructors are typically part of the interface for your class, they are usually public.

### A basic constructor example

```cpp
class Foo
{
private:
    int m_x {};
    int m_y {};

public:
    Foo(int x, int y) // here's our constructor function that takes two initializers
    {
        std::cout << "Foo(" << x << ", " << y << ") constructed\n";
    }
};
```

### Constructors should not be const

A constructor needs to be able to initialize the object being constructed -- therefore, a constructor must not be const.

### Constructors vs setters

Constructors are designed to initialize an entire object at the point of instantiation. Setters are designed to assign a value to a single member of an existing object.

---

## 14.10 — Constructor member initializer lists

### Member initialization via a member initialization list

To have a constructor initialize members, we do so using a **member initializer list** (often called a "member initialization list").

```cpp
Foo(int x, int y)
    : m_x { x }, m_y { y } // here's our member initialization list
{
    std::cout << "Foo(" << x << ", " << y << ") constructed\n";
}
```

The member initializer list is defined after the constructor parameters. It begins with a colon (:), and then lists each member to initialize along with the initialization value for that variable, separated by a comma. You must use a direct form of initialization here (preferably using braces, but parentheses works as well).

### Member initializer list formatting

Our recommendation:
- Put the colon on the line after the constructor name
- Indent your member initializer list

### Member initialization order

Because the C++ standard says so, the members in a member initializer list are always initialized in the order in which they are defined inside the class (not in the order they are defined in the member initializer list).

> **Best practice:** Member variables in a member initializer list should be listed in order that they are defined in the class. It's also a good idea to avoid initializing members using the value of other members (if possible).

### Member initializer list vs default member initializers

Members can be initialized in a few different ways:
- If a member is listed in the member initializer list, that initialization value is used
- Otherwise, if the member has a default member initializer, that initialization value is used
- Otherwise, the member is default-initialized.

This means that if a member has both a default member initializer and is listed in the member initializer list for the constructor, the member initializer list value takes precedence.

### Constructor function bodies

The bodies of constructors functions are most often left empty. This is because we primarily use constructor for initialization, which is done via the member initializer list.

> **Key insight:** Once the member initializer list has finished executing, the object is considered initialized. Once the function body has finished executing, the object is considered constructed.

> **Best practice:** Prefer using the member initializer list to initialize your members over assigning values in the body of the constructor.

### Detecting and handling invalid arguments to constructors

Inside a member initializer list, our tools for detecting and handling errors are quite limited. Inside the body of the constructor, we can use statements, so we have more options. When a constructor cannot construct a semantically valid object, we say it has failed.

> **Key insight:** Throwing an exception is usually the best thing to do when a constructor fails (and cannot recover).

---

## 14.11 — Default constructors and default arguments

A **default constructor** is a constructor that accepts no arguments. Typically, this is a constructor that has been defined with no parameters.

```cpp
class Foo
{
public:
    Foo() // default constructor
    {
        std::cout << "Foo default constructed\n";
    }
};
```

### Value initialization vs default initialization for class types

If a class type has a default constructor, both value initialization and default initialization will call the default constructor.

> **Best practice:** Prefer value initialization over default initialization for all class types.

### Constructors with default arguments

As with all functions, the rightmost parameters of constructors can have default arguments. If all of the parameters in a constructor have default arguments, the constructor is a default constructor (because it can be called with no arguments).

### Overloaded constructors

Because constructors are functions, they can be overloaded. That is, we can have multiple constructors so that we can construct objects in different ways. A class should only have one default constructor.

### An implicit default constructor

If a non-aggregate class type object has no user-declared constructors, the compiler will generate a public default constructor (so that the class can be value or default initialized). This constructor is called an **implicit default constructor**.

### Using `= default` to generate an explicitly defaulted default constructor

In cases where we would write a default constructor that is equivalent to the implicitly generated default constructor, we can instead tell the compiler to generate a default constructor for us. This constructor is called an **explicitly defaulted default constructor**, and it can be generated by using the `= default` syntax:

```cpp
Foo() = default; // generates an explicitly defaulted default constructor
```

### Only create a default constructor when it makes sense

A default constructor allows us to create objects of a non-aggregate class type with no user-provided initialization values. Thus, a class should only provide a default constructor when it makes sense for objects of a class type to be created using all default values.

---

## 14.12 — Delegating constructors

Whenever possible, we want to reduce redundant code (following the DRY principle -- Don't Repeat Yourself). When a class contains multiple constructors, it's extremely common for the code in each constructor to be similar if not identical.

### Calling a constructor in the body of a function creates a temporary object

When called from the body of a function, what looks like a function call to a constructor usually creates and direct-initializes a temporary object. It does NOT delegate initialization.

> **Best practice:** Constructors should not be called directly from the body of another function. Doing so will either result in a compilation error, or will direct-initialize a temporary object.

### Delegating constructors

Constructors are allowed to delegate (transfer responsibility for) initialization to another constructor from the same class type. This process is sometimes called **constructor chaining** and such constructors are called **delegating constructors**.

To make one constructor delegate initialization to another constructor, simply call the constructor in the member initializer list:

```cpp
Employee(std::string_view name)
    : Employee{ name, 0 } // delegate initialization to Employee(std::string_view, int) constructor
{
}
```

A constructor that delegates to another constructor is not allowed to do any member initialization itself. So your constructors can delegate or initialize, but not both.

> **Best practice:** If you have multiple constructors, consider whether you can use delegating constructors to reduce duplicate code.

### Reducing constructors using default arguments

Default values can also sometimes be used to reduce multiple constructors into fewer constructors.

> **Best practice:** Members for which the user must provide initialization values should be defined first (and as the leftmost parameters of the constructor). Members for which the user can optionally provide initialization values should be defined second (and as the rightmost parameters of the constructor).

---

## 14.13 — Temporary class objects

### Temporary class objects

A **temporary object** (sometimes called an **anonymous object** or an **unnamed object**) is an object that has no name and exists only for the duration of a single expression.

There are two common ways to create temporary class type objects:

```cpp
// Case 1: Pass variable
IntPair p { 3, 4 };
print(p);

// Case 2: Construct temporary IntPair and pass to function
print(IntPair { 5, 6 } );

// Case 3: Implicitly convert { 7, 8 } to a temporary IntPair and pass to function
print( { 7, 8 } );
```

To summarize:
```cpp
IntPair p { 1, 2 }; // create named object p initialized with { 1, 2 }
IntPair { 1, 2 };   // create temporary object initialized with { 1, 2 }
{ 1, 2 };           // compiler will try to convert { 1, 2 } to temporary object matching expected type
```

### Temporary objects and return by value

When a function returns by value, the object that is returned is a temporary object (initialized using the value or object identified in the return statement).

A few notes:
- When used in an expression, a temporary class object is an rvalue. Thus, such objects can only be used where rvalue expressions are accepted.
- Temporary objects are created at the point of definition, and destroyed at the end of the full expression in which they are defined.

---

## 14.14 — Introduction to the copy constructor

### The copy constructor

A **copy constructor** is a constructor that is used to initialize an object with an existing object of the same type. After the copy constructor executes, the newly created object should be a copy of the object passed in as the initializer.

### An implicit copy constructor

If you do not provide a copy constructor for your classes, C++ will create a public **implicit copy constructor** for you. By default, the implicit copy constructor will do memberwise initialization. This means each member will be initialized using the corresponding member of the class passed in as the initializer.

### Defining your own copy constructor

```cpp
// Copy constructor
Fraction(const Fraction& fraction)
    : m_numerator{ fraction.m_numerator }
    , m_denominator{ fraction.m_denominator }
{
    std::cout << "Copy constructor called\n";
}
```

> **Best practice:** Copy constructors should have no side effects beyond copying.

### Prefer the implicit copy constructor

Unlike the implicit default constructor, which does nothing (and thus is rarely what we want), the memberwise initialization performed by the implicit copy constructor is usually exactly what we want. Therefore, in most cases, using the implicit copy constructor is perfectly fine.

> **Best practice:** Prefer the implicit copy constructor, unless you have a specific reason to create your own.

### The copy constructor's parameter must be a reference

It is a requirement that the parameter of a copy constructor be an lvalue reference or const lvalue reference. Because the copy constructor should not be modifying the parameter, using a const lvalue reference is preferred.

> **Best practice:** If you write your own copy constructor, the parameter should be a const lvalue reference.

### Pass by value and the copy constructor

When an object is passed by value, the argument is copied into the parameter. When the argument and parameter are the same class type, the copy is made by implicitly invoking the copy constructor.

### Return by value and the copy constructor

Return by value creates a temporary object (holding a copy of the return value) that is passed back to the caller. When the return type and the return value are the same class type, the temporary object is initialized by implicitly invoking the copy constructor.

### Using `= delete` to prevent copies

Occasionally we run into cases where we do not want objects of a certain class to be copyable. We can prevent this by marking the copy constructor function as deleted, using the `= delete` syntax:

```cpp
Fraction(const Fraction& fraction) = delete;
```

---

## 14.15 — Class initialization and copy elision

### Unnecessary copies

```cpp
Something s { Something { 5 } }; // first construct temporary, then copy construct s
```

Without any optimizations, this would call two constructors. This is needlessly inefficient.

### Copy elision

**Copy elision** is a compiler optimization technique that allows the compiler to remove unnecessary copying of objects. In other words, in cases where the compiler would normally call a copy constructor, the compiler is free to rewrite the code to avoid the call to the copy constructor altogether. When the compiler optimizes away a call to the copy constructor, we say the constructor has been **elided**.

Unlike other types of optimization, copy elision is exempt from the "as-if" rule. That is, copy elision is allowed to elide the copy constructor even if the copy constructor has side effects (such as printing text to the console)! This is why copy constructors should not have side effects other than copying.

### Copy elision in pass by value and return by value

The copy constructor is normally called when an argument of the same type as the parameter is passed by value or return by value is used. However, in certain cases, these copies may be elided.

### Mandatory copy elision in C++17

Prior to C++17, copy elision was strictly an optional optimization that compilers could make. In C++17, copy elision became mandatory in some cases. In these cases, copy elision will be performed automatically (even if you tell your compiler not to perform copy elision).

---

## 14.16 — Converting constructors and the explicit keyword

### User-defined conversions

When one of our types is a program-defined type, the C++ standard doesn't have specific rules that tell the compiler how to convert values to (or from) a program-defined type. Instead, the compiler will look to see if we have defined some function that it can use to perform such a conversion. Such a function is called a **user-defined conversion**.

### Converting constructors

A constructor that can be used to perform an implicit conversion is called a **converting constructor**. By default, all constructors are converting constructors.

### Only one user-defined conversion may be applied

Only one user-defined conversion may be applied to perform an implicit conversion.

### The explicit keyword

To address issues with unexpected implicit conversions, we can use the **explicit** keyword to tell the compiler that a constructor should not be used as a converting constructor.

Making a constructor `explicit` has two notable consequences:
- An explicit constructor cannot be used to do copy initialization or copy list initialization.
- An explicit constructor cannot be used to do implicit conversions (since this uses copy initialization or copy list initialization).

```cpp
explicit Dollars(int d) // now explicit
    : m_dollars{ d }
{
}
```

Explicit constructors can still be used for direct and direct list initialization:

```cpp
Dollars d1(5); // ok
Dollars d2{5}; // ok
```

### Best practices for use of `explicit`

The modern best practice is to make any constructor that will accept a single argument `explicit` by default.

The following **should not** be made explicit:
- Copy (and move) constructors (as these do not perform conversions).

The following **are typically not** made explicit:
- Default constructors with no parameters.
- Constructors that only accept multiple arguments.

The following **should usually** be made explicit:
- Constructors that take a single argument.

> **Best practice:** Make any constructor that accepts a single argument `explicit` by default. If an implicit conversion between types is both semantically equivalent and performant, you can consider making the constructor non-explicit. Do not make copy or move constructors explicit, as these do not perform conversions.

---

## 14.17 — Constexpr aggregates and classes

### Constexpr member functions

Just like non-member functions, member functions can be made constexpr via use of the `constexpr` keyword. Constexpr member functions can be evaluated at either compile-time or runtime.

```cpp
struct Pair
{
    int m_x {};
    int m_y {};

    constexpr int greater() const
    {
        return (m_x > m_y  ? m_x : m_y);
    }
};
```

### Constexpr aggregates

Since aggregates implicitly support constexpr, if we make the object constexpr, constexpr member functions can evaluate at compile-time:

```cpp
constexpr Pair p { 5, 6 };        // now constexpr
constexpr int g { p.greater() };  // p.greater() must evaluate at compile-time
```

### Constexpr class objects and constexpr constructors

In C++, a **literal type** is any type for which it might be possible to create an object within a constant expression. An object can't be constexpr unless the type qualifies as a literal type.

The definition of a literal type includes:
- Scalar types (those holding a single value, such as fundamental types and pointers)
- Reference types
- Most aggregates
- Classes that have a constexpr constructor

To make a non-aggregate class a literal type, make its constructor constexpr:

```cpp
class Pair
{
private:
    int m_x {};
    int m_y {};

public:
    constexpr Pair(int x, int y): m_x { x }, m_y { y } {} // now constexpr

    constexpr int greater() const
    {
        return (m_x > m_y  ? m_x : m_y);
    }
};
```

> **Best practice:** If you want your class to be able to be evaluated at compile-time, make your member functions and constructor constexpr.

### Constexpr member functions may be const or non-const (C++14)

In C++11, non-static constexpr member functions are implicitly const (except constructors). However, as of C++14, constexpr member functions are no longer implicitly const.

---

## 14.x — Chapter 14 summary and quiz

### Chapter Review

In **procedural programming**, the focus is on creating "procedures" (which in C++ are called functions) that implement our program logic.

With **Object-oriented programming** (often abbreviated as OOP), the focus is on creating program-defined data types that contain both properties and a set of well-defined behaviors.

A **class invariant** is a condition that must be true throughout the lifetime of an object in order for the object to remain in a valid state. An object that has a violated class invariant is said to be in an **invalid state**.

A **class** is a program-defined compound type that bundles both data and functions that work on that data.

Functions that belong to a class type are called **member functions**. The object that a member function is called on is often called the **implicit object**.

A **const member function** is a member function that guarantees it will not modify the object or call any non-const member functions.

**Public members** are members of a class type that do not have any restrictions on how they can be accessed. By default, all members of a struct are public members.

**Private members** are members of a class type that can only be accessed by other members of the same class. By default, the members of a class are private.

We can explicitly set the access level of our members by using an **access specifier**.

An **access function** is a trivial public member function whose job is to retrieve or change the value of a private member variable. **Getters** return the value; **Setters** set the value.

The **interface** of a class type defines how a user of the class type will interact with objects. The **implementation** consists of the code that actually makes the class behave as intended.

**Data hiding** is a technique used to enforce the separation of interface and implementation by hiding the implementation from users.

A **constructor** is a special member function that is used to initialize class type objects. A **member initializer list** allows you to initialize your member variables from within a constructor.

A constructor that takes no parameters (or has all default parameters) is called a **default constructor**. If a non-aggregate class type object has no user-declared constructors, the compiler will generate an **implicit default constructor**.

Constructors are allowed to delegate initialization to another constructor. This is called **constructor chaining** and such constructors are called **delegating constructors**.

A **temporary object** is an object that has no name and exists only for the duration of a single expression.

A **copy constructor** is a constructor that is used to initialize an object with an existing object of the same type. **Copy elision** is a compiler optimization technique that allows the compiler to remove unnecessary copying of objects.

A **user-defined conversion** is a function we've written to convert a value to or from a program-defined type. A **converting constructor** can be used to perform an implicit conversion. By default, all constructors are converting constructors. The **explicit** keyword tells the compiler that a constructor should not be used as a converting constructor.

### Quiz

**Question #1**

a) Write a class named `Point2d`:

```cpp
class Point2d
{
private:
    double m_x{ 0.0 };
    double m_y{ 0.0 };

public:
    Point2d() = default;

    Point2d(double x, double y)
        : m_x{ x }, m_y{ y }
    {
    }

    void print() const
    {
        std::cout << "Point2d(" << m_x << ", " << m_y << ")\n";
    }
};
```

b) Add a member function named `distanceTo()`:

```cpp
double distanceTo(const Point2d& other) const
{
    return std::sqrt(
        (m_x - other.m_x)*(m_x - other.m_x) +
        (m_y - other.m_y)*(m_y - other.m_y)
    );
}
```

**Question #2**

Convert `Fraction` from a struct to a class:

```cpp
class Fraction
{
private:
    int m_numerator{ 0 };
    int m_denominator{ 1 };

public:
    explicit Fraction(int numerator=0, int denominator=1)
        : m_numerator { numerator }, m_denominator { denominator}
    {
    }

    void getFraction()
    {
        std::cout << "Enter a value for numerator: ";
        std::cin >> m_numerator;
        std::cout << "Enter a value for denominator: ";
        std::cin >> m_denominator;
        std::cout << '\n';
    }

    Fraction multiply(const Fraction& f) const
    {
        return Fraction{ m_numerator * f.m_numerator, m_denominator * f.m_denominator };
    }

    void printFraction() const
    {
        std::cout << m_numerator << '/' << m_denominator << '\n';
    }
};
```

**Question #3**

Why was the Fraction constructor made `explicit`? Making the constructor explicit prevents it from being used to create a `Fraction` via an implicit conversion with a single value. This helps prevent nonsense like `f1.multiply(true)`.

**Question #4**

Why might it be better to leave `getFraction()` and `print()` as non-members? With the non-member version, we can define and initialize in a single step. It also removes the function from the interface of the class, making the core functionality less cluttered.
