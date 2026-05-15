# Chapter 19 — Dynamic Allocation

## 19.1 — Dynamic memory allocation with new and delete

*Alex* July 13, 2007, 5:24 pm PDT January 1, 2025

### The need for dynamic memory allocation

C++ supports three basic types of memory allocation:

-   **Static memory allocation** happens for static and global variables. Memory for these types of variables is allocated once when your program is run and persists throughout the life of your program.
-   **Automatic memory allocation** happens for function parameters and local variables. Memory for these types of variables is allocated when the relevant block is entered, and freed when the block is exited.
-   **Dynamic memory allocation** is the topic of this article.

Both static and automatic allocation have two things in common:

-   The size of the variable / array must be known at compile time.
-   Memory allocation and deallocation happens automatically (when the variable is instantiated / destroyed).

However, you will come across situations where one or both of these constraints cause problems, usually when dealing with external (user or file) input. For example, we may want to use a string to hold someone's name, but we do not know how long their name is until they enter it.

If we have to declare the size of everything at compile time, the best we can do is try to make a guess the maximum size of variables we'll need and hope that's enough:

```cpp
char name[25]; // let's hope their name is less than 25 chars!
Record record[500]; // let's hope there are less than 500 records!
Monster monster[40]; // 40 monsters maximum
```

This is a poor solution because:
1. Wasted memory if the variables aren't actually used
2. Need to track which bits of memory are actually used
3. Stack memory is limited (typically ~1MB on Visual Studio). Stack overflow will result if exceeded
4. Artificial limitations and/or array overflows

Fortunately, these problems are easily addressed via dynamic memory allocation. **Dynamic memory allocation** is a way for running programs to request memory from the operating system when needed. This memory does not come from the program's limited stack memory -- instead, it is allocated from a much larger pool of memory managed by the operating system called the **heap**.

### Dynamically allocating single variables

To allocate a *single* variable dynamically, we use the scalar (non-array) form of the **new** operator:

```cpp
int* ptr{ new int }; // dynamically allocate an integer and assign the address to ptr
```

We can then dereference the pointer to access the memory:

```cpp
*ptr = 7; // assign value of 7 to allocated memory
```

### Initializing a dynamically allocated variable

When you dynamically allocate a variable, you can also initialize it via direct initialization or uniform initialization:

```cpp
int* ptr1{ new int (5) }; // use direct initialization
int* ptr2{ new int { 6 } }; // use uniform initialization
```

### Deleting a single variable

When we are done with a dynamically allocated variable, we need to explicitly tell C++ to free the memory for reuse. For single variables, this is done via the scalar (non-array) form of the **delete** operator:

```cpp
delete ptr; // return the memory pointed to by ptr to the operating system
ptr = nullptr; // set ptr to be a null pointer
```

The delete operator does not *actually* delete anything. It simply returns the memory being pointed to back to the operating system.

### Dangling pointers

C++ does not make any guarantees about what will happen to the contents of deallocated memory, or to the value of the pointer being deleted. A pointer that is pointing to deallocated memory is called a **dangling pointer**. Dereferencing or deleting a dangling pointer will lead to undefined behavior.

```cpp
#include <iostream>

int main()
{
    int* ptr{ new int }; // dynamically allocate an integer
    *ptr = 7; // put a value in that memory location

    delete ptr; // return the memory to the operating system. ptr is now a dangling pointer.

    std::cout << *ptr; // Dereferencing a dangling pointer will cause undefined behavior
    delete ptr; // trying to deallocate the memory again will also lead to undefined behavior.

    return 0;
}
```

Deallocating memory may create multiple dangling pointers:

```cpp
int* ptr{ new int{} };
int* otherPtr{ ptr }; // otherPtr is now pointed at that same memory location

delete ptr; // ptr and otherPtr are now dangling pointers.
ptr = nullptr; // ptr is now a nullptr
// however, otherPtr is still a dangling pointer!
```

