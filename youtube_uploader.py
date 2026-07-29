import base64
import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube.upload"


def get_latest_story_file() -> Path:
    output_dir = Path("output")

    story_files = list(output_dir.glob("*.json"))

    if not story_files:
        raise RuntimeError("Story JSON file nahi mili.")

    return max(
        story_files,
        key=lambda file_path: file_path.stat().st_mtime,
    )


def load_story(story_path: Path) -> dict:
    return json.loads(
        story_path.read_text(encoding="utf-8")
    )


def get_credentials() -> Credentials:
    credentials_b64 = os.getenv(
        "YOUTUBE_CREDENTIALS_B64",
        "",
    ).strip()

    if not credentials_b64:
        raise RuntimeError(
            "YOUTUBE_CREDENTIALS_B64 GitHub secret missing hai."
        )

    try:
        credentials_json = base64.b64decode(
            credentials_b64
        ).decode("utf-8")

        credentials_data = json.loads(credentials_json)

    except Exception as error:
        raise RuntimeError(
            "YOUTUBE_CREDENTIALS_B64 valid Base64 JSON nahi hai."
        ) from error

    required_fields = [
        "client_id",
        "client_secret",
        "refresh_token",
    ]

    missing_fields = [
        field
        for field in required_fields
        if not credentials_data.get(field)
    ]

    if missing_fields:
        raise RuntimeError(
            "YouTube credentials mein ye fields missing hain: "
            + ", ".join(missing_fields)
        )

    credentials_data.setdefault(
        "token_uri",
        "https://oauth2.googleapis.com/token",
    )

    credentials = Credentials.from_authorized_user_info(
        credentials_data,
        scopes=[YOUTUBE_SCOPE],
    )

    if not credentials.valid:
        credentials.refresh(Request())

    return credentials


def build_description(story: dict) -> str:
    youtube_data = story.get("youtube", {})

    description = str(
        youtube_data.get("description", "")
    ).strip()

    hashtags = youtube_data.get("hashtags", [])

    if not isinstance(hashtags, list):
        hashtags = []

    hashtags = [
        str(tag).strip()
        for tag in hashtags
        if str(tag).strip()
    ]

    if "#Shorts" not in hashtags:
        hashtags.insert(0, "#Shorts")

    return (
        description
        + "\n\n"
        + " ".join(hashtags)
    ).strip()


def upload_video(
    story: dict,
    credentials: Credentials,
) -> str:
    video_path = Path(
        story.get(
            "video_file",
            "output/video/final_short.mp4",
        )
    )

    if not video_path.exists():
        raise RuntimeError(
            f"Final video file nahi mili: {video_path}"
        )

    youtube_data = story.get("youtube", {})

    title = str(
        youtube_data.get(
            "title",
            "Milo & Friends #Shorts",
        )
    ).strip()

    if not title:
        title = "Milo & Friends #Shorts"

    title = title[:100]
    description = build_description(story)

    privacy_status = os.getenv(
        "YOUTUBE_PRIVACY_STATUS",
        "private",
    ).strip().lower()

    if privacy_status not in {
        "private",
        "unlisted",
        "public",
    }:
        privacy_status = "private"

    youtube = build(
        "youtube",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )

    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "1",
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": True,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        chunksize=8 * 1024 * 1024,
        resumable=True,
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media,
    )

    print("YouTube upload start ho raha hai...")
    print(f"Title: {title}")
    print(f"Privacy: {privacy_status}")

    response = None

    while response is None:
        upload_status, response = request.next_chunk()

        if upload_status:
            progress = int(
                upload_status.progress() * 100
            )
            print(f"Upload progress: {progress}%")

    video_id = response.get("id")

    if not video_id:
        raise RuntimeError(
            "YouTube ne video ID return nahi ki."
        )

    return video_id


def main() -> None:
    print("Milo & Friends YouTube uploader start ho raha hai...")

    story_path = get_latest_story_file()
    story = load_story(story_path)

    credentials = get_credentials()

    video_id = upload_video(
        story=story,
        credentials=credentials,
    )

    story["youtube_video_id"] = video_id
    story["youtube_upload_status"] = "uploaded"

    story_path.write_text(
        json.dumps(
            story,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("YouTube upload successful.")
    print(f"Video ID: {video_id}")


if __name__ == "__main__":
    main()
