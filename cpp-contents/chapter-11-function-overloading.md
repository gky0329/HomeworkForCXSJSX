# Chapter 11 — Function Overloading and Function Templates

## 11.1 — Introduction to function overloading

Consider the following function:

```cpp
int add(int x, int y)
{
    return x + y;
}
```

This trivial function adds two integers and returns an integer result. However, what if we also want a function that can add two floating point numbers? This `add()` function is not suitable, as any floating point parameters would be converted to integers, causing the floating point arguments to lose their fractional values.

One way to work around this issue is to define multiple functions with slightly different names:

```cpp
int addInteger(int x, int y)
{
    return x + y;
}

double addDouble(double x, double y)
{
    return x + y;
}
```

However, for best effect, this requires that you define a consistent function naming standard for similar functions that have parameters of different types, remember the names of these functions, and actually call the correct one.

And then what happens when we want to have a similar function that adds 3 integers instead of 2? Managing unique names for each function quickly becomes burdensome.

### Introduction to function overloading

Fortunately, C++ has an elegant solution to handle such cases. **Function overloading** allows us to create multiple functions with the same name, so long as each identically named function has different parameter types (or the functions can be otherwise differentiated). Each function sharing a name (in the same scope) is called an **overloaded function** (sometimes called an **overload** for short).

To overload our `add()` function, we can simply declare another `add()` function that takes double parameters:

```cpp
double add(double x, double y)
{
    return x + y;
}
```

We now have two versions of `add()` in the same scope:

```cpp
int add(int x, int y) // integer version
{
    return x + y;
}

double add(double x, double y) // floating point version
{
    return x + y;
}

int main()
{
    return 0;
}
```

The above program will compile. Although you might expect these functions to result in a naming conflict, that is not the case here. Because the parameter types of these functions differ, the compiler is able to differentiate these functions, and will treat them as separate functions that just happen to share a name.

> **Key insight:** Functions can be overloaded so long as each overloaded function can be differentiated by the compiler. If an overloaded function can not be differentiated, a compile error will result.

### Introduction to overload resolution

Additionally, when a function call is made to a function that has been overloaded, the compiler will try to match the function call to the appropriate overload based on the arguments used in the function call. This is called **overload resolution**.

Here's a simple example demonstrating this:

```cpp
#include <iostream>

int add(int x, int y)
{
    return x + y;
}

double add(double x, double y)
{
    return x + y;
}

int main()
{
    std::cout << add(1, 2); // calls add(int, int)
    std::cout << '\n';
    std::cout << add(1.2, 3.4); // calls add(double, double)

    return 0;
}
```

The above program compiles and produces the result:

```
3
4.6
```

When we provide integer arguments in the call to `add(1, 2)`, the compiler will determine that we're trying to call `add(int, int)`. And when we provide floating point arguments in the call to `add(1.2, 3.4)`, the compiler will determine that we're trying to call `add(double, double)`.

### Making it compile

In order for a program using overloaded functions to compile, two things have to be true:

1. Each overloaded function has to be differentiated from the others.
2. Each call to an overloaded function has to resolve to an overloaded function.

If an overloaded function is not differentiated, or if a function call to an overloaded function can not be resolved to an overloaded function, then a compile error will result.

### Conclusion

Function overloading provides a great way to reduce the complexity of your program by reducing the number of function names you need to remember. It can and should be used liberally.

> **Best practice:** Use function overloading to make your program simpler.

---

## 11.2 — Function overload differentiation

In the prior lesson, we introduced the concept of function overloading. In this lesson, we'll take a closer look at how overloaded functions are differentiated. Overloaded functions that are not properly differentiated will cause the compiler to issue a compile error.

### How overloaded functions are differentiated

| Function property | Used for differentiation | Notes |
|---|---|---|
| Number of parameters | Yes | |
| Type of parameters | Yes | Excludes typedefs, type aliases, and const qualifier on value parameters. Includes ellipses. |
| Return type | No | |

For member functions, additional function-level qualifiers are also considered:
- `const` or `volatile` — Yes
- Ref-qualifiers — Yes

### Overloading based on number of parameters

An overloaded function is differentiated so long as each overloaded function has a different number of parameters:

