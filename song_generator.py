import json
import os
from pathlib import Path
from typing import Any

from elevenlabs.client import ElevenLabs


MUSIC_MODEL_ID = os.getenv(
    "ELEVENLABS_MUSIC_MODEL_ID",
    "music_v2",
).strip()

SHORT_MUSIC_LENGTH_MS = 25_000
LONG_MUSIC_LENGTH_MS = 216_000


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


def clean_line(value: Any) -> str:
    return " ".join(str(value).strip().split())


def get_client() -> ElevenLabs:
    api_key = os.getenv(
        "ELEVENLABS_API_KEY",
        "",
    ).strip()

    if not api_key:
        raise RuntimeError(
            "ELEVENLABS_API_KEY GitHub secret missing hai."
        )

    return ElevenLabs(api_key=api_key)


def build_short_lyrics(story: dict[str, Any]) -> list[str]:
    scenes = story.get("scenes", [])

    if not isinstance(scenes, list) or not scenes:
        raise RuntimeError("Short scenes missing hain.")

    ordered_scenes = sorted(
        scenes,
        key=lambda scene: int(
            scene.get("scene_number", 0)
        ),
    )

    lines: list[str] = []

    for scene in ordered_scenes:
        if not isinstance(scene, dict):
            continue

        line = clean_line(
            scene.get("lyric")
            or scene.get("narration")
            or ""
        )

        if line:
            lines.append(line)

    if not lines:
        raise RuntimeError(
            "Short song ke lyrics nahi mile."
        )

    return lines


def build_long_lyrics(story: dict[str, Any]) -> list[str]:
    long_video = story.get("long_video", {})

    if not isinstance(long_video, dict):
        raise RuntimeError(
            "long_video planning missing hai."
        )

    lines: list[str] = []

    opening_lines = long_video.get(
        "opening_lines",
        [],
    )

    if isinstance(opening_lines, list):
        for value in opening_lines:
            line = clean_line(value)

            if line:
                lines.append(line)

    segments = long_video.get("segments", [])

    if not isinstance(segments, list):
        raise RuntimeError(
            "Long-video segments missing hain."
        )

    chorus = long_video.get("chorus", [])

    if not isinstance(chorus, list):
        chorus = []

    clean_chorus = [
        clean_line(line)
        for line in chorus
        if clean_line(line)
    ][:2]

    ordered_segments = sorted(
        segments,
        key=lambda segment: int(
            segment.get("segment_number", 0)
        ),
    )

    for index, segment in enumerate(
        ordered_segments,
        start=1,
    ):
        if not isinstance(segment, dict):
            continue

        lyrics = segment.get("lyrics", [])

        if isinstance(lyrics, list):
            for value in lyrics:
                line = clean_line(value)

                if line:
                    lines.append(line)

        if clean_chorus and index in {3, 6, 9, 12}:
            lines.extend(clean_chorus)

    ending_lines = long_video.get(
        "ending_lines",
        [],
    )

    if isinstance(ending_lines, list):
        for value in ending_lines:
            line = clean_line(value)

            if line:
                lines.append(line)

    if not lines:
        raise RuntimeError(
            "Long song ke lyrics nahi mile."
        )

    return lines


def build_short_prompt(story: dict[str, Any]) -> str:
    topic = clean_line(
        story.get(
            "selected_trend_topic",
            "preschool learning",
        )
    )

    title = clean_line(
        story.get(
            "song_title",
            "Milo and Friends Song",
        )
    )

    lyrics_text = "\n".join(
        build_short_lyrics(story)
    )

    return f"""
Create a completely original 25-second preschool nursery rhyme song
with natural sung vocals.

Song title: {title}
Learning topic: {topic}

Use these exact original lyric lines in this order:
{lyrics_text}

Music style:
- cheerful original preschool song
- warm playful lead vocal
- clear easy English pronunciation
- child-friendly singing, not spoken narration
- catchy melody children can follow
- ukulele, toy piano, xylophone, gentle drums and hand claps
- approximately 110 BPM
- bright, bouncy and educational
- short musical intro
- vocals begin almost immediately
- joyful clean ending
- no long instrumental break
- no adult lecture voice
- no copyrighted melody
- no imitation of any existing artist, song, channel or brand
- family friendly
""".strip()


