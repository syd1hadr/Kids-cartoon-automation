import json
import os
import re
from pathlib import Path
from typing import Any

from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs


VOICE_ID = os.getenv(
    "ELEVENLABS_VOICE_ID",
    "pNInz6obpgDQGcFmaJgB",
).strip()

MODEL_ID = os.getenv(
    "ELEVENLABS_MODEL_ID",
    "eleven_flash_v2_5",
).strip()

OUTPUT_FORMAT = "mp3_44100_128"


def get_latest_story_file() -> Path:
    output_dir = Path("output")

    if not output_dir.exists():
        raise RuntimeError("output folder nahi mila.")

    story_files = list(output_dir.glob("*.json"))

    if not story_files:
        raise RuntimeError(
            "output folder mein story JSON nahi mili."
        )

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


def clean_spoken_line(text: str) -> str:
    line = str(text).strip()
    line = re.sub(r"\s+", " ", line)
    line = line.replace("â", "-").replace("â", "-")

    if not line:
        return ""

    if line[-1] not in ".!?":
        line += "!"

    return line


def make_line_rhythmic(text: str) -> str:
    line = clean_spoken_line(text)

    replacements = {
        r"\bclap[\s,-]+clap\b": "Clap, clap!",
        r"\bjump[\s,-]+jump\b": "Jump, jump!",
        r"\bhop[\s,-]+hop\b": "Hop, hop!",
        r"\bpop[\s,-]+pop\b": "Pop, pop!",
        r"\bspin[\s,-]+spin\b": "Spin, spin!",
        r"\brun[\s,-]+run\b": "Run, run!",
        r"\btap[\s,-]+tap\b": "Tap, tap!",
        r"\bding[\s,-]+ding\b": "Ding, ding!",
        r"\bboing[\s,-]+boing\b": "Boing, boing!",
        r"\bla[\s,-]+la[\s,-]+la\b": "La, la, la!",
    }

    for pattern, replacement in replacements.items():
        line = re.sub(
            pattern,
            replacement,
            line,
            flags=re.IGNORECASE,
        )

    return line


def get_scene_lyrics(story: dict[str, Any]) -> list[str]:
    scenes = story.get("scenes", [])

    if not isinstance(scenes, list):
        raise RuntimeError("Story scenes list nahi hai.")

    if not scenes:
        raise RuntimeError("Story mein koi scene nahi hai.")

    ordered_scenes = sorted(
        scenes,
        key=lambda scene: int(scene.get("scene_number", 0)),
    )

    lyrics: list[str] = []

    for index, scene in enumerate(ordered_scenes, start=1):
        if not isinstance(scene, dict):
            raise RuntimeError(
                f"Scene {index} valid object nahi hai."
            )

        lyric = str(
            scene.get("lyric")
            or scene.get("narration")
            or ""
        ).strip()

        lyric = make_line_rhythmic(lyric)

        if not lyric:
            raise RuntimeError(
                f"Scene {index} mein lyric missing hai."
            )

        lyrics.append(lyric)

    return lyrics


def get_chorus(story: dict[str, Any]) -> list[str]:
    raw_chorus = story.get("chorus", [])

    if not isinstance(raw_chorus, list):
        return []

    chorus: list[str] = []

    for raw_line in raw_chorus:
        line = make_line_rhythmic(str(raw_line))

        if line and line not in chorus:
            chorus.append(line)

    return chorus[:2]


def build_narration(story: dict[str, Any]) -> str:
    lyrics = get_scene_lyrics(story)
    chorus = get_chorus(story)
    spoken_parts: list[str] = []

    for index, lyric in enumerate(lyrics):
        spoken_parts.append(lyric)

        if index == 3 and chorus:
            spoken_parts.extend(chorus)

    if chorus:
        final_line = chorus[-1]

        if final_line not in spoken_parts[-2:]:
            spoken_parts.append(final_line)

    narration_text = "\n\n".join(spoken_parts).strip()

    if not narration_text:
        raise RuntimeError(
            "Voice banane ke liye rhyme text nahi mila."
        )

    return narration_text


def generate_voice(
    narration_text: str,
    audio_path: Path,
) -> None:
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError(
            "ELEVENLABS_API_KEY GitHub secret missing hai."
        )

    if not VOICE_ID:
        raise RuntimeError("ELEVENLABS_VOICE_ID empty hai.")

    client = ElevenLabs(api_key=api_key)

    print("ElevenLabs rhythmic rhyme voice generate ho rahi hai...")
    print(f"Voice ID: {VOICE_ID}")
    print(f"Model: {MODEL_ID}")
    print(f"Rhyme characters: {len(narration_text)}")

    audio = client.text_to_speech.convert(
        voice_id=VOICE_ID,
        text=narration_text,
        model_id=MODEL_ID,
        output_format=OUTPUT_FORMAT,
        voice_settings=VoiceSettings(
            stability=0.35,
            similarity_boost=0.78,
            style=0.45,
            use_speaker_boost=True,
            speed=0.92,
        ),
    )

    audio_path.parent.mkdir(parents=True, exist_ok=True)

    with audio_path.open("wb") as audio_file:
        for chunk in audio:
            if chunk:
                audio_file.write(chunk)

    if not audio_path.exists():
        raise RuntimeError(
            "Rhyme narration MP3 create nahi hui."
        )

    if audio_path.stat().st_size == 0:
        raise RuntimeError("Rhyme narration MP3 empty hai.")


def update_story_metadata(
    story: dict[str, Any],
    story_path: Path,
    narration_text: str,
    audio_path: Path,
    script_path: Path,
) -> None:
    story["voice_model"] = MODEL_ID
    story["voice_id"] = VOICE_ID
    story["voice_style"] = "cheerful preschool rhythmic rhyme"
    story["voice_speed"] = 0.92
    story["narration_text"] = narration_text
    story["narration_file"] = str(audio_path)
    story["narration_script_file"] = str(script_path)

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
        "Milo & Friends rhyme voice generator start ho raha hai..."
    )

    story_path = get_latest_story_file()
    print(f"Story file: {story_path}")

    story = load_story(story_path)
    narration_text = build_narration(story)

    audio_dir = Path("output/audio")
    audio_dir.mkdir(parents=True, exist_ok=True)

    audio_path = audio_dir / "narration.mp3"
    script_path = audio_dir / "narration.txt"

    script_path.write_text(
        narration_text,
        encoding="utf-8",
    )

    print("Generated rhyme script:")
    print(narration_text)

    generate_voice(
        narration_text=narration_text,
        audio_path=audio_path,
    )

    update_story_metadata(
        story=story,
        story_path=story_path,
        narration_text=narration_text,
        audio_path=audio_path,
        script_path=script_path,
    )

    print("Rhyme voice successfully generate ho gayi.")
    print(f"Audio file: {audio_path}")
    print(f"Script file: {script_path}")


if __name__ == "__main__":
    main()
