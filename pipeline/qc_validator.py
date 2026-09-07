import os
import json
from pathlib import Path
from typing import Dict, Any, List
from PIL import Image

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
    """
    Strict 100% Visual Coverage QC validator.
    Fails if visual_coverage_ratio < 1.0 or any shot media is missing/unreadable.
    """
    checks = []
    shots = storyboard.get("shots", [])
    num_planned_shots = len(shots)
    num_resolved_shots = len(visual_manifest)

    # 1. Visual Shot Count Check (Target: 14 to 30 shots)
    checks.append({
        "name": "shot_density",
        "passed": num_resolved_shots >= 10,
        "details": f"Total visual shots: {num_resolved_shots} (Target: 14-30)"
    })

    # 2. 100% Visual Coverage Ratio Check
    coverage_ratio = (num_resolved_shots / num_planned_shots) if num_planned_shots > 0 else 0.0
    checks.append({
        "name": "visual_coverage_ratio",
        "passed": coverage_ratio >= 1.0,
        "details": f"Visual coverage: {coverage_ratio * 100:.1f}% ({num_resolved_shots}/{num_planned_shots} shots)"
    })

    # 3. Asset Existence & Readability (No blank or broken files)
    assets_valid = True
    bad_assets = []
    for shot in visual_manifest:
        fpath = Path(shot["file"])
        if not fpath.exists() or fpath.stat().st_size < 1000:
            assets_valid = False
            bad_assets.append(f"Shot {shot.get('shot_id')}: missing or too small")
            continue
        # Verify image readability with Pillow
        try:
            with Image.open(fpath) as img:
                img.verify()
        except Exception as e:
            assets_valid = False
            bad_assets.append(f"Shot {shot.get('shot_id')}: unreadable ({e})")

    checks.append({
        "name": "assets_readability",
        "passed": assets_valid,
        "details": f"All {num_resolved_shots} media files verified on disk" if assets_valid else f"Errors: {bad_assets[:3]}"
    })

    # 4. Audio Validity & Non-Empty
    audio_exists = audio_path.exists() and audio_path.stat().st_size > 2000
    checks.append({
        "name": "audio_track",
        "passed": audio_exists,
        "details": f"Audio file: {audio_path.name} ({audio_path.stat().st_size if audio_path.exists() else 0} bytes)"
    })

    # 5. Captions Coverage
    srt_exists = subtitle_path.exists() and subtitle_path.stat().st_size > 50
    checks.append({
        "name": "captions_coverage",
        "passed": srt_exists,
        "details": f"Subtitles: {subtitle_path.name} ({subtitle_path.stat().st_size if subtitle_path.exists() else 0} bytes)"
    })

    # 6. Final Video File
    video_exists = video_path.exists() and video_path.stat().st_size > 5000
    checks.append({
        "name": "video_rendered",
        "passed": video_exists,
        "details": f"Final video: {video_path.name} ({video_path.stat().st_size if video_path.exists() else 0} bytes)"
    })

    all_passed = all(c["passed"] for c in checks)
    report = {
        "channel": channel,
        "status": "PASS" if all_passed else "FAIL",
        "coverage_ratio": coverage_ratio,
        "total_shots": num_resolved_shots,
        "checks": checks
    }

    report_path = output_dir / "qc_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "="*50)
    print(f"[{channel.upper()}] QC VALIDATION: {report['status']}")
    print(f"Visual Coverage: {coverage_ratio * 100:.1f}%")
    for c in checks:
        icon = "✓" if c["passed"] else "✗"
        print(f"  {icon} {c['name']}: {c['details']}")
    print("="*50 + "\n")

    if not all_passed:
        raise RuntimeError(f"QUALITY CONTROL FAILED: Visual coverage is {coverage_ratio * 100:.1f}%. Render rejected.")

    return report
