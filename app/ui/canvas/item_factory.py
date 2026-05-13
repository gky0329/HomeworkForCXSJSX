from __future__ import annotations

from app.core.state_diff import StateDiff
from app.ui.canvas.oop_canvas import OopCanvas


def apply_diff(canvas: OopCanvas, diff: StateDiff) -> None:
    canvas.apply(diff)
