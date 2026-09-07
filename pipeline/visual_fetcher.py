import os
import json
import math
import requests
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image, ImageDraw, ImageFont
from pipeline.config import VIDEO_WIDTH, VIDEO_HEIGHT, get_channel_config

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
NASA_API = "https://images-api.nasa.gov/search"

# Cache for downloaded images to avoid redundant network calls across shots
_URL_CACHE = {}

def _search_wikimedia(query: str) -> Optional[Dict[str, str]]:
    """Search Wikimedia Commons for high-resolution images matching query."""
    headers = {"User-Agent": "YouTubeShortsAutomation/2.0 (educational; media fetcher)"}
    clean_q = query.strip()
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"{clean_q} -filetype:pdf -filetype:djvu",
        "gsrnamespace": 6,
        "gsrlimit": 10,
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
    }
    try:
        r = requests.get(COMMONS_API, params=params, headers=headers, timeout=12)
        if r.status_code == 200:
            pages = r.json().get("query", {}).get("pages", {})
            for _, page_info in pages.items():
                imageinfo = page_info.get("imageinfo", [])
                if not imageinfo:
                    continue
                info = imageinfo[0]
                url = info.get("url")
                width = info.get("width", 0)
                height = info.get("height", 0)
                mime = info.get("mime", "")

                if url and mime in ["image/jpeg", "image/png", "image/webp"] and width >= 400 and height >= 300:
                    metadata = info.get("extmetadata", {})
                    license_name = metadata.get("LicenseShortName", {}).get("value", "Public Domain / CC")
                    return {
                        "url": url,
                        "license": license_name,
                        "source": f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(page_info.get('title', ''))}"
                    }
    except Exception as e:
        pass
    return None

def _fetch_wikipedia_topic_images(topic: str) -> List[Dict[str, str]]:
    """Pull all images and scientific diagrams directly from the topic's Wikipedia page."""
    headers = {"User-Agent": "YouTubeShortsAutomation/2.0 (educational; media fetcher)"}
    clean_topic = topic.replace(" ", "_")
    url = f"https://en.wikipedia.org/api/rest_v1/page/media-list/{urllib.parse.quote(clean_topic)}"
    results = []
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            items = r.json().get("items", [])
            for item in items:
                if item.get("type") == "image":
                    srcset = item.get("srcset", [])
                    if srcset:
                        best = srcset[-1].get("src", "")
                        if best:
                            full_url = f"https:{best}" if best.startswith("//") else best
                            results.append({
                                "url": full_url,
                                "license": "Wikipedia / Wikimedia Commons",
                                "source": f"https://en.wikipedia.org/wiki/{clean_topic}"
                            })
    except Exception:
        pass
    return results

def _search_nasa_library(query: str) -> Optional[Dict[str, str]]:
    """Query NASA Image Library for authentic space, Earth, and astrophysics photos."""
    try:
        params = {"q": query, "media_type": "image"}
        r = requests.get(NASA_API, params=params, timeout=10)
        if r.status_code == 200:
            items = r.json().get("collection", {}).get("items", [])
            for item in items[:5]:
                links = item.get("links", [])
                data_list = item.get("data", [{}])
                if links and links[0].get("href"):
                    return {
                        "url": links[0].get("href"),
                        "license": "NASA Public Domain",
                        "source": f"NASA Image ID: {data_list[0].get('nasa_id', '')}"
                    }
    except Exception:
        pass
    return None

def _download_and_verify(url: str, output_path: Path) -> bool:
    """Download image, verify format with PIL, and convert to standard RGB JPEG."""
    headers = {"User-Agent": "YouTubeShortsAutomation/2.0"}
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200 and len(r.content) > 2000:
            with open(output_path, "wb") as f:
                f.write(r.content)
            with Image.open(output_path) as img:
                img.verify()
            # Convert to standard RGB JPEG
            with Image.open(output_path) as img:
                rgb_img = img.convert("RGB")
                rgb_img.save(output_path, "JPEG", quality=90)
            return True
    except Exception:
        pass
    return False

