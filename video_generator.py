import json
import os
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

MODEL_CANDIDATES = [
    os.getenv("VEO_MODEL", "veo-3.1-fast-generate-preview").strip(),
    "veo-3.1-generate-preview",
    "veo-3.1-lite-generate-preview",
]
POLL_SECONDS = 10
MAX_WAIT_SECONDS = int(os.getenv("VEO_MAX_WAIT_SECONDS", "1200"))
MAX_RETRIES = int(os.getenv("VEO_MAX_RETRIES", "2"))
VIDEO_DURATION_SECONDS = 8
VIDEO_RESOLUTION = os.getenv("VEO_RESOLUTION", "720p").strip()
GENERATE_LONG_MOTION = os.getenv(
    "GENERATE_LONG_MOTION", "true"
).strip().lower() in {"1", "true", "yes", "on"}


def get_client() -> genai.Client:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY missing hai.")
    return genai.Client(api_key=api_key)


def get_latest_story_file() -> Path:
    output_dir = Path("output")
    if not output_dir.exists():
        raise RuntimeError("output folder nahi mila.")
    story_files = list(output_dir.glob("*.json"))
    if not story_files:
        raise RuntimeError("Story JSON file nahi mili.")
    return max(story_files, key=lambda path: path.stat().st_mtime)


def load_story(story_path: Path) -> dict[str, Any]:
    try:
        story = json.loads(story_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Story JSON valid nahi hai: {error}") from error
    if not isinstance(story, dict):
        raise RuntimeError("Story JSON object nahi hai.")
    return story


def clean_text(value: Any) -> str:
    if isinstance(value, list):
        value = "; ".join(str(item) for item in value)
    return " ".join(str(value).strip().split())


def build_motion_prompt(item: dict[str, Any], label: str) -> str:
    action = clean_text(item.get("action") or item.get("actions") or "")
    visual = clean_text(
        item.get("visual_prompt") or item.get("visual_direction") or ""
    )
    emotion = clean_text(item.get("emotion", "happy"))
    return f"""
Animate the supplied first-frame image as a polished original 3D
preschool-cartoon shot.

SHOT: {label}
ACTION: {action}
VISUAL DIRECTION: {visual}
EMOTION: {emotion}

STRICT RULES:
- Preserve every character's exact face, fur, clothing, colors, size,
  proportions and identity from the supplied image.
- Do not add, remove, duplicate or redesign characters.
- Keep correct anatomy and natural body movement.
- Do not let bodies pass through floors, furniture, props or each other.
- Add blinking, head turns, paw or hand gestures and secondary motion.
- Use a smooth slow camera dolly, pan or orbit.
- No frozen slideshow look, sudden cuts, morphing, text, captions, logos,
  watermark, speech bubbles, dialogue, singing or spoken words.
- Keep background sound minimal because the final nursery song is added later.
- Family-friendly, cheerful, safe and bright.

Create one continuous animated shot.
""".strip()


def wait_for_operation(client: genai.Client, operation):
    started = time.monotonic()
    while not operation.done:
        elapsed = time.monotonic() - started
        if elapsed > MAX_WAIT_SECONDS:
            raise TimeoutError("Veo generation timeout ho gayi.")
        print(f"Veo processing... {int(elapsed)} seconds")
        time.sleep(POLL_SECONDS)
        operation = client.operations.get(operation)
    return operation


def save_generated_video(
    client: genai.Client,
    operation,
    output_path: Path,
) -> None:
    response = getattr(operation, "response", None)
    generated_videos = getattr(response, "generated_videos", None)
    if not generated_videos:
        raise RuntimeError("Veo ne generated video return nahi ki.")
    video = generated_videos[0].video
    output_path.parent.mkdir(parents=True, exist_ok=True)
    client.files.download(file=video)
    video.save(str(output_path))
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(f"Motion video save nahi hui: {output_path}")


def generate_one_motion_clip(
    client: genai.Client,
    image_path: Path,
    output_path: Path,
    prompt: str,
    aspect_ratio: str,
    label: str,
) -> str:
    if output_path.exists() and output_path.stat().st_size > 0:
        print(f"{label}: existing clip reuse ho rahi hai.")
        return "existing"
    if not image_path.exists():
        raise RuntimeError(f"{label}: image nahi mili: {image_path}")

    image = types.Image.from_file(location=str(image_path))
    errors: list[str] = []

    for model_name in MODEL_CANDIDATES:
        if not model_name:
            continue
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"{label}: model={model_name}, attempt={attempt}")
                operation = client.models.generate_videos(
                    model=model_name,
                    prompt=prompt,
                    image=image,
                    config=types.GenerateVideosConfig(
                        number_of_videos=1,
                        duration_seconds=VIDEO_DURATION_SECONDS,
                        aspect_ratio=aspect_ratio,
                        resolution=VIDEO_RESOLUTION,
                    ),
                )
                operation = wait_for_operation(client, operation)
                save_generated_video(client, operation, output_path)
                print(f"{label}: ready {output_path}")
                return model_name
            except Exception as error:
                message = f"{model_name} attempt {attempt}: {error}"
                print(message)
                errors.append(message)
                if attempt < MAX_RETRIES:
                    time.sleep(10 * attempt)

    raise RuntimeError(
        f"{label} ke tamam Veo models fail ho gaye: " + " | ".join(errors)
    )


