import json
import math
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SEARCH_QUERIES = [
    "nursery rhymes for kids",
    "preschool learning songs",
    "kids songs colors numbers",
    "ABC phonics song kids",
    "animal sounds song toddlers",
    "shapes song for preschool",
    "daily routine song for kids",
]

ALLOWED_TOPIC_KEYWORDS = {
    "abc": "ABC Alphabet Song",
    "alphabet": "ABC Alphabet Song",
    "phonics": "ABC Phonics Song",
    "number": "Numbers and Counting Song",
    "counting": "Numbers and Counting Song",
    "color": "Colors Learning Song",
    "colours": "Colors Learning Song",
    "shape": "Shapes Learning Song",
    "animal": "Animals and Sounds Song",
    "farm": "Farm Animals Song",
    "duck": "Little Ducks Counting Song",
    "bus": "Vehicles and Movement Song",
    "train": "Train Movement Song",
    "car": "Cars and Colors Song",
    "dinosaur": "Friendly Dinosaur Learning Song",
    "fruit": "Fruits and Colors Song",
    "vegetable": "Healthy Food Song",
    "body": "Body Parts Action Song",
    "head": "Body Parts Action Song",
    "hand": "Clap Your Hands Action Song",
    "brush": "Brush Your Teeth Routine Song",
    "bath": "Bath Time Routine Song",
    "bedtime": "Bedtime and Goodnight Song",
    "sleep": "Bedtime and Goodnight Song",
    "morning": "Good Morning Routine Song",
    "school": "Happy School Learning Song",
    "family": "My Happy Family Song",
    "friend": "Sharing and Friendship Song",
    "share": "Sharing and Friendship Song",
    "kind": "Kindness and Helping Song",
    "clean": "Clean Up Together Song",
    "weather": "Weather Learning Song",
    "rain": "Rainy Day Action Song",
    "sun": "Sunny Day Learning Song",
    "moon": "Moon and Stars Bedtime Song",
    "space": "Space Learning Adventure Song",
    "ocean": "Ocean Animals Song",
    "fish": "Ocean Animals Song",
}

FALLBACK_TOPICS = [
    "ABC Phonics Song",
    "Numbers and Counting Song",
    "Colors Learning Song",
    "Shapes Learning Song",
    "Animals and Sounds Song",
    "Body Parts Action Song",
    "Sharing and Friendship Song",
    "Brush Your Teeth Routine Song",
]

BLOCKED_WORDS = {
    "cocomelon",
    "pinkfong",
    "baby shark",
    "disney",
    "pixar",
    "peppa",
    "paw patrol",
    "blippi",
}

REGION_CODE = os.getenv(
    "YOUTUBE_TREND_REGION",
    "US",
).strip().upper()

LANGUAGE = os.getenv(
    "YOUTUBE_TREND_LANGUAGE",
    "en",
).strip().lower()

LOOKBACK_DAYS = 30
MAX_RESULTS_PER_QUERY = 10


def get_youtube_client():
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY GitHub secret missing hai."
        )

    return build(
        "youtube",
        "v3",
        developerKey=api_key,
        cache_discovery=False,
    )


