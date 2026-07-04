import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_minimal_light_palette_uses_light_surfaces():
    from app.ui.theme.colors import palette_for_theme
    from app.ui.theme.styles import stylesheet_for_theme

    light = palette_for_theme("minimal_light")
    dark = palette_for_theme("minimal_dark")

    assert light["CANVAS_BG"] == "#FFFFFF"
    assert light["SURFACE"] == "#FFFFFF"
    assert light["EDITOR_BG"] == "#FFFFFF"
    assert light["TEXT_PRIMARY"] == "#111111"
    assert dark["CANVAS_BG"] == "#000000"
    assert "url(" not in stylesheet_for_theme("minimal_light")


def test_minecraft_theme_keeps_original_palette():
    from app.ui.theme.colors import palette_for_theme
    from app.ui.theme.styles import stylesheet_for_theme

    mc = palette_for_theme("mc")
    light = palette_for_theme("minimal_light")

    assert mc["CANVAS_BG"] == "#111611"
    assert mc["SURFACE"] == "#242820"
    assert mc["EDITOR_BG"] == "#141713"
    assert mc["CANVAS_BG"] != light["CANVAS_BG"]
    assert palette_for_theme("dark")["CANVAS_BG"] == "#111611"
    assert palette_for_theme("unknown-theme")["CANVAS_BG"] == "#111611"
    assert "#111611" in stylesheet_for_theme("mc")
    assert "#78A84A" in stylesheet_for_theme("mc")
