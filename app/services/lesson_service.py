from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.session import Lesson


class LessonService:

    def __init__(self, levels_dir: str | Path = "data/levels") -> None:
        self._dir = Path(levels_dir)

    def load(self, level_id: str) -> Lesson | None:
        path = self._dir / f"{level_id}.json"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Lesson(
                id=data["id"],
                title=data.get("title", data["id"]),
                npc_dialogue=data.get("npc_dialogue", []),
                questions=data.get("questions", []),
            )
        except (json.JSONDecodeError, OSError, KeyError):
            return None

    def list_levels(self) -> list[str]:
        if not self._dir.exists():
            return []
        files = sorted(self._dir.glob("*.json"))
        return [f.stem for f in files if f.name != "index.json"]

    def load_index(self) -> list[dict[str, Any]]:
        path = self._dir / "index.json"
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
