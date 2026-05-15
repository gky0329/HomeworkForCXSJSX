# Chapter 20 — Functions (Advanced)

## 20.1 — Function Pointers

*Alex* August 8, 2007, 4:52 pm PDT December 14, 2024

In lesson 12.7 you learned that a pointer is a variable that holds the address of another variable. Function pointers are similar, except that instead of pointing to variables, they point to functions!

Consider the following function:

```cpp
int foo()
{
    return 5;
}
```

Functions have their own function type -- in this case, a function type that returns an integer and takes no parameters. Much like variables, functions live at an assigned address in memory (making them lvalues).

When a function is referred to by name (without parenthesis), C++ converts the function into a function pointer (holding the address of the function).

### Pointers to functions

The syntax for creating a non-const function pointer:

```cpp
// fcnPtr is a pointer to a function that takes no arguments and returns an integer
int (*fcnPtr)();
```

The parentheses around \*fcnPtr are necessary for precedence reasons, as `int* fcnPtr()` would be interpreted as a forward declaration for a function named fcnPtr that takes no parameters and returns a pointer to an integer.

To make a const function pointer, the const goes after the asterisk:

```cpp
int (*const fcnPtr)();
```

### Assigning a function to a function pointer

Function pointers can be initialized with a function (and non-const function pointers can be assigned a function):

```cpp
int foo()
{
    return 5;
}

int goo()
{
    return 6;
}

int main()
{
    int (*fcnPtr)(){ &foo }; // fcnPtr points to function foo
    fcnPtr = &goo; // fcnPtr now points to function goo

    return 0;
}
```

C++ *will* implicitly convert a function into a function pointer if needed (so you don't need to use the address-of operator (&) to get the function's address).

### Calling a function using a function pointer

There are two ways to call a function through a function pointer:

```cpp
int foo(int x)
{
    return x;
}

int main()
{
    int (*fcnPtr)(int){ &foo }; // Initialize fcnPtr with function foo
    (*fcnPtr)(5); // explicit dereference
    fcnPtr(5); // implicit dereference

    return 0;
}
```

**Key insight:** Because the resolution happens at runtime, default arguments are not resolved when a function is called through a function pointer.

### Passing functions as arguments to other functions

One of the most useful things to do with function pointers is pass a function as an argument to another function. Functions used as arguments to another function are sometimes called **callback functions**.

Here's a full example of a selection sort that uses a function pointer parameter to do a user-defined comparison:

```cpp
#include <utility> // for std::swap
#include <iostream>

void selectionSort(int* array, int size, bool (*comparisonFcn)(int, int))
{
    if (!array || !comparisonFcn)
        return;

    for (int startIndex{ 0 }; startIndex < (size - 1); ++startIndex)
    {
        int bestIndex{ startIndex };
 
        for (int currentIndex{ startIndex + 1 }; currentIndex < size; ++currentIndex)
        {
            if (comparisonFcn(array[bestIndex], array[currentIndex]))
            {
                bestIndex = currentIndex;
            }
        }
 
        std::swap(array[startIndex], array[bestIndex]);
    }
}

bool ascending(int x, int y)
{
    return x > y; // swap if the first element is greater than the second
}

bool descending(int x, int y)
{
    return x < y; // swap if the second element is greater than the first
}

int main()
{
    int array[9]{ 3, 7, 9, 5, 6, 1, 8, 2, 4 };

    selectionSort(array, 9, descending); // Sort in descending order
    selectionSort(array, 9, ascending);  // Sort in ascending order

    return 0;
}
```

### Using type aliases

```cpp
using ValidateFunction = bool(*)(int, int);
```

Now instead of:

```cpp
bool validate(int x, int y, bool (*fcnPtr)(int, int)); // ugly
```

You can do:

```cpp
bool validate(int x, int y, ValidateFunction pfcn) // clean
```

### Using std::function

An alternate method of defining and storing function pointers is to use std::function, which is part of the standard library <functional> header:

```cpp
#include <functional>
bool validate(int x, int y, std::function<bool(int, int)> fcn);
```

### Type inference for function pointers