def parse_youtube_datetime(value: str) -> datetime:
    cleaned = str(value).strip()

    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"

    parsed = datetime.fromisoformat(cleaned)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def safe_integer(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def normalize_title(title: str) -> str:
    title = str(title).lower()
    title = re.sub(r"[^a-z0-9\s]", " ", title)
    title = re.sub(r"\s+", " ", title)
    return title.strip()


def is_blocked_title(title: str) -> bool:
    normalized = normalize_title(title)

    return any(
        blocked_word in normalized
        for blocked_word in BLOCKED_WORDS
    )


def calculate_video_score(
    views: int,
    likes: int,
    comments: int,
    published_at: datetime,
) -> float:
    now = datetime.now(timezone.utc)

    age_days = max(
        1.0,
        (now - published_at).total_seconds() / 86400,
    )

    views_per_day = views / age_days

    engagement_rate = (
        (likes + comments * 2)
        / max(views, 1)
    )

    freshness_bonus = max(
        0.20,
        1.0 - (age_days / 60.0),
    )

    return (
        math.log10(max(views_per_day, 1)) * 4.0
        + engagement_rate * 100.0
        + freshness_bonus * 3.0
    )


def search_recent_videos(
    youtube,
) -> list[dict[str, Any]]:
    published_after = (
        datetime.now(timezone.utc)
        - timedelta(days=LOOKBACK_DAYS)
    ).isoformat().replace("+00:00", "Z")

    discovered: dict[str, dict[str, Any]] = {}

    for query in SEARCH_QUERIES:
        print(f"Searching YouTube trend: {query}")

        response = youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            order="viewCount",
            publishedAfter=published_after,
            maxResults=MAX_RESULTS_PER_QUERY,
            regionCode=REGION_CODE,
            relevanceLanguage=LANGUAGE,
            safeSearch="strict",
        ).execute()

        for item in response.get("items", []):
            video_id = str(
                item.get("id", {}).get("videoId", "")
            ).strip()

            snippet = item.get("snippet", {})
            title = str(snippet.get("title", "")).strip()

            if not video_id or not title:
                continue

            if is_blocked_title(title):
                continue

            discovered[video_id] = {
                "video_id": video_id,
                "title": title,
                "channel_title": str(
                    snippet.get("channelTitle", "")
                ).strip(),
                "published_at": str(
                    snippet.get("publishedAt", "")
                ).strip(),
                "search_query": query,
            }

    return list(discovered.values())