```cpp
int add(int x, int y)
{
    return x + y;
}

int add(int x, int y, int z)
{
    return x + y + z;
}
```

### Overloading based on type of parameters

A function can also be differentiated so long as each overloaded function's list of parameter types is distinct:

```cpp
int add(int x, int y); // integer version
double add(double x, double y); // floating point version
double add(int x, double y); // mixed version
double add(double x, int y); // mixed version
```

Because type aliases (or typedefs) are not distinct types, overloaded functions using type aliases are not distinct from overloads using the aliased type:

```cpp
typedef int Height; // typedef
using Age = int; // type alias

void print(int value);
void print(Age value); // not differentiated from print(int)
void print(Height value); // not differentiated from print(int)
```

For parameters passed by value, the const qualifier is also not considered:

```cpp
void print(int);
void print(const int); // not differentiated from print(int)
```

### The return type of a function is not considered for differentiation

A function's return type is not considered when differentiating overloaded functions:

```cpp
int getRandomValue();
double getRandomValue(); // error: overloaded function differs only by return type
```

The best way to address this is to give the functions different names:

```cpp
int getRandomInt();
double getRandomDouble();
```

### Type signature

A function's **type signature** (generally called a **signature**) is defined as the parts of the function header that are used for differentiation of the function. In C++, this includes the function name, number of parameters, parameter type, and function-level qualifiers. It notably does *not* include the return type.

### Name mangling

When the compiler compiles a function, it performs **name mangling**, which means the compiled name of the function is altered ("mangled") based on various criteria, such as the number and type of parameters, so that the linker has unique names to work with.

---

## 11.3 — Function overload resolution and ambiguous matches

In the previous lesson, we discussed which attributes of a function are used to differentiate overloaded functions from each other. If an overloaded function is not properly differentiated from the other overloads of the same name, then the compiler will issue a compile error.

However, having a set of differentiated overloaded functions is only half of the picture. When any function call is made, the compiler must also ensure that a matching function declaration can be found.

The process of matching function calls to a specific overloaded function is called **overload resolution**.

### Resolving overloaded function calls

When a function call is made to an overloaded function, the compiler steps through a sequence of rules to determine which (if any) of the overloaded functions is the best match.

At each step, the compiler applies a bunch of different type conversions to the argument(s) in the function call. For each conversion applied, the compiler checks if any of the overloaded functions are now a match. After all the different type conversions have been applied and checked for matches, the step is done. The result will be one of three possible outcomes:

- No matching functions were found. The compiler moves to the next step in the sequence.
- A single matching function was found. This function is considered to be the best match.
- More than one matching function was found. The compiler will issue an ambiguous match compile error.

If the compiler reaches the end of the entire sequence without finding a match, it will generate a compile error.

### The argument matching sequence

**Step 1)** The compiler tries to find an exact match. This happens in two phases. First, the compiler will see if there is an overloaded function where the type of the arguments in the function call exactly matches the type of the parameters. Second, the compiler will apply a number of trivial conversions to the arguments in the function call. The **trivial conversions** are:
- lvalue to rvalue conversions
- qualification conversions (e.g. non-const to const)
- non-reference to reference conversions

Matches made via the trivial conversions are considered exact matches.

**Step 2)** If no exact match is found, the compiler tries to find a match by applying numeric promotion to the argument(s).

**Step 3)** If no match is found via numeric promotion, the compiler tries to find a match by applying numeric conversions to the arguments.

**Step 4)** If no match is found via numeric conversion, the compiler tries to find a match through any user-defined conversions.

**Step 5)** If no match is found via user-defined conversion, the compiler will look for a matching function that uses ellipsis.

**Step 6)** If no matches have been found by this point, the compiler gives up and will issue a compile error.

> **Key insight:** Matches made by applying numeric promotions take precedence over any matches made by applying numeric conversions.

### Ambiguous matches

With overloaded functions, an **ambiguous match** may be found. An ambiguous match occurs when the compiler finds two or more functions that can be made to match in the same step.

```cpp
void foo(int) {}
void foo(double) {}
int main()
{
    foo(5L); // 5L is type long — ambiguous!
    return 0;
}
```

