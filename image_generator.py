import base64
import json
import os
import time
from pathlib import Path
from typing import Any

from google import genai


MODEL_CANDIDATES = [
    "gemini-3.1-flash-image",
    "gemini-3.1-flash-lite-image",
    "gemini-2.5-flash-image",
]

SHORT_SCENE_COUNT = 6
LONG_SEGMENT_COUNT = 12
MAX_RETRIES = 3
REQUEST_PAUSE_SECONDS = 2


CHARACTER_DESIGNS = """
Milo:
- baby orange-and-white kitten
- large bright blue eyes
- blue T-shirt
- red shorts
- white shoes
- brave, kind and curious

Coco:
- small white puppy
- light-brown floppy ears
- yellow hoodie
- blue shoes
- loyal, energetic and funny

Poko:
- cute baby panda
- green overalls
- tiny red backpack
- lovable and clumsy

Ducky:
- tiny yellow duckling
- purple cap
- tiny blue bag
- cheerful and clever
""".strip()


def get_client() -> genai.Client:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY GitHub secret missing hai."
        )

    return genai.Client(api_key=api_key)


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


def clean_text(value: Any) -> str:
    return " ".join(str(value).strip().split())


def character_names_from_item(
    item: dict[str, Any],
    fallback: list[str],
) -> list[str]:
    raw_names = item.get("characters_used", fallback)

    if not isinstance(raw_names, list):
        raw_names = fallback

    allowed = {"Milo", "Coco", "Poko", "Ducky"}

    names = [
        clean_text(name)
        for name in raw_names
        if clean_text(name) in allowed
    ]

    return names or fallback


def selected_character_descriptions(
    character_names: list[str],
) -> str:
    blocks = {
        "Milo": (
            "Milo is a baby orange-and-white kitten with large bright "
            "blue eyes, a blue T-shirt, red shorts and white shoes."
        ),
        "Coco": (
            "Coco is a small white puppy with light-brown floppy ears, "
            "a yellow hoodie and blue shoes."
        ),
        "Poko": (
            "Poko is a cute baby panda wearing green overalls and a "
            "tiny red backpack."
        ),
        "Ducky": (
            "Ducky is a tiny yellow duckling wearing a purple cap and "
            "carrying a tiny blue bag."
        ),
    }

    return "\n".join(
        f"- {blocks[name]}"
        for name in character_names
        if name in blocks
    )


def anatomy_rules() -> str:
    return """
STRICT PHYSICAL AND ANATOMY RULES:
- Every character must have one head, two eyes, two arms or front legs,
  and two legs unless normal species anatomy requires otherwise.
- No extra limbs, duplicate faces, merged bodies or twisted joints.
- Characters must never pass through benches, tables, walls, floors,
  toys, furniture or each other.
- Feet must visibly touch the correct floor, ground or platform.
- Sitting characters must sit on top of the seat, never inside it.
- Hands, paws and wings must hold or touch objects naturally.
- Objects must have believable size, placement, contact and shadows.
- Keep clear space between separate characters and props.
- Show the full action clearly in one readable moment.
- Use a simple uncluttered preschool environment.
""".strip()


def common_style_rules() -> str:
    return """
VISUAL STYLE:
- completely original premium polished 3D preschool cartoon
- rounded cute characters with expressive readable faces
- bright family-friendly colors
- soft cinematic lighting
- clean foreground, middle ground and background separation
- energetic learning action
- high visual clarity for children aged 2 to 6
- no text, letters, numbers, captions or subtitles inside the image
- no speech bubbles
- no logo
- no watermark
- no frightening imagery
- no copyrighted characters, brands or studio imitation
""".strip()


def build_short_prompt(
    story: dict[str, Any],
    scene: dict[str, Any],
) -> str:
    scene_number = int(scene.get("scene_number", 0))
    action = clean_text(scene.get("action", ""))
    learning_goal = clean_text(
        scene.get("learning_goal", "follow the action")
    )
    visual_prompt = clean_text(scene.get("visual_prompt", ""))
    emotion = clean_text(scene.get("emotion", "happy"))

    if not action or not visual_prompt:
        raise RuntimeError(
            f"Short scene {scene_number} ka prompt incomplete hai."
        )

    fallback_characters = story.get(
        "characters_used",
        ["Milo", "Coco"],
    )

    if not isinstance(fallback_characters, list):
        fallback_characters = ["Milo", "Coco"]

    names = character_names_from_item(
        scene,
        [
            clean_text(name)
            for name in fallback_characters
            if clean_text(name)
        ],
    )

    selected_characters = selected_character_descriptions(names)
    topic = clean_text(
        story.get(
            "selected_trend_topic",
            "preschool learning song",
        )
    )

    return f"""
Create exactly one finished original 3D preschool-cartoon image for
Milo & Friends.

FORMAT:
- vertical 9:16 YouTube Short composition
- full-frame image
- important faces and action near the center
- leave safe space near the top and bottom edges

LEARNING TOPIC:
{topic}

CHARACTERS SHOWN:
{selected_characters}

SCENE {scene_number}:
- Action: {action}
- Learning goal: {learning_goal}
- Main emotion: {emotion}
- Detailed scene direction: {visual_prompt}

{anatomy_rules()}

{common_style_rules()}

Show a lively action pose that can later receive camera movement.
Return only the completed image.
""".strip()


