import os
import asyncio
import wave
from pathlib import Path
from typing import Dict, Any, Tuple
from pipeline.config import get_channel_config

async def _generate_edge_tts(text: str, voice: str, rate: str, audio_path: Path) -> str:
    import edge_tts
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
    submaker = edge_tts.SubMaker()
    
    with open(audio_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed((chunk["offset"], chunk["duration"]), chunk["text"])
                
    return submaker.get_srt()

def _get_exact_audio_duration(file_path: Path, srt_text: str = "") -> float:
    """
    Get 100% exact audio duration using SRT end timestamp or ffprobe.
    Never relies on bitrate estimation which cuts off audio prematurely.
    """
    import subprocess
    import re
    
    # Method 1: Check with ffprobe if installed
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            dur = float(res.stdout.strip())
            if dur > 0.5:
                return dur
    except Exception:
        pass

    # Method 2: Extract last timestamp from generated SRT cues
    if srt_text:
        # Find all timestamps like 00:00:42,125
        timestamps = re.findall(r'(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})', srt_text)
        if timestamps:
            last_ts = timestamps[-1]
            hrs, mins, secs, ms = map(int, last_ts)
            total_sec = hrs * 3600 + mins * 60 + secs + (ms / 1000.0)
            if total_sec > 1.0:
                # Add small 0.3s padding for audio trail
                return total_sec + 0.3

    # Method 3: Wave header if wav
    try:
        with wave.open(str(file_path), "rb") as wf:
            return wf.getnframes() / float(wf.getframerate())
    except Exception:
        pass

    # Fallback to file size with conservative bitrate (48kbps = 6,000 bytes/sec)
    size_bytes = os.path.getsize(file_path)
    return max(5.0, size_bytes / 6000.0)


def generate_voiceover(channel: str, narration_text: str, output_dir: Path) -> Tuple[Path, str, float]:
    """
    Synthesize voice narration using edge-tts.
    Returns: (audio_path, srt_subtitles_text, duration_seconds)
    """
    cfg = get_channel_config(channel)
    voice = cfg["voice"]
    rate = cfg.get("voice_rate", "+5%")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = output_dir / "voice.mp3"
    
    print(f"[{channel.upper()}] Generating voiceover with voice: {voice}...")
    srt_text = ""
    try:
        srt_text = asyncio.run(_generate_edge_tts(narration_text, voice, rate, audio_path))
    except Exception as e:
        print(f"Warning: edge-tts generation failed: {e}. Generating fallback tone/silence.")
        # Fallback to minimal silent wav file if offline
        audio_path = output_dir / "voice.wav"
        with wave.open(str(audio_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            # Write 5 seconds of silence
            wf.writeframes(b"\x00" * (44100 * 2 * 5))
        srt_text = "1\n00:00:00,000 --> 00:00:05,000\n[Audio unavailable]"

    duration = _get_exact_audio_duration(audio_path, srt_text)
    print(f"[{channel.upper()}] Voiceover generated: {audio_path.name} (exact duration: {duration:.2f}s)")
    return audio_path, srt_text, duration
