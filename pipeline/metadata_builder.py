import os
import json
from pathlib import Path
from typing import Dict, Any, List
from google import genai
from pipeline.config import get_channel_config, DEFAULT_GEMINI_MODEL
from pipeline.topic_generator import _clean_json_response

def generate_youtube_metadata(
    channel: str,
    topic_data: Dict[str, Any],
    research_data: Dict[str, Any],
    visual_manifest: List[Dict[str, Any]],
    output_dir: Path,
    model_name: str = None
) -> Dict[str, Any]:
    """Generate optimized YouTube Shorts title, description, tags, and category ID."""
    cfg = get_channel_config(channel)
    topic = topic_data.get("topic", "")
    hook = topic_data.get("hook", "")
    script = topic_data.get("script", "")

    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key) if api_key else None
    model = model_name or os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)

    prompt = f"""You are a YouTube Shorts SEO and metadata specialist.

Channel: {channel}
Topic: {topic}
Hook: {hook}
Script: {script}

Generate:
1. A click-worthy, curiosity-inducing YouTube Shorts title (under 60 characters, including #Shorts).
2. A clean, engaging description (3-4 sentences) summarizing the insight, ending with hashtags.
3. 8-12 search tags for YouTube.

Return ONLY valid JSON in this format:
{{
  "title": "Title Here #Shorts",
  "description": "Description text...",
  "tags": ["tag1", "tag2", "tag3"]
}}

Do not use markdown.
"""

    parsed = None
    if client:
        try:
            res = client.models.generate_content(model=model, contents=prompt)
            clean_res = _clean_json_response(res.text)
            parsed = json.loads(clean_res)
        except Exception as e:
            print(f"Metadata generation warning: {e}")

    # Fallback if no LLM
    if not parsed or "title" not in parsed:
        parsed = {
            "title": f"{topic[:45]} #Shorts",
            "description": f"{hook}\n\nExplore this incredible {channel} story in today's short.",
            "tags": [channel, "shorts", "educational", "facts", "curiosity"]
        }

    # Append attribution and disclosures
    description = parsed.get("description", "") + "\n\n--- Attribution & Sources ---\n"
    wiki_url = research_data.get("wikipedia", {}).get("url")
    if wiki_url:
        description += f"• Reference: {wiki_url}\n"

    # Add image credits
    cc_credits = [v["source"] for v in visual_manifest if not v.get("is_fallback") and v.get("source")]
    if cc_credits:
        description += "• Visuals: Wikimedia Commons / Open Licenses\n"

    description += f"• Narration voice: {cfg['voice']}\n"
    description += f"• #Shorts #{channel.capitalize()} #Facts"

    metadata = {
        "title": parsed.get("title", f"{topic} #Shorts"),
        "description": description,
        "tags": parsed.get("tags", [channel, "shorts"]),
        "categoryId": cfg["category_id"],
        "privacyStatus": "private",  # Always private for user 10-minute review
        "madeForKids": False,
        "selfDeclaredMadeForKids": False
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    meta_path = output_dir / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"[{channel.upper()}] YouTube metadata created: '{metadata['title']}'")
    return metadata
