import re
from pathlib import Path
from typing import List, Dict

def _format_timestamp_srt(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

def _format_timestamp_ass(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        centis = 99
    return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"

def create_short_captions_from_srt(
    raw_srt: str,
    output_path: Path,
    narration_text: str = "",
    audio_duration: float = 0.0,
    max_words_per_cue: int = 3
) -> Path:
    """
    Format raw word-level or sentence-level subtitles into punchy 2-3 word uppercase cues
    optimized for YouTube Shorts visual engagement.
    Generates both an SRT and an Advanced SubStation Alpha (.ass) file for styling.
    """
    # Parse existing SRT cues
    cue_pattern = re.compile(
        r'(\d+)\s*\n'
        r'(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*\n'
        r'([\s\S]*?)(?=\n\s*\n\d+|\Z)'
    )

    cues = []
    for match in cue_pattern.finditer(raw_srt):
        _, start_str, end_str, text = match.groups()
        text = text.replace("\n", " ").strip()
        if text:
            # Parse start and end to seconds
            def to_secs(s):
                s = s.replace(",", ".")
                h, m, sec = s.split(":")
                return int(h) * 3600 + int(m) * 60 + float(sec)
            cues.append({
                "start": to_secs(start_str),
                "end": to_secs(end_str),
                "text": text
            })

    # If raw srt was empty or failed, generate proportional cues from narration text
    if not cues and narration_text:
        words = narration_text.split()
        dur = max(5.0, audio_duration)
        word_dur = dur / max(1, len(words))
        for i in range(0, len(words), max_words_per_cue):
            chunk = words[i:i + max_words_per_cue]
            cues.append({
                "start": i * word_dur,
                "end": min(dur, (i + len(chunk)) * word_dur),
                "text": " ".join(chunk)
            })
    elif not cues:
        cues = [{"start": 0.0, "end": 4.0, "text": "DISCOVER THE TRUTH"}]

    # Chunk cues into 2-4 words bursts
    chunked_cues = []
    current_words = []
    start_time = None
    end_time = None

    for cue in cues:
        words = cue["text"].split()
        if not words:
            continue
        duration = max(0.1, cue["end"] - cue["start"])
        word_dur = duration / len(words)

        for i, w in enumerate(words):
            w_start = cue["start"] + i * word_dur
            w_end = w_start + word_dur
            if start_time is None:
                start_time = w_start
            end_time = w_end
            current_words.append(w.upper())

            if len(current_words) >= max_words_per_cue:
                chunked_cues.append({
                    "start": start_time,
                    "end": end_time,
                    "text": " ".join(current_words)
                })
                current_words = []
                start_time = None

    if current_words and start_time and end_time:
        chunked_cues.append({
            "start": start_time,
            "end": end_time,
            "text": " ".join(current_words)
        })

    # Write SRT
    srt_file = output_path.with_suffix(".srt")
    with open(srt_file, "w", encoding="utf-8") as f:
        for idx, c in enumerate(chunked_cues, start=1):
            f.write(f"{idx}\n")
            f.write(f"{_format_timestamp_srt(c['start'])} --> {_format_timestamp_srt(c['end'])}\n")
            f.write(f"{c['text']}\n\n")

    # Write ASS (Advanced SubStation Alpha) for stylish vertical rendering
    ass_file = output_path.with_suffix(".ass")
    ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ShortsDefault,Arial,68,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,3,2,60,60,420,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    for c in chunked_cues:
        ass_content += f"Dialogue: 0,{_format_timestamp_ass(c['start'])},{_format_timestamp_ass(c['end'])},ShortsDefault,,0,0,0,,{c['text']}\n"

    with open(ass_file, "w", encoding="utf-8") as f:
        f.write(ass_content)

    return srt_file
