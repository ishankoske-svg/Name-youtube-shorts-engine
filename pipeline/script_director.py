import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List
from google import genai
from pipeline.config import get_channel_config, DEFAULT_GEMINI_MODEL, call_gemini
from pipeline.topic_generator import _clean_json_response

def create_storyboard(channel: str, topic_data: Dict[str, Any], model_name: str = None) -> Dict[str, Any]:
    """
    Break script into a high-density shot-based storyboard.
    Target: 15 to 28 visual shots (1.5 to 3.0 seconds per shot) for a 35-55 second Short.
    Every single narrative phrase receives a dedicated, relevant visual.
    """
    topic = topic_data.get("topic", "")
    hook = topic_data.get("hook", "")
    script = topic_data.get("script", "")
    visual_ideas = topic_data.get("visual_ideas", [])

    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key) if api_key else None
    model = model_name or os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)

    prompt = f"""You are an elite short-form video director for high-retention YouTube Shorts (like Kurzgesagt, Veritasium, or modern science documentary channels).

Channel: {channel}
Topic: {topic}
Hook: {hook}
Script: {script}

CRITICAL ARCHITECTURE REQUIREMENT:
A 30-55 second YouTube Short requires HIGH VISUAL DENSITY to maintain 90%+ audience retention.
Do NOT create only 5 or 6 long static scenes.
Instead, break the narration into 14 to 26 FAST, DYNAMIC VISUAL SHOTS (each lasting approximately 1.5 to 3.0 seconds).
Whenever the narration introduces a new fact, comparison, number, or subject, CUT TO A NEW VISUAL SHOT.

Example:
Narration: "Scientists discovered that your head is actually aging faster than your feet. It sounds insane, but according to Einstein's general relativity, gravity warps the fabric of time itself."
Shots:
Shot 1 (1.8s): Digital atomic clock counting nanoseconds
Shot 2 (2.1s): Human silhouette showing head vs feet height gradient
Shot 3 (1.9s): Albert Einstein writing equations on blackboard
Shot 4 (2.3s): Spacetime fabric 3D curvature grid around massive planet

RULES FOR "search_queries":
1. Each shot MUST have 2-3 CONCRETE, TANGIBLE SEARCH TERMS that exist in photography libraries, NASA archives, or Wikipedia.
2. For science: space telescopes, planets, laboratory equipment, particle collisions, cell microscopy, astronomical maps, mathematical formulas, physical experiments.
3. For history: ancient ruins, battle maps, archival black-and-white photos, museum artifacts, portraits, medieval armor, manuscripts.
4. If abstract: choose a concrete scientific diagram or visual analogy (e.g., "spacetime curvature grid", "optical atomic clock", "orbital gravity simulation").

Return ONLY valid JSON in this format:
{{
  "topic": "{topic}",
  "channel": "{channel}",
  "target_shots": 18,
  "shots": [
    {{
      "shot_id": 1,
      "narration_segment": "exact words spoken during this shot",
      "visual_description": "detailed description of what appears on screen",
      "visual_type": "scientific_photograph",
      "search_queries": ["query 1", "query 2", "query 3"],
      "onscreen_text": "PUNCHY 2-3 WORD STAT OR CALLOUT",
      "motion": "slow_zoom_in"
    }}
  ]
}}

Ensure all words of the original narration script are covered sequentially across the shots.
Do not use markdown.
"""

    storyboard = None
    if client:
        try:
            print(f"[{channel.upper()}] Directing high-density storyboard with Gemini (target 15-25 shots)...")
            res = call_gemini(client, prompt, preferred_model=model)
            clean_res = _clean_json_response(res.text)
            storyboard = json.loads(clean_res)
        except Exception as e:
            print(f"Storyboard generation LLM warning: {e}")

    # Fallback shot creator if LLM fails or returned too few shots
    raw_shots = storyboard.get("shots", []) if storyboard else []
    if len(raw_shots) < 8:
        print(f"[{channel.upper()}] Refining storyboard into fine-grained shots...")
        # Split script into phrase chunks of 4-8 words each to guarantee 14-25 shots
        words = script.replace("\n", " ").split()
        chunk_size = 7
        shots = []
        
        for idx in range(0, len(words), chunk_size):
            chunk = " ".join(words[idx:idx + chunk_size])
            shot_num = len(shots) + 1
            # Pick contextual search queries
            if idx == 0:
                q = [topic, f"{channel} science", "scientific discovery"]
                txt = "DID YOU KNOW?"
            elif "gravity" in chunk.lower() or "spacetime" in chunk.lower():
                q = ["spacetime curvature grid", "earth gravity orbit", "einstein relativity"]
                txt = "GRAVITY WARPS TIME"
            elif "clock" in chunk.lower() or "time" in chunk.lower():
                q = ["atomic clock laboratory", "digital clock nanoseconds", "pocket watch mechanism"]
                txt = "MEASURING TIME"
            elif "space" in chunk.lower() or "earth" in chunk.lower():
                q = ["earth from space orbit", "hubble space telescope galaxy", "satellite orbiting earth"]
                txt = "ORBITAL SCALE"
            elif "history" in chunk.lower() or "ancient" in chunk.lower():
                q = ["ancient roman colosseum", "historical archive manuscript", "ancient ruins"]
                txt = "ANCIENT HISTORY"
            else:
                fallback_idea = visual_ideas[shot_num % len(visual_ideas)] if visual_ideas else topic
                q = [fallback_idea, f"{topic} illustration", f"{channel} concept"]
                txt = topic.upper()[:22]

            shots.append({
                "shot_id": shot_num,
                "narration_segment": chunk,
                "visual_description": f"Visual representing: {chunk}",
                "visual_type": "scientific_photograph",
                "search_queries": q,
                "onscreen_text": txt,
                "motion": "slow_zoom_in" if shot_num % 2 == 1 else "pan_right"
            })
        
        storyboard = {
            "topic": topic,
            "channel": channel,
            "target_shots": len(shots),
            "shots": shots
        }
    else:
        # Standardize field names
        for idx, shot in enumerate(storyboard["shots"], start=1):
            shot["shot_id"] = idx
            if "search_queries" not in shot:
                shot["search_queries"] = [shot.get("visual_query", topic)]
            if "motion" not in shot:
                shot["motion"] = "slow_zoom_in" if idx % 2 == 1 else "pan_right"
            if "onscreen_text" not in shot:
                shot["onscreen_text"] = shot.get("caption_highlight", "")

    print(f"[{channel.upper()}] Storyboard ready with {len(storyboard['shots'])} high-density shots.")

    # Save to channel output dir
    cfg = get_channel_config(channel)
    out_dir = Path(cfg["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "storyboard.json", "w", encoding="utf-8") as f:
        json.dump(storyboard, f, indent=2, ensure_ascii=False)

    return storyboard
