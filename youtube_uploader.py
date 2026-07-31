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
UPLOAD_CHUNK_SIZE = 8 * 1024 * 1024


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


def get_privacy_status() -> str:
    privacy_status = os.getenv(
        "YOUTUBE_PRIVACY_STATUS",
        "private",
    ).strip().lower()

    if privacy_status not in VALID_PRIVACY_STATUSES:
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


def clean_text(value: Any) -> str:
    return " ".join(str(value).strip().split())


def normalize_hashtag(tag: Any) -> str:
    cleaned = clean_text(tag)

    if not cleaned:
        return ""

    if not cleaned.startswith("#"):
        cleaned = "#" + cleaned

    return cleaned.replace(" ", "")


def build_hashtags(
    raw_hashtags: Any,
    required_hashtags: list[str],
) -> list[str]:
    if not isinstance(raw_hashtags, list):
        raw_hashtags = []

    hashtags: list[str] = []

    for raw_tag in raw_hashtags + required_hashtags:
        hashtag = normalize_hashtag(raw_tag)

        if hashtag and hashtag not in hashtags:
            hashtags.append(hashtag)

    return hashtags[:12]


def build_description(
    youtube_data: dict[str, Any],
    required_hashtags: list[str],
) -> str:
    description = clean_text(
        youtube_data.get("description", "")
    )

    hashtags = build_hashtags(
        raw_hashtags=youtube_data.get(
            "hashtags",
            [],
        ),
        required_hashtags=required_hashtags,
    )

    hashtag_text = " ".join(hashtags)

    if description:
        return (
            description
            + "\n\n"
            + hashtag_text
        ).strip()

    return hashtag_text


def require_video_file(
    path_value: Any,
    fallback_path: str,
) -> Path:
    video_path = Path(
        str(path_value or fallback_path)
    )

    if not video_path.exists():
        raise RuntimeError(
            f"Final video file nahi mili: {video_path}"
        )

    if video_path.stat().st_size == 0:
        raise RuntimeError(
            f"Final video file empty hai: {video_path}"
        )

    return video_path


def get_short_upload_data(
    story: dict[str, Any],
) -> dict[str, Any]:
    youtube_data = story.get("youtube", {})

    if not isinstance(youtube_data, dict):
        youtube_data = {}

    title = clean_text(
        youtube_data.get(
            "title",
            "Milo & Friends Nursery Rhyme #Shorts",
        )
    )

    if not title:
        title = "Milo & Friends Nursery Rhyme #Shorts"

    if "#shorts" not in title.lower():
        title = f"{title} #Shorts"

    title = title[:100]

    description = build_description(
        youtube_data=youtube_data,
        required_hashtags=[
            "#Shorts",
            "#MiloAndFriends",
            "#NurseryRhymes",
            "#KidsSongs",
        ],
    )

    video_path = require_video_file(
        story.get(
            "short_video_file"
        )
        or story.get("video_file"),
        "output/video/final_short.mp4",
    )

    return {
        "kind": "short",
        "title": title,
        "description": description,
        "video_path": video_path,
        "category_id": "1",
    }


def get_long_upload_data(
    story: dict[str, Any],
) -> dict[str, Any]:
    long_data = story.get("long_video", {})

    if not isinstance(long_data, dict):
        raise RuntimeError(
            "long_video metadata missing hai."
        )

    youtube_data = long_data.get(
        "youtube",
        {},
    )

    if not isinstance(youtube_data, dict):
        youtube_data = {}

    title = clean_text(
        youtube_data.get(
            "title",
            long_data.get(
                "title",
                "Milo & Friends Learning Nursery Rhyme",
            ),
        )
    )

    if not title:
        title = "Milo & Friends Learning Nursery Rhyme"

    title = title[:100]

    description = build_description(
        youtube_data=youtube_data,
        required_hashtags=[
            "#MiloAndFriends",
            "#NurseryRhymes",
            "#KidsSongs",
            "#PreschoolLearning",
        ],
    )

    video_path = require_video_file(
        long_data.get("video_file"),
        "output/video/final_long.mp4",
    )

    return {
        "kind": "long",
        "title": title,
        "description": description,
        "video_path": video_path,
        "category_id": "1",
    }