If the `long` argument is numerically converted into an `int`, then the function call will match `foo(int)`. If the `long` argument is instead converted into a `double`, then it will match `foo(double)` instead. Since two possible matches via numeric conversion have been found, the function call is considered ambiguous.

### Resolving ambiguous matches

1. Often, the best way is simply to define a new overloaded function that takes parameters of exactly the type you are trying to call the function with.
2. Alternatively, explicitly cast the ambiguous argument(s) to match the type of the function you want to call.
3. If your argument is a literal, you can use the literal suffix to ensure your literal is interpreted as the correct type.

### Matching for functions with multiple arguments

If there are multiple arguments, the compiler applies the matching rules to each argument in turn. The function chosen is the one for which each argument matches at least as well as all the other functions, with at least one argument matching better than all the other functions.

---

## 11.4 — Deleting functions

In some cases, it is possible to write functions that don't behave as desired when called with values of certain types.

```cpp
void printInt(int x)
{
    std::cout << x << '\n';
}

int main()
{
    printInt(5);    // okay: prints 5
    printInt('a');  // prints 97 -- does this make sense?
    printInt(true); // print 1 -- does this make sense?
    return 0;
}
```

### Deleting a function using the `= delete` specifier

In cases where we have a function that we explicitly do not want to be callable, we can define that function as deleted by using the **= delete** specifier. If the compiler matches a function call to a deleted function, compilation will be halted with a compile error.

```cpp
void printInt(int x)
{
    std::cout << x << '\n';
}

void printInt(char) = delete; // calls to this function will halt compilation
void printInt(bool) = delete; // calls to this function will halt compilation

int main()
{
    printInt(97);   // okay
    printInt('a');  // compile error: function deleted
    printInt(true); // compile error: function deleted
    printInt(5.0);  // compile error: ambiguous match
    return 0;
}
```

> **Key insight:** `= delete` means "I forbid this", not "this doesn't exist". Deleted functions participate in all stages of function overload resolution (not just in the exact match stage). If a deleted function is selected, then a compilation error results.

### Deleting all non-matching overloads (Advanced)

There may be times when we want a certain function to be called only with arguments whose types exactly match the function parameters. We can do this by using a function template as follows:

```cpp
// This function will take precedence for arguments of type int
void printInt(int x)
{
    std::cout << x << '\n';
}

// This function template will take precedence for arguments of other types
// Since this function template is deleted, calls to it will halt compilation
template <typename T>
void printInt(T x) = delete;

int main()
{
    printInt(97);   // okay
    printInt('a');  // compile error
    printInt(true); // compile error
    return 0;
}
```

---

## 11.5 — Default arguments

A **default argument** is a default value provided for a function parameter:

```cpp
void print(int x, int y=10) // 10 is the default argument
{
    std::cout << "x: " << x << '\n';
    std::cout << "y: " << y << '\n';
}
```

When making a function call, the caller can optionally provide an argument for any function parameter that has a default argument. If the caller provides an argument, the value of the argument in the function call is used. If the caller does not provide an argument, the value of the default argument is used.

```cpp
int main()
{
    print(1, 2); // y will use user-supplied argument 2
    print(3); // y will use default argument 4
    return 0;
}
```

> **Key insight:** Default arguments are inserted by the compiler at the site of the function call.

### When to use default arguments

Default arguments are an excellent option when a function needs a value that has a reasonable default value, but for which you want to let the caller override if they wish.

### Multiple default arguments

A function can have multiple parameters with default arguments:

```cpp
void print(int x=10, int y=20, int z=30)
{
    std::cout << "Values: " << x << " " << y << " " << z << '\n';
}
```

C++ does not (as of C++23) support a function call syntax such as `print(,,3)`. This has three major consequences:

1. In a function call, any explicitly provided arguments must be the leftmost arguments (arguments with defaults cannot be skipped).
2. If a parameter is given a default argument, all subsequent parameters (to the right) must also be given default arguments.
3. If more than one parameter has a default argument, the leftmost parameter should be the one most likely to be explicitly set by the user.

> **Rule:** If a parameter is given a default argument, all subsequent parameters (to the right) must also be given default arguments.

### Default arguments can not be redeclared

