# Chapter 21 — Operator Overloading

## 21.1 — Introduction to operator overloading

*Alex* September 24, 2007, 2:23 pm PDT September 11, 2023

In C++, operators are implemented as functions. By using function overloading on the operator functions, you can define your own versions of the operators that work with different data types (including classes that you've written). Using function overloading to overload operators is called **operator overloading**.

### Operators as functions

```cpp
int x { 2 };
int y { 3 };
std::cout << x + y << '\n';
```

The expression `x + y` can be translated in your head to the function call `operator+(x, y)`.

### Resolving overloaded operators

When evaluating an expression containing an operator, the compiler uses the following rules:

-   If *all* of the operands are fundamental data types, the compiler will call a built-in routine if one exists.
-   If *any* of the operands are program-defined types, the compiler will use the function overload resolution algorithm to see if it can find an overloaded operator.

### Limitations on operator overloading

- Almost any existing operator in C++ can be overloaded. The exceptions are: conditional (?:), sizeof, scope (::), member selector (.), pointer member selector (.\*), typeid, and the casting operators.
- You can only overload the operators that exist. You can not create new operators or rename existing operators.
- At least one of the operands in an overloaded operator must be a user-defined type.
- It is not possible to change the number of operands an operator supports.
- All operators keep their default precedence and associativity.

**Best practice:** When overloading operators, it's best to keep the function of the operators as close to the original intent of the operators as possible.

**Best practice:** If the meaning of an overloaded operator is not clear and intuitive, use a named function instead.

**Best practice:** Operators that do not modify their operands (e.g. arithmetic operators) should generally return results by value. Operators that modify their leftmost operand (e.g. pre-increment, any of the assignment operators) should generally return the leftmost operand by reference.

---

## 21.2 — Overloading the arithmetic operators using friend functions

*Alex* September 26, 2007, 11:36 am PDT October 21, 2024

Some of the most commonly used operators in C++ are the arithmetic operators -- that is, the plus operator (+), minus operator (-), multiplication operator (\*), and division operator (/). All of the arithmetic operators are binary operators.

There are three different ways to overload operators: the member function way, the friend function way, and the normal function way.

### Overloading operators using friend functions

```cpp
#include <iostream>

class Cents
{
private:
	int m_cents {};

public:
	Cents(int cents) : m_cents{ cents } { }

	friend Cents operator+(const Cents& c1, const Cents& c2);

	int getCents() const { return m_cents; }
};

Cents operator+(const Cents& c1, const Cents& c2)
{
	return c1.m_cents + c2.m_cents;
}

int main()
{
	Cents cents1{ 6 };
	Cents cents2{ 8 };
	Cents centsSum{ cents1 + cents2 };
	std::cout << "I have " << centsSum.getCents() << " cents.\n";

	return 0;
}
```

### Friend functions can be defined inside the class

```cpp
class Cents
{
private:
	int m_cents {};

public:
	explicit Cents(int cents) : m_cents{ cents } { }

	friend Cents operator+(const Cents& c1, const Cents& c2)
	{
		return Cents { c1.m_cents + c2.m_cents };
	}

	int getCents() const { return m_cents; }
};
```

### Overloading operators for operands of different types

When the operands have different types, x + y does not call the same function as y + x. For example, `Cents(4) + 6` would call operator+(Cents, int), and `6 + Cents(4)` would call operator+(int, Cents). Consequently, whenever we overload binary operators for operands of different types, we actually need to write two functions -- one for each case.

It is often possible to define overloaded operators by calling other overloaded operators. For example `operator+(int, MinMax)` can be implemented as `return m + value;`.

---

## 21.3 — Overloading operators using normal functions

*Alex* May 23, 2016, 4:27 pm PDT September 11, 2023

If you don't need direct access to private members, you can write your overloaded operators as normal functions:

```cpp
#include <iostream>

class Cents
{
private:
  int m_cents{};

public:
  Cents(int cents)
    : m_cents{ cents }
  {}

  int getCents() const { return m_cents; }
};

Cents operator+(const Cents& c1, const Cents& c2)
{
  return Cents{ c1.getCents() + c2.getCents() };
}
```

With the normal function version, you'll have to provide your own function prototype in a header file.

**Best practice:** Prefer overloading operators as normal functions instead of friends if it's possible to do so without adding additional functions.

---

## 21.4 — Overloading the I/O operators

*Alex* October 1, 2007, 4:41 pm PDT January 29, 2025

### Overloading operator<<

Consider the expression `std::cout << point`. The left operand is the `std::cout` object (type `std::ostream`), and the right operand is your class object.

```cpp
#include <iostream>

class Point
{
private:
    double m_x{};
    double m_y{};
    double m_z{};

public:
    Point(double x=0.0, double y=0.0, double z=0.0)
      : m_x{x}, m_y{y}, m_z{z}
    {
    }

    friend std::ostream& operator<< (std::ostream& out, const Point& point);
};

std::ostream& operator<< (std::ostream& out, const Point& point)
{
    out << "Point(" << point.m_x << ", " << point.m_y << ", " << point.m_z << ')';
    return out; // return std::ostream so we can chain calls
}
```

By returning the `out` parameter as the return type, `(std::cout << point)` returns `std::cout`, allowing chaining: `std::cout << point << '\n'`.

### Overloading operator>>

```cpp
std::istream& operator>> (std::istream& in, Point& point)
{
    in >> point.m_x >> point.m_y >> point.m_z;
    return in;
}
```

### Guarding against partial extraction

A **transactional operation** must either completely succeed or completely fail -- no partial successes or failures are allowed. To implement this for operator>>:

```cpp
std::istream& operator>> (std::istream& in, Point& point)
{
    double x{};
    double y{};
    double z{};
    
    in >> x >> y >> z;
    point = in ? Point{x, y, z} : Point{};
        
    return in;
}
```

### Handling semantically invalid input

To manually put the input stream in failure mode for semantically invalid input, call `std::cin.setstate(std::ios_base::failbit);`.

---

## 21.5 — Overloading operators using member functions

*Alex* October 11, 2007, 10:22 am PDT October 30, 2023

When overloading an operator using a member function:

-   The overloaded operator must be added as a member function of the left operand.
-   The left operand becomes the implicit \*this object
-   All other operands become function parameters.

```cpp
#include <iostream>

class Cents
{
private:
    int m_cents {};

public:
    Cents(int cents) : m_cents { cents } { }

    Cents operator+(int value) const;

    int getCents() const { return m_cents; }
};

Cents Cents::operator+ (int value) const
{
    return Cents { m_cents + value };
}
```

### When to use normal, friend, or member function overload

-   Assignment (=), subscript ([]), function call (()), or member selection (->): **member function**
-   Unary operator: **member function**
-   Binary operator that does not modify its left operand (e.g. operator+): **normal function** (preferred) or friend function
-   Binary operator that modifies its left operand, but you can't modify the left operand's class (e.g. operator<<): **normal function** (preferred) or friend function
-   Binary operator that modifies its left operand (e.g. operator+=) and you can modify the left operand: **member function**

---

## 21.6 — Overloading unary operators +, -, and !

*Alex* October 8, 2007, 3:09 pm PDT November 25, 2023

The positive (+), negative (-) and logical not (!) operators all are unary operators. Because they only operate on the object they are applied to, typically unary operator overloads are implemented as member functions.

### Overloading operator-

```cpp
#include <iostream>

class Cents
{
private:
    int m_cents {};
 
public:
    Cents(int cents): m_cents{cents} {}
 
    Cents operator-() const;

    int getCents() const { return m_cents; }
};
 
Cents Cents::operator-() const
{
    return -m_cents;
}

int main()
{
    const Cents nickle{ 5 };
    std::cout << "A nickle of debt is worth " << (-nickle).getCents() << " cents\n";
    return 0;
}
```

### Overloading operator!

```cpp
class Point
{
private:
    double m_x {};
    double m_y {};
    double m_z {};
 
public:
    Point(double x=0.0, double y=0.0, double z=0.0):
        m_x{x}, m_y{y}, m_z{z}
    {
    }
 
    Point operator- () const;
    bool operator! () const;
};

Point Point::operator- () const
{
    return { -m_x, -m_y, -m_z };
}

bool Point::operator! () const
{
    return (m_x == 0.0 && m_y == 0.0 && m_z == 0.0);
}
```

---

## 21.7 — Overloading the comparison operators

*Alex* October 4, 2007, 5:10 pm PDT February 7, 2024

Because the comparison operators are all binary operators that do not modify their left operands, we will make our overloaded comparison operators friend functions.

```cpp
#include <iostream>
#include <string>
#include <string_view>

class Car
{
private:
    std::string m_make;
    std::string m_model;

public:
    Car(std::string_view make, std::string_view model)
        : m_make{ make }, m_model{ model }
    {
    }

    friend bool operator== (const Car& c1, const Car& c2);
    friend bool operator!= (const Car& c1, const Car& c2);
};

bool operator== (const Car& c1, const Car& c2)
{
    return (c1.m_make == c2.m_make && c1.m_model == c2.m_model);
}

bool operator!= (const Car& c1, const Car& c2)
{
    return (c1.m_make != c2.m_make || c1.m_model != c2.m_model);
}
```

**Best practice:** Only define overloaded operators that make intuitive sense for your class.

### Minimizing comparative redundancy

Many of the comparison operators can be implemented using the other comparison operators:

-   operator!= can be implemented as !(operator==)
-   operator> can be implemented as operator< with the order of the parameters flipped
-   operator>= can be implemented as !(operator<)
-   operator<= can be implemented as !(operator>)

This means that we only need to implement logic for operator== and operator<, and then the other four comparison operators can be defined in terms of those two.

### The spaceship operator <=> (C++20)

C++20 introduces the spaceship operator (`operator<=>`), which allows us to reduce the number of comparison functions we need to write down to 2 at most, and sometimes just 1.

---

## 21.8 — Overloading the increment and decrement operators

*Alex* October 15, 2007, 8:19 am PDT November 25, 2023

There are actually two versions of the increment and decrement operators: a prefix increment and decrement (e.g. `++x; --y;`) and a postfix increment and decrement (e.g. `x++; y--;`).

### Overloading prefix increment and decrement

Prefix increment and decrement are overloaded exactly the same as any normal unary operator:

```cpp
Digit& Digit::operator++()
{
    if (m_digit == 9)
        m_digit = 0;
    else
        ++m_digit;

    return *this;
}
```

### Overloading postfix increment and decrement

The compiler looks to see if the overloaded operator has an int parameter. If the overloaded operator has an int parameter, the operator is a postfix overload. If the overloaded operator has no parameter, the operator is a prefix overload.

```cpp
Digit Digit::operator++(int) // int parameter means postfix
{
    Digit temp{*this}; // save current state
    ++(*this);         // use prefix to increment
    return temp;        // return saved state
}
```

Note that the postfix operators are typically less efficient than the prefix operators because of the added overhead of instantiating a temporary variable and returning by value instead of reference.

---

## 21.9 — Overloading the subscript operator

*Alex* October 19, 2007, 9:50 am PDT February 2, 2025

The subscript operator is one of the operators that must be overloaded as a member function. An overloaded operator[] function will always take one parameter: the subscript.

```cpp
#include <iostream>

class IntList
{
private:
    int m_list[10]{};

public:
    int& operator[] (int index)
    {
        return m_list[index];
    }
};

int main()
{
    IntList list{};
    list[2] = 3; // set a value
    std::cout << list[2] << '\n'; // get a value

    return 0;
}
```

### Why operator[] returns a reference

Because the subscript operator has a higher precedence than the assignment operator, `list[2]` evaluates first. By returning a reference, the compiler is satisfied that we are returning an l-value.

### Const version

```cpp
class IntList
{
public:
    int& operator[] (int index)              // For non-const objects
    {
        return m_list[index];
    }

    const int& operator[] (int index) const  // For const objects
    {
        return m_list[index];
    }
};
```

### Detecting index validity

```cpp
int& operator[] (int index)
{
    assert(index >= 0 && static_cast<std::size_t>(index) < std::size(m_list));
    return m_list[index];
}
```

### Pointers to objects and overloaded operator[] don't mix

If you try to call operator[] on a pointer to an object, C++ will assume you're trying to index an array of objects of that type. The proper syntax would be to dereference the pointer first: `(*list)[2] = 3;`

The function parameter does not need to be an integral type -- you can define that your overloaded operator[] take a value of any type you desire (e.g. std::string).

---

## 21.10 — Overloading the parenthesis operator

*Alex* October 25, 2007, 1:19 pm PDT November 14, 2024

The parenthesis operator (operator()) is a particularly interesting operator in that it allows you to vary both the type AND number of parameters it takes.

There are two things to keep in mind: first, the parenthesis operator must be implemented as a member function. Second, in non-object-oriented C++, the () operator is used to call functions.

### Indexing multidimensional arrays

```cpp
class Matrix
{
private:
    double m_data[4][4]{};

public:
    double& operator()(int row, int col);
};

double& Matrix::operator()(int row, int col)
{
    assert(row >= 0 && row < 4);
    assert(col >= 0 && col < 4);
    return m_data[row][col];
}
```

Now we can declare a Matrix and access its elements like this:

```cpp
Matrix matrix;
matrix(1, 2) = 4.5;
std::cout << matrix(1, 2) << '\n';
```

### Functors

Operator() is also commonly overloaded to implement **functors** (or **function objects**), which are classes that operate like functions. The advantage of a functor over a normal function is that functors can store data in member variables.

```cpp
class Accumulator
{
private:
    int m_counter{ 0 };

public:
    int operator() (int i) { return (m_counter += i); }
};

int main()
{
    Accumulator acc{};
    std::cout << acc(1) << '\n'; // prints 1
    std::cout << acc(3) << '\n'; // prints 4
    
    return 0;
}
```

Because the () operator is so flexible, it can be tempting to use it for many different purposes. However, this is strongly discouraged, since the () symbol does not really give any indication of what the operator is doing.

---

## 21.11 — Overloading typecasts

*Alex* October 30, 2007, 12:54 pm PDT March 14, 2025

By default, C++ doesn't know how to convert any of our program-defined classes. Overloading the typecast operators comes into play for defining conversions from our class types to other types.

```cpp
class Cents
{
private:
    int m_cents{};
public:
    Cents(int cents=0) : m_cents{ cents } { }

    // Overloaded int cast
    operator int() const { return m_cents; }

    int getCents() const { return m_cents; }
    void setCents(int cents) { m_cents = cents; }
};
```

- Overloaded typecasts must be non-static members, and should be `const` so they can be used with const objects.
- Overloaded typecasts do not have explicit parameters.
- Overloaded typecast do not declare a return type. The name of the conversion is used as the return type.

### Explicit typecasts

Just like we can make constructors `explicit`, we can also make our overloaded typecasts `explicit`:

```cpp
explicit operator int() const { return m_cents; } // now marked as explicit
```

**Best practice:** Typecasts should be generally be marked as explicit. Exceptions can be made in cases where the conversion inexpensively converts to a similar user-defined type.

### When to use converting constructors vs overloaded typecasts

- A converting constructor is a member function of class type B that defines how B is created from A.
- An overloaded typecast is a member function of class type A that defines how A is converted to B.

**Best practice:** When possible, prefer converting constructors, and avoid overloaded typecasts.

There are a few cases where an overloaded typecast should be used instead:
-   When providing a conversion to a fundamental type.
-   When the conversion returns a reference or const reference.
-   When providing a conversion to a type you can't add members to.
-   When you do not want the type being constructed to be aware of the type being converted from (helpful for avoiding circular dependencies).

---

## 21.12 — Overloading the assignment operator

*Alex* June 5, 2016, 10:51 am PDT July 22, 2024

The **copy assignment operator** (operator=) is used to copy values from one object to another *already existing object*.

### Copy assignment vs Copy constructor

-   If a new object has to be created before the copying can occur, the copy constructor is used (note: this includes passing or returning objects by value).
-   If a new object does not have to be created before the copying can occur, the assignment operator is used.

### Overloading the assignment operator

The copy assignment operator must be overloaded as a member function.

```cpp
Fraction& Fraction::operator= (const Fraction& fraction)
{
    // self-assignment guard
    if (this == &fraction)
        return *this;

    // do the copy
    m_numerator = fraction.m_numerator;
    m_denominator = fraction.m_denominator;

    // return the existing object so we can chain this operator
    return *this;
}
```

### Issues due to self-assignment

C++ allows self-assignment: `f1 = f1;`. In cases where an assignment operator needs to dynamically assign memory, self-assignment can actually be dangerous.

### Detecting and handling self-assignment

```cpp
MyString& MyString::operator= (const MyString& str)
{
	// self-assignment check
	if (this == &str)
		return *this;
    // rest of copy...
}
```

### The implicit copy assignment operator

Unlike other operators, the compiler will provide an implicit public copy assignment operator for your class if you do not provide a user-defined one. This assignment operator does memberwise assignment.

You can prevent assignments by using the delete keyword:

```cpp
Fraction& operator= (const Fraction& fraction) = delete; // no copies through assignment!
```

---

## 21.13 — Shallow vs. deep copying

*Alex* November 9, 2007, 3:39 pm PST September 11, 2023

### Shallow copying

Because C++ does not know much about your class, the default copy constructor and default assignment operators it provides use a copying method known as a memberwise copy (also known as a **shallow copy**). When classes are simple (e.g. do not contain any dynamically allocated memory), this works very well.

However, when designing classes that handle dynamically allocated memory, memberwise (shallow) copying can get us in a lot of trouble! This is because shallow copies of a pointer just copy the address of the pointer -- it does not allocate any memory or copy the contents being pointed to!

### Deep copying

A **deep copy** allocates memory for the copy and then copies the actual value, so that the copy lives in distinct memory from the source. This way, the copy and source are distinct and will not affect each other in any way.

```cpp
void MyString::deepCopy(const MyString& source)
{
    delete[] m_data;

    m_length = source.m_length;

    if (source.m_data)
    {
        m_data = new char[m_length];
        for (int i{ 0 }; i < m_length; ++i)
            m_data[i] = source.m_data[i];
    }
    else
        m_data = nullptr;
}
```

### The rule of three

If a class requires a user-defined destructor, copy constructor, or copy assignment operator, then it probably requires all three. This is because if we're user-defining any of these functions, it's probably because we're dealing with dynamic memory allocation.

### Summary

-   The default copy constructor and default assignment operators do shallow copies, which is fine for classes that contain no dynamically allocated variables.
-   Classes with dynamically allocated variables need to have a copy constructor and assignment operator that do a deep copy.
-   Favor using classes in the standard library over doing your own memory management.

---

## 21.14 — Overloading operators and function templates

*Alex* April 29, 2008, 8:14 pm PDT September 11, 2023

When we try to use function templates with program-defined types, the instantiated functions may not compile because our actual class types don't support those operators.

For example, a `max` function template that uses `operator<`:

```cpp
template <typename T>
const T& max(const T& x, const T& y)
{
    return (x < y) ? y : x;
}
```

To get around this problem, simply overload `operator<` for any class we wish to use `max` with:

```cpp
friend bool operator< (const Cents& c1, const Cents& c2)
{
    return (c1.m_cents < c2.m_cents);
}
```

Similarly, for an `average` function template that uses `operator+=` and `operator/=`:

```cpp
Cents& operator+= (const Cents &cents)
{
    m_cents += cents.m_cents;
    return *this;
}

Cents& operator/= (int x)
{
    m_cents /= x;
    return *this;
}
```

Note that we didn't have to modify `average()` at all to make it work with objects of type `Cents`. We simply had to define the operators used to implement `average()` for the `Cents` class, and the compiler took care of the rest!

---

## 21.x — Chapter 21 summary and quiz

*Alex* August 9, 2016, 2:44 pm PDT December 28, 2024

### Summary

Operator overloading is a variant of function overloading that lets you overload operators for your classes. When operators are overloaded, the intent of the operators should be kept as close to the original intent of the operators as possible.

**Rules of thumb for which form to use:**

-   Assignment (=), subscript ([]), function call (()), or member selection (->): **member function**
-   Unary operator: **member function**
-   Binary operator that modifies its left operand (e.g. operator+=): **member function** if you can
-   Binary operator that does not modify its left operand (e.g. operator+): **normal function** or friend function

Typecasts can be overloaded to provide conversion functions. A copy constructor is a special type of constructor used to initialize an object from another object of the same type. The assignment operator can be overloaded to allow assignment to your class.

**Quiz highlights:**

- **Average class:** Keep track of the average of all integers passed to it using `operator+=`.
- **IntArray class:** Dynamically allocated integer array with deep copying.
- **FixedPoint2 class:** Fixed point number with two fractional digits, including constructors from integers and doubles, arithmetic operators, comparison operators, and I/O operators.

```cpp
class FixedPoint2
{
private:
	std::int16_t m_base{};
	std::int8_t m_decimal{};

public:
	FixedPoint2(std::int16_t base = 0, std::int8_t decimal = 0);
	FixedPoint2(double d);
	explicit operator double() const;
	
	friend bool operator==(const FixedPoint2&, const FixedPoint2&);
	FixedPoint2 operator-() const;
};

FixedPoint2 operator+(const FixedPoint2& fp1, const FixedPoint2& fp2);
std::ostream& operator<<(std::ostream& out, const FixedPoint2& fp);
std::istream& operator>>(std::istream& in, FixedPoint2& fp);
```

---

## 21.y — Chapter 21 project (15 Puzzle)

*Alex* March 30, 2023, 1:02 pm PDT September 13, 2024

### Project: 15 Puzzle Game

In 15 Puzzle, you begin with a randomized 4×4 grid of tiles. 15 of the tiles have numbers 1 through 15. One tile is missing.

Commands: w (up), a (left), s (down), d (right), q (quit)

The game is built in stages:

**Step 1: Design** - Plan classes: `Tile`, `Board`, `Point`, `Direction`, `UserInput`

**Step 2: Tile class** - Individual tile with display number, isEmpty(), getNum(), operator<<

**Step 3: Board class** - 4×4 grid of tiles, solved initial state, operator<< for display

**Step 4: User input** - Command loop with validation, quit command handling

**Step 5: Direction class** - Enum for up/down/left/right, operator-, random direction, char-to-Direction conversion

**Step 6: Point class** - {x, y} coordinates with getAdjacentPoint(), operator==/!=

**Step 7: Tile sliding** - moveTile(Direction), swapTiles(), getEmptyTilePos(), isValidTilePos()

**Step 8: Game completion** - randomize() via random moves, playerWon() check, win message

Key classes and their roles:

- **Tile**: Stores a single tile number, handles display formatting
- **Board**: 4×4 grid, randomization, sliding, win detection
- **Point**: {x, y} coordinate pair for indexing
- **Direction**: Cardinal direction abstraction with random generation
- **UserInput**: Command validation and input processing

The randomization is done by sliding tiles in random directions (rather than shuffling numbers) to ensure the puzzle is always solvable.
