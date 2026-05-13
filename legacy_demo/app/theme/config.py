from pathlib import Path


class Colors:
    BLACK = "#111111"
    BEDROCK = "#151915"
    DIRT = "#5B3A25"
    DIRT_DARK = "#352216"
    GRASS = "#4F8F2F"
    GRASS_LIGHT = "#6DBA3B"
    STONE = "#6F6F6F"
    STONE_LIGHT = "#8B8B8B"
    STONE_DARK = "#2B2B2B"
    OAK = "#B98A4A"
    GOLD = "#F7D65A"
    CREAM = "#F3F0D7"
    MUTED = "#D8D2A8"
    HEART = "#D52B2B"
    HEART_DARK = "#661010"
    HEART_OUTLINE = "#120707"
    DISABLED_BG = "#3A3A3A"
    DISABLED_BORDER = "#242424"
    DISABLED_TEXT = "#888888"
    CODE_BG = "#111811"
    PANEL_BG = "#263126"
    MENU_BUTTON = "#777777"
    MENU_BUTTON_HOVER = "#8B8B8B"
    MENU_BUTTON_PRESSED = "#555555"


class Assets:
    ROOT = Path("assets")
    AUDIO = ROOT / "audio"
    TEXTURES = ROOT / "textures"
    SOUND_PACK = Path("Minecraft Sound Pack 1.17 - Sound Effects")
    VANILLA_TEXTURES = Path("textures")
    MUSIC_LIBRARY = SOUND_PACK / "music"

    BUTTON_SOUNDS = [
        AUDIO / "ui" / "button_click.wav",
        SOUND_PACK / "random" / "click.ogg",
        SOUND_PACK / "random" / "click_stereo.ogg",
    ]
    XP_SOUNDS = [
        AUDIO / "effects" / "xp_orb.wav",
        SOUND_PACK / "random" / "orb.ogg",
    ]
    LEVEL_UP_SOUNDS = [
        AUDIO / "effects" / "level_up.wav",
        SOUND_PACK / "random" / "levelup.ogg",
    ]
    HURT_SOUNDS = [
        AUDIO / "effects" / "steve_hurt_old.wav",
        SOUND_PACK / "random" / "classic_hurt.ogg",
        SOUND_PACK / "damage" / "hit1.ogg",
        SOUND_PACK / "damage" / "hit2.ogg",
        SOUND_PACK / "damage" / "hit3.ogg",
    ]
    DEATH_SOUNDS = [
        AUDIO / "effects" / "death_augh_1.wav",
        AUDIO / "effects" / "death_augh_2.wav",
        SOUND_PACK / "random" / "classic_hurt.ogg",
    ]
    CHALLENGE_COMPLETE_SOUNDS = [
        AUDIO / "effects" / "challenge_complete.wav",
        SOUND_PACK / "ui" / "toast" / "challenge_complete.ogg",
    ]

    STARTUP_MUSIC = AUDIO / "music" / "startup"
    HEALTHY_MUSIC = AUDIO / "music" / "healthy"
    CRITICAL_MUSIC = AUDIO / "music" / "critical"
    HEALTHY_MUSIC_FALLBACKS = [
        SOUND_PACK / "ambient" / "underwater" / "underwater_ambience.ogg",
        SOUND_PACK / "ambient" / "weather" / "rain1.ogg",
        SOUND_PACK / "ambient" / "weather" / "rain2.ogg",
        SOUND_PACK / "ambient" / "weather" / "rain3.ogg",
    ]
    CRITICAL_MUSIC_FALLBACKS = [
        SOUND_PACK / "ambient" / "cave" / "cave11.ogg",
        SOUND_PACK / "ambient" / "cave" / "cave13.ogg",
        SOUND_PACK / "ambient" / "cave" / "cave14.ogg",
    ]

    HEART_FULL = VANILLA_TEXTURES / "gui" / "sprites" / "hud" / "heart" / "full.png"
    HEART_EMPTY = VANILLA_TEXTURES / "gui" / "sprites" / "hud" / "heart" / "container.png"
    HEART_FULL_ALT = VANILLA_TEXTURES / "gui" / "sprites" / "hud" / "heart_full.png"
    HEART_EMPTY_ALT = VANILLA_TEXTURES / "gui" / "sprites" / "hud" / "heart_container.png"

    TITLE_LOGO = VANILLA_TEXTURES / "gui" / "title" / "minecraft.png"
    TITLE_EDITION = VANILLA_TEXTURES / "gui" / "title" / "edition.png"
    PANORAMA_DIR = VANILLA_TEXTURES / "gui" / "title" / "background"
    BUTTON_NORMAL = VANILLA_TEXTURES / "gui" / "sprites" / "widget" / "button.png"
    BUTTON_HOVER = VANILLA_TEXTURES / "gui" / "sprites" / "widget" / "button_highlighted.png"
    BUTTON_DISABLED = VANILLA_TEXTURES / "gui" / "sprites" / "widget" / "button_disabled.png"
