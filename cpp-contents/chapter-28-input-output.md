# Chapter 28 — Input and Output (I/O)

## 28.1 — Input and output (I/O) streams

Input and output functionality is not defined as part of the core C++ language, but rather is provided through the C++ standard library (std namespace).

**Streams**: A **stream** is just a sequence of bytes that can be accessed sequentially. Over time, a stream may produce or consume potentially unlimited amounts of data.

- **Input streams** hold input from a data producer (keyboard, file, network)
- **Output streams** hold output for a data consumer (monitor, file, printer)

The nice thing about streams is the programmer only has to learn how to interact with the streams to read and write data to many different kinds of devices.

**Input/output in C++**:
- **istream**: primary class for input streams, uses extraction operator (>>)
- **ostream**: primary class for output streams, uses insertion operator (<<)
- **iostream**: handles both input and output, allowing bidirectional I/O

**Standard streams in C++**:
1. **cin** -- istream tied to standard input (keyboard)
2. **cout** -- ostream tied to standard output (monitor)
3. **cerr** -- ostream tied to standard error (unbuffered output)
4. **clog** -- ostream tied to standard error (buffered output)

## 28.2 — Input with istream

**The extraction operator (>>)**: Reads information from an input stream. C++ has predefined extraction operations for all built-in data types.

**setw manipulator**: Limits the number of characters read from a stream (in `<iomanip>` header):

```cpp
char buf[10]{};
std::cin >> std::setw(10) >> buf; // reads max 9 chars (leaves room for terminator)
```

**Extraction and whitespace**: The extraction operator skips whitespace (blanks, tabs, and newlines).

**Useful istream functions**:

- **get()**: Gets a character from the input stream (does NOT skip whitespace)
- **get(char*, int)**: Reads up to n-1 characters into a buffer (does not extract newline)
- **getline(char*, int)**: Reads up to n-1 characters and extracts/discards the delimiter
- **std::getline(std::cin, std::string)**: Special version for std::string (in `<string>` header)
- **gcount()**: Returns number of characters extracted by the last unformatted input operation
- **ignore()**: Discards the first character in the stream; `ignore(int nCount)` discards nCount characters
- **peek()**: Reads a character from the stream without removing it
- **unget()**: Returns the last character read back into the stream
- **putback(char ch)**: Puts a character back into the stream

## 28.3 — Output with ostream and ios

**Formatting**: Two ways to change formatting options -- flags and manipulators.

**Flags** are boolean variables that can be turned on and off using `setf()` and `unsetf()`:

```cpp
std::cout.setf(std::ios::showpos); // turn on + sign for positive numbers
std::cout.setf(std::ios::showpos | std::ios::uppercase); // multiple flags
std::cout.unsetf(std::ios::showpos); // turn off
```

**Format groups**: Groups of mutually exclusive flags. Use the two-parameter form of `setf()`:

```cpp
std::cout.setf(std::ios::hex, std::ios::basefield); // only hex is set
```

**Manipulators** are objects placed in a stream that affect formatting:

```cpp
std::cout << std::hex << 27 << '\n'; // print in hex
std::cout << std::dec << 29 << '\n'; // back to decimal
```

**Useful formatters**:

| Group | Flag/Manipulator | Meaning |
|---|---|---|
| boolalpha | std::boolalpha / std::noboolalpha | Print "true"/"false" or 0/1 |
| showpos | std::showpos / std::noshowpos | Prefix + for positive numbers |
| uppercase | std::uppercase / std::nouppercase | Use upper/lower case letters |
| basefield | std::dec / std::hex / std::oct | Print in decimal/hex/octal |

**Precision, notation, and decimal points**:

- `std::fixed` / `std::scientific`: Use decimal or scientific notation
- `std::showpoint` / `std::noshowpoint`: Show/hide decimal point and trailing zeros
- `std::setprecision(int)`: Sets the precision of floating-point numbers

**Width, fill characters, and justification**:

- `std::setw(int)`: Sets the field width (only affects the next output)
- `std::setfill(char)`: Sets the fill character
- `std::left`, `std::right`, `std::internal`: Justification options

## 28.4 — Stream classes for strings

Stream classes for strings allow you to use the familiar insertion (<<) and extraction (>>) operators to work with strings. They are not connected to an I/O channel.

There are six stream classes: istringstream, ostringstream, stringstream (and their wide char variants). Include the `<sstream>` header.

**Getting data into a stringstream**:
1. Use the insertion (<<) operator: `os << "en garde!\n";`
2. Use the str(string) function: `os.str("en garde!");`

**Getting data out of a stringstream**:
1. Use the str() function: `std::cout << os.str();`
2. Use the extraction (>>) operator to iterate through extractable values

**Conversion between strings and numbers**:

```cpp
// Number to string
std::stringstream os {};
os << nValue << ' ' << dValue;

// String to number
os >> nValue >> dValue;
```

