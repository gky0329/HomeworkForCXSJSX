# Future Sprint — Complex C++ Code Support

> Created: 2026-05-15 | Target: Post-MVP Sprint 2 or 3

## Problem

Current MVP LLM prompt supports only 7 memory-level statement types:
```
int a = 42;       // variable declaration
int* p;           // pointer declaration
p = &a;           // address-of
*p = 100;         // deref write
p = new int(5);   // heap alloc
delete p;         // memory free
{ ... }           // scope block
```

Full C++ programs (classes, STL containers, loops, conditionals, functions, IO streams) produce garbled or invalid JSON from the LLM, causing Pydantic validation failure with an opaque error in the status bar.

## Requirements

### 1. Extend LLM prompt for complex C++

| Category | Examples to support |
|----------|---------------------|
| Expressions | `a + b`, `*p + 1`, `arr[i]`, `obj.member` |
| Control flow | `if`/`else`, `for`, `while`, `switch` — skip or simulate path |
| Functions | `int foo(int x)` — track call stack, params, return value |
| Arrays | `int arr[5]`, stack-allocated |
| Structs/Classes | `struct S { int x; }; S s; s.x = 1;` — member addresses |
| STL | `vector<int> v; v.push_back(42);` — treat as heap-managed |
| Pointers to stack | `int* p = &a;` (already supported in MVP) |
| References | `int& r = a;` — alias tracking |
| `new[]` / `delete[]` | Array heap allocation |
| Smart pointers | `unique_ptr`, `shared_ptr` (stretch goal) |

### 2. Improved error UX

When LLM returns invalid JSON:
- [ ] Show a user-visible error dialog (not just status bar)
- [ ] Display the raw LLM response for debugging
- [ ] Offer to retry or fall back
- [ ] Warn user if input code is too complex for MVP (e.g., >50 lines, contains `#include`, `class`, `struct`)

### 3. Step-by-step LLM execution strategy

Instead of asking LLM to parse the entire program in one shot, consider:
- **Pre-process**: strip comments, normalize whitespace
- **Split**: break into individual statements
- **Batch**: send each statement to LLM with previous memory state as context
- **Accumulate**: build ExecutionTrace incrementally

This trades latency for accuracy and scales to larger programs.

## Test cases that should eventually work

### Basic
```cpp
int a = 5;
int b = a + 3;
int* p = &b;
*p = *p * 2;
```

### Loops
```cpp
int sum = 0;
for (int i = 1; i <= 3; i++) {
    sum += i;
}
```

### Structs
```cpp
struct Point { int x; int y; };
Point p;
p.x = 10;
p.y = 20;
```

### Arrays
```cpp
int arr[3] = {1, 2, 3};
int* p = &arr[1];
*p = 99;
```

### Warcraft-style simulation (long-term goal)
```cpp
struct Warrior { int hp, atk; };
Warrior w1, w2;
w1.hp = 100; w1.atk = 20;
w2.hp = 80;  w2.atk = 30;
Warrior* attacker = &w1;
Warrior* defender = &w2;
defender->hp -= attacker->atk;
```

## Dependencies
- Refactor `prompt_templates.py` — extend or create new templates per category
- Refactor `ai_executor.py` — support incremental step accumulation
- Add `code_preprocessor.py` — statement splitting, complexity detection
- Add `app/ui/widgets/error_dialog.py` — structured error display

---

## Future File Format — PowerPoint (.pptx)

> Target: Post-MVP | Priority: Low

### Scope
Add `.pptx` extraction to `app/services/file_service.py`, enabling users to upload lecture slides and have AI extract knowledge points and quiz questions.

### Technical approach
- **Library**: `python-pptx` — read slide shapes, extract text from paragraphs, tables, and text frames
- **Challenges**:
  - Slides often contain images/diagrams — text-only extraction may miss visual concepts
  - Text may be scattered across multiple text boxes in arbitrary order — need smart ordering (by position on slide)
  - Slide notes may contain lecture commentary — optionally include
- **Extraction strategy**:
  1. Iterate slides in order
  2. For each slide, collect all text shapes sorted by (y, x) position
  3. Optionally include slide notes
  4. Prefix each slide with `[Slide N]` marker in output
- **Integration**: register `".pptx"` extension in `HANDLERS` dict in `file_service.py`, add `EXT_PPTX` extractor function

### Example

```python
def _extract_pptx(path: Path) -> str:
    from pptx import Presentation
    prs = Presentation(str(path))
    lines = []
    for i, slide in enumerate(prs.slides):
        lines.append(f"[Slide {i + 1}]")
        shapes = sorted(
            [s for s in slide.shapes if s.has_text_frame],
            key=lambda s: (s.top or 0, s.left or 0)
        )
        for shape in shapes:
            text = shape.text_frame.text.strip()
            if text:
                lines.append(text)
    return "\n\n".join(lines)
```

### Dependencies
- `pip install python-pptx`
- Add `python-pptx>=0.6` to `requirements.txt`
