from dataclasses import dataclass
from pathlib import Path

from app.theme.config import Assets


@dataclass(frozen=True)
class MusicTrack:
    title: str
    path: Path
    dimension: str
    mood: str


class MusicLibrary:
    AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".mp4"}

    OVERWORLD_CALM = {
        "minecraft",
        "clark",
        "sweden",
        "subwoofer lullaby",
        "living mice",
        "haggstrom",
        "danny",
        "key",
        "oxygene",
        "dry hands",
        "wet hands",
        "mice on venus",
        "an ordinary day",
        "comforting memories",
        "floating dream",
        "infinite amethyst",
        "left to bloom",
        "one more day",
        "stand tall",
        "wending",
        "shuniji",
        "axolotl",
        "dragon fish",
        "biome fest",
        "blind spots",
        "haunt muskie",
        "aria math",
        "dreiton",
        "taswell",
        "mutation",
        "moog city",
        "moog city 2",
        "beginning",
        "beginning 2",
        "floating trees",
    }
    OVERWORLD_TENSE = {"11", "thirteen", "ward", "mellohi", "death"}
    NETHER_CALM = {"warmth", "ballad of the cats", "chrysopoeia", "rubedo", "so below"}
    NETHER_TENSE = {"concrete halls", "dead voxel", "pigstep"}
    END_CALM = {"alpha"}
    END_TENSE = {"boss", "the end"}

    def __init__(self, music_dir: Path | None = None) -> None:
        self.music_dir = music_dir or Assets.MUSIC_LIBRARY
        self.tracks = self._scan()

    def select(self, dimension: str = "overworld", mood: str = "calm") -> list[Path]:
        direct = [track.path for track in self.tracks if track.dimension == dimension and track.mood == mood]
        if direct:
            return direct
        same_mood = [track.path for track in self.tracks if track.mood == mood]
        if same_mood:
            return same_mood
        return [track.path for track in self.tracks]

    def _scan(self) -> list[MusicTrack]:
        if not self.music_dir.exists():
            return []
        tracks = []
        for path in self.music_dir.rglob("*"):
            if path.is_file() and path.suffix.lower() in self.AUDIO_EXTENSIONS:
                title = self._title_from_filename(path)
                dimension, mood = self._classify(title)
                tracks.append(MusicTrack(title=title, path=path, dimension=dimension, mood=mood))
        return tracks

    def _title_from_filename(self, path: Path) -> str:
        stem = path.stem.replace("_音频", "")
        if "_" in stem:
            return stem.rsplit("_", 1)[-1].strip()
        return stem.strip()

    def _classify(self, title: str) -> tuple[str, str]:
        normalized = title.lower().strip()
        if normalized in self.NETHER_TENSE:
            return "nether", "tense"
        if normalized in self.NETHER_CALM:
            return "nether", "calm"
        if normalized in self.END_TENSE:
            return "end", "tense"
        if normalized in self.END_CALM:
            return "end", "calm"
        if normalized in self.OVERWORLD_TENSE:
            return "overworld", "tense"
        return "overworld", "calm"
