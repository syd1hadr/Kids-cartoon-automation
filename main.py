import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types


MODEL_CANDIDATES = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
]

SCENE_DURATIONS = [4, 4, 4, 4, 4, 5]
EXPECTED_SCENES = 6


def get_client() -> genai.Client:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY missing hai.")

    return genai.Client(api_key=api_key)


def create_prompt() -> str:
    return """
You are the creative song and story director for an original preschool
cartoon series called "Milo & Friends".

TARGET AUDIENCE:
- Children aged 2 to 6 years.
- Children must understand the story without difficult words.
- The Short must feel like a tiny sing-along rhyme, not a lecture.
- Use cheerful repetition that children can copy and sing.

PERMANENT ORIGINAL CHARACTERS:

Milo:
- baby orange-and-white kitten
- large blue eyes
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

VISUAL STYLE:
- original premium 3D preschool cartoon
- rounded, cute and expressive characters
- bright family-friendly colors
- soft cinematic lighting
- clear visible movement
- simple uncluttered backgrounds
- vertical 9:16 composition
- no text inside images
- no logos or watermarks
- do not copy any existing cartoon, studio, song or copyrighted character

CONTENT STYLE:
Create one completely original 25-second musical cartoon Short.

The story must feel like a playful preschool rhyme.

Use:
- very short English sentences
- mostly 3 to 7 words per line
- easy words such as jump, clap, run, hop, stop, go, up, down, red,
  blue, happy, funny and yay
- fun sounds such as Pop-pop, Hop-hop, Clap-clap, Ding-ding,
  Boing-boing, Whoosh and Yay
- clear rhythm and repetition
- one short repeated chorus
- one simple visible action in every scene
- a happy ending
- a smooth visual loop

Avoid:
- long narration
- difficult lessons
- complicated dialogue
- scary danger
- sad endings
- abstract morals
- repeated giant bubble stories
- repeating the same object or adventure from recent Milo videos
- violence, weapons, adult themes, politics or unsafe behaviour

STORY STRUCTURE:

Scene 1:
- immediate fun surprise in the first second
- introduce one short catchy lyric

Scene 2:
- characters move, clap, jump, run or dance
- continue the rhyme

Scene 3:
- a small funny problem happens
- use a playful sound

Scene 4:
- friends help together
- repeat part of the chorus

Scene 5:
- problem is solved
- joyful celebration

Scene 6:
- happy final chorus
- last action visually connects back to scene 1
- do not end abruptly

MUSIC DIRECTION:
- cheerful preschool instrumental
- ukulele
- toy piano
- xylophone
- gentle hand claps
- soft drum beat
- approximately 110 BPM
- no copyrighted melody
- no vocals inside the instrumental
- energetic but not loud or frightening

Return ONLY valid JSON using this exact structure:

{
  "story_id": "short-original-story-name",
  "concept": "one simple sentence describing the musical adventure",
  "hook": "the fun visual surprise shown in the first second",
  "moral": "a very short positive idea using easy words",
  "duration_seconds": 25,
  "characters_used": ["Milo", "Coco"],
  "content_type": "preschool_sing_along",
  "song_title": "short original rhyme title",
  "music": {
    "style": "happy preschool instrumental with ukulele, toy piano and xylophone",
    "bpm": 110,
    "mood": "cheerful and playful",
    "loop_friendly": true,
    "instrumental_only": true
  },
  "chorus": [
    "first short chorus line",
    "second short chorus line"
  ],
  "scenes": [
    {
      "scene_number": 1,
      "duration_seconds": 4,
      "action": "one clear visible action",
      "emotion": "one simple emotion",
      "narration": "one short rhythmic lyric line",
      "lyric": "same short rhythmic lyric line",
      "sound_effects": ["one or two simple sounds"],
      "visual_prompt": "complete detailed visual prompt for this scene"
    }
  ],
  "youtube": {
    "title": "catchy YouTube title under 70 characters",
    "description": "two short family-friendly sentences",
    "hashtags": [
      "#Shorts",
      "#MiloAndFriends",
      "#KidsSongs",
      "#KidsCartoon"
    ]
  }
}

STRICT RULES:
- Return exactly 6 scenes.
- Scene durations must be exactly: 4, 4, 4, 4, 4 and 5 seconds.
- Total duration must equal exactly 25 seconds.
- Each scene must have narration and lyric.
- Narration and lyric must contain the same sentence.
- Each lyric must be short and easy to sing.
- Do not use more than 8 words in one lyric line.
- Use at least one repeated chorus line.
- Do not create a lecture or complicated moral.
- Every visual_prompt must repeat the complete appearance and clothing
  description of every character shown in that scene.
- Every scene must show clear action.
- The final scene must look complete and joyful.
- The final visual action must naturally lead back into scene 1.
- Use only Milo, Coco, Poko and Ducky.
- Do not mention Pixar, Disney, CoComelon or any existing brand.
- No Markdown.
- Return only JSON.
""".strip()


def clean_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[7:].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:].strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Gemini ka JSON invalid hai: {error}"
        ) from error

    if not isinstance(parsed, dict):
        raise RuntimeError("Gemini response JSON object nahi hai.")

    return parsed


