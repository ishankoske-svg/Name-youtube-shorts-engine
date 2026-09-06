import os
from google import genai

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)

prompt = """
You are the topic generator for a YouTube Shorts channel.

Generate 10 highly interesting science video ideas.

Rules:
- Must be scientifically accurate.
- Must work as a 30-60 second Short.
- Must create curiosity.
- Avoid generic "5 facts" topics.
- Prefer questions, surprising phenomena, strange discoveries,
  hypothetical situations, and counterintuitive facts.

Return ONLY a numbered list.
"""

response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=prompt
)

print(response.text)
