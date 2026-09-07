import os
import sys
import argparse
import json
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from pipeline.config import get_channel_config
from pipeline.topic_generator import generate_topic
from pipeline.researcher import research_topic
from pipeline.script_director import create_storyboard
from pipeline.voice_engine import generate_voiceover
from pipeline.caption_engine import create_short_captions_from_srt
from pipeline.visual_fetcher import fetch_scene_visuals
from pipeline.video_renderer import render_video
from pipeline.qc_validator import run_quality_check
from pipeline.metadata_builder import generate_youtube_metadata
from pipeline.uploader import upload_to_youtube

def run_pipeline(channel: str, stage: str = "all", model_name: str = None) -> None:
    cfg = get_channel_config(channel)
    out_dir = Path(cfg["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*60)
    print(f"🎬 YOUTUBE SHORTS ENGINE: {cfg['name'].upper()}")
    print(f"Target Stage: {stage.upper()}")
    print(f"Output Directory: {out_dir}")
    print("="*60 + "\n")

    topic_file = out_dir / f"{channel.lower()}_topic.json"
    topic_data = None

    # --- STAGE 1: TOPIC GENERATION ---
    if stage in ["topic", "all"]:
        print("📌 [1/7] Generating unique topic...")
        topic_data = generate_topic(channel, model_name=model_name)
    else:
        if topic_file.exists():
            with open(topic_file, "r", encoding="utf-8") as f:
                topic_data = json.load(f)
        else:
            raise FileNotFoundError(f"Missing {topic_file}. Run with '--stage topic' first.")

    if stage == "topic":
        print("Done topic generation stage.")
        return

    # --- STAGE 2: RESEARCH & FACT-CHECKING ---
    print("\n🔍 [2/7] Researching & verifying facts...")
    research_data = research_topic(channel, topic_data, model_name=model_name)
    if stage == "research":
        print("Done research stage.")
        return

    # --- STAGE 3: STORYBOARD & SCENE DIRECTION ---
    print("\n📐 [3/7] Directing scenes and storyboard...")
    storyboard = create_storyboard(channel, topic_data, model_name=model_name)
    if stage == "storyboard":
        print("Done storyboard stage.")
        return

    # --- STAGE 4: VOICEOVER & SUBTITLES ---
    print("\n🎙️ [4/7] Synthesizing voice narration & subtitles...")
    script_text = topic_data.get("script", "")
    audio_path, raw_srt, audio_dur = generate_voiceover(channel, script_text, out_dir)
    subtitle_path = create_short_captions_from_srt(raw_srt, out_dir / "captions")
    if stage == "voice":
        print("Done voice & captions stage.")
        return

    # --- STAGE 5: VISUAL ASSET FETCHING ---
    print("\n🖼️ [5/7] Acquiring high-resolution visual assets...")
    visuals_dir = out_dir / "visuals"
    visual_manifest = fetch_scene_visuals(channel, storyboard, visuals_dir)
    if stage == "visuals":
        print("Done visual assets stage.")
        return

    # --- STAGE 6: VIDEO RENDERING ---
    print("\n🎞️ [6/7] Rendering 1080x1920 vertical video...")
    output_video_path = out_dir / f"{channel.lower()}_short.mp4"
    bg_music = cfg.get("default_music")
    render_video(
        channel=channel,
        storyboard=storyboard,
        visual_manifest=visual_manifest,
        audio_path=audio_path,
        subtitle_path=subtitle_path,
        total_audio_duration=audio_dur,
        output_video_path=output_video_path,
        bg_music_path=bg_music if (bg_music and bg_music.exists()) else None
    )

    # --- STAGE 7: QUALITY CONTROL & METADATA ---
    print("\n🛡️ [7/7] Executing QC and building YouTube metadata...")
    metadata = generate_youtube_metadata(
        channel=channel,
        topic_data=topic_data,
        research_data=research_data,
        visual_manifest=visual_manifest,
        output_dir=out_dir,
        model_name=model_name
    )

    qc_report = run_quality_check(
        channel=channel,
        topic_data=topic_data,
        storyboard=storyboard,
        visual_manifest=visual_manifest,
        audio_path=audio_path,
        subtitle_path=subtitle_path,
        video_path=output_video_path,
        output_dir=out_dir
    )

    print("\n" + "="*60)
    print(f"✨ PIPELINE EXECUTION COMPLETE: {cfg['name'].upper()}")
    print(f"Video File:    {output_video_path}")
    print(f"Metadata File: {out_dir / 'metadata.json'}")
    print(f"QC Status:     {qc_report['status']}")
    print("="*60 + "\n")

    # Optional Upload stage
    if stage == "upload":
        upload_to_youtube(channel, output_video_path, out_dir / "metadata.json")

def main():
    parser = argparse.ArgumentParser(description="YouTube Shorts Automation Engine")
    parser.add_argument(
        "--channel",
        choices=["science", "history"],
        required=True,
        help="Channel to run (science or history)"
    )
    parser.add_argument(
        "--stage",
        choices=["topic", "research", "storyboard", "voice", "visuals", "render", "all", "upload"],
        default="all",
        help="Pipeline stage to execute (default: all)"
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override default Gemini model (e.g. gemini-3.6-flash)"
    )
    args = parser.parse_args()
    run_pipeline(channel=args.channel, stage=args.stage, model_name=args.model)

if __name__ == "__main__":
    main()