**Best practice:** Set deleted pointers to nullptr unless they are going out of scope immediately afterward.
**Best practice:** Deleting a null pointer is okay, and does nothing. There is no need to conditionalize your delete statements.

### Operator new can fail

By default, if new fails, a *bad_alloc* exception is thrown. There's an alternate form of new that returns a null pointer if memory can't be allocated:

```cpp
int* value { new (std::nothrow) int }; // value will be set to a null pointer if the integer allocation fails
```

### Memory leaks

Dynamically allocated memory stays allocated until it is explicitly deallocated or until the program ends. This is called a **memory leak**. Memory leaks happen when your program loses the address of some bit of dynamically allocated memory before giving it back to the operating system.

```cpp
void doSomething()
{
    int* ptr{ new int{} };
} // ptr goes out of scope, but the allocated memory is never freed - memory leak!
```

Memory leaks can also occur if a pointer is reassigned without first deleting:

```cpp
int value = 5;
int* ptr{ new int{} }; // allocate memory
ptr = &value; // old address lost, memory leak results
```

This can be fixed by deleting the pointer before reassigning it.

---

## 19.2 — Dynamically allocating arrays

*Alex* August 18, 2015, 1:52 pm PDT November 20, 2023

In addition to dynamically allocating single values, we can also dynamically allocate arrays of variables. Unlike a fixed array, where the array size must be fixed at compile time, dynamically allocating an array allows us to choose an array length at runtime.

To allocate an array dynamically, we use the array form of new and delete (often called new[] and delete[]):

```cpp
#include <cstddef>
#include <iostream>

int main()
{
    std::cout << "Enter a positive integer: ";
    std::size_t length{};
    std::cin >> length;

    int* array{ new int[length]{} }; // use array new. Note that length does not need to be constant!

    std::cout << "I just allocated an array of integers of length " << length << '\n';

    array[0] = 5; // set element 0 to value 5

    delete[] array; // use array delete to deallocate array

    return 0;
}
```

The length of dynamically allocated arrays has type `std::size_t`.

### Dynamically deleting arrays

When deleting a dynamically allocated array, we have to use the array version of delete, which is delete[]. Using the scalar version of delete on an array will result in undefined behavior, such as data corruption, memory leaks, crashes, or other problems.

### Dynamic arrays are almost identical to fixed arrays

A dynamic array starts its life as a pointer that points to the first element of the array. Consequently, it has the same limitations in that it doesn't know its length or size. A dynamic array functions identically to a decayed fixed array, with the exception that the programmer is responsible for deallocating the dynamic array via the delete[] keyword.

### Initializing dynamically allocated arrays

If you want to initialize a dynamically allocated array to 0:

```cpp
int* array{ new int[length]{} };
```

Starting with C++11, it's now possible to initialize dynamic arrays using initializer lists:

```cpp
int* array{ new int[5]{ 9, 7, 5, 3, 1 } };
```

### Resizing arrays

C++ does not provide a built-in way to resize an array that has already been allocated. It is possible to work around this limitation by dynamically allocating a new array, copying the elements over, and deleting the old array. However, this is error prone. We recommend using `std::vector` instead.

### Quiz

Write a program that:
- Asks the user how many names they wish to enter.
- Dynamically allocates a `std::string` array.
- Asks the user to enter each name.
- Calls `std::sort` to sort the names.
- Prints the sorted list of names.

---

## 19.3 — Destructors

*Alex* September 6, 2007, 9:14 am PDT November 30, 2023

A **destructor** is another special kind of class member function that is executed when an object of that class is destroyed. Whereas constructors are designed to initialize a class, destructors are designed to help clean up.

When an object goes out of scope normally, or a dynamically allocated object is explicitly deleted using the delete keyword, the class destructor is automatically called (if it exists) to do any necessary clean up before the object is removed from memory.

If your class object is holding any resources (e.g. dynamic memory, or a file or database handle), or if you need to do any kind of maintenance before the object is destroyed, the destructor is the perfect place to do so.

### Destructor naming

Like constructors, destructors have specific naming rules:

1.  The destructor must have the same name as the class, preceded by a tilde (~).
2.  The destructor can not take arguments.
3.  The destructor has no return type.

A class can only have a single destructor.

### A destructor example

```cpp
#include <iostream>
#include <cassert>
#include <cstddef>

class IntArray
{
private:
	int* m_array{};
	int m_length{};

public:
	IntArray(int length) // constructor
	{
		assert(length > 0);

		m_array = new int[static_cast<std::size_t>(length)]{};
		m_length = length;
	}

	~IntArray() // destructor
	{
		// Dynamically delete the array we allocated earlier
		delete[] m_array;
	}

	void setValue(int index, int value) { m_array[index] = value; }
	int getValue(int index) { return m_array[index]; }

	int getLength() { return m_length; }
};

int main()
{
	IntArray ar ( 10 ); // allocate 10 integers
	for (int count{ 0 }; count < ar.getLength(); ++count)
		ar.setValue(count, count+1);

	std::cout << "The value of element 5 is: " << ar.getValue(5) << '\n';

	return 0;
} // ar is destroyed here, so the ~IntArray() destructor function is called here
```

### Constructor and destructor timing

The constructor is called when an object is created, and the destructor is called when an object is destroyed. Global variables are constructed before main() and destroyed after main().

### RAII

RAII (Resource Acquisition Is Initialization) is a programming technique whereby resource use is tied to the lifetime of objects with automatic duration. In C++, RAII is implemented via classes with constructors and destructors. A resource is typically acquired in the object's constructor and released in the destructor when the object is destroyed. The primary advantage of RAII is that it helps prevent resource leaks.

The IntArray class above is an example of a class that implements RAII. std::string and std::vector are examples of classes in the standard library that follow RAII.

### A warning about std::exit()

If you use the std::exit() function, your program will terminate and no destructors will be called. Be wary if you're relying on your destructors to do necessary cleanup work.

---

## 19.4 — Pointers to pointers and dynamic multidimensional arrays

*Alex* September 14, 2015, 3:44 pm PDT September 9, 2024

*This lesson is optional, for advanced readers who want to learn more about C++. No future lessons build on this lesson.*

### Pointers to pointers

A normal pointer to an int is declared using a single asterisk:

```cpp
int* ptr; // pointer to an int, one asterisk
```

A pointer to a pointer to an int is declared using two asterisks:

```cpp
int** ptrptr; // pointer to a pointer to an int, two asterisks
```

A pointer to a pointer works just like a normal pointer — you can dereference it to retrieve the value pointed to. And because that value is itself a pointer, you can dereference it again to get to the underlying value:

```cpp
int value { 5 };

int* ptr { &value };
std::cout << *ptr << '\n'; // Dereference pointer to int to get int value

int** ptrptr { &ptr };
std::cout << **ptrptr << '\n'; // dereference to get pointer to int, dereference again to get int value
```

Note that you can not set a pointer to a pointer directly to a value:

```cpp
int value { 5 };
int** ptrptr { &&value }; // not valid (address of operator requires an lvalue)
```

### Arrays of pointers

Pointers to pointers have a few uses. The most common use is to dynamically allocate an array of pointers:

```cpp
int** array { new int*[10] }; // allocate an array of 10 int pointers
```

### Two-dimensional dynamically allocated arrays

Unlike a two dimensional fixed array:

```cpp
int array[10][5];
```

Dynamically allocating a two-dimensional array is a little more challenging. If the rightmost array dimension is constexpr, you can do this:

```cpp
int x { 7 }; // non-constant
int (*array)[5] { new int[x][5] }; // rightmost dimension must be constexpr
```

Or using auto:

```cpp
auto array { new int[x][5] }; // so much simpler!
```

If the rightmost array dimension isn't a compile-time constant, we have to get a little more complicated:

```cpp
int** array { new int*[10] }; // allocate an array of 10 int pointers — these are our rows
for (int count { 0 }; count < 10; ++count)
    array[count] = new int[5]; // these are our columns
```