Much like the *auto* keyword can be used to infer the type of normal variables, the *auto* keyword can also infer the type of a function pointer:

```cpp
auto fcnPtr{ &foo };
```

---

## 20.2 — The stack and the heap

*Alex* August 10, 2007, 4:56 pm PDT June 25, 2024

The memory that a program uses is typically divided into a few different areas, called segments:

-   The **code segment** (also called a text segment), where the compiled program sits in memory. The code segment is typically read-only.
-   The **bss segment** (also called the uninitialized data segment), where zero-initialized global and static variables are stored.
-   The **data segment** (also called the initialized data segment), where initialized global and static variables are stored.
-   The **heap**, where dynamically allocated variables are allocated from.
-   The **call stack**, where function parameters, local variables, and other function-related information are stored.

### The heap segment

In C++, when you use the new operator to allocate memory, this memory is allocated in the application's heap segment. When a dynamically allocated variable is deleted, the memory is "returned" to the heap and can then be reassigned.

The heap has advantages and disadvantages:
- Allocating memory on the heap is comparatively slow.
- Allocated memory stays allocated until it is specifically deallocated (beware memory leaks) or the application ends.
- Dynamically allocated memory must be accessed through a pointer. Dereferencing a pointer is slower than accessing a variable directly.
- Because the heap is a big pool of memory, large arrays, structures, or classes can be allocated here.

### The call stack

The **call stack** (usually referred to as "the stack") keeps track of all the active functions (those that have been called but have not yet terminated) from the start of the program to the current point of execution, and handles allocation of all function parameters and local variables.

The call stack is implemented as a stack data structure. A stack is a last-in, first-out (LIFO) structure. The last item pushed onto the stack will be the first item popped off.

**The call stack in action:**

1.  The program encounters a function call.
2.  A stack frame is constructed and pushed on the stack. The stack frame consists of:
    -   The return address
    -   All function arguments
    -   Memory for any local variables
    -   Saved copies of any registers modified by the function
3.  The CPU jumps to the function's start point.
4.  The instructions inside of the function begin executing.

When the function terminates:
1.  Registers are restored from the call stack
2.  The stack frame is popped off the stack
3.  The return value is handled
4.  The CPU resumes execution at the return address

### Stack overflow

The stack has a limited size, and consequently can only hold a limited amount of information. On Visual Studio for Windows, the default stack size is 1MB. With g++/Clang for Unix variants, it can be as large as 8MB. If the program tries to put too much information on the stack, **stack overflow** will result.

The stack has advantages and disadvantages:
- Allocating memory on the stack is comparatively fast.
- Memory allocated on the stack stays in scope as long as it is on the stack. It is destroyed when it is popped off the stack.
- All memory allocated on the stack is known at compile time. Consequently, this memory can be accessed directly through a variable.
- Because the stack is relatively small, it is generally not a good idea to do anything that eats up lots of stack space.

---

## 20.3 — Recursion

*Alex* August 13, 2007, 9:30 pm PST February 5, 2024

A **recursive function** in C++ is a function that calls itself.

```cpp
#include <iostream>

void countDown(int count)
{
    std::cout << "push " << count << '\n';
    countDown(count-1); // countDown() calls itself recursively
}

int main()
{
    countDown(5);
    return 0;
}
```

This is poorly-written because it has no termination condition - it will run until stack overflow.

### Recursive termination conditions

Recursive function calls generally work just like normal function calls. However, you must include a recursive termination condition, or they will run "forever" (actually, until the call stack runs out of memory). A **recursive termination** is a condition that, when met, will cause the recursive function to stop calling itself.

```cpp
#include <iostream>

void countDown(int count)
{
    std::cout << "push " << count << '\n';

    if (count > 1) // termination condition
        countDown(count-1);

    std::cout << "pop " << count << '\n';
}

int main()
{
    countDown(5);
    return 0;
}
```

Output:

push 5
push 4
push 3
push 2
push 1
pop 1
pop 2
pop 3
pop 4
pop 5

### A more useful example

