from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class WindowConfig:
    width: int = 1400
    height: int = 820
    title: str = "C++ OOP 教学工具"


@dataclass(frozen=True)
class SplashConfig:
    duration_ms: int = 900


@dataclass(frozen=True)
class AudioConfig:
    enabled: bool = True
    music_volume: float = 0.28
    sfx_volume: float = 0.7
    music_dir: str = "Minecraft Sound Pack 1.17 - Sound Effects/music"


@dataclass(frozen=True)
class LevelsConfig:
    dir: str = "data/levels"
    index_file: str = "index.json"


@dataclass(frozen=True)
class SavesConfig:
    dir: str = "data/saves"


@dataclass(frozen=True)
class CanvasConfig:
    class_color: str = "#4A90D9"
    instance_color: str = "#E8A840"
    member_color: str = "#AAAAAA"
    error_color: str = "#FF4444"
    warning_color: str = "#FF8844"
    animation_duration_ms: int = 300
    class_column_x: int = 80
    instance_column_x: int = 500
    row_height: int = 60
    column_width: int = 200


@dataclass(frozen=True)
class UrlsConfig:
    teaching: str = "https://..."


@dataclass(frozen=True)
class Config:
    window: WindowConfig = field(default_factory=WindowConfig)
    splash: SplashConfig = field(default_factory=SplashConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    levels: LevelsConfig = field(default_factory=LevelsConfig)
    saves: SavesConfig = field(default_factory=SavesConfig)
    canvas: CanvasConfig = field(default_factory=CanvasConfig)
    urls: UrlsConfig = field(default_factory=UrlsConfig)


class ConfigLoader:
    @staticmethod
    def load(path: str | Path = "config.yaml") -> Config:
        path = Path(path)
        if not path.exists():
            return Config()

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return Config(
            window=WindowConfig(**data.get("window", {})),
            splash=SplashConfig(**data.get("splash", {})),
            audio=AudioConfig(**data.get("audio", {})),
            levels=LevelsConfig(**data.get("levels", {})),
            saves=SavesConfig(**data.get("saves", {})),
            canvas=CanvasConfig(**data.get("canvas", {})),
            urls=UrlsConfig(**data.get("urls", {})),
        )