def build_long_prompt(
    story: dict[str, Any],
    segment: dict[str, Any],
) -> str:
    segment_number = int(
        segment.get("segment_number", 0)
    )
    section_name = clean_text(
        segment.get("section_name", "")
    )
    learning_goal = clean_text(
        segment.get("learning_goal", "")
    )
    visual_direction = clean_text(
        segment.get("visual_direction", "")
    )

    actions = segment.get("actions", [])

    if not isinstance(actions, list):
        actions = []

    action_text = "; ".join(
        clean_text(action)
        for action in actions
        if clean_text(action)
    )

    if not visual_direction:
        raise RuntimeError(
            f"Long segment {segment_number} ka visual direction missing hai."
        )

    names = character_names_from_item(
        segment,
        ["Milo", "Coco"],
    )

    selected_characters = selected_character_descriptions(names)
    topic = clean_text(
        story.get(
            "selected_trend_topic",
            "preschool learning song",
        )
    )

    return f"""
Create exactly one finished original 3D preschool-cartoon image for
a Milo & Friends long nursery-rhyme video.

FORMAT:
- horizontal 16:9 YouTube composition
- full-frame image
- balanced wide scene
- main characters large enough to read on a phone screen
- leave visual room for later camera pans and zooms

LEARNING TOPIC:
{topic}

CHARACTERS SHOWN:
{selected_characters}

LONG VIDEO SEGMENT {segment_number}:
- Section: {section_name}
- Learning goal: {learning_goal}
- Character actions: {action_text}
- Detailed visual direction: {visual_direction}

{anatomy_rules()}

{common_style_rules()}

Show a lively mid-action pose, not a static group portrait.
Return only the completed image.
""".strip()


def decode_output_image(interaction) -> bytes:
    output_image = getattr(
        interaction,
        "output_image",
        None,
    )

    if output_image is None:
        raise RuntimeError(
            "Gemini interaction mein output_image nahi mili."
        )

    raw_data = getattr(output_image, "data", None)

    if not raw_data:
        raise RuntimeError(
            "Gemini output_image data empty hai."
        )

    if isinstance(raw_data, bytes):
        return raw_data

    return base64.b64decode(str(raw_data))


def generate_image_with_model(
    client: genai.Client,
    model_name: str,
    prompt: str,
    aspect_ratio: str,
) -> bytes:
    interaction = client.interactions.create(
        model=model_name,
        input=prompt,
        response_format={
            "type": "image",
            "mime_type": "image/png",
            "aspect_ratio": aspect_ratio,
            "image_size": "1K",
        },
    )

    return decode_output_image(interaction)


def generate_image_with_fallback(
    client: genai.Client,
    prompt: str,
    aspect_ratio: str,
    label: str,
) -> tuple[bytes, str]:
    errors: list[str] = []

    for model_name in MODEL_CANDIDATES:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(
                    f"{label}: model={model_name}, attempt={attempt}"
                )

                image_bytes = generate_image_with_model(
                    client=client,
                    model_name=model_name,
                    prompt=prompt,
                    aspect_ratio=aspect_ratio,
                )

                if not image_bytes:
                    raise RuntimeError(
                        "Generated image bytes empty hain."
                    )

                return image_bytes, model_name

            except Exception as error:
                message = (
                    f"{model_name} attempt {attempt}: {error}"
                )
                print(message)
                errors.append(message)

                if attempt < MAX_RETRIES:
                    time.sleep(5 * attempt)

    raise RuntimeError(
        f"{label} ke tamam image models fail ho gaye: "
        + " | ".join(errors)
    )