```cpp
// return the sum of all the integers between 1 (inclusive) and sumto (inclusive)
int sumTo(int sumto)
{
    if (sumto <= 0)
        return 0; // base case (termination condition)
    if (sumto == 1)
        return 1; // normal base case (termination condition)

    return sumTo(sumto - 1) + sumto; // recursive function call
}
```

### Fibonacci numbers

Fibonacci numbers are defined mathematically as:

F(n) = 0 if n = 0, 1 if n = 1, f(n-1) + f(n-2) if n > 1

```cpp
#include <iostream>

int fibonacci(int count)
{
    if (count == 0)
        return 0; // base case
    if (count == 1)
        return 1; // base case
    return fibonacci(count-1) + fibonacci(count-2);
}
```

### Memoization algorithms

The above recursive Fibonacci algorithm isn't very efficient. One technique, called **memoization**, caches the results of expensive function calls so the result can be returned when the same input occurs again.

```cpp
#include <iostream>
#include <vector>

int fibonacci(std::size_t count)
{
	static std::vector results{ 0, 1 };

	if (count < std::size(results))
		return results[count];

	results.push_back(fibonacci(count - 1) + fibonacci(count - 2));
	return results[count];   
}
```

### Recursive vs iterative

Iterative functions (those using a for-loop or while-loop) are almost always more efficient than their recursive counterparts. This is because every time you call a function there is some amount of overhead that takes place in pushing and popping stack frames.

In general, recursion is a good choice when most of the following are true:
-   The recursive code is much simpler to implement.
-   The recursion depth can be limited.
-   The iterative version of the algorithm requires managing a stack of data.
-   This isn't a performance-critical section of code.

**Best practice:** Generally favor iteration over recursion, except when recursion really makes sense.

---

## 20.4 — Command line arguments

*Alex* February 15, 2008, 4:06 pm PST June 25, 2024

**Command line arguments** are optional string arguments that are passed by the operating system to the program when it is launched. The program can then use them as input (or ignore them).

### Passing command line arguments

Executable programs can be run on the command line by invoking them by name:

```
WordCount Myfile.txt Myotherfile.txt
```

### Using command line arguments

To access command line arguments from within our C++ program, we use a different form of main():

```cpp
int main(int argc, char* argv[])
```

**argc** is an integer parameter containing a count of the number of arguments passed to the program. argc will always be at least 1, because the first argument is always the name of the program itself.

**argv** is where the actual argument values are stored. Although the declaration of argv looks intimidating, argv is really just a C-style array of char pointers (each of which points to a C-style string). The length of this array is argc.

```cpp
// Program: MyArgs
#include <iostream>

int main(int argc, char* argv[])
{
    std::cout << "There are " << argc << " arguments:\n";

    for (int count{ 0 }; count < argc; ++count)
    {
        std::cout << count << ' ' << argv[count] << '\n';
    }

    return 0;
}
```

### Dealing with numeric arguments

Command line arguments are always passed as strings, even if the value provided is numeric in nature. To use a command line argument as a number, you must convert it from a string to a number:

```cpp
#include <iostream>
#include <sstream> // for std::stringstream
#include <string>

int main(int argc, char* argv[])
{
	if (argc <= 1)
	{
		if (argv[0])
			std::cout << "Usage: " << argv[0] << " <number>" << '\n';
		else
			std::cout << "Usage: <program name> <number>" << '\n';
		return 1;
	}

	std::stringstream convert{ argv[1] };

	int myint{};
	if (!(convert >> myint)) // do the conversion
		myint = 0; // if conversion fails, set myint to a default value

	std::cout << "Got integer: " << myint << '\n';

	return 0;
}
```

---

## 20.5 — Ellipsis (and why to avoid them)

*Alex* February 22, 2008, 4:08 pm PST September 11, 2023

C++ provides a special specifier known as ellipsis (aka "...") that allow us to pass a variable number of parameters to a function.

Functions that use ellipsis take the form:

```
return_type function_name(argument_list, ...)
```

The ellipsis (which are represented as three periods in a row) must always be the last parameter in the function.

### An ellipsis example

