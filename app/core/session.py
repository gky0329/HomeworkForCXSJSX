from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class WorldType(str, Enum):
    CPP = "cpp"
    PYTHON = "python"
    MINECRAFT = "minecraft"


class GameMode(str, Enum):
    SURVIVAL = "survival"
    CREATIVE = "creative"


class Difficulty(str, Enum):
    PEACEFUL = "peaceful"
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    HARDCORE = "hardcore"


@dataclass
class WorldMeta:
    world_name: str
    world_type: WorldType
    game_mode: GameMode
    difficulty: Difficulty
    id: str = field(default_factory=lambda: uuid4().hex)
    completed_lessons: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorldMeta":
        return cls(
            id=data.get("id", uuid4().hex),
            world_name=data["world_name"],
            world_type=WorldType(data["world_type"]),
            game_mode=GameMode(data["game_mode"]),
            difficulty=Difficulty(data["difficulty"]),
            completed_lessons=data.get("completed_lessons", []),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "world_name": self.world_name,
            "world_type": self.world_type.value,
            "game_mode": self.game_mode.value,
            "difficulty": self.difficulty.value,
            "completed_lessons": self.completed_lessons,
        }


@dataclass
class Lesson:
    id: str
    title: str
    npc_dialogue: list[dict[str, str]]
    questions: list[dict[str, Any]]


@dataclass
class AppSession:
    current_world: WorldMeta | None = None
    current_lesson: Lesson | None = None
    hearts: int = 5
    max_hearts: int = 5
    skips_left: int = 2
    current_question_index: int = 0
    correct_count: int = 0
    answered_count: int = 0
    streak_count: int = 0

    def start_world(self, world: WorldMeta) -> None:
        self.current_world = world
        self.current_lesson = None

    def start_lesson(self, lesson: Lesson) -> None:
        self.current_lesson = lesson
        self.reset_quiz()

    def reset_quiz(self) -> None:
        self.current_question_index = 0
        self.correct_count = 0
        self.answered_count = 0
        self.streak_count = 0
        world = self.current_world
        self.max_hearts = 999 if world and world.game_mode == GameMode.CREATIVE else 5
        self.hearts = self.max_hearts
        self.skips_left = 999 if world and world.game_mode == GameMode.CREATIVE else 2

    def is_creative(self) -> bool:
        return bool(self.current_world and self.current_world.game_mode == GameMode.CREATIVE)
