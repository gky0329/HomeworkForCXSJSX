import json
from pathlib import Path

from app.models.session import Lesson


class LessonService:
    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or Path("data/levels")

    def load_level(self, level_id: str) -> Lesson:
        path = self.data_dir / f"{level_id}.json"
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return Lesson(
            id=data["id"],
            title=data["title"],
            npc_dialogue=data.get("npc_dialogue", []),
            questions=data.get("questions", []),
        )