```cpp
#include <iostream>
#include <cstdarg> // needed to use ellipsis

double findAverage(int count, ...)
{
    int sum{ 0 };

    std::va_list list;
    va_start(list, count);

    for (int arg{ 0 }; arg < count; ++arg)
    {
         sum += va_arg(list, int);
    }

    va_end(list);

    return static_cast<double>(sum) / count;
}

int main()
{
    std::cout << findAverage(5, 1, 2, 3, 4, 5) << '\n';
    std::cout << findAverage(6, 1, 2, 3, 4, 5, 6) << '\n';

    return 0;
}
```

The components: `va_list`, `va_start()`, `va_arg()`, and `va_end()`.

### Why ellipsis are dangerous

1. **Type checking is suspended:** The compiler completely suspends type checking for ellipsis parameters. If the actual parameter type doesn't match the expected parameter type, bad things will usually happen.

2. **Ellipsis don't know how many parameters were passed:** We have to devise our own solution for keeping track of the number of parameters passed into the ellipsis. Three common methods:
   - **Method 1: Pass a length parameter** (e.g. the count in findAverage)
   - **Method 2: Use a sentinel value** (a special value to terminate)
   - **Method 3: Use a decoder string** (like printf does)

### Recommendations

First, if possible, do not use ellipsis at all! Oftentimes, other reasonable solutions are available. If you do use ellipsis, it is better if all values passed to the ellipses parameter are the same type.

---

## 20.6 — Introduction to lambdas (anonymous functions)

*nascardriver* January 3, 2020, 5:19 am PST June 14, 2024

A **lambda expression** (also called a **lambda** or **closure**) allows us to define an anonymous function inside another function. The nesting is important, as it allows us both to avoid namespace naming pollution, and to define the function as close to where it is used as possible.

Lambdas take the form:

```
[ captureClause ] ( parameters ) -> returnType
{
    statements;
}
```

- The capture clause can be empty if no captures are needed.
- The parameter list can be empty if no parameters are required.
- The return type is optional, and if omitted, `auto` will be assumed.

A trivial lambda definition:

```cpp
#include <iostream>

int main()
{
  [] {}; // a lambda with an omitted return type, no captures, and omitted parameters.
  return 0;
}
```

### Example using a lambda

```cpp
#include <algorithm>
#include <array>
#include <iostream>
#include <string_view>

int main()
{
  constexpr std::array<std::string_view, 4> arr{ "apple", "banana", "walnut", "lemon" };

  auto found{ std::find_if(arr.begin(), arr.end(),
                           [](std::string_view str)
                           {
                             return str.find("nut") != std::string_view::npos;
                           }) };

  if (found == arr.end())
  {
    std::cout << "No nuts\n";
  }
  else
  {
    std::cout << "Found " << *found << '\n';
  }

  return 0;
}
```

### Type of a lambda

Lambdas don't have a type that we can explicitly use. When we write a lambda, the compiler generates a unique type just for the lambda that is not exposed to us. There are several ways of storing a lambda:

```cpp
#include <functional>

int main()
{
  // A regular function pointer. Only works with an empty capture clause.
  double (*addNumbers1)(double, double){
    [](double a, double b) {
      return a + b;
    }
  };

  // Using std::function
  std::function addNumbers2{ // note: pre-C++17, use std::function<double(double, double)> instead
    [](double a, double b) {
      return a + b;
    }
  };

  // Using auto. Stores the lambda with its real type.
  auto addNumbers3{
    [](double a, double b) {
      return a + b;
    }
  };

  return 0;
}
```

**Best practice:** When storing a lambda in a variable, use `auto` as the variable's type.

### Generic lambdas

Since C++14 we're allowed to use `auto` for parameters. When a lambda has one or more `auto` parameter, the compiler will infer what parameter types are needed. Because lambdas with one or more `auto` parameter can potentially work with a wide variety of types, they are called **generic lambdas**.

### Constexpr lambdas

As of C++17, lambdas are implicitly constexpr if the result satisfies the requirements of a constant expression.

### Standard library function objects

For common operations (e.g. addition, negation, or comparison) you don't need to write your own lambdas, because the standard library comes with many basic callable objects. These are defined in the `<functional>` header.

---

## 20.7 — Lambda captures

*nascardriver* January 3, 2020, 5:19 am PST December 4, 2024

