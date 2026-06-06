# Mac Demo Runbook

Use the Mac build for the recorded demo. It avoids Windows debugger variance and
uses the stable LLDB/DWARF path that exercises the real rendering pipeline.

## Preflight

Run from a clean checkout of `main`:

```bash
python -m pip install -r requirements.txt
python tools/native_debug_smoke.py --list-backends --json
python tools/native_debug_smoke.py --backend lldb-dwarf --case basic_double --case inherited_virtual_object --case roadshow_native_demo
```

Expected:

- `lldb-dwarf` is `available: true`.
- All three smoke cases print `PASS`.
- `roadshow_native_demo` reports rendered canvas items.

## Recording Setup

```bash
python main.py
```

The Code Editor now opens with `Roadshow Demo` selected by default. For the main
recording path:

1. Open `Code Editor`.
2. Click `Run`.
3. Use `PageDown` for controlled stepping.
4. Keep `Auto Fit` off during stepping so the canvas position stays stable.
5. Use the fit button only when starting a new trace or after manually dragging.

## 90-Second Talk Track

1. Start at the first scalar step: show `total` on the stack.
2. Step to `int* focus = &total;`: point out the stack pointer edge.
3. Step through `Node first` and `Node second`: show object members and
   `second.next -> first`.
4. Step through `vector<unique_ptr<Node>>`: show smart pointer elements pointing
   to heap object blocks.
5. Step to `unique_ptr<Animal> pet = make_unique<Dog>(4, 6);`: show runtime
   `Dog` metadata, base `Animal`, and the vtable rows.
6. Step to `int sound = pet->speak();`: show polymorphic dispatch producing `10`.
7. Finish with `optional<Node>` / `variant<int, Node>` to frame the product as a
   broader C++ learning workbench, not just a pointer visualizer.

## Fallback

If the app tries the AI path, the status bar will say `AI provider` or
`AI fallback...`. For the recorded demo, stop and fix the LLDB preflight first;
the Mac recording should use `Native debugger: LLDB / DWARF`.
