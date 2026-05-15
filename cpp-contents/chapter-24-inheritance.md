# Chapter 24 — Inheritance

## 24.1 — Introduction to inheritance

In the last chapter, we discussed object composition, where complex classes are constructed from simpler classes and types. Object composition is perfect for building new objects that have a "has-a" relationship with their parts. However, object composition is just one of the two major ways that C++ lets you construct complex classes. The second way is through inheritance, which models an "is-a" relationship between two objects.

Unlike object composition, which involves creating new objects by combining and connecting other objects, inheritance involves creating new objects by directly acquiring the attributes and behaviors of other objects and then extending or specializing them.

Consider apples and bananas. Although apples and bananas are different fruits, both have in common that they *are* fruits. And because apples and bananas are fruits, simple logic tells us that anything that is true of fruits is also true of apples and bananas.

**Hierarchies**

A hierarchy is a diagram that shows how various objects are related. Most hierarchies either show a progression over time, or categorize things in a way that moves from general to specific.

## 24.2 — Basic inheritance in C++

Inheritance in C++ takes place between classes. In an inheritance (is-a) relationship, the class being inherited from is called the **parent class**, **base class**, or **superclass**, and the class doing the inheriting is called the **child class**, **derived class**, or **subclass**.

A child class inherits both behaviors (member functions) and properties (member variables) from the parent (subject to some access restrictions).

Because child classes are full-fledged classes, they can have their own members that are specific to that class.

**Making a derived class**

To have a class inherit from another, the syntax is:

```cpp
class BaseballPlayer : public Person
{
public:
    double m_battingAverage{};
    int m_homeRuns{};

    BaseballPlayer(double battingAverage = 0.0, int homeRuns = 0)
       : m_battingAverage{battingAverage}, m_homeRuns{homeRuns}
    {
    }
};
```

When BaseballPlayer inherits from Person, BaseballPlayer acquires the member functions and variables from Person. Additionally, BaseballPlayer defines two members of its own.

**Inheritance chains**

It's possible to inherit from a class that is itself derived from another class:

```cpp
class Supervisor: public Employee
{
public:
    long m_overseesIDs[5]{};
};
```

All Supervisor objects inherit the functions and variables from both Employee and Person, and add their own m_overseesIDs member variable.

**Why is this kind of inheritance useful?**

Inheriting from a base class means we don't have to redefine the information from the base class in our derived classes. If we ever update or modify the base class, all of our derived classes will automatically inherit the changes.

## 24.3 — Order of construction of derived classes

When C++ constructs derived objects, it does so in phases. First, the most-base class (at the top of the inheritance tree) is constructed. Then each child class is constructed in order, until the most-child class is constructed last.

```cpp
#include <iostream>

class Base
{
public:
    Base() { std::cout << "Base\n"; }
};

class Derived: public Base
{
public:
    Derived() { std::cout << "Derived\n"; }
};
```

When we construct Derived, it prints: Base then Derived.

For inheritance chains (A → B → C → D), constructing D prints: A, B, C, D.

**Conclusion**: C++ constructs derived classes in phases, starting with the most-base class and finishing with the most-child class.

## 24.4 — Constructors and initialization of derived classes

When a derived class is instantiated:

1. Memory for derived is set aside (enough for both the Base and Derived portions)
2. The appropriate Derived constructor is called
3. The Base object is constructed first using the appropriate Base constructor
4. The member initializer list initializes variables
5. The body of the constructor executes

**Initializing base class members**

C++ prevents classes from initializing inherited member variables in the member initializer list of a constructor. The value of a member variable can only be set in a member initializer list of a constructor belonging to the same class as the variable.

To properly initialize inherited members, call the Base class constructor in the member initializer list:

```cpp
class Derived: public Base
{
public:
    double m_cost {};

    Derived(double cost=0.0, int id=0)
        : Base{ id } // Call Base(int) constructor with value id!
        , m_cost{ cost }
    {
    }
};
```

**Now we can make our members private**: Derived classes can not access private members of the base class directly. They will need to use access functions.

**Destructors**: When a derived class is destroyed, each destructor is called in the *reverse* order of construction.

**Warning**: If your base class has virtual functions, your destructor should also be virtual.

## 24.5 — Inheritance and access specifiers

C++ has a third access specifier: **protected**. The protected access specifier allows the class the member belongs to, friends, and derived classes to access the member. However, protected members are not accessible from outside the class.

```cpp
class Base
{
public:
    int m_public {};
protected:
    int m_protected {}; // accessible by Base, friends, and derived classes
private:
    int m_private {};   // only accessible by Base members and friends
};
```

**Best practice**: Favor private members over protected members.

**Different kinds of inheritance, and their impact on access**

There are three different ways for classes to inherit: public, protected, and private.