Once declared, a default argument can not be redeclared in the same translation unit. That means for a function with a forward declaration and a function definition, the default argument can be declared in either the forward declaration or the function definition, but not both.

> **Best practice:** If the function has a forward declaration (especially one in a header file), put the default argument there. Otherwise, put the default argument in the function definition.

### Default arguments and function overloading

Functions with default arguments may be overloaded. Default values are not part of a function's signature, so function declarations with different default arguments are differentiated overloads. However, default arguments can easily lead to ambiguous function calls.

---

## 11.6 — Function templates

Let's say you wanted to write a function to calculate the maximum of two numbers:

```cpp
int max(int x, int y)
{
    return (x < y) ? y : x;
}
```

While the caller can pass different values into the function, the type of the parameters is fixed. So what happens later when you want to find the max of two `double` values? Because C++ requires us to specify the type of all function parameters, the solution is to create a new overloaded version.

Having to create overloaded functions with the same implementation for each set of parameter types we want to support is a maintenance headache, a recipe for errors, and a clear violation of the DRY (don't repeat yourself) principle.

### Introduction to C++ templates

In C++, the template system was designed to simplify the process of creating functions (or classes) that are able to work with different data types.

Instead of manually creating a bunch of mostly-identical functions or classes (one for each set of different types), we instead create a single *template*. Just like a normal definition, a **template** definition describes what a function or class looks like. Unlike a normal definition (where all types must be specified), in a template we can use one or more placeholder types. A placeholder type represents some type that is not known at the time the template is defined, but that will be provided later (when the template is used).

Once a template is defined, the compiler can use the template to generate as many overloaded functions (or classes) as needed, each using different actual types!

> **Key insight:** The compiler can use a single template to generate a family of related functions or classes, each using a different set of actual types.

### Function templates

A **function template** is a function-like definition that is used to generate one or more overloaded functions, each with a different set of actual types. The initial function template that is used to generate other functions is called the **primary template**, and the functions generated from the primary template are called **instantiated functions**.

When we create a primary function template, we use **placeholder types** (technically called **type template parameters**, informally called **template types**) for any parameter types, return types, or types used in the function body that we want to be specified later.

### Creating a `max()` function template

Here's the `int` version of `max()` again:

```cpp
int max(int x, int y)
{
    return (x < y) ? y : x;
}
```

To create a function template, we replace actual types with type template parameters, and add a template parameter declaration:

```cpp
template <typename T> // this is the template parameter declaration defining T as a type template parameter
T max(T x, T y) // this is the function template definition for max<T>
{
    return (x < y) ? y : x;
}
```

In our template parameter declaration, we start with the keyword `template`, which tells the compiler that we're creating a template. Next, we specify all of the template parameters that our template will use inside angled brackets (`<>`). For each type template parameter, we use the keyword `typename` (preferred) or `class`, followed by the name of the type template parameter (e.g. `T`).

### Naming template parameters

It's conventional to use a single capital letter (starting with `T`) when the template parameter is used in a trivial or obvious way. If a type template parameter has a non-obvious usage or specific requirements that must be met, a more descriptive name is warranted (e.g. `Allocator` or `TAllocator`).

> **Best practice:** Use a single capital letter starting with `T` (e.g. `T`, `U`, `V`, etc...) to name type template parameters that are used in trivial or obvious ways and represent "any reasonable type".

---

## 11.7 — Function template instantiation

In the previous lesson, we introduced function templates, and converted a normal `max()` function into a `max<T>` function template:

```cpp
template <typename T>
T max(T x, T y)
{
    return (x < y) ? y : x;
}
```

In this lesson, we'll focus on how function templates are used.

### Using a function template

Function templates are not actually functions -- their code isn't compiled or executed directly. Instead, function templates have one job: to generate functions (that are compiled and executed).

To use our `max<T>` function template, we can make a function call with the following syntax:

```
max<actual_type>(arg1, arg2); // actual_type is some actual type, like int or double
```

When the compiler encounters the function call `max<int>(1, 2)`, it will determine that a function definition for `max<int>(int, int)` does not already exist. Consequently, the compiler will implicitly use our `max<T>` function template to create one.

The process of creating functions (with specific types) from function templates (with template types) is called **function template instantiation** (or **instantiation** for short). When a function is instantiated due to a function call, it's called **implicit instantiation**. A function that is instantiated from a template is technically called a **specialization**, but in common language is often called a **function instance**.

### Template argument deduction

In most cases, the actual types we want to use for instantiation will match the type of our function parameters. In cases where the type of the arguments match the actual type we want, we do not need to specify the actual type -- instead, we can use **template argument deduction** to have the compiler deduce the actual type that should be used from the argument types in the function call.

```cpp
std::cout << max<int>(1, 2) << '\n'; // specifying we want to call max<int>
std::cout << max<>(1, 2) << '\n';    // deduces max<int>(int, int)
std::cout << max(1, 2) << '\n';      // deduces max<int>(int, int) (also considers non-template functions)
```

> **Key insight:** The normal function call syntax will prefer a non-template function over an equally viable function instantiated from a template.

> **Best practice:** Favor the normal function call syntax when making calls to a function instantiated from a function template (unless you need the function template version to be preferred over a matching non-template function).

### Function templates with non-template parameters

It's possible to create function templates that have both template parameters and non-template parameters. The type template parameters can be matched to any type, and the non-template parameters work like the parameters of normal functions.

### Instantiated functions may not always compile

The compiler will successfully compile an instantiated function template as long as it makes sense syntactically. However, the compiler does not have any way to check that such a function actually makes sense semantically.

> **Warning:** The compiler will instantiate and compile function templates that do not make sense semantically as long as they are syntactically valid. It is your responsibility to make sure you are calling such function templates with arguments that make sense.

### Beware function templates with modifiable static local variables

When a static local variable is used in a function template, each function instantiated from that template will have a separate version of the static local variable.

### Conclusion

> **Best practice:** Use function templates to write generic code that can work with a wide variety of types whenever you have the need.

---

## 11.8 — Function templates with multiple template types

In lesson 11.6, we wrote a function template to calculate the maximum of two values:

```cpp
template <typename T>
T max(T x, T y)
{
    return (x < y) ? y : x;
}
```

Now consider the following similar program:

```cpp
int main()
{
    std::cout << max(2, 3.5) << '\n';  // compile error
    return 0;
}
```

You may be surprised to find that this program won't compile. This will fail because `T` can only represent a single type. There is no type for `T` that would allow the compiler to instantiate function template `max<T>(T, T)` into a function with two different parameter types.

This lack of type conversion is intentional for at least two reasons. First, it helps keep things simple: we either find an exact match between the function call arguments and template type parameters, or we don't. Second, it allows us to create function templates for cases where we want to ensure that two or more parameters have the same type.

### Solutions

**Use static_cast to convert the arguments:**

```cpp
std::cout << max(static_cast<double>(2), 3.5) << '\n';
```

**Provide an explicit type template argument:**

```cpp
std::cout << max<double>(2, 3.5) << '\n';
```

### Function templates with multiple template type parameters

The best way to solve this problem is to rewrite our function template so our parameters can resolve to different types:

```cpp
template <typename T, typename U>
auto max(T x, U y)
{
    return (x < y) ? y : x;
}
```

> **Key insight:** Because `T` and `U` are independent template parameters, they resolve their types independent of each other. This means `T` and `U` can resolve to different types, or they can resolve to the same type.

### Abbreviated function templates (C++20)

C++20 introduces a new use of the `auto` keyword: When the `auto` keyword is used as a parameter type in a normal function, the compiler will automatically convert the function into a function template with each auto parameter becoming an independent template type parameter.

```cpp
auto max(auto x, auto y)
{
    return (x < y) ? y : x;
}
```

This is shorthand in C++20 for:

```cpp
template <typename T, typename U>
auto max(T x, U y)
{
    return (x < y) ? y : x;
}
```

> **Best practice:** Feel free to use abbreviated function templates with a single auto parameter, or where each auto parameter should be an independent type (and your language standard is set to C++20 or newer).

### Function templates may be overloaded

Just like functions may be overloaded, function templates may also be overloaded. Such overloads can have a different number of template types and/or a different number or type of function parameters.

---

## 11.9 — Non-type template parameters

While type template parameters are by far the most common type of template parameter used, there is another kind of template parameter worth knowing about: the non-type template parameter.

### Non-type template parameters

A **non-type template parameter** is a template parameter with a fixed type that serves as a placeholder for a constexpr value passed in as a template argument.

A non-type template parameter can be any of the following types:
- An integral type
- An enumeration type
- `std::nullptr_t`
- A floating point type (since C++20)
- A pointer or reference to an object
- A pointer or reference to a function
- A pointer or reference to a member function
- A literal class type (since C++20)

We saw our first example of a non-type template parameter when we discussed `std::bitset`:

```cpp
std::bitset<8> bits{ 0b0000'0101 }; // The <8> is a non-type template parameter
```

### Defining our own non-type template parameters

```cpp
template <int N> // declare a non-type template parameter of type int named N
void print()
{
    std::cout << N << '\n';
}

int main()
{
    print<5>(); // 5 is our non-type template argument
    return 0;
}
```

Much like `T` is typically used as the name for the first type template parameter, `N` is conventionally used as the name of an int non-type template parameter.

> **Best practice:** Use `N` as the name of an int non-type template parameter.

### What are non-type template parameters useful for?

As of C++20, function parameters cannot be constexpr. Non-type template parameters are used primarily when we need to pass constexpr values to functions (or class types) so they can be used in contexts that require a constant expression.

> **Key insight:** Non-type template parameters are used primarily when we need to pass constexpr values to functions (or class types) so they can be used in contexts that require a constant expression.

### Type deduction for non-type template parameters using `auto` (C++17)

As of C++17, non-type template parameters may use `auto` to have the compiler deduce the non-type template parameter from the template argument:

```cpp
template <auto N> // deduce non-type template parameter from template argument
void print()
{
    std::cout << N << '\n';
}
```

---

## 11.10 — Using function templates in multiple files

Consider the following program, which doesn't work correctly:

*main.cpp:*
```cpp
template <typename T>
T addOne(T x); // function template forward declaration

int main()
{
    std::cout << addOne(1) << '\n';
    std::cout << addOne(2.3) << '\n';
    return 0;
}
```

*add.cpp:*
```cpp
template <typename T>
T addOne(T x) // function template definition
{
    return x + 1;
}
```

If `addOne` were a non-template function, this program would work fine. But because `addOne` is a template, this program doesn't work, and we get a linker error.

In *main.cpp*, we call `addOne<int>` and `addOne<double>`. However, since the compiler can't see the definition for function template `addOne`, it can't instantiate those functions inside *main.cpp*.

When the compiler goes to compile *add.cpp*, it will see the definition for function template `addOne`. However, there are no uses of this template in *add.cpp*, so the compiler will not instantiate anything.

The most conventional way to address this issue is to put all your template code in a header (.h) file instead of a source (.cpp) file:

*add.h:*
```cpp
#ifndef ADD_H
#define ADD_H

template <typename T>
T addOne(T x) // function template definition
{
    return x + 1;
}

#endif
```

> **Key insight:** Template definitions are exempt from the part of the one-definition rule that requires only one definition per program, so it is not a problem to have the same template definition #included into multiple source files. And functions implicitly instantiated from function templates are implicitly inline, so they can be defined in multiple files, so long as each definition is identical.

> **Best practice:** Templates that are needed in multiple files should be defined in a header file, and then #included wherever needed. This allows the compiler to see the full template definition and instantiate the template when needed.

---

## 11.x — Chapter 11 summary and quiz

### Chapter Review

**Function overloading** allows us to create multiple functions with the same name, so long as each identically named function has different set of parameter types (or the functions can be otherwise differentiated). Such a function is called an **overloaded function** (or **overload** for short). Return types are not considered for differentiation.

When resolving overloaded functions, if an exact match isn't found, the compiler will favor overloaded functions that can be matched via numeric promotions over those that require numeric conversions. When a function call is made to function that has been overloaded, the compiler will try to match the function call to the appropriate overload based on the arguments used in the function call. This is called **overload resolution**.

An **ambiguous match** occurs when the compiler finds two or more functions that can match a function call to an overloaded function and can't determine which one is best.

A **default argument** is a default value provided for a function parameter. Parameters with default arguments must always be the rightmost parameters, and they are not used to differentiate functions when resolving overloaded functions.

**Function templates** allow us to create a function-like definition that serves as a pattern for creating related functions. In a function template, we use **type template parameters** as placeholders for any types we want to be specified later. The syntax that tells the compiler we're defining a template and declares the template types is called a **template parameter declaration**.

The process of creating functions (with specific types) from function templates (with template types) is called **function template instantiation** (or **instantiation**) for short. When this process happens due to a function call, it's called **implicit instantiation**. An instantiated function is called a **function instance** (or **instance** for short, or sometimes a **template function**).

**Template argument deduction** allows the compiler to deduce the actual type that should be used to instantiate a function from the arguments of the function call. Template argument deduction does not do type conversion.

Template types are sometimes called **generic types**, and programming using templates is sometimes called **generic programming**.

In C++20, when the auto keyword is used as a parameter type in a normal function, the compiler will automatically convert the function into a function template with each auto parameter becoming an independent template type parameter. This method for creating a function template is called an **abbreviated function template**.

A **non-type template parameter** is a template parameter with a fixed type that serves as a placeholder for a constexpr value passed in as a template argument.

### Quiz

**Question #1**

1a) What is the output of this program and why?

