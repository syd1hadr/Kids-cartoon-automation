import json
import os
import time
from pathlib import Path

from google import genai


MODEL_NAME = "gemini-2.5-flash-image"
SCENE_COUNT = 6


def get_client() -> genai.Client:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY secret missing hai.")

    return genai.Client(api_key=api_key)


def get_latest_story_file() -> Path:
    output_dir = Path("output")

    if not output_dir.exists():
        raise RuntimeError("output folder nahi mila.")

    story_files = list(output_dir.glob("*.json"))

    if not story_files:
        raise RuntimeError("output folder mein story JSON nahi mili.")

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


def build_image_prompt(scene: dict) -> str:
    scene_number = scene.get("scene_number", "unknown")
    visual_prompt = str(
        scene.get("visual_prompt", "")
    ).strip()

    if not visual_prompt:
        raise RuntimeError(
            f"Scene {scene_number} mein visual_prompt missing hai."
        )

    return f"""
Create exactly one original premium 3D animated kids-cartoon image.

SERIES:
Milo & Friends

PERMANENT CHARACTER DESIGNS:

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

STRICT CONSISTENCY RULES:
- Keep every character's face, fur, clothing, colors and body proportions consistent.
- Do not change or redesign the characters.
- Show only characters required by this scene.
- Make the visible action very clear.
- Use expressive, readable facial emotions.
- Premium polished 3D cartoon quality.
- Bright family-friendly colors.
- Cinematic soft lighting.
- Strong foreground and background separation.
- Vertical composition designed for a 9:16 YouTube Short.
- Keep important characters near the center.
- No text.
- No subtitles.
- No speech bubbles.
- No logo.
- No watermark.
- No copyrighted characters.
- No frightening, violent or unsafe imagery.

SCENE {scene_number}:
{visual_prompt}

Return the finished cartoon image.
""".strip()


def save_generated_image(
    response,
    image_path: Path,
    scene_number: int,
) -> None:
    parts = response.parts or []

    for part in parts:
        if part.inline_data is None:
            continue

        image = part.as_image()

        if image is None:
            continue

        image.save(str(image_path))
        return

    raise RuntimeError(
        f"Scene {scene_number} ke response mein image nahi mili."
    )


def generate_scene_image(
    client: genai.Client,
    scene: dict,
    images_dir: Path,
) -> Path:
    try:
        scene_number = int(scene.get("scene_number", 0))
    except (TypeError, ValueError) as error:
        raise RuntimeError(
            "Invalid scene_number mila."
        ) from error

    if scene_number <= 0:
        raise RuntimeError("Invalid scene_number mila.")

    prompt = build_image_prompt(scene)
    image_path = images_dir / f"scene_{scene_number:02d}.png"

    print(
        f"Scene {scene_number} ki image generate ho rahi hai..."
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[prompt],
    )

    save_generated_image(
        response=response,
        image_path=image_path,
        scene_number=scene_number,
    )

    print(
        f"Scene {scene_number} successfully save ho gayi: "
        f"{image_path}"
    )

    return image_path


def main() -> None:
    print("Milo & Friends image generator start ho raha hai...")

    story_path = get_latest_story_file()
    print(f"Story file mili: {story_path}")

    story = load_story(story_path)
    scenes = story.get("scenes", [])

    if not isinstance(scenes, list):
        raise RuntimeError(
            "Story mein scenes list ki form mein nahi hain."
        )

    if len(scenes) != SCENE_COUNT:
        raise RuntimeError(
            f"Exactly {SCENE_COUNT} scenes expected thin, "
            f"lekin {len(scenes)} milin."
        )

    images_dir = Path("output/images")
    images_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    client = get_client()
    generated_files = []

    for index, scene in enumerate(scenes):
        image_path = generate_scene_image(
            client=client,
            scene=scene,
            images_dir=images_dir,
        )

        scene["image_file"] = str(image_path)
        generated_files.append(str(image_path))

        # API ko consecutive requests ke darmiyan chhota pause.
        if index < len(scenes) - 1:
            time.sleep(2)

    story["image_model"] = MODEL_NAME
    story["generated_image_files"] = generated_files

    story_path.write_text(
        json.dumps(
            story,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("----------------------------------------")
    print("Tamam 6 images successfully generate ho gayi hain.")
    print(f"Updated story file: {story_path}")
    print(f"Images folder: {images_dir}")
    print("----------------------------------------")


if __name__ == "__main__":
    main()