def build_long_prompt(story: dict[str, Any]) -> str:
    topic = clean_line(
        story.get(
            "selected_trend_topic",
            "preschool learning",
        )
    )

    long_video = story.get("long_video", {})

    if not isinstance(long_video, dict):
        long_video = {}

    title = clean_line(
        long_video.get(
            "title",
            "Milo and Friends Learning Song",
        )
    )

    lyrics_text = "\n".join(
        build_long_lyrics(story)
    )

    return f"""
Create a completely original 216-second preschool nursery rhyme song
with natural sung vocals.

Song title: {title}
Learning topic: {topic}

Use these original lyric lines in this order:
{lyrics_text}

Music style:
- original 3 minute 36 second preschool learning song
- playful child-friendly sung vocals
- very clear easy English
- catchy repeating chorus
- ukulele, toy piano, xylophone, gentle drums, hand claps and soft bass
- approximately 108 to 112 BPM
- energetic sections with short musical transitions
- children should be able to clap, count, point, dance and sing along
- no spoken lecture
- no serious adult narrator
- no long empty instrumental sections
- begin with a short welcome
- end with a happy recap and goodbye
- no copyrighted melody
- no imitation of any existing artist, song, channel or brand
- family friendly
""".strip()


def save_audio_stream(
    audio_stream,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open("wb") as audio_file:
        for chunk in audio_stream:
            if chunk:
                audio_file.write(chunk)

    if (
        not output_path.exists()
        or output_path.stat().st_size == 0
    ):
        raise RuntimeError(
            f"Audio file create nahi hui: {output_path}"
        )


def generate_song(
    client: ElevenLabs,
    prompt: str,
    duration_ms: int,
    output_path: Path,
) -> None:
    print(
        f"Song generate ho rahi hai: {output_path}"
    )
    print(
        f"Duration target: {duration_ms / 1000:.0f} seconds"
    )
    print(f"Model: {MUSIC_MODEL_ID}")

    track = client.music.compose(
        prompt=prompt,
        music_length_ms=duration_ms,
        model_id=MUSIC_MODEL_ID,
        force_instrumental=False,
    )

    save_audio_stream(
        audio_stream=track,
        output_path=output_path,
    )

    print(
        f"Song successfully save ho gayi: {output_path}"
    )


def update_story_metadata(
    story: dict[str, Any],
    story_path: Path,
    short_song_path: Path,
    long_song_path: Path,
) -> None:
    story["audio_engine"] = "Eleven Music"
    story["music_model"] = MUSIC_MODEL_ID
    story["short_song_file"] = str(
        short_song_path
    )

    story["narration_file"] = str(
        short_song_path
    )

    story["narration_text"] = "\n".join(
        build_short_lyrics(story)
    )

    long_video = story.get("long_video")

    if not isinstance(long_video, dict):
        long_video = {}
        story["long_video"] = long_video

    long_video["song_file"] = str(
        long_song_path
    )

    long_video["song_duration_seconds"] = (
        LONG_MUSIC_LENGTH_MS // 1000
    )

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
        "Milo & Friends proper song generator "
        "start ho raha hai..."
    )

    story_path = get_latest_story_file()
    print(f"Story file: {story_path}")

    story = load_story(story_path)
    client = get_client()

    audio_dir = Path("output/audio")

    short_song_path = (
        audio_dir / "short_song.mp3"
    )

    long_song_path = (
        audio_dir / "long_song.mp3"
    )

    short_prompt = build_short_prompt(story)
    long_prompt = build_long_prompt(story)

    generate_song(
        client=client,
        prompt=short_prompt,
        duration_ms=SHORT_MUSIC_LENGTH_MS,
        output_path=short_song_path,
    )

    generate_song(
        client=client,
        prompt=long_prompt,
        duration_ms=LONG_MUSIC_LENGTH_MS,
        output_path=long_song_path,
    )

    update_story_metadata(
        story=story,
        story_path=story_path,
        short_song_path=short_song_path,
        long_song_path=long_song_path,
    )

    print("----------------------------------------")
    print("Short aur Long dono songs ready hain.")
    print(f"Short song: {short_song_path}")
    print(f"Long song: {long_song_path}")
    print("----------------------------------------")


if __name__ == "__main__":
    main()
