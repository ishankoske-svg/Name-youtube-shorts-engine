import os
import json
from google import genai

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)

HISTORY_FILE = "history_output/previous_topics.json"

# Create output directory
os.makedirs("history_output", exist_ok=True)

# Load previously generated topics
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        previous_topics = json.load(f)
else:
    previous_topics = []

# Give Gemini the previous topics
previous_text = "\n".join(
    f"- {topic}" for topic in previous_topics
)

prompt = f"""
You are the topic generator for a YouTube Shorts channel about HISTORY.

Your job is to generate ONE completely new and interesting historical topic.

IMPORTANT:
The topic MUST NOT be the same as, or substantially similar to,
any topic in the previous-topic list below.

PREVIOUS TOPICS:
{previous_text}

Choose a topic that:
- Is genuinely historical
- Has a strong curiosity hook
- Can be explained in 30-60 seconds
- Has strong visual potential
- Is interesting to viewers aged 14-25
- Is not a generic "5 facts" list
- Avoids common repetitive topics
- Avoids myths unless the video is specifically about debunking the myth
- Can eventually be supported by reliable historical sources

Try to explore different areas such as:
- Ancient civilizations
- Strange historical events
- Lost cities
- Historical inventions
- Wars and battles
- Engineering
- Daily life
- Historical mysteries
- Unexpected discoveries
- Important people
- Forgotten events

Return ONLY valid JSON.

Use exactly this format:

{{
  "topic": "topic here",
  "hook": "opening sentence here",
  "script": "complete short narration here",
  "why_interesting": "why viewers would care",
  "visual_ideas": [
    "visual idea 1",
    "visual idea 2",
    "visual idea 3"
  ]
}}

Do not use markdown.
"""

response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=prompt
)

text = response.text.strip()

print(text)

# Convert Gemini response into JSON
data = json.loads(text)

new_topic = data["topic"]

# Safety check: don't save an empty topic
if not new_topic.strip():
    raise ValueError("Gemini returned an empty topic.")

# Add new topic to our history
previous_topics.append(new_topic)

with open(HISTORY_FILE, "w", encoding="utf-8") as f:
    json.dump(
        previous_topics,
        f,
        indent=2,
        ensure_ascii=False
    )

# Save the current result
with open(
    "history_output/history_topic.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        data,
        f,
        indent=2,
        ensure_ascii=False
    )

print("\nNew History topic saved successfully.")