```cpp
#include <iostream>

void print(int x)
{
    std::cout << "int " << x << '\n';
}

void print(double x)
{
    std::cout << "double " << x << '\n';
}

int main()
{
    short s { 5 };
    print(s);
    return 0;
}
```

**Answer:** The output is `int 5`. Converting a `short` to an `int` is a numeric promotion, whereas converting a `short` to a `double` is a numeric conversion. The compiler will favor the option that is a numeric promotion over the option that is a numeric conversion.

1b) Why won't the following compile?

```cpp
void print() { std::cout << "void\n"; }
void print(int x=0) { std::cout << "int " << x << '\n'; }
void print(double x) { std::cout << "double " << x << '\n'; }

int main()
{
    print(5.0f);
    print();
    return 0;
}
```

**Answer:** Because parameters with default arguments aren't counted for resolving overloaded functions, the compiler can't tell whether the call to `print()` should resolve to `print()` or `print(int x=0)`.

1c) Why won't the following compile?

```cpp
void print(long x) { std::cout << "long " << x << '\n'; }
void print(double x) { std::cout << "double " << x << '\n'; }

int main()
{
    print(5);
    return 0;
}
```

**Answer:** The literal 5 is an `int`. Converting an `int` to a `long` or a `double` is a numeric conversion, and the compiler will be unable to determine which function is a better match.

