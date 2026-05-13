import random
from pathlib import Path

from PySide6.QtCore import QPropertyAnimation, QUrl
from PySide6.QtWidgets import QApplication

from app.services.music_library import MusicLibrary
from app.theme.config import Assets

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QSoundEffect
except ModuleNotFoundError:
    QAudioOutput = None
    QMediaPlayer = None
    QSoundEffect = None


class AudioManager:
    def __init__(self) -> None:
        self.effects: dict[str, list[Path]] = {}
        self.music_output = QAudioOutput() if QAudioOutput else None
        self.music_player = QMediaPlayer() if QMediaPlayer else None
        self.music_fade = QPropertyAnimation(self.music_output, b"volume") if self.music_output else None
        if self.music_output:
            self.music_output.setVolume(0.0)
        if self.music_player and self.music_output:
            self.music_player.setAudioOutput(self.music_output)
            self.music_player.mediaStatusChanged.connect(self._handle_music_status)
        self.current_music_mood = ""
        self.current_dimension = "overworld"
        self.target_music_volume = 0.28
        self.pending_music_track: Path | None = None
        self.one_shots = []
        self.effect_pools = {}
        self.effect_pool_index = {}
        self.music_library = MusicLibrary()

        self._load_effect("button", Assets.BUTTON_SOUNDS)
        self._load_effect("xp", Assets.XP_SOUNDS)
        self._load_effect("level_up", Assets.LEVEL_UP_SOUNDS)
        self._load_effect("hurt", Assets.HURT_SOUNDS)
        self._load_effect("complete", Assets.CHALLENGE_COMPLETE_SOUNDS)

    def play_button(self) -> None:
        self._play_effect("button", 0.65, beep=True)

    def play_xp(self) -> None:
        self._play_effect("xp", 0.7)

    def play_level_up(self) -> None:
        self._play_effect("level_up", 0.75)

    def play_hurt(self) -> None:
        self._play_effect("hurt", 0.8)

    def play_death(self) -> None:
        death = self._choose_existing(Assets.DEATH_SOUNDS)
        if death:
            self._play_one_shot(death, 0.8)
        else:
            # Placeholder for popular death-cry assets when the user provides one locally.
            QApplication.beep()

    def play_challenge_complete(self) -> None:
        self._play_effect("complete", 0.8)

    def play_startup_music(self) -> None:
        self.play_music("overworld", "calm")

    def play_quiz_music(self, critical: bool) -> None:
        if critical:
            self.play_music(self.current_dimension, "tense")
        else:
            self.play_music(self.current_dimension, "calm")

    def play_music(self, dimension: str = "overworld", mood: str = "calm") -> None:
        if mood == "tense":
            fallbacks = Assets.CRITICAL_MUSIC_FALLBACKS
            folder = Assets.CRITICAL_MUSIC
        else:
            fallbacks = Assets.HEALTHY_MUSIC_FALLBACKS
            folder = Assets.HEALTHY_MUSIC
        library_tracks = self.music_library.select(dimension, mood)
        tracks = self._audio_files(folder) or library_tracks or [path for path in fallbacks if path.exists()]
        self._play_music_tracks(tracks, f"{dimension}:{mood}")

    def _load_effect(self, name: str, candidates: list[Path]) -> None:
        paths = [path for path in candidates if path.exists()]
        self.effects[name] = paths
        self.effect_pools[name] = self._build_player_pool(paths[:1], pool_size=4 if name == "button" else 2)
        self.effect_pool_index[name] = 0

    def _play_effect(self, name: str, volume: float, beep: bool = False) -> None:
        pool = self.effect_pools.get(name, [])
        if pool:
            index = self.effect_pool_index.get(name, 0) % len(pool)
            self.effect_pool_index[name] = index + 1
            player, output = pool[index]
            output.setVolume(volume)
            player.stop()
            player.setPosition(0)
            player.play()
        elif self.effects.get(name):
            self._play_one_shot(random.choice(self.effects[name]), volume)
        elif beep:
            QApplication.beep()

    def _build_player_pool(self, paths: list[Path], pool_size: int) -> list:
        if not paths or not QMediaPlayer or not QAudioOutput:
            return []
        pool = []
        path = paths[0]
        for _ in range(pool_size):
            player = QMediaPlayer()
            output = QAudioOutput()
            output.setVolume(0.0)
            player.setAudioOutput(output)
            player.setSource(QUrl.fromLocalFile(str(path.resolve())))
            pool.append((player, output))
        return pool

    def _play_one_shot(self, path: Path, volume: float) -> None:
        if not QMediaPlayer or not QAudioOutput:
            return
        player = QMediaPlayer()
        output = QAudioOutput()
        output.setVolume(volume)
        player.setAudioOutput(output)
        player.setSource(QUrl.fromLocalFile(str(path.resolve())))
        player.mediaStatusChanged.connect(lambda status: self._forget_player(player, output, status))
        self.one_shots.append((player, output))
        player.play()

    def _forget_player(self, player: QMediaPlayer, output: QAudioOutput, status) -> None:
        if QMediaPlayer and status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.one_shots = [(p, o) for p, o in self.one_shots if p is not player]
            player.deleteLater()
            output.deleteLater()

    def _play_music_tracks(self, tracks: list[Path], mood_key: str) -> None:
        if not self.music_player or not QMediaPlayer:
            return
        if self.current_music_mood == mood_key and self.music_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            return
        if not tracks:
            return
        self.current_music_mood = mood_key
        if ":" in mood_key:
            self.current_dimension = mood_key.split(":", 1)[0]
        self._fade_to_track(random.choice(tracks))

    def _fade_to_track(self, path: Path) -> None:
        if not self.music_player or not self.music_output:
            return
        if self.music_player.source().isEmpty():
            self._start_track_with_fade_in(path)
            return
        self.pending_music_track = path
        if self.music_fade:
            self.music_fade.stop()
            try:
                self.music_fade.finished.disconnect()
            except RuntimeError:
                pass
            self.music_fade.setDuration(450)
            self.music_fade.setStartValue(self.music_output.volume())
            self.music_fade.setEndValue(0.0)
            self.music_fade.finished.connect(self._start_pending_track)
            self.music_fade.start()
        else:
            self._start_track_with_fade_in(path)

    def _start_pending_track(self) -> None:
        if self.pending_music_track:
            self._start_track_with_fade_in(self.pending_music_track)
            self.pending_music_track = None

    def _start_track_with_fade_in(self, path: Path) -> None:
        if not self.music_player or not self.music_output:
            return
        try:
            self.music_fade.finished.disconnect()
        except RuntimeError:
            pass
        self.music_player.setSource(QUrl.fromLocalFile(str(path.resolve())))
        self.music_output.setVolume(0.0)
        self.music_player.play()
        if self.music_fade:
            self.music_fade.stop()
            self.music_fade.setDuration(1400)
            self.music_fade.setStartValue(0.0)
            self.music_fade.setEndValue(self.target_music_volume)
            self.music_fade.start()
        else:
            self.music_output.setVolume(self.target_music_volume)

    def _handle_music_status(self, status) -> None:
        if QMediaPlayer and status == QMediaPlayer.MediaStatus.EndOfMedia:
            dimension, mood = (self.current_music_mood.split(":", 1) + ["calm"])[:2]
            self.current_music_mood = ""
            self.play_music(dimension, mood)

    def _choose_existing(self, candidates: list[Path]) -> Path | None:
        existing = [path for path in candidates if path.exists()]
        return random.choice(existing) if existing else None

    def _audio_files(self, folder: Path) -> list[Path]:
        if not folder.exists():
            return []
        extensions = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".mp4"}
        return [path for path in folder.rglob("*") if path.is_file() and path.suffix.lower() in extensions]