### Capture clauses and capture by value

Lambdas can only access certain kinds of objects that have been defined outside the lambda. This includes objects with static (or thread local) storage duration and objects that are constexpr.

To access variables from the surrounding scope, we need to use a capture clause.

The **capture clause** is used to (indirectly) give a lambda access to variables available in the surrounding scope that it normally would not have access to. All we need to do is list the entities we want to access from within the lambda as part of the capture clause:

```cpp
  auto found{ std::find_if(arr.begin(), arr.end(), [search](std::string_view str) {
    return str.find(search) != std::string_view::npos;
  }) };
```

**Key insight:** The captured variables of a lambda are *copies* of the outer scope variables, not the actual variables.

### Captures are treated as const by default

By default, `operator()` treats captures as const, meaning the lambda is not allowed to modify those captures.

### Mutable captures

To allow modifications of variables that were captured, we can mark the lambda as `mutable`:

```cpp
  auto shoot{
    [ammo]() mutable {
      --ammo;
      std::cout << "Pew! " << ammo << " shot(s) left.\n";
    }
  };
```

### Capture by reference

To capture a variable by reference, we prepend an ampersand (`&`) to the variable name in the capture:

```cpp
  auto shoot{
    [&ammo]() {
      --ammo;
      std::cout << "Pew! " << ammo << " shot(s) left.\n";
    }
  };
```

### Default captures

- To capture all used variables by value, use a capture value of `=`.
- To capture all used variables by reference, use a capture value of `&`.

```cpp
  auto found{ std::find_if(areas.begin(), areas.end(),
                           [=](int knownArea) { // will default capture variables by value
                             return width * height == knownArea;
                           }) };
```

Default captures can be mixed with normal captures:

```cpp
  [=, &enemies](){};  // Capture enemies by reference and everything else by value.
  [&, armor](){};     // Capture armor by value and everything else by reference.
```

### Defining new variables in the lambda-capture

```cpp
  [userArea{ width * height }](int knownArea) {
    return userArea == knownArea;
  }
```

### Dangling captured variables

Variables are captured at the point where the lambda is defined. If a variable captured by reference dies before the lambda, the lambda will be left holding a dangling reference.

**Warning:** Be extra careful when you capture variables by reference, especially with a default reference capture. The captured variables must outlive the lambda.

### Unintended copies of mutable lambdas

Because lambdas are objects, they can be copied. If you want to provide lambdas with mutable captured variables, pass them by reference using `std::ref`.

**Best practice:** Try to avoid mutable lambdas. Non-mutable lambdas are easier to understand and don't suffer from copy-related issues.

---

## 20.x — Chapter 20 summary and quiz

*Alex* December 4, 2015, 7:31 pm PST February 8, 2025

### Chapter Review

- Function arguments can be passed by value, reference or address.
- Values can be returned by value, reference, or address.
- Function pointers allow us to pass a function to another function.
- Dynamic memory is allocated on the heap.
- The call stack keeps track of all of the active functions.
- A recursive function is a function that calls itself. All recursive functions need a termination condition.
- Command line arguments allow users or other programs to pass data into our program at startup.
- Ellipsis allow you to pass a variable number of arguments to a function. However, ellipsis arguments suspend type checking.
- Lambda functions are functions that can be nested inside other functions. They don't need a name and are very useful in combination with the algorithms library.

### Quiz (Key Questions)

**Question #1:** Write function prototypes for max() taking two doubles, swap() swapping two ints, and getLargestElement() taking a dynamically allocated array.

**Question #2:** Identify issues with code snippets (returning reference to local, no termination condition in recursion, function redefinition, stack overflow arrays, string-to-int conversion).

**Question #3:** Write both iterative and recursive versions of binary search.

```cpp
int binarySearch(const int* array, int target, int min, int max)
{
    assert(array);

    while (min <= max)
    {
        int midpoint{ std::midpoint(min, max) };

        if (array[midpoint] > target)
            max = midpoint - 1;
        else if (array[midpoint] < target)
            min = midpoint + 1;
        else
            return midpoint;
    }
    
    return -1;
}
```