**Question #2**

Write a function template named `add()` that allows the users to add 2 values of the same type:

```cpp
template <typename T>
T add(T x, T y)
{
    return x + y;
}
```

Write a function template named `mult()` that allows the user to multiply one value of any type (first parameter) and an integer (second parameter):

```cpp
template <typename T>
T mult(T x, int y)
{
    return x * y;
}
```

Write a function template named `sub()` that allows the user to subtract two values of different types:

```cpp
template <typename T, typename U>
auto sub(T x, U y)
{
    return x - y;
}
```

**Question #3**

What is the output of this program and why?

```cpp
template <typename T>
int count(T)
{
    static int c { 0 };
    return ++c;
}

int main()
{
    std::cout << count(1) << '\n';      // 1
    std::cout << count(1) << '\n';      // 2
    std::cout << count(2.3) << '\n';    // 1 (new function with its own static c)
    std::cout << count<double>(1) << '\n'; // 2 (same as count(2.3))
    return 0;
}
```

**Question #4**

What is the output of this program?

```cpp
int foo(int n) { return n + 10; }

template <typename T>
int foo(T n) { return n; }

int main()
{
    std::cout << foo(1) << '\n';      // 11 (non-template exact match)
    short s { 2 };
    std::cout << foo(s) << '\n';      // 2 (template generates exact match)
    std::cout << foo<int>(4) << '\n'; // 4 (explicit template call)
    std::cout << foo<int>(s) << '\n'; // 2 (explicit + promotion)
    std::cout << foo<>(6) << '\n';    // 6 (deduces foo<int>(int))
    return 0;
}
```
