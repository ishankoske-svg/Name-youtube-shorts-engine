import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
MUSIC_DIR = ASSETS_DIR / "music"
FONTS_DIR = ASSETS_DIR / "fonts"

# Gemini Model configuration
DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# Video Output Specifications
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30
TARGET_MIN_DURATION = 30
TARGET_MAX_DURATION = 58  # Must stay under 60 seconds for YouTube Shorts

# Channels Configuration
CHANNELS = {
    "science": {
        "name": "Science Channel",
        "topic_file": BASE_DIR / "science_data" / "previous_topics.json",
        "output_dir": BASE_DIR / "science_output",
        "research_dir": BASE_DIR / "science_research",
        "voice": "en-US-ChristopherNeural",  # Authoritative, educational
        "voice_rate": "+5%",
        "category_id": "28",  # Science & Technology on YouTube
        "default_music": MUSIC_DIR / "science_ambient.mp3",
        "fallback_colors": [("#0f2027", "#203a43", "#2c5364"), ("#141e30", "#243b55")],
    },
    "history": {
        "name": "History Channel",
        "topic_file": BASE_DIR / "history_data" / "previous_topics.json",
        "output_dir": BASE_DIR / "history_output",
        "research_dir": BASE_DIR / "history_research",
        "voice": "en-US-GuyNeural",  # Storyteller, engaging
        "voice_rate": "+5%",
        "category_id": "27",  # Education on YouTube
        "default_music": MUSIC_DIR / "history_dramatic.mp3",
        "fallback_colors": [("#1a0000", "#3b1414", "#5c2525"), ("#1f1c18", "#3b342e")],
    }
}

def get_channel_config(channel: str) -> dict:
    channel_key = channel.lower()
    if channel_key not in CHANNELS:
        raise ValueError(f"Unknown channel '{channel}'. Available: {list(CHANNELS.keys())}")
    return CHANNELS[channel_key]
