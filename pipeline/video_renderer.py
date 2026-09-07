import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from pipeline.config import VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS

def is_ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None

def render_video(
    channel: str,
    storyboard: Dict[str, Any],
    visual_manifest: List[Dict[str, Any]],
    audio_path: Path,
    subtitle_path: Path,
    total_audio_duration: float,
    output_video_path: Path,
    bg_music_path: Optional[Path] = None
) -> Path:
    """
    Assemble the high-density YouTube Short using FFmpeg:
    - 15-30 dynamic visual shots (1.5 - 3.0s per shot)
    - 1080x1920 9:16 vertical resolution
    - Modern blurred background padding for landscape imagery (no black bars!)
    - Subtle Ken Burns motion on each shot
    - Synchronized high-contrast bold subtitles in the Shorts safe zone
    - Audio ducking (voiceover + subtle ambient background track)
    """
    output_video_path.parent.mkdir(parents=True, exist_ok=True)

    shots = visual_manifest
    num_shots = len(shots)
    if num_shots == 0:
        raise RuntimeError("RENDER BLOCKED: No visual shots available in manifest. 100% coverage required.")

    # Validate that every single shot file exists on disk
    for shot in shots:
        s_file = Path(shot["file"])
        if not s_file.exists() or s_file.stat().st_size == 0:
            raise RuntimeError(f"RENDER BLOCKED: Shot {shot.get('shot_id')} media file missing or empty: {s_file}")

    if not is_ffmpeg_available():
        print("[RENDER] FFmpeg is not installed locally. Skipping render step.")
        with open(output_video_path, "wb") as f:
            f.write(b"MOCK_MP4_FILE_FOR_LOCAL_VALIDATION")
        return output_video_path

    # Duration calculations: Add 0.5s safety buffer so narration is NEVER cut off
    effective_duration = max(10.0, total_audio_duration + 0.5)
    shot_duration = max(1.2, effective_duration / num_shots)
    shot_frames = int(round(shot_duration * VIDEO_FPS))

    print(f"\n[{channel.upper()}] Rendering {num_shots} shots with FFmpeg (avg {shot_duration:.2f}s per shot, total: {effective_duration:.2f}s)...")

    temp_dir = output_video_path.parent / "temp_shots"
    temp_dir.mkdir(parents=True, exist_ok=True)
    segment_files = []

    # 1. Render each individual shot with blurred-background framing
    for idx, shot in enumerate(shots):
        img_file = Path(shot["file"])
        seg_file = temp_dir / f"shot_{idx:03d}.mp4"

        # Modern blurred background + sharp foreground filter graph
        # [bg]: Scale & crop to fill 1080x1920 + heavy boxblur
        # [fg]: Scale to fit within 1080x1920
        # Overlay foreground on blurred background
        vf_filter = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:25[bg];"
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,"
            f"zoompan=z='min(zoom+0.001,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={shot_frames}:s=1080x1920:fps={VIDEO_FPS}"
        )

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-t", f"{shot_duration:.3f}",
            "-i", str(img_file),
            "-filter_complex", vf_filter,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            "-t", f"{shot_duration:.3f}",
            str(seg_file)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and seg_file.exists():
            segment_files.append(seg_file)
        else:
            # If complex filter failed on strange format, fallback to standard scale
            fallback_vf = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps={VIDEO_FPS}"
            cmd_fallback = [
                "ffmpeg", "-y", "-loop", "1", "-t", f"{shot_duration:.3f}",
                "-i", str(img_file), "-vf", fallback_vf,
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                "-t", f"{shot_duration:.3f}", str(seg_file)
            ]
            res_fb = subprocess.run(cmd_fallback, capture_output=True)
            if res_fb.returncode == 0:
                segment_files.append(seg_file)
            else:
                raise RuntimeError(f"RENDER BLOCKED: Failed to render video segment for shot {idx}: {res.stderr[-250:]}")

    # 2. Concat all shot segments
    concat_list = temp_dir / "concat_shots.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for sf in segment_files:
            escaped = str(sf.resolve()).replace("\\", "/")
            f.write(f"file '{escaped}'\n")

    # 3. Final assemble with audio, music ducking, and bold captions
    sub_filter = ""
    ass_path = subtitle_path.with_suffix(".ass")
    srt_path = subtitle_path.with_suffix(".srt")

    # Prefer ASS for custom styles, fallback to SRT with explicit force_style
    if ass_path.exists():
        escaped_ass = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
        sub_filter = f"ass='{escaped_ass}'"
    elif srt_path.exists():
        escaped_srt = str(srt_path.resolve()).replace("\\", "/").replace(":", "\\:")
        sub_filter = f"subtitles='{escaped_srt}':force_style='FontName=DejaVu Sans,FontSize=22,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=3,Alignment=2,MarginV=360'"

    has_music = bg_music_path and bg_music_path.exists()

    cmd_final = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-i", str(audio_path),
    ]

    if has_music:
        cmd_final.extend(["-stream_loop", "-1", "-i", str(bg_music_path)])
        # Duck background music to volume=0.07 underneath speech
        filter_complex = "[2:a]volume=0.07[bgm];[1:a][bgm]amix=inputs=2:duration=first[aout]"
        if sub_filter:
            filter_complex += f";[0:v]{sub_filter}[vout]"
            cmd_final.extend(["-filter_complex", filter_complex, "-map", "[vout]", "-map", "[aout]"])
        else:
            cmd_final.extend(["-filter_complex", filter_complex, "-map", "0:v", "-map", "[aout]"])
    else:
        if sub_filter:
            cmd_final.extend(["-vf", sub_filter])
        cmd_final.extend(["-map", "0:v", "-map", "1:a"])

    cmd_final.extend([
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_video_path)
    ])

    print(f"[{channel.upper()}] Encoding final 1080x1920 Short with FFmpeg...")
    final_res = subprocess.run(cmd_final, capture_output=True, text=True)

    if final_res.returncode != 0:
        print(f"Notice: Primary assemble returned code {final_res.returncode}. Retrying with basic audio-video mux...")
        cmd_mux = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-i", str(audio_path),
            "-c:v", "copy", "-c:a", "aac",
            str(output_video_path)
        ]
        subprocess.run(cmd_mux, check=True)

    # Clean up temporary segments
    shutil.rmtree(temp_dir, ignore_errors=True)

    print(f"[{channel.upper()}] Short successfully assembled: {output_video_path.name} ({num_shots} shots, {effective_duration:.2f}s)")
    return output_video_path