def generate_short_motion(
    client: genai.Client,
    story: dict[str, Any],
) -> list[str]:
    scenes = story.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) != 6:
        raise RuntimeError("Short ke liye exactly 6 scenes chahiye.")

    files: list[str] = []
    ordered = sorted(scenes, key=lambda item: int(item.get("scene_number", 0)))
    for index, scene in enumerate(ordered):
        number = int(scene.get("scene_number", index + 1))
        image_path = Path(str(scene.get(
            "image_file", f"output/images/short/scene_{number:02d}.png"
        )))
        output_path = Path(f"output/motion/short/scene_{number:02d}.mp4")
        model = generate_one_motion_clip(
            client,
            image_path,
            output_path,
            build_motion_prompt(scene, f"Short scene {number}"),
            "9:16",
            f"Short scene {number}",
        )
        scene["motion_file"] = str(output_path)
        scene["motion_model"] = model
        files.append(str(output_path))
    return files


def generate_long_motion(
    client: genai.Client,
    story: dict[str, Any],
) -> list[str]:
    if not GENERATE_LONG_MOTION:
        print("Long motion generation disabled hai.")
        return []

    long_data = story.get("long_video")
    if not isinstance(long_data, dict):
        raise RuntimeError("long_video planning missing hai.")
    segments = long_data.get("segments", [])
    if not isinstance(segments, list) or len(segments) != 12:
        raise RuntimeError("Long ke liye exactly 12 segments chahiye.")

    files: list[str] = []
    ordered = sorted(
        segments,
        key=lambda item: int(item.get("segment_number", 0)),
    )
    for index, segment in enumerate(ordered):
        number = int(segment.get("segment_number", index + 1))
        image_path = Path(str(segment.get(
            "image_file", f"output/images/long/segment_{number:02d}.png"
        )))
        output_path = Path(f"output/motion/long/segment_{number:02d}.mp4")
        model = generate_one_motion_clip(
            client,
            image_path,
            output_path,
            build_motion_prompt(segment, f"Long segment {number}"),
            "16:9",
            f"Long segment {number}",
        )
        segment["motion_file"] = str(output_path)
        segment["motion_model"] = model
        files.append(str(output_path))
    long_data["motion_files"] = files
    return files


def main() -> None:
    print("Milo & Friends Veo motion generator start...")
    story_path = get_latest_story_file()
    story = load_story(story_path)
    client = get_client()

    short_files = generate_short_motion(client, story)
    long_files = generate_long_motion(client, story)

    story["short_motion_files"] = short_files
    story["motion_generation_status"] = (
        "short_and_long_complete" if long_files else "short_complete"
    )
    story_path.write_text(
        json.dumps(story, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Short animated clips: {len(short_files)}")
    print(f"Long animated clips: {len(long_files)}")


if __name__ == "__main__":
    main()
