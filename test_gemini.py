import os
import json
from google import genai

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)

SCIENCE_FILE = "science_data/previous_topics.json"

# Create output directory
os.makedirs("science_output", exist_ok=True)

# Load previously generated topics
if os.path.exists(SCIENCE_FILE):
    with open(SCIENCE_FILE, "r", encoding="utf-8") as f:
        previous_topics = json.load(f)
else:
    previous_topics = []

# Give Gemini the previous topics
previous_text = "\n".join(
    f"- {topic}" for topic in previous_topics
)

prompt = f"""
You are the topic generator for a YouTube Shorts channel about SCIENCE.

Your job is to generate ONE fascinating and genuinely educational
science topic for a 30-60 second YouTube Short.

IMPORTANT:
The topic MUST NOT be the same as, or substantially similar to,
any topic in the previous-topic list below.

PREVIOUS TOPICS:
{previous_text}

Choose a topic that:

- Is scientifically accurate
- Has a strong curiosity hook
- Can be explained clearly in 30-60 seconds
- Has strong visual potential
- Is interesting to viewers aged 14-25
- Makes the viewer think "Wait, why does that happen?"
- Has a surprising or counterintuitive explanation
- Can eventually be supported by reliable scientific sources
- Is understandable to a general audience
- Is NOT a generic list such as "5 interesting science facts"

Explore different science areas such as:

- Space
- Physics
- Human body
- Animals
- Earth
- Ocean
- Chemistry
- Biology
- Neuroscience
- Technology
- Astronomy
- Genetics
- Weather
- Evolution
- Weird natural phenomena

Good examples of the style we want:

"What would happen if Earth suddenly stopped spinning?"

"Why don't birds get electrocuted when they sit on power lines?"

"Why doesn't your stomach digest itself?"

"Why does space look black even when the Sun is shining?"

"Why can you see lightning before you hear thunder?"

Avoid:

- Fake science
- Pseudoscience
- Conspiracy theories
- Medical misinformation
- Exaggerated claims
- Made-up experiments
- Topics requiring dangerous experiments
- Generic "10 science facts" content

The goal is NOT simply to produce a fact.

The goal is to find a fascinating scientific question
with a surprising explanation.

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

# Safety check
if not new_topic.strip():
    raise ValueError("Gemini returned an empty topic.")

# Add new topic to history
previous_topics.append(new_topic)

with open(SCIENCE_FILE, "w", encoding="utf-8") as f:
    json.dump(
        previous_topics,
        f,
        indent=2,
        ensure_ascii=False
    )

# Save current result
with open(
    "science_output/science_topic.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        data,
        f,
        indent=2,
        ensure_ascii=False
    )

print("\nNew Science topic saved successfully.")
