import base64
import json
import os
import random
import time
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload


YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube.upload"

VALID_PRIVACY_STATUSES = {
    "private",
    "unlisted",
    "public",
}

RETRIABLE_STATUS_CODES = {
    500,
    502,
    503,
    504,
}

MAX_UPLOAD_RETRIES = 6


def get_latest_story_file() -> Path:
    output_dir = Path("output")

    if not output_dir.exists():
        raise RuntimeError("output folder nahi mila.")

    story_files = list(output_dir.glob("*.json"))

    if not story_files:
        raise RuntimeError("Story JSON file nahi mili.")

    return max(
        story_files,
        key=lambda file_path: file_path.stat().st_mtime,
    )


def load_story(story_path: Path) -> dict[str, Any]:
    try:
        story = json.loads(
            story_path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Story JSON valid nahi hai: {error}"
        ) from error

    if not isinstance(story, dict):
        raise RuntimeError(
            "Story JSON object format mein nahi hai."
        )

    return story


def decode_credentials_secret() -> dict[str, Any]:
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
            credentials_b64,
            validate=True,
        ).decode("utf-8")

        credentials_data = json.loads(
            credentials_json
        )
    except Exception as error:
        raise RuntimeError(
            "YOUTUBE_CREDENTIALS_B64 valid Base64 JSON nahi hai."
        ) from error

    if not isinstance(credentials_data, dict):
        raise RuntimeError(
            "YouTube credentials JSON object format mein nahi hai."
        )

    return credentials_data


