import json
import os
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import types


def get_client():
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY missing hai.")

    return genai.Client(api_key=api_key)


def create_prompt():
    return """
You are the story director for an original YouTube Shorts cartoon series
called "Milo & Friends".

MAIN CHARACTERS:

Milo:
- baby orange and white kitten
- large blue eyes
- blue T-shirt
- red shorts
- white shoes
- brave, kind and curious

Coco:
- small white puppy
- light brown floppy ears
- yellow hoodie
- blue shoes
- loyal, energetic and funny

Poko:
- baby panda
- green overalls
- tiny red backpack
- lovable and clumsy

Ducky:
- tiny yellow duckling
- purple cap
- tiny blue bag
- cheerful and clever

VISUAL STYLE:
- original premium 3D cartoon
- bright family-friendly colors
- rounded cute characters
- expressive faces
- cinematic lighting
- vertical 9:16 format
- do not copy any existing cartoon, studio or copyrighted character

Create one completely original 25 to 30 second cartoon Short.

Return ONLY valid JSON using this exact structure:

{
  "story_id": "short-story-name",
  "concept": "one sentence story idea",
  "hook": "what happens in the first second",
  "moral": "short positive lesson",
  "duration_seconds": 28,
  "characters_used": ["Milo", "Coco"],
  "scenes": [
    {
      "scene_number": 1,
      "duration_seconds": 4,
      "action": "what happens in this scene",
      "emotion": "main emotion",
      "narration": "short narration or empty string",
      "sound_effects": ["sound effect"],
      "visual_prompt": "complete visual prompt for this scene"
    }
  ],
  "youtube": {
    "title": "YouTube title under 70 characters",
    "description": "two short sentences",
    "hashtags": [
      "#Shorts",
      "#MiloAndFriends",
      "#KidsCartoon"
    ]
  }
}

RULES:
- Create exactly 6 scenes.
- Total duration must be between 25 and 30 seconds.
- First scene must immediately show surprise, danger, emotion or curiosity.
- Every scene must contain visible action.
- Use very little dialogue so children worldwide can understand.
- Story must end happily.
- Last scene should connect naturally to the first scene for a smooth loop.
- Use only Milo, Coco, Poko and Ducky.
- No violence, weapons, adult themes, politics or unsafe behaviour.
- No Markdown.
- Return only JSON.
"""


def clean_json(text):
    cleaned = text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[7:].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:].strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    return json.loads(cleaned)


def generate_story():
    client = get_client()

    models = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-flash-latest",
    ]

    errors = []

    for model_name in models:
        try:
            print(f"Trying model: {model_name}")

            response = client.models.generate_content(
                model=model_name,
                contents=create_prompt(),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.9,
                ),
            )

            if not response.text:
                raise RuntimeError("Gemini ne empty response diya.")

            story = clean_json(response.text)

            if "scenes" not in story:
                raise RuntimeError("Story mein scenes missing hain.")

            if "youtube" not in story:
                raise RuntimeError("Story mein YouTube data missing hai.")

            story["gemini_model"] = model_name
            story["generated_at"] = datetime.utcnow().isoformat() + "Z"

            print(f"Success with model: {model_name}")
            return story

        except Exception as error:
            print(f"Model failed: {model_name}")
            print(error)
            errors.append(f"{model_name}: {error}")

    raise RuntimeError(
        "Sab Gemini models fail ho gaye: " + " | ".join(errors)
    )


def save_story(story):
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    story_id = story.get("story_id", "milo-story")
    safe_name = "".join(
        character if character.isalnum() or character in "-_"
        else "-"
        for character in story_id.lower()
    )

    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    output_path = output_dir / f"{timestamp}-{safe_name}.json"

    output_path.write_text(
        json.dumps(story, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return output_path


def main():
    print("Milo & Friends Story Brain start ho raha hai...")

    story = generate_story()
    output_path = save_story(story)

    print("Story successfully generate ho gayi.")
    print(f"Title: {story['youtube']['title']}")
    print(f"Saved file: {output_path}")


if __name__ == "__main__":
    main()