```cpp
class Pub: public Base { };    // Public inheritance (most common)
class Pro: protected Base { }; // Protected inheritance (rare)
class Pri: private Base { };   // Private inheritance (rare)
class Def: Base { };           // Defaults to private inheritance
```

**Public inheritance**: Inherited public members stay public, inherited protected members stay protected, inherited private members stay inaccessible.

**Protected inheritance**: Public and protected members become protected, private members stay inaccessible.

**Private inheritance**: All members from the base class are inherited as private.

Summary table:

| Access specifier in base class | Public inheritance | Private inheritance | Protected inheritance |
|---|---|---|---|
| Public | Public | Private | Protected |
| Protected | Protected | Private | Protected |
| Private | Inaccessible | Inaccessible | Inaccessible |

**Best practice**: Use public inheritance unless you have a specific reason to do otherwise.

## 24.6 — Adding new functionality to a derived class

One of the biggest benefits of using derived classes is the ability to reuse already written code. You can inherit the base class functionality and then add new functionality.

To add new functionality to a derived class, simply declare that functionality in the derived class like normal:

```cpp
class Derived: public Base
{
public:
    Derived(int value) : Base { value } { }
    int getValue() const { return m_value; }
};
```

Note that objects of type Base have no access to functions defined only in Derived. Because Derived is a Base, Derived has access to stuff in Base. However, Base does not have access to anything in Derived.

## 24.7 — Calling inherited functions and overriding behavior

When a member function is called on a derived class object, the compiler first looks to see if any function with that name exists in the derived class. If so, all overloaded functions with that name are considered. If not, the compiler walks up the inheritance chain.

**Calling a base class function**: If the derived class has no matching function but the base class does, the base class version is called.

**Redefining behaviors**: To modify the way a function defined in a base class works in the derived class, simply redefine the function in the derived class.

**Adding to existing functionality**: To have a derived function call a base function of the same name, prefix the function with the scope qualifier:

```cpp
void identify() const
{
    std::cout << "Derived::identify()\n";
    Base::identify(); // call Base::identify()
}
```

**Friend functions in base classes**: Use `static_cast` to call the base version:

```cpp
friend std::ostream& operator<< (std::ostream& out, const Derived& d)
{
    out << "In Derived\n";
    out << static_cast<const Base&>(d);
    return out;
}
```

**Overload resolution in derived classes**: The compiler will select the best matching function from the most-derived class with at least one function with that name. Use a using-declaration to make all Base functions visible:

```cpp
class Derived: public Base
{
public:
    using Base::print; // make all Base::print() functions eligible for overload resolution
    void print(double) { std::cout << "Derived::print(double)"; }
};
```

## 24.8 — Hiding inherited functionality

**Changing an inherited member's access level**

C++ gives us the ability to change an inherited member's access specifier in the derived class using a *using declaration*:

```cpp
class Derived: public Base
{
public:
    Derived(int value) : Base { value } { }
    using Base::printValue; // change from protected to public
};
```

You can only change the access specifiers of base members the derived class would normally be able to access.

**Hiding functionality**: You can make a public member private:

```cpp
class Derived : public Base
{
private:
    using Base::m_value;
};
```

**Deleting functions in the derived class**:

```cpp
int getValue() const = delete; // mark this function as inaccessible
```

## 24.9 — Multiple inheritance

**Multiple inheritance** enables a derived class to inherit members from more than one parent.

```cpp
class Teacher : public Person, public Employee
{
private:
    int m_teachesGrade{};
public:
    Teacher(std::string_view name, int age, std::string_view employer, double wage, int teachesGrade)
        : Person{ name, age }, Employee{ employer, wage }, m_teachesGrade{ teachesGrade }
    {
    }
};
```

**Mixins**: A mixin is a small class that can be inherited from in order to add properties to a class. The name mixin indicates that the class is intended to be mixed into other classes, not instantiated on its own.

**Problems with multiple inheritance**:

1. **Ambiguity**: When multiple base classes contain a function with the same name, you must use explicit scoping (e.g. `c54G.USBDevice::getID()`).
2. **The diamond problem**: Occurs when a class multiply inherits from two classes which each inherit from a single base class.

**Best practice**: Avoid multiple inheritance unless alternatives lead to more complexity.

## 24.x — Chapter 24 summary and quiz

Summary of key concepts:

- Inheritance allows us to model an is-a relationship between two objects
- When a derived class is constructed, the base portion is constructed first, then the derived portion
- Destruction happens in the opposite order, from most-derived to most-base class
- C++ has 3 access specifiers: public, private, and protected
- Classes can inherit publicly, privately, or protectedly (almost always inherit publicly)
- Derived classes can add new functions, change inherited function behavior, change access levels, or hide functionality
- Multiple inheritance enables inheriting from more than one parent
