import os
import json
from pathlib import Path
from typing import Dict, Any, List

def run_quality_check(
    channel: str,
    topic_data: Dict[str, Any],
    storyboard: Dict[str, Any],
    visual_manifest: List[Dict[str, Any]],
    audio_path: Path,
    subtitle_path: Path,
    video_path: Path,
    output_dir: Path
) -> Dict[str, Any]:
    """Execute quality control checks across all generated assets."""
    checks = []

    # 1. Topic check
    topic = topic_data.get("topic", "").strip()
    checks.append({
        "name": "topic_validity",
        "passed": bool(topic),
        "details": f"Topic: '{topic}'"
    })

    # 2. Script word count
    script = topic_data.get("script", "").strip()
    word_count = len(script.split())
    checks.append({
        "name": "script_length",
        "passed": 40 <= word_count <= 220,
        "details": f"Narration word count: {word_count} words"
    })

    # 3. Audio file
    audio_exists = audio_path.exists() and audio_path.stat().st_size > 1000
    checks.append({
        "name": "audio_track",
        "passed": audio_exists,
        "details": f"Audio file size: {audio_path.stat().st_size if audio_path.exists() else 0} bytes"
    })

    # 4. Subtitles
    srt_exists = subtitle_path.exists() and subtitle_path.stat().st_size > 50
    checks.append({
        "name": "subtitles",
        "passed": srt_exists,
        "details": f"Subtitle file: {subtitle_path.name}"
    })

    # 5. Visual assets
    visuals_valid = len(visual_manifest) >= 3 and all(Path(v["file"]).exists() for v in visual_manifest)
    checks.append({
        "name": "visual_assets",
        "passed": visuals_valid,
        "details": f"Total visual scenes: {len(visual_manifest)}"
    })

    # 6. Video file
    video_exists = video_path.exists() and video_path.stat().st_size > 0
    checks.append({
        "name": "video_rendered",
        "passed": video_exists,
        "details": f"Video output: {video_path.name} ({video_path.stat().st_size if video_path.exists() else 0} bytes)"
    })

    all_passed = all(c["passed"] for c in checks)
    report = {
        "channel": channel,
        "status": "PASS" if all_passed else "FAIL",
        "checks": checks
    }

    report_path = output_dir / "qc_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"[{channel.upper()}] QC Report Status: {report['status']}")
    for c in checks:
        icon = "✓" if c["passed"] else "✗"
        print(f"  {icon} {c['name']}: {c['details']}")

    return report
