# Chapter 23 — Object Relationships

## 23.1 — Object relationships

Life is full of recurring patterns, relationships, and hierarchies between objects. By exploring and understanding these, we can gain insight into how real-life objects behave, enhancing our understanding of those objects.

Similarly, programming is also full of recurring patterns, relationships and hierarchies. Particularly when it comes to programming objects, the same patterns that govern real-life objects are applicable to the programming objects we create ourselves. By examining these in more detail, we can better understand how to improve code reusability and write classes that are more extensible.

**Relationships between objects**

There are many different kinds of relationships two objects may have in real-life, and we use specific "relation type" words to describe these relationships. For example: a square "is-a" shape. A car "has-a" steering wheel. A computer programmer "uses-a" keyboard. A flower "depends-on" a bee for pollination. A student is a "member-of" a class. And your brain exists as "part-of" you.

All of these relation types have useful analogies in C++.

In this chapter, we'll explore the nuances of the relation types "part-of", "has-a", "uses-a", "depends-on", and "member-of", and show how they can be useful in the context of C++ classes.

## 23.2 — Composition

**Object composition**

In real-life, complex objects are often built from smaller, simpler objects. This process of building complex objects from simpler ones is called **object composition**.

Broadly speaking, object composition models a "has-a" relationship between two objects. A car "has-a" transmission. Your computer "has-a" CPU. You "have-a" heart. The complex object is sometimes called the whole, or the parent. The simpler object is often called the part, child, or component.

In C++, when we build classes with data members, we're essentially constructing a complex object from simpler parts, which is object composition. For this reason, structs and classes are sometimes referred to as **composite types**.

Object Composition is useful in a C++ context because it allows us to create complex classes by combining simpler, more easily manageable parts. This reduces complexity, and allows us to write code faster and with less errors because we can reuse code that has already been written, tested, and verified as working.

**Types of object composition**

There are two basic subtypes of object composition: composition and aggregation.

**Composition**

To qualify as a **composition**, an object and a part must have the following relationship:

- The part (member) is part of the object (class)
- The part (member) can only belong to one object (class) at a time
- The part (member) has its existence managed by the object (class)
- The part (member) does not know about the existence of the object (class)

A good real-life example of a composition is the relationship between a person's body and a heart. Composition is sometimes called a "death relationship".

In a composition relationship, the object is responsible for the existence of the parts. Most often, this means the part is created when the object is created, and destroyed when the object is destroyed.

And finally, the part doesn't know about the existence of the whole. We call this a **unidirectional** relationship, because the body knows about the heart, but not the other way around.

Our ubiquitous Fraction class is a great example of a composition:

```cpp
class Fraction
{
private:
	int m_numerator;
	int m_denominator;

public:
	Fraction(int numerator=0, int denominator=1)
		: m_numerator{ numerator }, m_denominator{ denominator }
	{
	}
};
```

**Implementing compositions**

Compositions are one of the easiest relationship types to implement in C++. They are typically created as structs or classes with normal data members. Because these data members exist directly as part of the struct/class, their lifetimes are bound to that of the class instance itself.

Compositions that need to do dynamic allocation or deallocation may be implemented using pointer data members. In this case, the composition class should be responsible for doing all necessary memory management itself (not the user of the class).

In general, if you *can* design a class using composition, you *should* design a class using composition. Classes designed using composition are straightforward, flexible, and robust.

**A good rule of thumb** is that each class should be built to accomplish a single task. That task should either be the storage and manipulation of some kind of data, OR the coordination of its members. Ideally not both.

## 23.3 — Aggregation

**Aggregation**

To qualify as an **aggregation**, a whole object and its parts must have the following relationship:

- The part (member) is part of the object (class)
- The part (member) can (if desired) belong to more than one object (class) at a time
- The part (member) does *not* have its existence managed by the object (class)
- The part (member) does not know about the existence of the object (class)

Like a composition, an aggregation is still a part-whole relationship, where the parts are contained within the whole, and it is a unidirectional relationship. However, unlike a composition, parts can belong to more than one object at a time, and the whole object is not responsible for the existence and lifespan of the parts.

We can say that aggregation models "has-a" relationships (a department has teachers, the car has an engine).

**Implementing aggregations**

In an aggregation, we also add parts as member variables. However, these member variables are typically either references or pointers that are used to point at objects that have been created outside the scope of the class. Consequently, an aggregation usually either takes the objects it is going to point to as constructor parameters, or it begins empty and the subobjects are added later via access functions or operators.

Because these parts exist outside of the scope of the class, when the class is destroyed, the pointer or reference member variable will be destroyed (but not deleted). Consequently, the parts themselves will still exist.

**std::reference_wrapper**

`std::reference_wrapper` is a class that acts like a reference, but also allows assignment and copying, so it's compatible with lists like `std::vector`. It lives in the `<functional>` header.

**Summarizing composition and aggregation**

- **Compositions**: Typically use normal member variables; Can use pointer members if the class handles object allocation/deallocation itself; Responsible for creation/destruction of parts
- **Aggregations**: Typically use pointer or reference members that point to or reference objects that live outside the scope of the aggregate class; Not responsible for creating/destroying parts

While aggregations can be extremely useful, they are also potentially more dangerous, because aggregations do not handle deallocation of their parts. For this reason, compositions should be favored over aggregations.

**Best practice**: Implement the simplest relationship type that meets the needs of your program, not what seems right in real-life.

## 23.4 — Association

**Association**