def save_image(
    image_bytes: bytes,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_bytes(image_bytes)

    if (
        not output_path.exists()
        or output_path.stat().st_size == 0
    ):
        raise RuntimeError(
            f"Image save nahi hui: {output_path}"
        )


def generate_short_images(
    client: genai.Client,
    story: dict[str, Any],
) -> tuple[list[str], list[str]]:
    scenes = story.get("scenes", [])

    if not isinstance(scenes, list):
        raise RuntimeError(
            "Short scenes list missing hai."
        )

    if len(scenes) != SHORT_SCENE_COUNT:
        raise RuntimeError(
            f"Exactly {SHORT_SCENE_COUNT} Short scenes chahiye."
        )

    short_dir = Path("output/images/short")
    generated_files: list[str] = []
    used_models: list[str] = []

    ordered_scenes = sorted(
        scenes,
        key=lambda scene: int(
            scene.get("scene_number", 0)
        ),
    )

    for index, scene in enumerate(ordered_scenes):
        scene_number = int(
            scene.get("scene_number", index + 1)
        )

        prompt = build_short_prompt(
            story=story,
            scene=scene,
        )

        output_path = (
            short_dir
            / f"scene_{scene_number:02d}.jpg"
        )

        image_bytes, model_name = (
            generate_image_with_fallback(
                client=client,
                prompt=prompt,
                aspect_ratio="9:16",
                label=f"Short scene {scene_number}",
            )
        )

        save_image(
            image_bytes=image_bytes,
            output_path=output_path,
        )

        scene["image_file"] = str(output_path)
        scene["image_model"] = model_name
        generated_files.append(str(output_path))
        used_models.append(model_name)

        print(
            f"Short scene {scene_number} save ho gayi: "
            f"{output_path}"
        )

        if index < len(ordered_scenes) - 1:
            time.sleep(REQUEST_PAUSE_SECONDS)

    return generated_files, used_models


def generate_long_images(
    client: genai.Client,
    story: dict[str, Any],
) -> tuple[list[str], list[str]]:
    long_video = story.get("long_video")

    if not isinstance(long_video, dict):
        raise RuntimeError(
            "long_video planning missing hai."
        )

    segments = long_video.get("segments", [])

    if not isinstance(segments, list):
        raise RuntimeError(
            "Long segments list missing hai."
        )

    if len(segments) != LONG_SEGMENT_COUNT:
        raise RuntimeError(
            f"Exactly {LONG_SEGMENT_COUNT} Long segments chahiye."
        )

    long_dir = Path("output/images/long")
    generated_files: list[str] = []
    used_models: list[str] = []

    ordered_segments = sorted(
        segments,
        key=lambda segment: int(
            segment.get("segment_number", 0)
        ),
    )

    for index, segment in enumerate(ordered_segments):
        segment_number = int(
            segment.get("segment_number", index + 1)
        )

        prompt = build_long_prompt(
            story=story,
            segment=segment,
        )

        output_path = (
            long_dir
            / f"segment_{segment_number:02d}.jpg"
        )

        image_bytes, model_name = (
            generate_image_with_fallback(
                client=client,
                prompt=prompt,
                aspect_ratio="16:9",
                label=f"Long segment {segment_number}",
            )
        )

        save_image(
            image_bytes=image_bytes,
            output_path=output_path,
        )

        segment["image_file"] = str(output_path)
        segment["image_model"] = model_name
        generated_files.append(str(output_path))
        used_models.append(model_name)

        print(
            f"Long segment {segment_number} save ho gaya: "
            f"{output_path}"
        )

        if index < len(ordered_segments) - 1:
            time.sleep(REQUEST_PAUSE_SECONDS)

    long_video["generated_image_files"] = (
        generated_files
    )

    return generated_files, used_models


def update_story_file(
    story: dict[str, Any],
    story_path: Path,
    short_files: list[str],
    long_files: list[str],
    used_models: list[str],
) -> None:
    unique_models: list[str] = []

    for model_name in used_models:
        if model_name not in unique_models:
            unique_models.append(model_name)

    story["image_models_used"] = unique_models
    story["generated_image_files"] = short_files
    story["short_image_files"] = short_files
    story["long_image_files"] = long_files
    story["image_generation_status"] = "complete"

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
        "Milo & Friends final Short and Long image generator "
        "start ho raha hai..."
    )

    story_path = get_latest_story_file()
    print(f"Story file: {story_path}")

    story = load_story(story_path)
    client = get_client()

    short_files, short_models = (
        generate_short_images(
            client=client,
            story=story,
        )
    )

    long_files, long_models = (
        generate_long_images(
            client=client,
            story=story,
        )
    )

    update_story_file(
        story=story,
        story_path=story_path,
        short_files=short_files,
        long_files=long_files,
        used_models=short_models + long_models,
    )

    print("----------------------------------------")
    print(
        f"{len(short_files)} Short images ready hain."
    )
    print(
        f"{len(long_files)} Long images ready hain."
    )
    print(f"Updated story file: {story_path}")
    print("----------------------------------------")


if __name__ == "__main__":
    main()