def add_video_statistics(
    youtube,
    videos: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not videos:
        return []

    videos_by_id = {
        video["video_id"]: video
        for video in videos
    }

    video_ids = list(videos_by_id.keys())

    for start in range(0, len(video_ids), 50):
        batch_ids = video_ids[start:start + 50]

        response = youtube.videos().list(
            part="statistics,snippet,contentDetails",
            id=",".join(batch_ids),
        ).execute()

        for item in response.get("items", []):
            video_id = str(item.get("id", "")).strip()

            if video_id not in videos_by_id:
                continue

            statistics = item.get("statistics", {})
            snippet = item.get("snippet", {})

            video = videos_by_id[video_id]

            video["views"] = safe_integer(
                statistics.get("viewCount")
            )
            video["likes"] = safe_integer(
                statistics.get("likeCount")
            )
            video["comments"] = safe_integer(
                statistics.get("commentCount")
            )
            video["category_id"] = str(
                snippet.get("categoryId", "")
            )
            video["duration"] = str(
                item.get(
                    "contentDetails",
                    {},
                ).get("duration", "")
            )

            try:
                published_at = parse_youtube_datetime(
                    video["published_at"]
                )
            except Exception:
                published_at = datetime.now(
                    timezone.utc
                ) - timedelta(days=LOOKBACK_DAYS)

            video["trend_score"] = round(
                calculate_video_score(
                    views=video["views"],
                    likes=video["likes"],
                    comments=video["comments"],
                    published_at=published_at,
                ),
                4,
            )

    return sorted(
        videos_by_id.values(),
        key=lambda video: float(
            video.get("trend_score", 0)
        ),
        reverse=True,
    )


def extract_topic_candidates(
    videos: list[dict[str, Any]],
) -> dict[str, float]:
    topic_scores: dict[str, float] = {}

    for video in videos:
        normalized_title = normalize_title(
            video.get("title", "")
        )

        video_score = float(
            video.get("trend_score", 0)
        )

        for keyword, topic_name in (
            ALLOWED_TOPIC_KEYWORDS.items()
        ):
            if re.search(
                rf"\b{re.escape(keyword)}\w*\b",
                normalized_title,
            ):
                topic_scores[topic_name] = (
                    topic_scores.get(topic_name, 0.0)
                    + video_score
                )

    return topic_scores


def load_used_topics() -> list[str]:
    history_path = Path("trend_history.json")

    if not history_path.exists():
        return []

    try:
        history = json.loads(
            history_path.read_text(encoding="utf-8")
        )
    except (json.JSONDecodeError, OSError):
        return []

    if not isinstance(history, list):
        return []

    return [
        str(item.get("topic", "")).strip()
        for item in history[-20:]
        if isinstance(item, dict)
        and str(item.get("topic", "")).strip()
    ]


def choose_best_topic(
    topic_scores: dict[str, float],
) -> tuple[str, float]:
    used_topics = set(load_used_topics())

    ranked_topics = sorted(
        topic_scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    for topic, score in ranked_topics:
        if topic not in used_topics:
            return topic, round(score, 4)

    for topic in FALLBACK_TOPICS:
        if topic not in used_topics:
            return topic, 0.0

    return FALLBACK_TOPICS[0], 0.0


def save_trend_result(
    selected_topic: str,
    selected_score: float,
    videos: list[dict[str, Any]],
    topic_scores: dict[str, float],
) -> Path:
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "selected_topic": selected_topic,
        "selected_score": selected_score,
        "region": REGION_CODE,
        "language": LANGUAGE,
        "lookback_days": LOOKBACK_DAYS,
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "topic_rankings": [
            {
                "topic": topic,
                "score": round(score, 4),
            }
            for topic, score in sorted(
                topic_scores.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:10]
        ],
        "reference_videos": [
            {
                "title": video.get("title"),
                "channel_title": video.get(
                    "channel_title"
                ),
                "views": video.get("views", 0),
                "likes": video.get("likes", 0),
                "published_at": video.get(
                    "published_at"
                ),
                "trend_score": video.get(
                    "trend_score",
                    0,
                ),
            }
            for video in videos[:15]
        ],
        "copyright_rule": (
            "Use only the selected general learning topic. "
            "Do not copy titles, lyrics, melodies, characters, "
            "visuals or story sequences."
        ),
    }

    trend_path = output_dir / "trend.json"

    trend_path.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return trend_path


def update_history(
    selected_topic: str,
    selected_score: float,
) -> None:
    history_path = Path("trend_history.json")

    try:
        history = json.loads(
            history_path.read_text(encoding="utf-8")
        )
        if not isinstance(history, list):
            history = []
    except (FileNotFoundError, json.JSONDecodeError):
        history = []

    history.append(
        {
            "topic": selected_topic,
            "score": selected_score,
            "selected_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }
    )

    history = history[-50:]

    history_path.write_text(
        json.dumps(
            history,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main() -> None:
    print(
        "Milo & Friends nursery trend finder "
        "start ho raha hai..."
    )

    youtube = get_youtube_client()

    try:
        videos = search_recent_videos(youtube)
        videos = add_video_statistics(
            youtube,
            videos,
        )

        topic_scores = extract_topic_candidates(
            videos
        )

        selected_topic, selected_score = (
            choose_best_topic(topic_scores)
        )

    except HttpError as error:
        print(
            "YouTube trend request fail hui. "
            "Fallback topic use kiya jayega."
        )
        print(error)

        videos = []
        topic_scores = {}
        selected_topic, selected_score = (
            choose_best_topic({})
        )

    trend_path = save_trend_result(
        selected_topic=selected_topic,
        selected_score=selected_score,
        videos=videos,
        topic_scores=topic_scores,
    )

    update_history(
        selected_topic=selected_topic,
        selected_score=selected_score,
    )

    print("----------------------------------------")
    print(f"Selected trend topic: {selected_topic}")
    print(f"Trend score: {selected_score}")
    print(f"Saved trend file: {trend_path}")
    print("----------------------------------------")


if __name__ == "__main__":
    main()