To qualify as an **association**, an object and another object must have the following relationship:

- The associated object (member) is otherwise unrelated to the object (class)
- The associated object (member) can belong to more than one object (class) at a time
- The associated object (member) does *not* have its existence managed by the object (class)
- The associated object (member) may or may not know about the existence of the object (class)

Unlike a composition or aggregation, where the part is a part of the whole object, in an association, the associated object is otherwise unrelated to the object. In an association, the relationship may be unidirectional or bidirectional (where the two objects are aware of each other).

We can say that association models as "uses-a" relationship. The doctor "uses" the patient (to earn income). The patient uses the doctor (for whatever health purposes they need).

**Implementing associations**

Because associations are a broad type of relationship, they can be implemented in many different ways. However, most often, associations are implemented using pointers, where the object points at the associated object.

In general, you should avoid bidirectional associations if a unidirectional one will do, as they add complexity and tend to be harder to write without making errors.

**Reflexive association**

Sometimes objects may have a relationship with other objects of the same type. This is called a **reflexive association**. A good example is the relationship between a university course and its prerequisites (which are also university courses).

**Associations can be indirect**

In an association, this is not strictly required to use pointers or references. Any kind of data that allows you to link two objects together suffices. For example, you can reference things by a unique ID instead of a pointer.

**Composition vs aggregation vs association summary**

| Property | Composition | Aggregation | Association |
|---|---|---|---|
| Relationship type | Whole/part | Whole/part | Otherwise unrelated |
| Members can belong to multiple classes | No | Yes | Yes |
| Members' existence managed by class | Yes | No | No |
| Directionality | Unidirectional | Unidirectional | Unidirectional or bidirectional |
| Relationship verb | Part-of | Has-a | Uses-a |

## 23.5 — Dependencies

A **dependency** occurs when one object invokes another object's functionality in order to accomplish some specific task. This is a weaker relationship than an association, but still, any change to object being depended upon may break functionality in the (dependent) caller. A dependency is always a unidirectional relationship.

A good example of a dependency is std::ostream. Our classes that use std::ostream use it in order to accomplish the task of printing something to the console, but not otherwise.

**Dependencies vs Association in C++**

In C++, associations are a relationship where one class keeps a direct or indirect "link" to the associated class as a member. Dependencies typically are not members. Rather, the object being depended on is typically instantiated as needed, or passed into a function as a parameter.

## 23.6 — Container classes

A **container class** is a class designed to hold and organize multiple instances of another type (either another class, or a fundamental type). By far the most commonly used container in programming is the array.

Container classes typically implement a fairly standardized minimal set of functionality:

- Create an empty container (via a constructor)
- Insert a new object into the container
- Remove an object from the container
- Report the number of objects currently in the container
- Empty the container of all objects
- Provide access to the stored objects
- Sort the elements (optional)

Container classes implement a member-of relationship. For example, elements of an array are members-of (belong to) the array.

**Types of containers**

- **Value containers** are compositions that store copies of the objects that they are holding (and thus are responsible for creating and destroying those copies).
- **Reference containers** are aggregations that store pointers or references to other objects (and thus are not responsible for creation or destruction of those objects).

The lesson goes on to implement a complete IntArray class demonstrating constructors, destructor, copy constructor, assignment operator, `erase()`, `reallocate()`, `resize()`, `insertBefore()`, and `remove()` methods.

**Key takeaway**: If a class in the standard library meets your needs, use that instead of creating your own (e.g. `std::vector<int>` instead of IntArray).

## 23.7 — std::initializer_list

When a compiler sees an initializer list, it automatically converts it into an object of type `std::initializer_list`. If we create a constructor that takes a `std::initializer_list` parameter, we can create objects using the initializer list as an input.

`std::initializer_list` lives in the `<initializer_list>` header.

Key points:
- `std::initializer_list` has a `size()` function which returns the number of elements in the list
- `std::initializer_list` is often passed by value (it's a view; copying does not copy elements)
- It does not provide access via subscripting (operator[]), but you can use range-based for loop or `begin()` iterator

**List initialization prefers list constructors over non-list constructors**

Non-empty initializer lists will always favor a matching `initializer_list` constructor over other potentially matching constructors. This is important to remember:

```cpp
std::vector<int> array(5); // 5 value-initialized elements: 0 0 0 0 0
std::vector<int> array{ 5 }; // 1 element: 5
```

**Best practice**: When initializing a container that has a list constructor:
- Use brace initialization when intending to call the list constructor
- Use direct initialization when intending to call a non-list constructor

**Warning**: Adding a list constructor to an existing class that did not have one may break existing programs.

You can also use `std::initializer_list` to assign new values to a class by overloading the assignment operator.

**Best practice**: If you provide list construction, it's a good idea to provide list assignment as well.

## 23.x — Chapter 23 summary and quiz

**Summary**

The process of building complex objects from simpler ones is called **object composition**. There are two types of object composition: composition, and aggregation.

### summary table

| Property/Type | Composition | Aggregation | Association | Dependency |
|---|---|---|---|---|
| Relationship type | Whole/part | Whole/part | Otherwise unrelated | Otherwise unrelated |
| Members can belong to multiple classes | No | Yes | Yes | Yes |
| Members existence managed by class | Yes | No | No | No |
| Directionality | Unidirectional | Unidirectional | Unidirectional or bidirectional | Unidirectional |
| Relationship verb | Part-of | Has-a | Uses-a | Depends-on |

**Key concept**: If you can design a class using composition, then you should.
