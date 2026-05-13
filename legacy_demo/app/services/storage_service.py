import json
from pathlib import Path

from app.models.session import WorldMeta


class StorageService:
    def __init__(self, save_dir: Path | None = None) -> None:
        self.save_dir = save_dir or Path("saves")
        self.worlds_file = self.save_dir / "worlds.json"
        self.save_dir.mkdir(exist_ok=True)

    def load_worlds(self) -> list[WorldMeta]:
        if not self.worlds_file.exists():
            return []
        with self.worlds_file.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return [WorldMeta.from_dict(item) for item in data]

    def save_world(self, world: WorldMeta) -> None:
        worlds = self.load_worlds()
        worlds = [item for item in worlds if item.id != world.id]
        worlds.append(world)
        self._write_worlds(worlds)

    def update_world_progress(self, world_id: str, lesson_id: str, completed: bool) -> None:
        if not completed or not lesson_id:
            return
        worlds = self.load_worlds()
        for world in worlds:
            if world.id == world_id and lesson_id not in world.completed_lessons:
                world.completed_lessons.append(lesson_id)
        self._write_worlds(worlds)

    def _write_worlds(self, worlds: list[WorldMeta]) -> None:
        with self.worlds_file.open("w", encoding="utf-8") as file:
            json.dump([world.to_dict() for world in worlds], file, ensure_ascii=False, indent=2)
