import json
import os
from pathlib import Path

from google import genai
from google.genai import types


MODEL_NAME = "gemini-2.5-flash-image"


def get_latest_story_file() -> Path:
    output_dir = Path("output")

    if not output_dir.exists():
        raise RuntimeError("output folder nahi mila.")

    story_files = list(output_dir.glob("*.json"))

    if not story_files:
        raise RuntimeError("output folder mein story JSON nahi mili.")

    return max(story_files, key=lambda file: file.stat().st_mtime)


def get_client() -> genai.Client:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY missing hai.")

    return genai.Client(api_key=api_key)


def build_image_prompt(scene: dict) -> str:
    visual_prompt = scene.get("visual_prompt", "").strip()

    if not visual_prompt:
        raise RuntimeError(
            f"Scene {scene.get('scene_number')} mein visual_prompt missing hai."
        )

    consistency_prompt = """
Create one original premium 3D animated kids-cartoon frame.

Permanent character designs:

Milo:
baby orange-and-white kitten, large blue eyes, blue T-shirt,
red shorts, white shoes.

Coco:
small white puppy, light-brown floppy ears, yellow hoodie,
blue shoes.

Poko:
cute baby panda, green overalls, tiny red backpack.

Ducky:
tiny yellow duckling, purple cap, tiny blue bag.

Keep character appearance, clothing colors, body proportions,
facial design and art style consistent.

Image requirements:
vertical 9:16 composition,
bright family-friendly colors,
cinematic lighting,
expressive faces,
clear visible action,
clean background,
no text,
no captions,
no logo,
no watermark,
no copyrighted characters.
""".strip()

    return f"{consistency_prompt}\n\nScene:\n{visual_prompt}"


def generate_scene_image(
    client: genai.Client,
    scene: dict,
    images_dir: Path,
) -> Path:
    scene_number = int(scene.get("scene_number", 0))

    if scene_number <= 0:
        raise RuntimeError("Invalid scene_number mila.")

    prompt = build_image_prompt(scene)

    print(f"Scene {scene_number} ki image generate ho rahi hai...")

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            response_format={
                "image": {
                    "aspect_ratio": "9:16",
                }
            },
        ),
    )

    image_path = images_dir / f"scene_{scene_number:02d}.png"
    image_saved = False

    for part in response.parts:
        image = part.as_image()

        if image is not None:
            image.save(str(image_path))
            image_saved = True
            break

    if not image_saved:
        raise RuntimeError(
            f"Scene {scene_number} ke liye Gemini ne image nahi di."
        )

    print(f"Scene {scene_number} save ho gayi: {image_path}")
    return image_path


def main():
    print("Milo & Friends image generator start ho raha hai...")

    story_path = get_latest_story_file()
    print(f"Story file: {story_path}")

    story = json.loads(story_path.read_text(encoding="utf-8"))
    scenes = story.get("scenes", [])

    if len(scenes) != 6:
        raise RuntimeError(
            f"Exactly 6 scenes expected thin, lekin {len(scenes)} milin."
        )

    images_dir = Path("output/images")
    images_dir.mkdir(parents=True, exist_ok=True)

    client = get_client()

    for scene in scenes:
        image_path = generate_scene_image(
            client=client,
            scene=scene,
            images_dir=images_dir,
        )

        scene["image_file"] = str(image_path)

    story["image_model"] = MODEL_NAME

    story_path.write_text(
        json.dumps(story, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("Tamam 6 images successfully generate ho gayi hain.")


if __name__ == "__main__":
    main()
