# Chapter 18 — Iterators and Algorithms

## 18.1 — Sorting an array using selection sort

*Alex* July 3, 2007, 1:47 pm PDT September 11, 2023

### A case for sorting

Sorting an array is the process of arranging all of the elements in the array in a particular order. There are many different cases in which sorting an array can be useful. For example, your email program generally displays emails in order of time received, because more recent emails are typically considered more relevant. When you go to your contact list, the names are typically in alphabetical order, because it's easier to find the name you are looking for that way. Both of these presentations involve sorting data before presentation.

Sorting an array can make searching an array more efficient, not only for humans, but also for computers. For example, consider the case where we want to know whether a name appears in a list of names. In order to see whether a name was on the list, we'd have to check every element in the array to see if the name appears. For an array with many elements, searching through them all can be expensive.

However, now assume our array of names is sorted alphabetically. In this case, we only need to search up to the point where we encounter a name that is alphabetically greater than the one we are looking for. At that point, if we haven't found the name, we know it doesn't exist in the rest of the array, because all of the names we haven't looked at in the array are guaranteed to be alphabetically greater!

It turns out that there are even better algorithms to search sorted arrays. Using a simple algorithm, we can search a sorted array containing 1,000,000 elements using only 20 comparisons! The downside is, of course, that sorting an array is comparatively expensive, and it often isn't worth sorting an array in order to make searching fast unless you're going to be searching it many times.

In some cases, sorting an array can make searching unnecessary. Consider another example where we want to find the best test score. If the array is unsorted, we have to look through every element in the array to find the greatest test score. If the list is sorted, the best test score will be in the first or last position (depending on whether we sorted in ascending or descending order), so we don't need to search at all!

### How sorting works

Sorting is generally performed by repeatedly comparing pairs of array elements, and swapping them if they meet some predefined criteria. The order in which these elements are compared differs depending on which sorting algorithm is used. The criteria depends on how the list will be sorted (e.g. in ascending or descending order).

To swap two elements, we can use the std::swap() function from the C++ standard library, which is defined in the utility header.

```cpp
#include <iostream>
#include <utility>

int main()
{
    int x{ 2 };
    int y{ 4 };
    std::cout << "Before swap: x = " << x << ", y = " << y << '\n';
    std::swap(x, y); // swap the values of x and y
    std::cout << "After swap:  x = " << x << ", y = " << y << '\n';

    return 0;
}
```

This program prints:

Before swap: x = 2, y = 4
After swap:  x = 4, y = 2

Note that after the swap, the values of x and y have been interchanged!

### Selection sort

There are many ways to sort an array. Selection sort is probably the easiest sort to understand, which makes it a good candidate for teaching even though it is one of the slower sorts.

Selection sort performs the following steps to sort an array from smallest to largest:

1.  Starting at array index 0, search the entire array to find the smallest value
2.  Swap the smallest value found in the array with the value at index 0
3.  Repeat steps 1 & 2 starting from the next index

In other words, we're going to find the smallest element in the array, and swap it into the first position. Then we're going to find the next smallest element, and swap it into the second position. This process will be repeated until we run out of elements.

Here is an example of this algorithm working on 5 elements. Let's start with a sample array:

{ 30, 50, 20, 10, 40 }

First, we find the smallest element, starting from index 0:

{ 30, 50, 20, **10**, 40 }

We then swap this with the element at index 0:

{ **10**, 50, 20, **30**, 40 }

Now that the first element is sorted, we can ignore it. Now, we find the smallest element, starting from index 1:

{ *10*, 50, **20**, 30, 40 }

And swap it with the element in index 1:

{ *10*, **20**, **50**, 30, 40 }

Now we can ignore the first two elements. Find the smallest element starting at index 2:

{ *10*, *20*, 50, **30**, 40 }

And swap it with the element in index 2:

{ *10*, *20*, **30**, **50**, 40 }

Find the smallest element starting at index 3:

{ *10*, *20*, *30*, 50, **40** }

And swap it with the element in index 3:

{ *10*, *20*, *30*, **40**, **50** }

Finally, find the smallest element starting at index 4:

