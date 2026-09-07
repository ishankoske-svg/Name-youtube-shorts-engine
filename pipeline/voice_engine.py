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

def _estimate_audio_duration(file_path: Path) -> float:
    """Get duration in seconds using mutagen, wave, or file size estimation."""
    try:
        # Try wave first
        with wave.open(str(file_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate)
    except Exception:
        pass

    # For MP3, approximate with typical 128kbps bit rate or read metadata
    size_bytes = os.path.getsize(file_path)
    # 128 kbps = 16,000 bytes/sec
    return max(1.0, size_bytes / 16000.0)

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

    duration = _estimate_audio_duration(audio_path)
    print(f"[{channel.upper()}] Voiceover generated: {audio_path.name} (approx {duration:.1f}s)")
    return audio_path, srt_text, duration
