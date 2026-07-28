import json
import os
from pathlib import Path

from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs


VOICE_ID = os.getenv(
    "ELEVENLABS_VOICE_ID",
    "pNInz6obpgDQGcFmaJgB",
).strip()

MODEL_ID = "eleven_flash_v2_5"


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


def load_story(story_path: Path) -> dict:
    try:
        return json.loads(
            story_path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Story JSON valid nahi hai: {error}"
        ) from error


def build_narration(story: dict) -> str:
    narration_parts = []

    hook = str(story.get("hook", "")).strip()

    if hook:
        narration_parts.append(hook)

    scenes = story.get("scenes", [])

    if not isinstance(scenes, list):
        raise RuntimeError("Story scenes list nahi hai.")

    for scene in scenes:
        narration = str(
            scene.get("narration", "")
        ).strip()

        if narration:
            narration_parts.append(narration)

    moral = str(story.get("moral", "")).strip()

    if moral:
        narration_parts.append(moral)

    narration_text = " ".join(narration_parts).strip()

    if not narration_text:
        raise RuntimeError(
            "Story mein voice banane ke liye narration nahi mili."
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

    print("ElevenLabs voice generate ho rahi hai...")
    print(f"Voice ID: {VOICE_ID}")
    print(f"Text characters: {len(narration_text)}")

    audio_response = client.text_to_speech.convert(
        voice_id=VOICE_ID,
        output_format="mp3_44100_128",
        text=narration_text,
        model_id=MODEL_ID,
        voice_settings=VoiceSettings(
            stability=0.45,
            similarity_boost=0.75,
            style=0.25,
            use_speaker_boost=True,
            speed=1.05,
        ),
    )

    with audio_path.open("wb") as audio_file:
        for chunk in audio_response:
            if chunk:
                audio_file.write(chunk)

    if not audio_path.exists() or audio_path.stat().st_size == 0:
        raise RuntimeError(
            "ElevenLabs ne valid MP3 file generate nahi ki."
        )


def main() -> None:
    print("Milo & Friends voice generator start ho raha hai...")

    story_path = get_latest_story_file()
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

    generate_voice(
        narration_text=narration_text,
        audio_path=audio_path,
    )

    story["voice_model"] = MODEL_ID
    story["voice_id"] = VOICE_ID
    story["narration_text"] = narration_text
    story["narration_file"] = str(audio_path)

    story_path.write_text(
        json.dumps(
            story,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("Voice successfully generate ho gayi.")
    print(f"Audio file: {audio_path}")
    print(f"Script file: {script_path}")


if __name__ == "__main__":
    main()