def validate_and_normalize_story(
    story: dict[str, Any],
) -> dict[str, Any]:
    scenes = story.get("scenes")

    if not isinstance(scenes, list):
        raise RuntimeError("Story mein scenes list missing hai.")

    if len(scenes) != EXPECTED_SCENES:
        raise RuntimeError(
            f"Exactly {EXPECTED_SCENES} scenes expected thin, "
            f"lekin {len(scenes)} mili."
        )

    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            raise RuntimeError(
                f"Scene {index + 1} valid object nahi hai."
            )

        scene_number = index + 1
        duration = SCENE_DURATIONS[index]

        scene["scene_number"] = scene_number
        scene["duration_seconds"] = duration

        lyric = str(
            scene.get("lyric")
            or scene.get("narration")
            or ""
        ).strip()

        if not lyric:
            raise RuntimeError(
                f"Scene {scene_number} mein lyric missing hai."
            )

        lyric_words = lyric.split()

        if len(lyric_words) > 10:
            raise RuntimeError(
                f"Scene {scene_number} ki lyric bohat lambi hai: "
                f"{len(lyric_words)} words."
            )

        scene["lyric"] = lyric
        scene["narration"] = lyric

        action = str(scene.get("action", "")).strip()
        visual_prompt = str(
            scene.get("visual_prompt", "")
        ).strip()

        if not action:
            raise RuntimeError(
                f"Scene {scene_number} mein action missing hai."
            )

        if not visual_prompt:
            raise RuntimeError(
                f"Scene {scene_number} mein visual_prompt missing hai."
            )

        sound_effects = scene.get("sound_effects", [])

        if not isinstance(sound_effects, list):
            scene["sound_effects"] = []
        else:
            scene["sound_effects"] = [
                str(sound).strip()
                for sound in sound_effects
                if str(sound).strip()
            ][:3]

    youtube = story.get("youtube")

    if not isinstance(youtube, dict):
        raise RuntimeError("Story mein YouTube data missing hai.")

    title = str(youtube.get("title", "")).strip()

    if not title:
        raise RuntimeError("YouTube title missing hai.")

    youtube["title"] = title[:70]

    hashtags = youtube.get("hashtags", [])

    if not isinstance(hashtags, list):
        hashtags = []

    required_hashtags = [
        "#Shorts",
        "#MiloAndFriends",
        "#KidsSongs",
        "#KidsCartoon",
    ]

    final_hashtags: list[str] = []

    for hashtag in hashtags + required_hashtags:
        hashtag = str(hashtag).strip()

        if hashtag and hashtag not in final_hashtags:
            final_hashtags.append(hashtag)

    youtube["hashtags"] = final_hashtags[:8]

    chorus = story.get("chorus", [])

    if not isinstance(chorus, list) or not chorus:
        chorus = [
            scenes[0]["lyric"],
            scenes[-1]["lyric"],
        ]

    story["chorus"] = [
        str(line).strip()
        for line in chorus
        if str(line).strip()
    ][:2]

    story["duration_seconds"] = sum(SCENE_DURATIONS)
    story["content_type"] = "preschool_sing_along"

    music = story.get("music")

    if not isinstance(music, dict):
        music = {}

    music.update(
        {
            "style": (
                "happy preschool instrumental with ukulele, "
                "toy piano, xylophone and gentle claps"
            ),
            "bpm": 110,
            "mood": "cheerful and playful",
            "loop_friendly": True,
            "instrumental_only": True,
        }
    )

    story["music"] = music

    return story


def generate_story() -> dict[str, Any]:
    client = get_client()
    errors: list[str] = []

    for model_name in MODEL_CANDIDATES:
        try:
            print(f"Trying model: {model_name}")

            response = client.models.generate_content(
                model=model_name,
                contents=create_prompt(),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.85,
                    max_output_tokens=8192,
                ),
            )

            response_text = response.text

            if not response_text:
                raise RuntimeError(
                    "Gemini ne empty response diya."
                )

            story = clean_json(response_text)
            story = validate_and_normalize_story(story)

            story["gemini_model"] = model_name
            story["generated_at"] = (
                datetime.now(timezone.utc).isoformat()
            )

            print(f"Success with model: {model_name}")
            return story

        except Exception as error:
            print(f"Model failed: {model_name}")
            print(error)
            errors.append(f"{model_name}: {error}")

    raise RuntimeError(
        "Sab Gemini models fail ho gaye: "
        + " | ".join(errors)
    )


def safe_story_name(story_id: str) -> str:
    safe_name = "".join(
        character
        if character.isalnum() or character in "-_"
        else "-"
        for character in story_id.lower()
    )

    safe_name = safe_name.strip("-_")

    return safe_name or "milo-song"


def save_story(story: dict[str, Any]) -> Path:
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    story_id = str(
        story.get("story_id", "milo-song")
    )

    safe_name = safe_story_name(story_id)

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%d-%H%M%S"
    )

    output_path = output_dir / (
        f"{timestamp}-{safe_name}.json"
    )

    output_path.write_text(
        json.dumps(
            story,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return output_path


def main() -> None:
    print(
        "Milo & Friends Sing-Along Story Brain "
        "start ho raha hai..."
    )

    story = generate_story()
    output_path = save_story(story)

    print("Musical story successfully generate ho gayi.")
    print(f"Song: {story.get('song_title', 'Milo Song')}")
    print(f"Title: {story['youtube']['title']}")
    print(f"Duration: {story['duration_seconds']} seconds")
    print(f"Saved file: {output_path}")


if __name__ == "__main__":
    main()
