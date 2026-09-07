# YouTube Shorts Production Engine (₹0 Cloud Architecture)

An automated, cloud-native YouTube Shorts production system built for two channels:
1. **Science / Scientific Facts**
2. **History / Historical Facts**

Runs entirely on **GitHub Actions** at **₹0 operating cost**, producing 1 ready-to-publish vertical Short per day per channel with just ~10 minutes of daily review.

---

## ⚡ Key Features

- **₹0 Operating Cost**: Uses GitHub Actions (unlimited minutes on public repos), Google Gemini Free Tier, Microsoft Edge Neural TTS, Wikipedia & NASA public APIs, and FFmpeg.
- **Computer-Independent**: Cloud-executed daily via scheduled GitHub Actions crons. Your computer does not need to stay on.
- **10-Minute Daily Review Workflow**: Workflows automatically generate the video, synced captions, and YouTube metadata, packaging them as download artifacts. You inspect the video, then approve with 1 click.
- **1080x1920 Vertical Video**: Native 9:16 Shorts format with Ken Burns pan/zoom motion dynamics and burned-in high-contrast subtitles.
- **Fact-Checked & Grounded**: LLM extracts verified facts from Wikipedia and NASA APIs, preventing hallucinations and generic lists.
- **Duplicate Prevention**: Automatically records all covered topics in `science_data/previous_topics.json` and `history_data/previous_topics.json` and commits them back to git.

---

## 🏗️ Architecture & Pipeline Stages

```
GitHub Actions Cron (Daily)
   │
   ├── [1. Topic Generator]       --> Gemini 2.0/2.5 Flash + previous_topics.json deduplication
   ├── [2. Research & Grounding]  --> Wikipedia API & NASA Image/Data Library
   ├── [3. Storyboard Director]   --> Scene breakdown, pacing, and visual search terms
   ├── [4. Neural Voiceover]      --> Edge-TTS (en-US-ChristopherNeural / en-US-GuyNeural)
   ├── [5. Synchronized Captions] --> 2-3 word bold uppercase animated subtitles (.srt / .ass)
   ├── [6. Visual Acquisition]    --> Wikimedia Commons (CC/Public Domain) + PIL Fallback Cards
   ├── [7. FFmpeg Rendering]      --> 1080x1920 video, Ken Burns zoom, audio ducking, subtitle burn
   ├── [8. Quality Control]       --> 6-point automated asset and duration verification
   ├── [9. Metadata Generator]    --> YouTube title, description, tags, citations, and disclosures
   └── [10. Artifact Packaging]   --> Packaged for 10-minute human review before publishing
```

---

## 🔐 Required GitHub Secrets

To run the automated workflows, configure these in **GitHub Repository → Settings → Secrets and variables → Actions**:

| Secret Name | Required | Description | Where to Get |
|---|---|---|---|
| `GEMINI_API_KEY` | **Yes** | Google Gemini API Key | [Google AI Studio](https://aistudio.google.com/) (Free) |
| `YOUTUBE_CLIENT_ID` | Optional | YouTube OAuth2 Client ID | Google Cloud Console |
| `YOUTUBE_CLIENT_SECRET` | Optional | YouTube OAuth2 Client Secret | Google Cloud Console |
| `YOUTUBE_REFRESH_TOKEN_SCIENCE` | Optional | OAuth Refresh Token (Science) | One-time OAuth setup |
| `YOUTUBE_REFRESH_TOKEN_HISTORY` | Optional | OAuth Refresh Token (History) | One-time OAuth setup |

*(Note: YouTube secrets are only needed if you want automated API publishing via `publish.yml`. You can also just download the artifact and upload manually in 2 minutes.)*

---

## 📅 Scheduled Daily Runs

| Channel | Schedule (UTC) | Schedule (IST) | Workflow File |
|---|---|---|---|
| **Science Channel** | 03:00 AM UTC | 08:30 AM IST | `.github/workflows/science.yml` |
| **History Channel** | 04:00 AM UTC | 09:30 AM IST | `.github/workflows/history.yml` |

You can also manually trigger any pipeline run at any time via the **Actions** tab on GitHub (**Run workflow** button).

---

## 💻 Local Usage & Testing

### 1. Installation
```bash
git clone https://github.com/ishankoske-svg/Name-youtube-shorts-engine.git
cd Name-youtube-shorts-engine
pip install -r requirements.txt
```

### 2. Set API Key
```bash
# Windows PowerShell
$env:GEMINI_API_KEY="your_api_key_here"

# Linux / macOS
export GEMINI_API_KEY="your_api_key_here"
```

### 3. Run Pipeline CLI
```bash
# Run full pipeline for Science
python run_pipeline.py --channel science --stage all

# Run full pipeline for History
python run_pipeline.py --channel history --stage all

# Test individual stages:
python run_pipeline.py --channel science --stage topic
python run_pipeline.py --channel science --stage research
python run_pipeline.py --channel science --stage voice
python run_pipeline.py --channel science --stage visuals
```

---

## 📂 Repository Structure

```
.
├── .github/workflows/
│   ├── science.yml              # Daily Science Shorts cron
│   ├── history.yml              # Daily History Shorts cron
│   ├── test.yml                 # Interactive diagnostic workflow
│   └── publish.yml              # YouTube publishing workflow
├── pipeline/
│   ├── config.py                # Channel voices, specs, and directories
│   ├── topic_generator.py       # Topic creation & deduplication
│   ├── researcher.py            # Wikipedia & NASA fact verification
│   ├── script_director.py       # Storyboard & scene pacing
│   ├── voice_engine.py          # Edge-TTS voiceover synthesis
│   ├── caption_engine.py        # Synchronized bold captions
│   ├── visual_fetcher.py        # Wikimedia Commons asset downloader
│   ├── video_renderer.py        # FFmpeg assembly (1080x1920)
│   ├── qc_validator.py          # Quality control validation
│   ├── metadata_builder.py      # YouTube titles, tags, and description
│   └── uploader.py              # YouTube Data API uploader
├── science_data/
│   └── previous_topics.json     # Science topic memory
├── history_data/
│   └── previous_topics.json     # History topic memory
├── assets/
│   ├── music/                   # Royalty-free background audio
│   └── fonts/                   # Fonts for styled subtitles
├── history_generator.py         # Backwards-compatible history runner
├── test_gemini.py               # Backwards-compatible science runner
├── run_pipeline.py              # Unified pipeline CLI
├── requirements.txt
└── .env.example
```

---

## 📜 License
This project is open source and available under the [MIT License](LICENSE).
