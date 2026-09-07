import os
import json
from pathlib import Path
from typing import Dict, Any

def upload_to_youtube(channel: str, video_path: Path, metadata_path: Path) -> Dict[str, Any]:
    """Upload completed video to YouTube as private/unlisted using OAuth refresh token."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    token_env = f"YOUTUBE_REFRESH_TOKEN_{channel.upper()}"
    refresh_token = os.environ.get(token_env)

    if not (client_id and client_secret and refresh_token):
        raise ValueError(
            f"Missing YouTube OAuth credentials. Please configure YOUTUBE_CLIENT_ID, "
            f"YOUTUBE_CLIENT_SECRET, and {token_env} in your environment or GitHub Secrets."
        )

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret
    )

    youtube = build("youtube", "v3", credentials=creds)

    with open(metadata_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    body = {
        "snippet": {
            "title": meta.get("title", "Educational Short #Shorts"),
            "description": meta.get("description", ""),
            "tags": meta.get("tags", []),
            "categoryId": meta.get("categoryId", "27"),
        },
        "status": {
            "privacyStatus": meta.get("privacyStatus", "private"),
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024 * 5
    )

    print(f"[{channel.upper()}] Uploading '{meta.get('title')}' to YouTube as {body['status']['privacyStatus']}...")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Upload progress: {int(status.progress() * 100)}%")

    video_id = response.get("id")
    video_url = f"https://youtube.com/shorts/{video_id}"
    print(f"[{channel.upper()}] Upload successful! Video URL: {video_url}")

    return {
        "video_id": video_id,
        "video_url": video_url,
        "channel": channel,
        "status": body["status"]["privacyStatus"]
    }
