import os
import json
import requests
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List
from google import genai
from pipeline.config import get_channel_config, DEFAULT_GEMINI_MODEL
from pipeline.topic_generator import _clean_json_response

def search_wikipedia(query: str) -> Dict[str, Any]:
    """Search Wikipedia REST API for page summary and extracts."""
    headers = {
        "User-Agent": "YouTubeShortsAutomation/1.0 (educational channel automation; contact: automation@example.com)"
    }
    encoded_query = urllib.parse.quote(query)
    search_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={encoded_query}&limit=3&namespace=0&format=json"

    try:
        r = requests.get(search_url, headers=headers, timeout=10)
        if r.status_code == 200:
            results = r.json()
            # results format: [query, [titles], [descriptions], [urls]]
            if len(results) >= 4 and len(results[1]) > 0:
                best_title = results[1][0]
                summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(best_title)}"
                sum_r = requests.get(summary_url, headers=headers, timeout=10)
                if sum_r.status_code == 200:
                    data = sum_r.json()
                    return {
                        "title": data.get("title", best_title),
                        "extract": data.get("extract", ""),
                        "url": data.get("content_urls", {}).get("desktop", {}).get("page", results[3][0]),
                        "thumbnail": data.get("thumbnail", {}).get("source")
                    }
    except Exception as e:
        print(f"Warning: Wikipedia query failed for '{query}': {e}")
    return {"title": query, "extract": "", "url": "", "thumbnail": None}

def search_nasa(query: str) -> List[Dict[str, Any]]:
    """Search NASA Image and Video Library for public media & captions."""
    url = f"https://images-api.nasa.gov/search?q={urllib.parse.quote(query)}&media_type=image"
    items = []
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            collection = data.get("collection", {}).get("items", [])
            for item in collection[:3]:
                d = item.get("data", [{}])[0]
                links = item.get("links", [{}])
                img_url = links[0].get("href") if links else None
                items.append({
                    "title": d.get("title", ""),
                    "description": d.get("description", "")[:300],
                    "nasa_id": d.get("nasa_id", ""),
                    "image_url": img_url
                })
    except Exception as e:
        print(f"Warning: NASA query failed for '{query}': {e}")
    return items

def research_topic(channel: str, topic_data: Dict[str, Any], model_name: str = None) -> Dict[str, Any]:
    """Ground topic claims using Wikipedia/NASA and extract citations using Gemini."""
    cfg = get_channel_config(channel)
    topic = topic_data.get("topic", "")
    script = topic_data.get("script", "")

    # Retrieve source context
    wiki_info = search_wikipedia(topic)
    nasa_info = search_nasa(topic) if channel.lower() == "science" else []

    context_text = f"Wikipedia: {wiki_info.get('title')}\n{wiki_info.get('extract')}\n"
    if nasa_info:
        for idx, n in enumerate(nasa_info):
            context_text += f"NASA Ref {idx+1}: {n.get('title')} - {n.get('description')}\n"

    # Use Gemini to verify and structure facts
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key) if api_key else None
    model = model_name or os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)

    facts = []
    if client and context_text.strip():
        prompt = f"""You are a factual verification assistant for educational short videos.
Topic: {topic}
Proposed Script: {script}

Retrieved Research Context:
{context_text}

Task:
Extract 3-5 verified key facts and ensure the script doesn't contain obvious myths or historical/scientific inaccuracies.

Return ONLY valid JSON in this format:
{{
  "verified_facts": ["fact 1", "fact 2", "fact 3"],
  "accuracy_confidence": "high",
  "source_urls": ["{wiki_info.get('url', '')}"]
}}
Do not use markdown.
"""
        try:
            res = client.models.generate_content(model=model, contents=prompt)
            clean_res = _clean_json_response(res.text)
            parsed = json.loads(clean_res)
            facts = parsed.get("verified_facts", [])
        except Exception as e:
            print(f"Fact extraction warning: {e}")

    research_result = {
        "topic": topic,
        "channel": channel,
        "wikipedia": wiki_info,
        "nasa": nasa_info,
        "verified_facts": facts or [wiki_info.get("extract", "")]
    }

    # Save to research dir
    res_dir = Path(cfg["research_dir"])
    res_dir.mkdir(parents=True, exist_ok=True)
    with open(res_dir / "research.json", "w", encoding="utf-8") as f:
        json.dump(research_result, f, indent=2, ensure_ascii=False)

    return research_result
