# Roadshow Demo Script

Use the `Roadshow Demo` option in the Code Editor example dropdown. It is a real C++ snippet designed to show the current visualizer clearly and quickly, not a hardcoded trace.

## What It Demonstrates

- Basic scalar variables: `total`, `sound`, `done`
- Stack pointer edge: `focus -> total`
- Stack object member pointers: `second.next -> first`
- Heap object state from `vector<unique_ptr<Node>>`
- Heap member pointer edge: `nodes[0]->next -> second`
- Polymorphism through `unique_ptr<Animal>` holding a runtime `Dog`
- `std::optional<Node>` and `std::variant<int, Node>` nested object values
- Stable canvas auto-fit across steps

## Suggested Talk Track

1. Click `Roadshow Demo`, then `Run`.
2. Step through the scalar setup: point out that stack values update line by line.
3. Stop at `int* focus = &total;`: explain stack-to-stack pointer visualization.
4. Step through `Node first` and `Node second`: show object member rows and the `second.next -> first` edge.
5. Step through `vector<unique_ptr<Node>>`: show a smart pointer element cell pointing to a heap `Node` block.
6. Step through `unique_ptr<Animal> pet = make_unique<Dog>(...)`: show the heap block resolves to runtime `Dog`, including base `Animal` metadata.
7. Step through `optional<Node>` and `variant<int, Node>`: show nested object values with member pointer edges.

## Demo Code

```cpp
#include <memory>
#include <optional>
#include <variant>
#include <vector>
using namespace std;
struct Node { int value; Node* next; };
class Animal { public: int age; virtual int speak() { return age; } virtual ~Animal() {} };
class Dog : public Animal { public: int bones; Dog(int a, int b) { age = a; bones = b; } int speak() override { return age + bones; } };
int total = 42;
int* focus = &total;
*focus = 52;
Node first{1, nullptr};
Node second{2, &first};
second.next->value = 5;
vector<unique_ptr<Node>> nodes;
nodes.push_back(make_unique<Node>(Node{3, &second}));
nodes[0]->next->next->value = 8;
unique_ptr<Animal> pet = make_unique<Dog>(4, 6);
int sound = pet->speak();
optional<Node> maybe = Node{7, &first};
maybe->next->value = 9;
variant<int, Node> either = Node{10, &second};
int done = first.value + second.value + sound;
```
