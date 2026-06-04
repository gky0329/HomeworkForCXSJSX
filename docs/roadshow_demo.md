# Roadshow Demo Script

Use the `Roadshow Demo` option in the Code Editor example dropdown. It is a real C++ snippet designed to show the current visualizer clearly and quickly, not a hardcoded trace.

## What It Demonstrates

- Basic scalar variables: `total`, `average`
- Array visualization: `scores[3]`
- Stack pointer edge: `focus -> total`
- Stack object state: `alice`
- Heap object state: `mentor`
- Heap scalar allocation: `reward`
- Freed/dangling memory state after `delete`
- Stable canvas auto-fit across steps

## Suggested Talk Track

1. Click `Roadshow Demo`, then `Run`.
2. Step through the scalar and array setup: point out that stack values update line by line.
3. Stop at `int* focus = &total;`: explain stack-to-stack pointer visualization.
4. Step through `Student alice`: show object member rows and the object summary line.
5. Step through `new Student()` and `new int(...)`: show heap blocks and pointer edges.
6. Step through both `delete` lines: show freed/dangling memory, which is one of the most teachable C++ concepts.

## Demo Code

```cpp
class Student {
public:
  int score;
  double progress;
};
int scores[3] = {72, 85, 91};
int total = scores[0] + scores[1] + scores[2];
double average = total / 3.0;
int* focus = &total;
*focus = total + 5;
Student alice;
alice.score = 88;
alice.progress = 0.75;
Student* mentor = new Student();
mentor->score = alice.score + 7;
mentor->progress = 0.95;
int* reward = new int(mentor->score);
*reward = *reward + 2;
delete reward;
delete mentor;
```
