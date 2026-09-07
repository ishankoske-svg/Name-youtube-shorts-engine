import os
import json
from pathlib import Path
from typing import Dict, Any, List
from google import genai
from pipeline.config import get_channel_config, DEFAULT_GEMINI_MODEL
from pipeline.topic_generator import _clean_json_response

def create_storyboard(channel: str, topic_data: Dict[str, Any], model_name: str = None) -> Dict[str, Any]:
    """Break script into 5-8 cinematic visual scenes with search queries and pacing."""
    topic = topic_data.get("topic", "")
    hook = topic_data.get("hook", "")
    script = topic_data.get("script", "")
    visual_ideas = topic_data.get("visual_ideas", [])

    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key) if api_key else None
    model = model_name or os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)

    prompt = f"""You are an elite short-form video director for YouTube Shorts.

Channel: {channel}
Topic: {topic}
Hook: {hook}
Script: {script}
Initial Visual Ideas: {json.dumps(visual_ideas)}

Task:
Divide the narration script into 5 to 8 sequential scenes for a fast-paced 30-50 second video.
Every word of the original script must be preserved across the scenes in order.

For each scene provide:
- "scene_id": integer starting from 1
- "narration": the exact chunk of narration for this scene
- "visual_query": a 2-4 word specific search query for Wikimedia Commons / public photos (e.g., "Jupiter Great Red Spot", "Roman Legionary armor")
- "caption_highlight": 1-3 punchy uppercase words to display as a title highlight (e.g., "GIANT STORM", "ROMAN SHIELD")

Return ONLY valid JSON in this format:
{{
  "topic": "{topic}",
  "channel": "{channel}",
  "scenes": [
    {{
      "scene_id": 1,
      "narration": "...",
      "visual_query": "...",
      "caption_highlight": "..."
    }}
  ]
}}

Do not use markdown.
"""

    storyboard = None
    if client:
        try:
            print(f"[{channel.upper()}] Directing storyboard with Gemini...")
            res = client.models.generate_content(model=model, contents=prompt)
            clean_res = _clean_json_response(res.text)
            storyboard = json.loads(clean_res)
        except Exception as e:
            print(f"Storyboard generation fallback triggered: {e}")

    # Fallback if Gemini fails or no client: split by sentences
    if not storyboard or "scenes" not in storyboard or not storyboard["scenes"]:
        sentences = [s.strip() for s in script.replace("\n", " ").split(".") if s.strip()]
        scenes = []
        for idx, s in enumerate(sentences):
            query = visual_ideas[idx % len(visual_ideas)] if visual_ideas else topic
            scenes.append({
                "scene_id": idx + 1,
                "narration": s + ".",
                "visual_query": query,
                "caption_highlight": topic.upper()[:20]
            })
        storyboard = {
            "topic": topic,
            "channel": channel,
            "scenes": scenes
        }

    # Save to channel output dir
    cfg = get_channel_config(channel)
    out_dir = Path(cfg["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "storyboard.json", "w", encoding="utf-8") as f:
        json.dump(storyboard, f, indent=2, ensure_ascii=False)

    return storyboard
