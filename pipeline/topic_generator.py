import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List
from google import genai
from pipeline.config import get_channel_config, DEFAULT_GEMINI_MODEL, call_gemini

def _clean_json_response(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()

def load_previous_topics(topic_file: Path) -> List[str]:
    if topic_file.exists():
        try:
            with open(topic_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "topics" in data:
                    return data["topics"]
        except Exception as e:
            print(f"Warning: Could not read {topic_file}: {e}")
    return []

def save_previous_topics(topic_file: Path, topics: List[str]) -> None:
    topic_file.parent.mkdir(parents=True, exist_ok=True)
    with open(topic_file, "w", encoding="utf-8") as f:
        json.dump(topics, f, indent=2, ensure_ascii=False)

def get_topic_prompt(channel: str, previous_topics: List[str]) -> str:
    previous_text = "\n".join(f"- {t}" for t in previous_topics[-50:])  # Keep prompt concise with recent 50

    if channel.lower() == "history":
        return f"""You are the topic generator for a YouTube Shorts channel about HISTORY.

Your job is to generate ONE completely new and interesting historical topic.

IMPORTANT:
The topic MUST NOT be the same as, or substantially similar to,
any topic in the previous-topic list below.

PREVIOUS TOPICS:
{previous_text if previous_text else "(None yet)"}

Choose a topic that:
- Is genuinely historical
- Has a strong curiosity hook
- Can be explained in 30-60 seconds (around 80 to 140 words of narration)
- Has strong visual potential
- Is interesting to viewers aged 14-25
- Is not a generic "5 facts" list
- Avoids common repetitive topics
- Avoids myths unless the video is specifically about debunking the myth
- Can eventually be supported by reliable historical sources

Try to explore different areas such as:
- Ancient civilizations
- Strange historical events
- Lost cities
- Historical inventions
- Wars and battles
- Engineering
- Daily life
- Historical mysteries
- Unexpected discoveries
- Important people
- Forgotten events

Return ONLY valid JSON.

Use exactly this format:

{{
  "topic": "topic here",
  "hook": "opening sentence here",
  "script": "complete short narration here (80-140 words)",
  "why_interesting": "why viewers would care",
  "visual_ideas": [
    "visual idea 1",
    "visual idea 2",
    "visual idea 3"
  ]
}}

Do not use markdown.
"""
    elif channel.lower() == "science":
        return f"""You are the topic generator for a YouTube Shorts channel about SCIENCE.

Your job is to generate ONE fascinating and genuinely educational
science topic for a 30-60 second YouTube Short.

IMPORTANT:
The topic MUST NOT be the same as, or substantially similar to,
any topic in the previous-topic list below.

PREVIOUS TOPICS:
{previous_text if previous_text else "(None yet)"}

Choose a topic that:
- Is scientifically accurate
- Has a strong curiosity hook
- Can be explained clearly in 30-60 seconds (around 80 to 140 words of narration)
- Has strong visual potential
- Is interesting to viewers aged 14-25
- Makes the viewer think "Wait, why does that happen?"
- Has a surprising or counterintuitive explanation
- Can eventually be supported by reliable scientific sources
- Is understandable to a general audience
- Is NOT a generic list such as "5 interesting science facts"

Explore different science areas such as:
- Space
- Physics
- Human body
- Animals
- Earth
- Ocean
- Chemistry
- Biology
- Neuroscience
- Technology
- Astronomy
- Genetics
- Weather
- Evolution
- Weird natural phenomena

Good examples of the style we want:
"What would happen if Earth suddenly stopped spinning?"
"Why don't birds get electrocuted when they sit on power lines?"
"Why doesn't your stomach digest itself?"
"Why does space look black even when the Sun is shining?"
"Why can you see lightning before you hear thunder?"

Avoid:
- Fake science
- Pseudoscience
- Conspiracy theories
- Medical misinformation
- Exaggerated claims
- Made-up experiments
- Topics requiring dangerous experiments
- Generic "10 science facts" content

The goal is NOT simply to produce a fact.
The goal is to find a fascinating scientific question with a surprising explanation.

Return ONLY valid JSON.

Use exactly this format:

{{
  "topic": "topic here",
  "hook": "opening sentence here",
  "script": "complete short narration here (80-140 words)",
  "why_interesting": "why viewers would care",
  "visual_ideas": [
    "visual idea 1",
    "visual idea 2",
    "visual idea 3"
  ]
}}

Do not use markdown.
"""
    else:
        raise ValueError(f"Unknown channel {channel}")

def generate_topic(channel: str, model_name: str = None) -> Dict[str, Any]:
    cfg = get_channel_config(channel)
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required.")

    client = genai.Client(api_key=api_key)
    model = model_name or os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)

    previous_topics = load_previous_topics(cfg["topic_file"])
    prompt = get_topic_prompt(channel, previous_topics)

    print(f"[{channel.upper()}] Calling Gemini for new topic...")
    response = call_gemini(client, prompt, preferred_model=model)

    clean_text = _clean_json_response(response.text)
    data = json.loads(clean_text)

    new_topic = data.get("topic", "").strip()
    if not new_topic:
        raise ValueError("Gemini returned an empty topic.")

    # Save to history
    previous_topics.append(new_topic)
    save_previous_topics(cfg["topic_file"], previous_topics)

    # Save to output directory
    out_dir = Path(cfg["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{channel.lower()}_topic.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[{channel.upper()}] New topic saved successfully: '{new_topic}'")
    return data
