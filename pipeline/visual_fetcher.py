import os
import json
import requests
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image, ImageDraw, ImageFont
from pipeline.config import VIDEO_WIDTH, VIDEO_HEIGHT, get_channel_config

COMMONS_API = "https://commons.wikimedia.org/w/api.php"

def _search_wikimedia_image(query: str) -> Optional[Dict[str, str]]:
    """Search Wikimedia Commons for high-resolution images."""
    headers = {
        "User-Agent": "YouTubeShortsAutomation/1.0 (educational; media fetcher)"
    }
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"{query} filetype:bitmap",
        "gsrnamespace": 6,  # File namespace
        "gsrlimit": 5,
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
    }
    try:
        r = requests.get(COMMONS_API, params=params, headers=headers, timeout=12)
        if r.status_code == 200:
            data = r.json()
            pages = data.get("query", {}).get("pages", {})
            for _, page_info in pages.items():
                imageinfo = page_info.get("imageinfo", [])
                if not imageinfo:
                    continue
                info = imageinfo[0]
                url = info.get("url")
                width = info.get("width", 0)
                height = info.get("height", 0)
                mime = info.get("mime", "")

                # Prefer high-res images
                if url and mime in ["image/jpeg", "image/png", "image/webp"] and width >= 800 and height >= 600:
                    metadata = info.get("extmetadata", {})
                    license_name = metadata.get("LicenseShortName", {}).get("value", "Public Domain / CC")
                    return {
                        "url": url,
                        "license": license_name,
                        "source": f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(page_info.get('title', ''))}"
                    }
    except Exception as e:
        print(f"Wikimedia search warning for '{query}': {e}")
    return None

def _create_fallback_card(text: str, highlight: str, output_path: Path, channel: str) -> None:
    """Generate a sleek, minimalist cinematic gradient card for vertical video."""
    cfg = get_channel_config(channel)
    colors = cfg.get("fallback_colors", [("#0f2027", "#203a43", "#2c5364")])[0]

    # Create vertical image with vertical gradient
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), colors[0])
    draw = ImageDraw.Draw(img)

    # Simple 2-point gradient
    r1, g1, b1 = int(colors[0][1:3], 16), int(colors[0][3:5], 16), int(colors[0][5:7], 16)
    r2, g2, b2 = int(colors[-1][1:3], 16), int(colors[-1][3:5], 16), int(colors[-1][5:7], 16)

    for y in range(VIDEO_HEIGHT):
        ratio = y / float(VIDEO_HEIGHT)
        nr = int(r1 + (r2 - r1) * ratio)
        ng = int(g1 + (g2 - g1) * ratio)
        nb = int(b1 + (b2 - b1) * ratio)
        draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(nr, ng, nb))

    # Add decorative geometric accents
    accent_color = (255, 215, 0) if channel == "history" else (0, 200, 255)
    draw.line([(120, 400), (960, 400)], fill=accent_color, width=4)
    draw.line([(120, 1520), (960, 1520)], fill=accent_color, width=4)

    # Use default font or truetype
    try:
        font_large = ImageFont.truetype("arial.ttf", 64)
        font_small = ImageFont.truetype("arial.ttf", 40)
    except Exception:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Draw highlight title
    title_text = highlight.upper() if highlight else text[:30].upper()
    draw.text((VIDEO_WIDTH // 2, 850), title_text, fill=(255, 255, 255), font=font_large, anchor="mm")
    
    channel_tag = f"• {cfg['name'].upper()} •"
    draw.text((VIDEO_WIDTH // 2, 450), channel_tag, fill=accent_color, font=font_small, anchor="mm")

    img.save(output_path, "JPEG", quality=92)

def fetch_scene_visuals(channel: str, storyboard: Dict[str, Any], output_dir: Path) -> List[Dict[str, Any]]:
    """Acquire or render an image for each scene in the storyboard."""
    scenes = storyboard.get("scenes", [])
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = []

    headers = {"User-Agent": "YouTubeShortsAutomation/1.0 (educational)"}

    for scene in scenes:
        scene_id = scene.get("scene_id", 1)
        query = scene.get("visual_query", "")
        highlight = scene.get("caption_highlight", "")
        narration = scene.get("narration", "")

        img_filename = f"scene_{scene_id:02d}.jpg"
        img_path = output_dir / img_filename

        print(f"[{channel.upper()}] Scene {scene_id}: Searching visual for '{query}'...")
        media_info = _search_wikimedia_image(query)

        downloaded = False
        if media_info and media_info.get("url"):
            try:
                img_res = requests.get(media_info["url"], headers=headers, timeout=20)
                if img_res.status_code == 200:
                    with open(img_path, "wb") as f:
                        f.write(img_res.content)
                    
                    # Verify Pillow can open and process
                    with Image.open(img_path) as test_img:
                        test_img.verify()
                    downloaded = True
                    manifest.append({
                        "scene_id": scene_id,
                        "file": str(img_path),
                        "query": query,
                        "source": media_info.get("source"),
                        "license": media_info.get("license"),
                        "is_fallback": False
                    })
                    print(f"  ✓ Downloaded image from Wikimedia ({media_info.get('license')})")
            except Exception as e:
                print(f"  ✗ Failed to download/verify Wikimedia image: {e}")

        if not downloaded:
            print("  ↳ Generating cinematic fallback visual card...")
            _create_fallback_card(narration, highlight, img_path, channel)
            manifest.append({
                "scene_id": scene_id,
                "file": str(img_path),
                "query": query,
                "source": "Generated Fallback",
                "license": "Internal",
                "is_fallback": True
            })

    # Save visual manifest
    with open(output_dir / "visual_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest
