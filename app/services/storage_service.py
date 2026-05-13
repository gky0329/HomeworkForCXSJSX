from __future__ import annotations

import json
from pathlib import Path

from app.core.session import WorldMeta


class StorageService:

    def __init__(self, save_dir: str | Path = "saves") -> None:
        self._dir = Path(save_dir)
        self._file = self._dir / "worlds.json"
        self._dir.mkdir(parents=True, exist_ok=True)

    def load_worlds(self) -> list[WorldMeta]:
        if not self._file.exists():
            return []
        try:
            with open(self._file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [WorldMeta.from_dict(item) for item in data]
        except (json.JSONDecodeError, OSError):
            return []

    def save_world(self, world: WorldMeta) -> None:
        worlds = self.load_worlds()
        worlds = [w for w in worlds if w.id != world.id]
        worlds.append(world)
        self._write(worlds)

    def update_progress(self, world_id: str, lesson_id: str, completed: bool) -> None:
        if not completed or not lesson_id:
            return
        worlds = self.load_worlds()
        for w in worlds:
            if w.id == world_id and lesson_id not in w.completed_lessons:
                w.completed_lessons.append(lesson_id)
        self._write(worlds)

    def _write(self, worlds: list[WorldMeta]) -> None:
        try:
            with open(self._file, "w", encoding="utf-8") as f:
                json.dump([w.to_dict() for w in worlds], f, ensure_ascii=False, indent=2)
        except OSError:
            pass