We can then access our array like usual:

```cpp
array[9][4] = 3; // This is the same as (array[9])[4] = 3;
```

With this method, because each array column is dynamically allocated independently, it's possible to make dynamically allocated two dimensional arrays that are not rectangular. For example, we can make a triangle-shaped array:

```cpp
int** array { new int*[10] };
for (int count { 0 }; count < 10; ++count)
    array[count] = new int[count+1]; // these are our columns
```

### Deallocating a dynamically allocated two-dimensional array

```cpp
for (int count { 0 }; count < 10; ++count)
    delete[] array[count];
delete[] array; // this needs to be done last
```

Note that we delete the array in the opposite order that we created it (elements first, then the array itself).

### Flattening a two-dimensional array

Because allocating and deallocating two-dimensional arrays is complex and easy to mess up, it's often easier to "flatten" a two-dimensional array (of size x by y) into a one-dimensional array of size x * y:

```cpp
int *array { new int[50] }; // a 10x5 array flattened into a single array
```

Simple math can then be used to convert a row and column index:

```cpp
int getSingleIndex(int row, int col, int numberOfColumnsInArray)
{
     return (row * numberOfColumnsInArray) + col;
}
```

### Conclusion

We recommend avoiding using pointers to pointers unless no other options are available, because they're complicated to use and potentially dangerous.

---

## 19.5 — Void pointers

*Alex* July 19, 2007, 2:07 pm PDT September 29, 2023

The **void pointer**, also known as the generic pointer, is a special type of pointer that can be pointed at objects of any data type! A void pointer is declared like a normal pointer, using the void keyword as the pointer's type:

```cpp
void* ptr {}; // ptr is a void pointer
```

A void pointer can point to objects of any data type:

```cpp
int nValue {};
float fValue {};

struct Something
{
    int n;
    float f;
};

Something sValue {};

void* ptr {};
ptr = &nValue; // valid
ptr = &fValue; // valid
ptr = &sValue; // valid
```

However, because the void pointer does not know what type of object it is pointing to, dereferencing a void pointer is illegal. Instead, the void pointer must first be cast to another pointer type before the dereference can be performed.

```cpp
int value{ 5 };
void* voidPtr{ &value };

// std::cout << *voidPtr << '\n'; // illegal: dereference of void pointer

int* intPtr{ static_cast<int*>(voidPtr) }; // however, if we cast our void pointer to an int pointer...

std::cout << *intPtr << '\n'; // then we can dereference the result
```

Here's an example of a void pointer in use:

```cpp
#include <cassert>
#include <iostream>

enum class Type
{
    tInt,
    tFloat,
    tCString
};

void printValue(void* ptr, Type type)
{
    switch (type)
    {
    case Type::tInt:
        std::cout << *static_cast<int*>(ptr) << '\n';
        break;
    case Type::tFloat:
        std::cout << *static_cast<float*>(ptr) << '\n';
        break;
    case Type::tCString:
        std::cout << static_cast<char*>(ptr) << '\n';
        break;
    default:
        std::cerr << "printValue(): invalid type provided\n"; 
        assert(false && "type not found");
        break;
    }
}

int main()
{
    int nValue{ 5 };
    float fValue{ 7.5f };
    char szValue[]{ "Mollie" };

    printValue(&nValue, Type::tInt);
    printValue(&fValue, Type::tFloat);
    printValue(szValue, Type::tCString);

    return 0;
}
```

### Void pointer miscellany

- Void pointers can be set to a null value: `void* ptr{ nullptr };`
- Deleting a void pointer will result in undefined behavior. If you need to delete a void pointer, `static_cast` it back to the appropriate type first.
- It is not possible to do pointer arithmetic on a void pointer.
- There is no such thing as a void reference.

### Conclusion

In general, it is a good idea to avoid using void pointers unless absolutely necessary, as they effectively allow you to avoid type checking. C++ actually offers much better ways to handle multiple data types (via function overloading and templates) that retain type checking.