def build_request_body(
    upload_data: dict[str, Any],
    privacy_status: str,
) -> dict[str, Any]:
    return {
        "snippet": {
            "title": upload_data["title"],
            "description": upload_data["description"],
            "categoryId": upload_data["category_id"],
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
    label: str,
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
                    upload_status.progress() * 100
                )

                print(
                    f"{label} upload progress: {progress}%"
                )

        except HttpError as error:
            status_code = getattr(
                error.resp,
                "status",
                None,
            )

            if (
                status_code not in RETRIABLE_STATUS_CODES
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
                f"{label}: temporary YouTube error "
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
                    f"{label} network retries ke baad bhi fail ho gaya."
                ) from error

            retry_count += 1

            sleep_seconds = min(
                60,
                (2 ** retry_count)
                + random.random(),
            )

            print(
                f"{label}: temporary network error. "
                f"{sleep_seconds:.1f}s baad retry..."
            )

            time.sleep(sleep_seconds)

    if not isinstance(response, dict):
        raise RuntimeError(
            f"{label}: YouTube ne valid response return nahi ki."
        )

    return response


def upload_one_video(
    youtube,
    upload_data: dict[str, Any],
    privacy_status: str,
) -> dict[str, str]:
    kind = str(upload_data["kind"])
    label = kind.upper()

    request_body = build_request_body(
        upload_data=upload_data,
        privacy_status=privacy_status,
    )

    media = MediaFileUpload(
        str(upload_data["video_path"]),
        mimetype="video/mp4",
        chunksize=UPLOAD_CHUNK_SIZE,
        resumable=True,
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media,
    )

    print("----------------------------------------")
    print(f"{label} YouTube upload start ho raha hai...")
    print(f"Video file: {upload_data['video_path']}")
    print(f"Title: {upload_data['title']}")
    print(f"Privacy: {privacy_status}")
    print("Made for kids: yes")
    print("----------------------------------------")

    response = resumable_upload(
        request=request,
        label=label,
    )

    video_id = clean_text(
        response.get("id", "")
    )

    if not video_id:
        raise RuntimeError(
            f"{label}: YouTube ne video ID return nahi ki."
        )

    video_url = (
        f"https://www.youtube.com/watch?v={video_id}"
    )

    print(f"{label} upload successful.")
    print(f"{label} Video ID: {video_id}")
    print(f"{label} Video URL: {video_url}")

    return {
        "video_id": video_id,
        "video_url": video_url,
    }


def already_uploaded(
    story: dict[str, Any],
    kind: str,
) -> bool:
    if kind == "short":
        return bool(
            clean_text(
                story.get("youtube_short_video_id", "")
            )
        )

    long_data = story.get("long_video", {})

    if not isinstance(long_data, dict):
        return False

    return bool(
        clean_text(
            long_data.get("youtube_video_id", "")
        )
    )


def update_story_metadata(
    story: dict[str, Any],
    story_path: Path,
    short_result: dict[str, str],
    long_result: dict[str, str],
    privacy_status: str,
) -> None:
    story["youtube_short_video_id"] = (
        short_result["video_id"]
    )

    story["youtube_short_video_url"] = (
        short_result["video_url"]
    )

    story["youtube_video_id"] = (
        short_result["video_id"]
    )

    story["youtube_video_url"] = (
        short_result["video_url"]
    )

    story["youtube_short_upload_status"] = (
        "uploaded"
    )

    long_data = story.get("long_video")

    if not isinstance(long_data, dict):
        long_data = {}
        story["long_video"] = long_data

    long_data["youtube_video_id"] = (
        long_result["video_id"]
    )

    long_data["youtube_video_url"] = (
        long_result["video_url"]
    )

    long_data["youtube_upload_status"] = (
        "uploaded"
    )

    story["youtube_upload_status"] = (
        "short_and_long_uploaded"
    )

    story["youtube_privacy_status"] = (
        privacy_status
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
        "Milo & Friends Short and Long YouTube uploader "
        "start ho raha hai..."
    )

    story_path = get_latest_story_file()
    print(f"Story file: {story_path}")

    story = load_story(story_path)

    if already_uploaded(story, "short"):
        raise RuntimeError(
            "Is story ka Short pehle hi upload ho chuka hai. "
            "Duplicate upload rok diya gaya."
        )

    if already_uploaded(story, "long"):
        raise RuntimeError(
            "Is story ki Long video pehle hi upload ho chuki hai. "
            "Duplicate upload rok diya gaya."
        )

    credentials = get_credentials()
    youtube = create_youtube_client(
        credentials
    )
    privacy_status = get_privacy_status()

    short_upload_data = get_short_upload_data(
        story
    )

    long_upload_data = get_long_upload_data(
        story
    )

    short_result = upload_one_video(
        youtube=youtube,
        upload_data=short_upload_data,
        privacy_status=privacy_status,
    )

    long_result = upload_one_video(
        youtube=youtube,
        upload_data=long_upload_data,
        privacy_status=privacy_status,
    )

    update_story_metadata(
        story=story,
        story_path=story_path,
        short_result=short_result,
        long_result=long_result,
        privacy_status=privacy_status,
    )

    print("----------------------------------------")
    print("Short aur Long dono YouTube par upload ho gayi hain.")
    print(
        "Short URL: "
        f"{short_result['video_url']}"
    )
    print(
        "Long URL: "
        f"{long_result['video_url']}"
    )
    print("----------------------------------------")


if __name__ == "__main__":
    main()