def get_credentials() -> Credentials:
    credentials_data = decode_credentials_secret()

    required_fields = [
        "client_id",
        "client_secret",
        "refresh_token",
    ]

    missing_fields = [
        field
        for field in required_fields
        if not str(
            credentials_data.get(field, "")
        ).strip()
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

    credentials_data["scopes"] = [
        YOUTUBE_SCOPE
    ]

    try:
        credentials = (
            Credentials.from_authorized_user_info(
                credentials_data,
                scopes=[YOUTUBE_SCOPE],
            )
        )

        if not credentials.valid:
            credentials.refresh(Request())
    except Exception as error:
        raise RuntimeError(
            "YouTube OAuth credentials refresh nahi ho saken. "
            "Refresh token ya client details check karo."
        ) from error

    if not credentials.valid:
        raise RuntimeError(
            "YouTube credentials valid nahi huin."
        )

    return credentials


def normalize_hashtag(tag: str) -> str:
    cleaned = str(tag).strip()

    if not cleaned:
        return ""

    if not cleaned.startswith("#"):
        cleaned = "#" + cleaned

    return cleaned.replace(" ", "")


def build_description(
    story: dict[str, Any],
) -> str:
    youtube_data = story.get("youtube", {})

    if not isinstance(youtube_data, dict):
        youtube_data = {}

    description = str(
        youtube_data.get("description", "")
    ).strip()

    raw_hashtags = youtube_data.get(
        "hashtags",
        [],
    )

    if not isinstance(raw_hashtags, list):
        raw_hashtags = []

    hashtags: list[str] = []

    for raw_tag in raw_hashtags:
        tag = normalize_hashtag(
            str(raw_tag)
        )

        if tag and tag not in hashtags:
            hashtags.append(tag)

    required_hashtags = [
        "#Shorts",
        "#MiloAndFriends",
        "#KidsSongs",
        "#KidsCartoon",
    ]

    for tag in required_hashtags:
        if tag not in hashtags:
            hashtags.append(tag)

    hashtag_text = " ".join(
        hashtags[:12]
    )

    if description:
        return (
            description
            + "\n\n"
            + hashtag_text
        ).strip()

    return hashtag_text


def get_video_path(
    story: dict[str, Any],
) -> Path:
    video_path = Path(
        str(
            story.get(
                "video_file",
                "output/video/final_short.mp4",
            )
        )
    )

    if not video_path.exists():
        raise RuntimeError(
            f"Final video file nahi mili: {video_path}"
        )

    if video_path.stat().st_size == 0:
        raise RuntimeError(
            "Final video file empty hai."
        )

    return video_path


def get_privacy_status() -> str:
    privacy_status = os.getenv(
        "YOUTUBE_PRIVACY_STATUS",
        "private",
    ).strip().lower()

    if (
        privacy_status
        not in VALID_PRIVACY_STATUSES
    ):
        print(
            "Warning: invalid privacy status mila. "
            "Private use kiya jayega."
        )
        return "private"

    return privacy_status


def create_youtube_client(
    credentials: Credentials,
):
    return build(
        "youtube",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )


def build_request_body(
    story: dict[str, Any],
    privacy_status: str,
) -> dict[str, Any]:
    youtube_data = story.get("youtube", {})

    if not isinstance(youtube_data, dict):
        youtube_data = {}

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

    return {
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


def resumable_upload(
    request,
) -> dict[str, Any]:
    response = None
    retry_count = 0

    while response is None:
        try:
            upload_status, response = (
                request.next_chunk()
            )

            if upload_status:
                progress = int(
                    upload_status.progress()
                    * 100
                )
                print(
                    f"Upload progress: {progress}%"
                )

        except HttpError as error:
            status_code = getattr(
                error.resp,
                "status",
                None,
            )

            if (
                status_code
                not in RETRIABLE_STATUS_CODES
                or retry_count >= MAX_UPLOAD_RETRIES
            ):
                raise

            retry_count += 1

            sleep_seconds = min(
                60,
                (2 ** retry_count)
                + random.random(),
            )

            print(
                "Temporary YouTube error mila "
                f"({status_code}). "
                f"{sleep_seconds:.1f}s baad retry..."
            )

            time.sleep(sleep_seconds)

        except (
            ConnectionError,
            TimeoutError,
            OSError,
        ) as error:
            if retry_count >= MAX_UPLOAD_RETRIES:
                raise RuntimeError(
                    "YouTube upload network retries ke "
                    "baad bhi fail ho gaya."
                ) from error

            retry_count += 1

            sleep_seconds = min(
                60,
                (2 ** retry_count)
                + random.random(),
            )

            print(
                "Temporary network error mila. "
                f"{sleep_seconds:.1f}s baad retry..."
            )

            time.sleep(sleep_seconds)

    if not isinstance(response, dict):
        raise RuntimeError(
            "YouTube ne valid response return nahi ki."
        )

    return response


def upload_video(
    story: dict[str, Any],
    credentials: Credentials,
) -> str:
    video_path = get_video_path(story)
    privacy_status = get_privacy_status()

    youtube = create_youtube_client(
        credentials
    )

    request_body = build_request_body(
        story=story,
        privacy_status=privacy_status,
    )

    title = request_body["snippet"]["title"]

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
    print(f"Video file: {video_path}")
    print(f"Title: {title}")
    print(f"Privacy: {privacy_status}")
    print("Made for kids: yes")

    response = resumable_upload(request)

    video_id = str(
        response.get("id", "")
    ).strip()

    if not video_id:
        raise RuntimeError(
            "YouTube ne video ID return nahi ki."
        )

    return video_id


def update_story_metadata(
    story: dict[str, Any],
    story_path: Path,
    video_id: str,
) -> None:
    story["youtube_video_id"] = video_id
    story["youtube_video_url"] = (
        f"https://www.youtube.com/watch?v={video_id}"
    )
    story["youtube_upload_status"] = "uploaded"
    story["youtube_privacy_status"] = (
        get_privacy_status()
    )
    story["youtube_made_for_kids"] = True

    story_path.write_text(
        json.dumps(
            story,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main() -> None:
    print(
        "Milo & Friends YouTube uploader "
        "start ho raha hai..."
    )

    story_path = get_latest_story_file()
    print(f"Story file: {story_path}")

    story = load_story(story_path)
    credentials = get_credentials()

    video_id = upload_video(
        story=story,
        credentials=credentials,
    )

    update_story_metadata(
        story=story,
        story_path=story_path,
        video_id=video_id,
    )

    print("YouTube upload successful.")
    print(f"Video ID: {video_id}")
    print(
        "Video URL: "
        f"https://www.youtube.com/watch?v={video_id}"
    )


if __name__ == "__main__":
    main()
