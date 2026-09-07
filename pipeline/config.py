import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
MUSIC_DIR = ASSETS_DIR / "music"
FONTS_DIR = ASSETS_DIR / "fonts"

import time

# Gemini Model configuration
DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
FALLBACK_GEMINI_MODELS = [
    "gemini-3.6-flash",
    "gemini-3-flash-preview",
    "gemini-2.0-flash",
    "gemini-1.5-flash"
]

def call_gemini(client, contents: str, preferred_model: str = None):
    """
    Call Gemini generate_content with automatic retry and model rotation if a model
    is deprecated, unavailable (503), rate-limited (429), or experiencing high demand spikes.
    """
    models_to_try = []
    if preferred_model:
        models_to_try.append(preferred_model)
    elif os.environ.get("GEMINI_MODEL"):
        models_to_try.append(os.environ.get("GEMINI_MODEL"))
    
    for m in FALLBACK_GEMINI_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    transient_indicators = ["503", "429", "404", "UNAVAILABLE", "NOT_FOUND", "high demand", "RESOURCE_EXHAUSTED", "ServerError"]

    for model in models_to_try:
        for attempt in range(2):
            try:
                # print(f"Calling Gemini with model: {model} (attempt {attempt+1})...")
                response = client.models.generate_content(
                    model=model,
                    contents=contents
                )
                return response
            except Exception as e:
                err_str = str(e)
                is_transient_or_model_error = any(ind.lower() in err_str.lower() for ind in transient_indicators)
                if is_transient_or_model_error:
                    print(f"Notice: Model '{model}' issue (attempt {attempt+1}): {err_str[:90]}... Rotating/Retrying...")
                    last_error = e
                    time.sleep(2)
                    continue
                raise e

    if last_error:
        raise last_error
    raise RuntimeError("No Gemini models available to try.")



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