{ *10*, *20*, *30*, *40*, **50** }

And swap it with the element in index 4 (which doesn't do anything):

{ *10*, *20*, *30*, *40*, **50** }

Done!

{ 10, 20, 30, 40, 50 }

Note that the last comparison will always be with itself (which is redundant), so we can actually stop 1 element before the end of the array.

### Selection sort in C++

Here's how this algorithm is implemented in C++:

```cpp
#include <iostream>
#include <iterator>
#include <utility>

int main()
{
	int array[]{ 30, 50, 20, 10, 40 };
	constexpr int length{ static_cast<int>(std::size(array)) };

	// Step through each element of the array
	// (except the last one, which will already be sorted by the time we get there)
	for (int startIndex{ 0 }; startIndex < length - 1; ++startIndex)
	{
		// smallestIndex is the index of the smallest element we've encountered this iteration
		// Start by assuming the smallest element is the first element of this iteration
		int smallestIndex{ startIndex };

		// Then look for a smaller element in the rest of the array
		for (int currentIndex{ startIndex + 1 }; currentIndex < length; ++currentIndex)
		{
			// If we've found an element that is smaller than our previously found smallest
			if (array[currentIndex] < array[smallestIndex])
				// then keep track of it
				smallestIndex = currentIndex;
		}

		// smallestIndex is now the index of the smallest element in the remaining array
        // swap our start element with our smallest element (this sorts it into the correct place)
		std::swap(array[startIndex], array[smallestIndex]);
	}

	// Now that the whole array is sorted, print our sorted array as proof it works
	for (int index{ 0 }; index < length; ++index)
		std::cout << array[index] << ' ';

	std::cout << '\n';

	return 0;
}
```

The most confusing part of this algorithm is the loop inside of another loop (called a **nested loop**). The outside loop (startIndex) iterates through each element one by one. For each iteration of the outer loop, the inner loop (currentIndex) is used to find the smallest element in the remaining array (starting from startIndex+1). smallestIndex keeps track of the index of the smallest element found by the inner loop. Then smallestIndex is swapped with startIndex. Finally, the outer loop (startIndex) advances one element, and the process is repeated.

### std::sort

Because sorting arrays is so common, the C++ standard library includes a sorting function named `std::sort`. `std::sort` lives in the <algorithm> header, and can be invoked on an array like so:

```cpp
#include <algorithm> // for std::sort
#include <iostream>
#include <iterator> // for std::size

int main()
{
	int array[]{ 30, 50, 20, 10, 40 };

	std::sort(std::begin(array), std::end(array));

	for (int i{ 0 }; i < static_cast<int>(std::size(array)); ++i)
		std::cout << array[i] << ' ';

	std::cout << '\n';

	return 0;
}
```

By default, std::sort sorts in ascending order using operator< to compare pairs of elements and swapping them if necessary (much like our selection sort example does above).

### Quiz

**Question #1:** Manually show how selection sort works on the following array: { 30, 60, 20, 50, 40, 10 }.

**Question #2:** Rewrite the selection sort code above to sort in descending order (largest numbers first).

**Question #3:** Write bubble sort code. Bubble sort works by comparing adjacent pairs of elements, and swapping them if the criteria is met.

**Question #4:** Add two optimizations to the bubble sort algorithm: skip already-sorted elements and terminate early if no swaps occurred.

---

## 18.2 — Introduction to iterators

*Alex* December 17, 2019, 10:38 am PST February 11, 2025

Iterating through an array (or other structure) of data is quite a common thing to do in programming. And so far, we've covered many different ways to do so: with loops and an index (`for-loops` and `while loops`), with pointers and pointer arithmetic, and with `range-based for-loops`:

```cpp
#include <array>
#include <cstddef>
#include <iostream>

int main()
{
    // In C++17, the type of variable arr is deduced to std::array<int, 7>
    std::array arr{ 0, 1, 2, 3, 4, 5, 6 };
    std::size_t length{ std::size(arr) };

    // while-loop with explicit index
    std::size_t index{ 0 };
    while (index < length)
    {
        std::cout << arr[index] << ' ';
        ++index;
    }
    std::cout << '\n';

    // for-loop with explicit index
    for (index = 0; index < length; ++index)
    {
        std::cout << arr[index] << ' ';
    }
    std::cout << '\n';

    // for-loop with pointer (Note: ptr can't be const, because we increment it)
    for (auto ptr{ &arr[0] }; ptr != (&arr[0] + length); ++ptr)
    {
        std::cout << *ptr << ' ';
    }
    std::cout << '\n';

    // range-based for loop
    for (int i : arr)
    {
        std::cout << i << ' ';
    }
    std::cout << '\n';

    return 0;
}
```

Looping using indexes is more typing than needed if we only use the index to access elements. It also only works if the container (e.g. the array) provides direct access to elements (which arrays do, but some other types of containers, such as lists, do not).

Looping with pointers and pointer arithmetic is verbose, and can be confusing to readers who don't know the rules of pointer arithmetic. Pointer arithmetic also only works if elements are consecutive in memory.

Range-based for-loops are a little more interesting, as the mechanism for iterating through our container is hidden -- and yet, they still work for all kinds of different structures (arrays, lists, trees, maps, etc…). How do these work? They use iterators.

### Iterators

An **iterator** is an object designed to traverse through a container (e.g. the values in an array, or the characters in a string), providing access to each element along the way.

A container may provide different kinds of iterators. For example, an array container might offer a forwards iterator that walks through the array in forward order, and a reverse iterator that walks through the array in reverse order.

Once the appropriate type of iterator is created, the programmer can then use the interface provided by the iterator to traverse and access elements without having to worry about what kind of traversal is being done or how the data is being stored in the container. And because C++ iterators typically use the same interface for traversal (operator++ to move to the next element) and access (operator\* to access the current element), we can iterate through a wide variety of different container types using a consistent method.

### Pointers as an iterator

The simplest kind of iterator is a pointer, which (using pointer arithmetic) works for data stored sequentially in memory:

```cpp
#include <array>
#include <iostream>

int main()
{
    std::array arr{ 0, 1, 2, 3, 4, 5, 6 };

    auto begin{ &arr[0] };
    auto end{ begin + std::size(arr) };

    for (auto ptr{ begin }; ptr != end; ++ptr)
    {
        std::cout << *ptr << ' ';
    }
    std::cout << '\n';

    return 0;
}
```

### Standard library iterators

Iterating is such a common operation that all standard library containers offer direct support for iteration. Instead of calculating our own begin and end points, we can simply ask the container for the begin and end points via member functions conveniently named `begin()` and `end()`:

```cpp
#include <array>
#include <iostream>

int main()
{
    std::array array{ 1, 2, 3 };

    auto begin{ array.begin() };
    auto end{ array.end() };

    for (auto p{ begin }; p != end; ++p)
    {
        std::cout << *p << ' ';
    }
    std::cout << '\n';

    return 0;
}
```

The `iterator` header also contains two generic functions (`std::begin` and `std::end`) that can be used.

### operator< vs operator!= for iterators

With iterators, it is conventional to use `operator!=` to test whether the iterator has reached the end element:

```cpp
    for (auto p{ begin }; p != end; ++p)
```

This is because some iterator types are not relationally comparable. `operator!=` works with all iterator types.

### Back to range-based for loops

All types that have both `begin()` and `end()` member functions, or that can be used with `std::begin()` and `std::end()`, are usable in range-based for-loops.

Behind the scenes, the range-based for-loop calls `begin()` and `end()` of the type to iterate over.

### Iterator invalidation (dangling iterators)

Much like pointers and references, iterators can be left "dangling" if the elements being iterated over change address or are destroyed. When this happens, we say the iterator has been **invalidated**. Accessing an invalidated iterator produces undefined behavior.

Some operations that modify containers (such as adding an element to a `std::vector`) can have the side effect of causing the elements in the container to change addresses. When this happens, existing iterators to those elements will be invalidated.

Since range-based for-loops use iterators behind the scenes, we must be careful not to do anything that invalidates the iterators of the container we are actively traversing:

```cpp
#include <vector>

int main()
{
    std::vector v { 0, 1, 2, 3 };

    for (auto num : v) // implicitly iterates over v
    {
        if (num % 2 == 0)
            v.push_back(num + 1); // when this invalidates the iterators of v, undefined behavior will result
    }

    return 0;
}
```

Invalidated iterators can be revalidated by assigning a valid iterator to them (e.g. `begin()`, `end()`, or the return value of some other function that returns an iterator).

The `erase()` function returns an iterator to the element one past the erased element (or `end()` if the last element was removed):

```cpp
#include <iostream>
#include <vector>

int main()
{
	std::vector v{ 1, 2, 3, 4, 5, 6, 7 };

	auto it{ v.begin() };

	++it; // move to second element
	std::cout << *it << '\n';

	it = v.erase(it); // erase the element currently being iterated over, set `it` to next element

	std::cout << *it << '\n'; // now ok, prints 3

	return 0;
}
```

---

## 18.3 — Introduction to standard library algorithms

*nascardriver* January 3, 2020, 5:04 am PST September 4, 2024

New programmers typically spend a lot of time writing custom loops to perform relatively simple tasks, such as sorting or counting or searching arrays. These loops can be problematic, both in terms of how easy it is to make an error, and in terms of overall maintainability, as loops can be hard to understand.

Because searching, counting, and sorting are such common operations to do, the C++ standard library comes with a bunch of functions to do these things in just a few lines of code. Additionally, these standard library functions come pre-tested, are efficient, work on a variety of different container types, and many support parallelization.

The functionality provided in the algorithms library generally fall into one of three categories:

-   **Inspectors** -- Used to view (but not modify) data in a container. Examples include searching and counting.
-   **Mutators** -- Used to modify data in a container. Examples include sorting and shuffling.
-   **Facilitators** -- Used to generate a result based on values of the data members.

These algorithms live in the [algorithms](https://en.cppreference.com/w/cpp/algorithm) library.

### std::find

[`std::find`](https://en.cppreference.com/w/cpp/algorithm/find) searches for the first occurrence of a value in a container. `std::find` takes 3 parameters: an iterator to the starting element in the sequence, an iterator to the ending element in the sequence, and a value to search for. It returns an iterator pointing to the element (if it is found) or the end of the container (if the element is not found).

```cpp
#include <algorithm>
#include <array>
#include <iostream>

int main()
{
    std::array arr{ 13, 90, 99, 5, 40, 80 };

    std::cout << "Enter a value to search for and replace with: ";
    int search{};
    int replace{};
    std::cin >> search >> replace;

    auto found{ std::find(arr.begin(), arr.end(), search) };

    if (found == arr.end())
    {
        std::cout << "Could not find " << search << '\n';
    }
    else
    {
        *found = replace;
    }

    for (int i : arr)
    {
        std::cout << i << ' ';
    }

    std::cout << '\n';

    return 0;
}
```

### std::find_if

The `std::find_if` function works similarly to `std::find`, but instead of passing in a specific value to search for, we pass in a callable object, such as a function pointer (or a lambda). For each element being iterated over, `std::find_if` will call this function (passing the element as an argument to the function), and the function can return `true` if a match is found, or `false` otherwise.

```cpp
#include <algorithm>
#include <array>
#include <iostream>
#include <string_view>

bool containsNut(std::string_view str)
{
    return str.find("nut") != std::string_view::npos;
}

int main()
{
    std::array<std::string_view, 4> arr{ "apple", "banana", "walnut", "lemon" };

    auto found{ std::find_if(arr.begin(), arr.end(), containsNut) };

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

### std::count and std::count_if

[`std::count`](https://en.cppreference.com/w/cpp/algorithm/count) and `std::count_if` search for all occurrences of an element or an element fulfilling a condition.

```cpp
#include <algorithm>
#include <array>
#include <iostream>
#include <string_view>

bool containsNut(std::string_view str)
{
	return str.find("nut") != std::string_view::npos;
}

int main()
{
	std::array<std::string_view, 5> arr{ "apple", "banana", "walnut", "lemon", "peanut" };

	auto nuts{ std::count_if(arr.begin(), arr.end(), containsNut) };

	std::cout << "Counted " << nuts << " nut(s)\n";

	return 0;
}
```

### std::sort custom sort

There's a version of `std::sort` that takes a function as its third parameter that allows us to sort however we like:

```cpp
#include <algorithm>
#include <array>
#include <iostream>

bool greater(int a, int b)
{
    return (a > b);
}

int main()
{
    std::array arr{ 13, 90, 99, 5, 40, 80 };

    std::sort(arr.begin(), arr.end(), greater);

    for (int i : arr)
    {
        std::cout << i << ' ';
    }

    std::cout << '\n';

    return 0;
}
```

Tip: Because sorting in descending order is so common, C++ provides `std::greater` for that too:

```cpp
  std::sort(arr.begin(), arr.end(), std::greater{});
```

### std::for_each

[`std::for_each`](https://en.cppreference.com/w/cpp/algorithm/for_each) takes a list as input and applies a custom function to every element:

```cpp
#include <algorithm>
#include <array>
#include <iostream>

void doubleNumber(int& i)
{
    i *= 2;
}

int main()
{
    std::array arr{ 1, 2, 3, 4 };

    std::for_each(arr.begin(), arr.end(), doubleNumber);

    for (int i : arr)
    {
        std::cout << i << ' ';
    }

    std::cout << '\n';

    return 0;
}
```

With `std::for_each`, our intentions are clear. Additionally, `std::for_each` can skip elements at the beginning or end of a container, and can be parallelized.

### Performance and order of execution

Many of the algorithms in the algorithms library make some kind of guarantee about how they will execute. The following algorithms guarantee sequential execution: `std::for_each`, `std::copy`, `std::copy_backward`, `std::move`, and `std::move_backward`.

### Ranges in C++20

C++20 adds *ranges*, which allow us to simply pass the container (e.g. `arr`) instead of `arr.begin()` and `arr.end()`.

**Best practice:** Favor using functions from the algorithms library over writing your own functionality to do the same thing.

---

## 18.4 — Timing your code

*Alex* January 4, 2018, 3:10 pm PST October 31, 2023

When writing your code, sometimes you'll run across cases where you're not sure whether one method or another will be more performant. One easy way is to time your code to see how long it takes to run. C++11 comes with some functionality in the chrono library to do just that.

Here's a reusable Timer class:

```cpp
#include <chrono> // for std::chrono functions

class Timer
{
private:
	using Clock = std::chrono::steady_clock;
	using Second = std::chrono::duration<double, std::ratio<1> >;
	
	std::chrono::time_point<Clock> m_beg { Clock::now() };

public:
	void reset()
	{
		m_beg = Clock::now();
	}
	
	double elapsed() const
	{
		return std::chrono::duration_cast<Second>(Clock::now() - m_beg).count();
	}
};
```

To use it, we instantiate a Timer object at the top of our main function, and then call the elapsed() member function whenever we want to know how long the program took to run to that point.

```cpp
#include <iostream>

int main()
{
    Timer t;

    // Code to time goes here

    std::cout << "Time elapsed: " << t.elapsed() << " seconds\n";

    return 0;
}
```

### Performance comparison example

Using the selection sort algorithm on 10000 elements, the author's machine produced timings of ~0.05 seconds. Using std::sort from the standard library on the same data produced results of ~0.0007 seconds. In other words, std::sort is roughly 100 times faster than the hand-written selection sort!

### Things that can impact performance

-   **Use a release build target**, not a debug build target. Debug build targets typically turn optimization off.
-   **Background processes** can influence results. Shut down as many apps as possible before measuring.
-   **Random number generators** can cause variance. Seed with a literal value for consistent results.
-   **Don't time user input.** If user input is required, provide input from a file or command line.

### Measuring performance

When measuring the performance of your program, gather at least 3 results. If the results are all similar, these likely represent the actual performance of your program on that machine.

On a single machine, relative performance measurements can be useful. We can gather performance results from several different variants of a program to determine which variant is the most performant. After measuring the second variant, a good sanity check is to measure the first variant again.
