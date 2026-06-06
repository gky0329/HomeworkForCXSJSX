"""Asset resolution and reusable QSS snippets for the Minecraft theme."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ASSET_ROOT = ROOT / "assets" / "ui"


def asset_path(category: str, name: str) -> str:
    """Return a QSS-safe asset path, preferring generated raster assets."""
    base = ASSET_ROOT / category / name
    for suffix in (".webp", ".png", ".svg"):
        candidate = base.with_suffix(suffix)
        if candidate.exists():
            return candidate.as_posix()
    return base.with_suffix(".svg").as_posix()


def asset_url(category: str, name: str) -> str:
    return f"url({asset_path(category, name)})"


def border_image(category: str, name: str, inset: int = 8) -> str:
    return f"border-image: {asset_url(category, name)} {inset} {inset} {inset} {inset} stretch stretch;"


def bg_image(category: str, name: str) -> str:
    return f"background-image: {asset_url(category, name)};"