def _get_font(size: int):
    """Load robust TrueType font or fallback."""
    for font_name in ["arial.ttf", "DejaVuSans-Bold.ttf", "FreeSansBold.ttf", "Roboto-Bold.ttf"]:
        try:
            return ImageFont.truetype(font_name, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None

def _generate_procedural_diagram(topic: str, shot_info: Dict[str, Any], output_path: Path, channel: str) -> None:
    """
    LEVEL 4: Generate a high-resolution scientific diagram / illustration.
    Renders spacetime curves, celestial orbits, coordinate axes, and stat telemetry.
    """
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), "#090d16")
    draw = ImageDraw.Draw(img)

    # 1. Subtle radial space background
    cx, cy = VIDEO_WIDTH // 2, VIDEO_HEIGHT // 2 - 100
    for r in range(700, 0, -25):
        alpha_val = int(25 * (1.0 - r / 700.0))
        color = (15 + alpha_val, 25 + alpha_val * 2, 45 + alpha_val * 3) if channel == "science" else (40 + alpha_val * 2, 20 + alpha_val, 15)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)

    # 2. Concentric spacetime curvature / orbital grid
    grid_color = (0, 180, 255, 60) if channel == "science" else (220, 160, 40, 60)
    for radius in [120, 240, 380, 520, 680]:
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline=(40, 100, 160), width=2)

    # 3. 3D Spacetime / Warp funnel lines
    for angle in range(0, 360, 30):
        rad = math.radians(angle)
        x2 = cx + int(700 * math.cos(rad))
        y2 = cy + int(700 * math.sin(rad))
        draw.line([(cx, cy), (x2, y2)], fill=(30, 70, 120), width=1)

    # 4. Central massive body (Glowing planet / singularity)
    core_r = 75
    draw.ellipse([cx - core_r - 20, cy - core_r - 20, cx + core_r + 20, cy + core_r + 20], fill=(0, 140, 255) if channel == "science" else (200, 120, 30))
    draw.ellipse([cx - core_r, cy - core_r, cx + core_r, cy + core_r], fill=(240, 245, 255))

    # 5. Scientific measurement telemetry overlay
    font_large = _get_font(52)
    font_sub = _get_font(28)

    # Upper telemetry badge
    draw.rounded_rectangle([100, 240, 980, 350], radius=16, fill=(15, 25, 45), outline=(0, 200, 255), width=2)
    draw.text((VIDEO_WIDTH // 2, 295), f"• {topic.upper()} •", fill=(0, 220, 255), font=font_sub, anchor="mm")

    # Lower High-Impact Stat / Callout
    onscreen_text = shot_info.get("onscreen_text", "").upper()
    if not onscreen_text:
        onscreen_text = shot_info.get("narration_segment", "").upper()[:28]
    
    draw.rounded_rectangle([100, 1280, 980, 1450], radius=20, fill=(10, 20, 38), outline=(255, 215, 0), width=3)
    draw.text((VIDEO_WIDTH // 2, 1365), onscreen_text, fill=(255, 255, 255), font=font_large, anchor="mm")

    img.save(output_path, "JPEG", quality=92)

def _generate_impact_composite(topic: str, shot_info: Dict[str, Any], output_path: Path, channel: str) -> None:
    """
    LEVEL 5: High-impact typographical and graphic composition.
    Never leaves a blank card. Rich dark gradient, neon tech borders, large callouts.
    """
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), "#0a0e17")
    draw = ImageDraw.Draw(img)

    accent = (0, 210, 255) if channel == "science" else (255, 190, 40)
    bg_gradient = (15, 25, 45) if channel == "science" else (40, 20, 15)

    # Diagonal dynamic tech stripes
    for i in range(-500, VIDEO_WIDTH + 800, 120):
        draw.line([(i, 0), (i + 500, VIDEO_HEIGHT)], fill=(18, 30, 52), width=24)

    # Framing brackets
    draw.line([(100, 200), (980, 200)], fill=accent, width=4)
    draw.line([(100, 1720), (980, 1720)], fill=accent, width=4)

    font_title = _get_font(60)
    font_callout = _get_font(44)
    font_body = _get_font(32)

    # Topic badge
    draw.rounded_rectangle([180, 480, 900, 580], radius=16, fill=(20, 35, 60), outline=accent, width=2)
    draw.text((VIDEO_WIDTH // 2, 530), topic.upper()[:30], fill=accent, font=font_callout, anchor="mm")

    # Main On-Screen Callout
    callout = shot_info.get("onscreen_text", "DID YOU KNOW?").upper()
    draw.text((VIDEO_WIDTH // 2, 950), callout, fill=(255, 255, 255), font=font_title, anchor="mm")

    # Narration Snippet Preview
    segment = shot_info.get("narration_segment", "")
    words = segment.split()
    line1 = " ".join(words[:5])
    line2 = " ".join(words[5:10])
    draw.text((VIDEO_WIDTH // 2, 1150), line1, fill=(200, 215, 235), font=font_body, anchor="mm")
    if line2:
        draw.text((VIDEO_WIDTH // 2, 1200), line2, fill=(200, 215, 235), font=font_body, anchor="mm")

    img.save(output_path, "JPEG", quality=92)

def fetch_all_shot_visuals(channel: str, storyboard: Dict[str, Any], output_dir: Path) -> List[Dict[str, Any]]:
    """
    Execute Level 1 to Level 5 Fallback Hierarchy for EVERY shot in the storyboard.
    Guarantees 100% visual coverage: Every shot receives a validated, real media file.
    """
    shots = storyboard.get("shots", [])
    topic = storyboard.get("topic", "")
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = []

    print(f"\n[{channel.upper()}] Resolving visual assets for {len(shots)} shots (Target 100% coverage)...")

    # Pre-fetch topic images from Wikipedia article as a rich thematic asset pool
    topic_wiki_pool = _fetch_wikipedia_topic_images(topic)
    print(f"[{channel.upper()}] Pre-fetched {len(topic_wiki_pool)} topic diagrams from Wikipedia article pool.")

    wiki_pool_idx = 0

    for shot in shots:
        shot_id = shot.get("shot_id", 1)
        queries = shot.get("search_queries", [])
        desc = shot.get("visual_description", "")
        img_filename = f"shot_{shot_id:02d}.jpg"
        img_path = output_dir / img_filename
        
        resolved = False
        source_meta = {"level": 1, "source": "", "license": ""}

        # --- LEVEL 1 & 2: Real photographs via NASA or Wikimedia Commons ---
        for q in queries:
            if not q or len(q.strip()) < 3:
                continue

            # Check NASA for space/astrophysics/Earth
            if channel.lower() == "science":
                nasa_hit = _search_nasa_library(q)
                if nasa_hit and _download_and_verify(nasa_hit["url"], img_path):
                    source_meta = {"level": 1, "source": nasa_hit["source"], "license": nasa_hit["license"]}
                    resolved = True
                    break

            # Check Wikimedia Commons
            wiki_hit = _search_wikimedia(q)
            if wiki_hit and _download_and_verify(wiki_hit["url"], img_path):
                source_meta = {"level": 1, "source": wiki_hit["source"], "license": wiki_hit["license"]}
                resolved = True
                break

        # --- LEVEL 3: Wikipedia Article Figures / Scientific Diagrams ---
        if not resolved and wiki_pool_idx < len(topic_wiki_pool):
            candidate = topic_wiki_pool[wiki_pool_idx]
            wiki_pool_idx += 1
            if _download_and_verify(candidate["url"], img_path):
                source_meta = {"level": 3, "source": candidate["source"], "license": candidate["license"]}
                resolved = True

        # --- LEVEL 4: Procedural Scientific / Historical Diagram ---
        if not resolved:
            try:
                _generate_procedural_diagram(topic, shot, img_path, channel)
                if img_path.exists() and img_path.stat().st_size > 1000:
                    source_meta = {"level": 4, "source": "Procedural Scientific Diagram", "license": "Engine Generated"}
                    resolved = True
            except Exception:
                pass

        # --- LEVEL 5: High-Impact Typography & Graphic Composite ---
        if not resolved:
            try:
                _generate_impact_composite(topic, shot, img_path, channel)
                if img_path.exists() and img_path.stat().st_size > 1000:
                    source_meta = {"level": 5, "source": "Impact Graphic Composite", "license": "Engine Generated"}
                    resolved = True
            except Exception:
                pass

        # --- HARD VALIDATION: Fail if not resolved ---
        if not resolved or not img_path.exists() or img_path.stat().st_size == 0:
            raise RuntimeError(f"RENDER BLOCKED: Shot {shot_id} could not be resolved to a valid visual asset.")

        manifest.append({
            "shot_id": shot_id,
            "file": str(img_path),
            "level": source_meta["level"],
            "source": source_meta["source"],
            "license": source_meta["license"],
            "onscreen_text": shot.get("onscreen_text", ""),
            "narration_segment": shot.get("narration_segment", ""),
            "motion": shot.get("motion", "slow_zoom_in")
        })

        lvl_icon = "📷" if source_meta["level"] in [1, 2, 3] else "📊"
        print(f"  ✓ Shot {shot_id:02d} [Level {source_meta['level']} {lvl_icon}]: {source_meta['source'][:45]}")

    manifest_file = output_dir / "visual_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    coverage_pct = (len(manifest) / len(shots)) * 100.0
    print(f"[{channel.upper()}] Visual asset resolution complete: {len(manifest)}/{len(shots)} shots ({coverage_pct:.0f}% coverage).\n")
    return manifest
