import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_minimal_dark_palette_uses_black_surfaces():
    from app.ui.theme.colors import palette_for_theme
    from app.ui.theme.styles import stylesheet_for_theme

    dark = palette_for_theme("minimal_dark")

    assert dark["CANVAS_BG"] == "#000000"
    assert dark["SURFACE"] == "#0D0D0D"
    assert dark["EDITOR_BG"] == "#030303"
    assert dark["TEXT_PRIMARY"] == "#F7F7F7"
    assert "url(" not in stylesheet_for_theme("minimal_dark")


def test_minecraft_theme_keeps_original_palette():
    from app.ui.theme.colors import palette_for_theme
    from app.ui.theme.styles import stylesheet_for_theme

    mc = palette_for_theme("mc")

    assert mc["CANVAS_BG"] == "#111611"
    assert mc["SURFACE"] == "#242820"
    assert mc["EDITOR_BG"] == "#141713"
    assert palette_for_theme("dark")["CANVAS_BG"] == "#111611"
    assert palette_for_theme("unknown-theme")["CANVAS_BG"] == "#111611"
    assert "#111611" in stylesheet_for_theme("mc")
    assert "#78A84A" in stylesheet_for_theme("mc")


def test_minimal_light_alias_falls_back_to_minecraft():
    from app.ui.theme.colors import palette_for_theme
    from app.ui.theme.manager import THEME_LABELS, normalize_theme
    from app.ui.theme.styles import stylesheet_for_theme

    assert normalize_theme("minimal_light") == "mc"
    assert "minimal_light" not in THEME_LABELS
    assert palette_for_theme("minimal_light") == palette_for_theme("mc")
    assert stylesheet_for_theme("minimal_light") == stylesheet_for_theme("mc")


def test_public_docs_match_supported_themes_and_existing_files():
    checked = [
        _PROJECT_ROOT / "AGENTS.md",
        _PROJECT_ROOT / "README.md",
        _PROJECT_ROOT / "docs" / "PROJECT_GUIDE.md",
        _PROJECT_ROOT / "config.yaml.example",
    ]

    for path in checked:
        text = path.read_text(encoding="utf-8")
        assert "minimal_light" not in text
        assert "Minimal White" not in text
        assert "need.md" not in text
        assert "架构设计文档v2.md" not in text


def test_minimal_dark_runtime_does_not_load_theme_icons():
    from PySide6.QtWidgets import QApplication, QPushButton

    app = QApplication.instance() or QApplication([])
    previous = app.property("cppraftingTheme")
    app.setProperty("cppraftingTheme", "minimal_dark")
    try:
        from app.ui.theme.icon_helpers import icon_label, set_button_icon, theme_icon, theme_uses_icons

        assert theme_uses_icons() is False
        assert theme_icon("nav_home").isNull()

        button = QPushButton("Run")
        set_button_icon(button, "action_run")
        assert button.icon().isNull()
        assert icon_label("empty_book", 32) is None
    finally:
        app.setProperty("cppraftingTheme", previous)


def test_minecraft_assets_stay_inside_theme_layer():
    allowed = {
        Path("app/ui/theme/minecraft_assets.py"),
        Path("app/ui/theme/colors.py"),
        Path("app/ui/theme/styles.py"),
        Path("app/ui/theme/icon_helpers.py"),
        Path("app/ui/theme/manager.py"),
    }
    offenders = []
    for path in (_PROJECT_ROOT / "app" / "ui").rglob("*.py"):
        rel = path.relative_to(_PROJECT_ROOT)
        if rel in allowed:
            continue
        text = path.read_text(encoding="utf-8")
        if "minecraft_assets" in text or "asset_path(" in text:
            offenders.append(str(rel))

    assert offenders == []


def test_knowledge_markdown_code_blocks_match_active_theme():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    previous = app.property("cppraftingTheme")
    try:
        from app.ui.pages.knowledge_page import _md_to_html
        from app.ui.theme.colors import EDITOR_BG

        markdown = "```cpp\nint x = 1;\n```\ninline `new int`"

        app.setProperty("cppraftingTheme", "mc")
        mc_html = _md_to_html(markdown)
        assert "#E6C77E" in mc_html
        assert "#F0D997" in mc_html
        assert EDITOR_BG not in mc_html

        app.setProperty("cppraftingTheme", "minimal_dark")
        dark_html = _md_to_html(markdown)
        assert EDITOR_BG in dark_html
    finally:
        app.setProperty("cppraftingTheme", previous)
