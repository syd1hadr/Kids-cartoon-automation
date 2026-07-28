import json
import os
from pathlib import Path

from google import genai
from google.genai import types


MODEL_NAME = "imagen-4.0-fast-generate-001"
LOCATION = os.getenv("GCP_LOCATION", "us-central1")


def get_latest_story_file() -> Path:
    output_dir = Path("output")

    if not output_dir.exists():
        raise RuntimeError("output folder nahi mila.")

    story_files = list(output_dir.glob("*.json"))

    if not story_files:
        raise RuntimeError("output folder mein story JSON nahi mili.")

    return max(story_files, key=lambda file: file.stat().st_mtime)


def get_vertex_client() -> genai.Client:
    project_id = os.getenv("GCP_PROJECT_ID", "").strip()

    if not project_id:
        raise RuntimeError("GCP_PROJECT_ID missing hai.")

    return genai.Client(
        vertexai=True,
        project=project_id,
        location=LOCATION,
    )


def build_image_prompt(scene: dict) -> str:
    visual_prompt = scene.get("visual_prompt", "").strip()

    if not visual_prompt:
        raise RuntimeError(
            f"Scene {scene.get('scene_number')} mein visual_prompt missing hai."
        )

    consistency_prompt = """
Create a polished original 3D animated kids-cartoon frame.

Permanent character designs:
Milo: baby orange-and-white kitten, large blue eyes, blue T-shirt,
red shorts and white shoes.

Coco: small white puppy, light-brown floppy ears, yellow hoodie
and blue shoes.

Poko: cute baby panda, green overalls and tiny red backpack.

Ducky: tiny yellow duckling, purple cap and tiny blue bag.

Maintain exactly the same character appearance, clothing, colors,
body proportions and facial design in every scene.

Visual requirements:
vertical 9:16 composition, premium 3D animation, cinematic lighting,
bright family-friendly colors, expressive faces, clear visible action,
clean background separation, no text, no captions, no logos,
no watermark, no copyrighted characters.
""".strip()

    return f"{consistency_prompt}\n\nScene to create:\n{visual_prompt}"


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

    response = client.models.generate_images(
        model=MODEL_NAME,
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio="9:16",
            output_mime_type="image/png",
        ),
    )

    if not response.generated_images:
        raise RuntimeError(
            f"Scene {scene_number} ke liye Imagen ne image nahi di."
        )

    image_path = images_dir / f"scene_{scene_number:02d}.png"
    response.generated_images[0].image.save(str(image_path))

    print(f"Scene {scene_number} save ho gayi: {image_path}")
    return image_path


def main():
    print("Milo & Friends Imagen Generator start ho raha hai...")

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

    client = get_vertex_client()

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
