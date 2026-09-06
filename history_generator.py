import os
import json
from google import genai

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)

prompt = """
You are the topic and script researcher for a YouTube Shorts channel
about HISTORY.

Generate ONE highly interesting history topic suitable for a 30-60 second
YouTube Short.

The topic should:
- Be genuinely historical
- Have a strong curiosity hook
- Be possible to explain accurately in under 60 seconds
- Have good visual potential
- Avoid common overused "top 5 history facts" formats
- Avoid myths or claims that cannot be reliably supported
- Be interesting to viewers aged roughly 14-25

Then write a short narration script for the topic.

Return ONLY valid JSON in exactly this format:

{
  "topic": "topic here",
  "hook": "opening sentence here",
  "script": "complete narration here",
  "why_interesting": "why viewers would care",
  "visual_ideas": [
    "visual idea 1",
    "visual idea 2",
    "visual idea 3"
  ]
}

Do not use markdown.
"""

response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=prompt
)

text = response.text.strip()

print(text)

# Verify that Gemini actually returned valid JSON
data = json.loads(text)

os.makedirs("history_output", exist_ok=True)

with open("history_output/history_topic.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("\nHistory topic successfully generated.")