**Clearing a stringstream for reuse**:
1. `os.str("");` or `os.str(std::string{});` -- erase the buffer
2. `os.clear();` -- reset error flags

## 28.5 — Stream states and input validation

**Stream states** (flags in ios_base):

| Flag | Meaning |
|---|---|
| goodbit | Everything is okay |
| badbit | Fatal error occurred |
| eofbit | Stream has reached end of file |
| failbit | Non-fatal error occurred |

**Member functions** to check states:

| Function | Meaning |
|---|---|
| good() | Returns true if goodbit is set |
| bad() | Returns true if badbit is set |
| eof() | Returns true if eofbit is set |
| fail() | Returns true if failbit is set |
| clear() | Clears all flags, restores to goodbit |
| rdstate() | Returns currently set flags |
| setstate(state) | Sets the state flag passed in |

**Input validation**: The process of checking whether user input meets some set of criteria.

**String validation**: Step through each character and ensure it meets validation criteria. Use `std::all_of` or `std::ranges::all_of` with character classification functions from `<cctype>`:

- `std::isalnum(int)` -- letter or digit
- `std::isalpha(int)` -- letter
- `std::isdigit(int)` -- digit
- `std::isspace(int)` -- whitespace
- `std::isxdigit(int)` -- hexadecimal digit
- etc.

**Numeric validation**: Use extraction operator and check failbit. Remember to:
1. `std::cin.clear()` to reset state bits
2. `std::cin.ignore()` to clear bad input from stream
3. Check `std::cin.gcount()` to handle mixed numeric/alphabetic input

**Alternative approach**: Read input as a string, then try to convert to numeric type using `std::from_chars`.

## 28.6 — Basic file I/O

There are 3 basic file I/O classes (in `<fstream>` header):
- **ifstream** (derived from istream) -- file input
- **ofstream** (derived from ostream) -- file output
- **fstream** (derived from iostream) -- file input/output

**File output**:

```cpp
std::ofstream outf{ "Sample.txt" };
if (!outf) { /* error handling */ }
outf << "This is line 1\n";
outf << "This is line 2\n";
// automatically closed when outf goes out of scope
```

**File input**:

```cpp
std::ifstream inf{ "Sample.txt" };
if (!inf) { /* error handling */ }
std::string strInput{};
while (std::getline(inf, strInput))
    std::cout << strInput << '\n';
```

**Buffered output**: Output may be buffered (not written to disk immediately). Use `ostream::flush()` or `std::flush` to flush manually. Note: `std::endl` also flushes the output stream.

**File modes** (ios flags):

| Mode | Meaning |
|---|---|
| app | Opens in append mode |
| ate | Seeks to end of file before reading/writing |
| binary | Opens in binary mode |
| in | Opens in read mode (default for ifstream) |
| out | Opens in write mode (default for ofstream) |
| trunc | Erases the file if it already exists |

```cpp
std::ofstream outf{ "Sample.txt", std::ios::app }; // append mode
```

**Explicitly opening files using open()**:

```cpp
std::ofstream outf{ "Sample.txt" };
outf << "This is line 1\n";
outf.close();
outf.open("Sample.txt", std::ios::app);
outf << "This is line 3\n";
outf.close();
```

## 28.7 — Random file I/O

**The file pointer**: Each file stream class contains a file pointer that keeps track of the current read/write position within the file.

**Random file access** is done using:
- **seekg()** (for input -- "seek get")
- **seekp()** (for output -- "seek put")

Both take an offset and an ios seek flag:

| Seek flag | Meaning |
|---|---|
| beg | Offset relative to beginning of file |
| cur | Offset relative to current position |
| end | Offset relative to end of file |

```cpp
inf.seekg(14, std::ios::cur);  // move forward 14 bytes
inf.seekg(-18, std::ios::cur); // move backwards 18 bytes
inf.seekg(22, std::ios::beg);  // move to 22nd byte in file
inf.seekg(0, std::ios::end);   // move to end of file
```

**Warning**: In a text file, seeking to a position other than the beginning may result in unexpected behavior due to different newline encodings (CR+LF on Windows, LF on Unix).

**tellg() and tellp()**: Return the absolute position of the file pointer. This can be used to determine file size:

```cpp
inf.seekg(0, std::ios::end);
std::cout << inf.tellg(); // prints file size in bytes
```

**Reading and writing at the same time using fstream**: After switching between read and write, you must perform a seek operation:

```cpp
iofile.seekg(iofile.tellg(), std::ios::beg); // seek to current position
```

**Other useful file functions**:
- `remove()` -- delete a file
- `is_open()` -- returns true if the stream is currently open

**Warning about writing pointers to disk**: Do not write memory addresses to files. Variable addresses may differ from execution to execution, making stored addresses invalid.
