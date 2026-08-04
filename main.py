import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from anthropic import Anthropic

from topic_manager import (
    choose_topic,
    reserve_topic,
)


MODEL_CANDIDATES = [
    os.getenv(
        "CLAUDE_MODEL",
        "claude-sonnet-5",
    ).strip(),
    "claude-haiku-4-5",
]

SHORT_SCENE_DURATIONS = [4, 4, 4, 4, 4, 5]
SHORT_SCENE_COUNT = 6

LONG_SEGMENT_DURATIONS = [18] * 12
LONG_SEGMENT_COUNT = 12
LONG_DURATION_SECONDS = sum(LONG_SEGMENT_DURATIONS)


def get_client() -> Anthropic:
    api_key = os.getenv(
        "ANTHROPIC_API_KEY",
        "",
    ).strip()

    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY GitHub secret missing hai."
        )

    return Anthropic(
        api_key=api_key,
        max_retries=2,
        timeout=180.0,
    )


def load_trend_data() -> dict[str, Any]:
    trend_path = Path("output/trend.json")

    if not trend_path.exists():
        print(
            "Warning: output/trend.json nahi mili. "
            "Topic manager apna unique topic select karega."
        )

        return {
            "selected_topic": "",
            "selected_score": 0,
            "topic_rankings": [],
            "copyright_rule": (
                "Create completely original lyrics, melody direction, "
                "story and visuals."
            ),
            "trend_source_available": False,
        }

    try:
        trend_data = json.loads(
            trend_path.read_text(
                encoding="utf-8",
            )
        )
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"trend.json valid JSON nahi hai: {error}"
        ) from error

    if not isinstance(trend_data, dict):
        raise RuntimeError(
            "trend.json object format mein nahi hai."
        )

    selected_topic = str(
        trend_data.get(
            "selected_topic",
            "",
        )
    ).strip()

    trend_data["selected_topic"] = selected_topic
    trend_data["trend_source_available"] = bool(
        selected_topic
    )

    return trend_data


def select_unique_topic(
    trend_data: dict[str, Any],
) -> dict[str, str]:
    suggested_topic = str(
        trend_data.get(
            "selected_topic",
            "",
        )
    ).strip()

    selected = choose_topic(
        suggested_topic=suggested_topic,
    )

    print("----------------------------------------")
    print("Unique topic manager result:")
    print(
        f"Trend suggestion: "
        f"{suggested_topic or 'none'}"
    )
    print(f"Final topic: {selected['topic']}")
    print(f"Category: {selected['category']}")
    print("----------------------------------------")

    return selected


def create_prompt(
    trend_data: dict[str, Any],
    selected_topic: str,
    topic_category: str,
) -> str:
    topic_rankings = trend_data.get(
        "topic_rankings",
        [],
    )

    ranking_text = json.dumps(
        topic_rankings[:5]
        if isinstance(topic_rankings, list)
        else [],
        ensure_ascii=False,
    )

    return f"""
You are the original preschool song director and learning-content writer
for an independent cartoon series called "Milo & Friends".

FINAL UNIQUE LEARNING TOPIC:
{selected_topic}

TOPIC CATEGORY:
{topic_category}

TREND RESEARCH SIGNALS:
{ranking_text}

IMPORTANT:

The final topic above was selected by a repeat-blocking topic manager.
You must create the Short and Long video around exactly this topic.

Do not switch back to ABC Phonics unless the final unique topic itself
is ABC Phonics.

Do not turn unrelated topics into alphabet lessons.

IMPORTANT COPYRIGHT RULE:

Use the selected topic only as a general learning idea.

Do not copy:
- any existing title
- any lyrics
- any melody
- any chorus
- any character
- any scene sequence
- any thumbnail
- any visual composition
- any channel branding

Create a completely original Milo & Friends nursery rhyme.

TARGET AUDIENCE:

- Children aged 2 to 6.
- Use very easy English.
- Children should be able to sing, copy actions and learn.
- Make the song cheerful, repetitive and memorable.
- Avoid adult-style narration.
- Avoid long explanations.
- Avoid difficult vocabulary.

PERMANENT ORIGINAL CHARACTERS:

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

VISUAL QUALITY RULES:

- original premium 3D preschool cartoon
- rounded cute characters
- correct anatomy and body positioning
- characters must stand, sit, jump and move naturally
- no character may pass through furniture or objects
- feet must touch the floor or correct surface
- hands and paws must hold objects naturally
- no merged bodies
- no duplicated limbs
- no floating objects unless the story requires it
- no character trapped inside a bench, wall, floor or prop
- bright family-friendly colors
- soft cinematic lighting
- clean and uncluttered backgrounds
- clear visible learning action
- expressive faces
- no text inside generated visuals
- no subtitles
- no logos
- no watermarks
- no copyrighted characters

ANIMATION REQUIREMENTS:

- This is not a static slideshow.
- Every scene must describe continuous real character animation.
- Characters must walk, dance, jump, clap, point or interact naturally.
- Include facial expressions and eye movement.
- Include natural head, hand, paw and body movement.
- Include clear camera movement when useful.
- Keep character identity and clothing consistent.
- Scene directions must be suitable for animated video generation.
- Never describe a still photograph.
- Never request simple image zooming as the main movement.
- Every scene must have a clear beginning action and ending action.
- Short scenes should connect smoothly.
- The final Short scene should loop naturally into scene one.

CREATE TWO CONNECTED OUTPUTS:

1. One 25-second vertical YouTube Short.
2. One 216-second long nursery-rhyme plan.

Both outputs must teach exactly this topic:
{selected_topic}

SHORT REQUIREMENTS:

- exactly 6 scenes
- durations exactly 4, 4, 4, 4, 4 and 5 seconds
- total exactly 25 seconds
- vertical 9:16
- immediate visual hook
- one easy lyric line per scene
- maximum 8 words per lyric line
- visible animated movement in every scene
- actions such as clap, point, jump, dance, count, match or repeat
- one catchy two-line chorus
- joyful complete ending
- final action should loop naturally to the first scene

LONG VIDEO REQUIREMENTS:

- exactly 12 learning segments
- every segment exactly 18 seconds
- total exactly 216 seconds
- horizontal 16:9 planning
- each segment teaches one small part of the selected topic
- use repetition without sounding identical
- include action instructions children can follow
- include a two-line chorus after segments 3, 6, 9 and 12
- begin with a clear welcome
- end with a happy recap and goodbye
- no filler
- no complicated story
- no scary problem
- no adult lecture
- no static slideshow direction
- every segment must describe continuous character animation

MUSIC DIRECTION:

- original nursery-rhyme melody direction
- cheerful and warm
- approximately 105 to 115 BPM
- ukulele
- toy piano
- xylophone
- gentle drums
- soft hand claps
- simple bass
- no copyrighted melody
- vocals should sound playful and child-friendly
- do not make the singer sound like a serious adult narrator

Return ONLY valid JSON using exactly this structure:

{{
  "story_id": "original-topic-based-id",
  "selected_trend_topic": "{selected_topic}",
  "topic_category": "{topic_category}",
  "concept": "one simple original learning-song concept",
  "hook": "clear animated visual hook in the first second",
  "moral": "very short positive learning idea",
  "duration_seconds": 25,
  "characters_used": ["Milo", "Coco"],
  "content_type": "preschool_learning_rhyme",
  "song_title": "original short song title",
  "music": {{
    "style": "original cheerful preschool song",
    "bpm": 110,
    "mood": "playful and educational",
    "vocals_required": true,
    "instrumental_only": false,
    "copyrighted_melody": false
  }},
  "chorus": [
    "first original chorus line",
    "second original chorus line"
  ],
  "scenes": [
    {{
      "scene_number": 1,
      "duration_seconds": 4,
      "action": "clear continuous physical action",
      "learning_goal": "small learning goal",
      "emotion": "simple emotion",
      "narration": "short singable lyric",
      "lyric": "same short singable lyric",
      "sound_effects": ["simple sound"],
      "camera_motion": "simple animated camera movement",
      "animation_prompt": "complete continuous animation direction",
      "visual_prompt": "complete original premium 3D animated scene description"
    }}
  ],
  "long_video": {{
    "title": "original long nursery-rhyme title",
    "duration_seconds": 216,
    "format": "16:9",
    "opening_lines": [
      "easy welcome line",
      "easy topic introduction"
    ],
    "chorus": [
      "first long-video chorus line",
      "second long-video chorus line"
    ],
    "segments": [
      {{
        "segment_number": 1,
        "duration_seconds": 18,
        "section_name": "short section name",
        "learning_goal": "one simple skill",
        "characters_used": ["Milo", "Coco"],
        "lyrics": [
          "short singable line one",
          "short singable line two",
          "short singable line three",
          "short singable line four"
        ],
        "actions": [
          "clear continuous movement one",
          "clear continuous movement two"
        ],
        "sound_effects": [
          "simple sound"
        ],
        "camera_motion": "natural animated camera direction",
        "animation_prompt": "complete continuous animation direction",
        "visual_direction": "animated scene direction with natural movement"
      }}
    ],
    "ending_lines": [
      "happy recap line",
      "simple goodbye line"
    ],
    "youtube": {{
      "title": "long video YouTube title under 90 characters",
      "description": "two family-friendly sentences",
      "hashtags": [
        "#MiloAndFriends",
        "#NurseryRhymes",
        "#KidsSongs",
        "#PreschoolLearning"
      ]
    }}
  }},
  "youtube": {{
    "title": "Short title under 70 characters",
    "description": "two short family-friendly sentences",
    "hashtags": [
      "#Shorts",
      "#MiloAndFriends",
      "#NurseryRhymes",
      "#KidsSongs"
    ]
  }}
}}

STRICT RULES:

- Return exactly 6 Short scenes.
- Short scene durations must be 4, 4, 4, 4, 4 and 5.
- Return exactly 12 long-video segments.
- Every long segment must be 18 seconds.
- Every Short scene must contain lyric and narration.
- Lyric and narration must be identical.
- Every Short lyric must contain 8 words or fewer.
- Every long-video lyric line should contain 3 to 9 words.
- Every scene and segment must include visible continuous animation.
- Every Short scene must include animation_prompt.
- Every Short scene must include camera_motion.
- Every long segment must include animation_prompt.
- Every long segment must include camera_motion.
- Every visual description must specify natural anatomy.
- Repeat full appearance and clothing of characters shown.
- Use only Milo, Coco, Poko and Ducky.
- Create original learning content.
- Do not mention any existing brand or channel.
- Do not return Markdown.
- Return only JSON.
""".strip()


def extract_text_from_response(
    response: Any,
) -> str:
    text_parts: list[str] = []

    for block in response.content:
        block_type = getattr(
            block,
            "type",
            "",
        )

        if block_type != "text":
            continue

        block_text = getattr(
            block,
            "text",
            "",
        )

        if block_text:
            text_parts.append(
                str(block_text)
            )

    return "\n".join(
        text_parts
    ).strip()


def clean_json(
    text: str,
) -> dict[str, Any]:
    cleaned = text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[7:].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:].strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")

    if (
        first_brace >= 0
        and last_brace > first_brace
    ):
        cleaned = cleaned[
            first_brace:last_brace + 1
        ]

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as error:
        preview = cleaned[:500]

        raise RuntimeError(
            "Claude ka JSON invalid hai: "
            f"{error}. Response preview: {preview}"
        ) from error

    if not isinstance(parsed, dict):
        raise RuntimeError(
            "Claude response JSON object nahi hai."
        )

    return parsed


def normalize_text(
    value: Any,
) -> str:
    return " ".join(
        str(value).strip().split()
    )


def validate_short_scenes(
    story: dict[str, Any],
) -> None:
    scenes = story.get("scenes")

    if not isinstance(scenes, list):
        raise RuntimeError(
            "Story mein Short scenes list missing hai."
        )

    if len(scenes) != SHORT_SCENE_COUNT:
        raise RuntimeError(
            f"Exactly {SHORT_SCENE_COUNT} Short scenes "
            f"expected thin, lekin {len(scenes)} mili."
        )

    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            raise RuntimeError(
                f"Short scene {index + 1} valid object nahi hai."
            )

        scene_number = index + 1
        duration = SHORT_SCENE_DURATIONS[index]

        scene["scene_number"] = scene_number
        scene["duration_seconds"] = duration

        lyric = normalize_text(
            scene.get("lyric")
            or scene.get("narration")
            or ""
        )

        if not lyric:
            raise RuntimeError(
                f"Short scene {scene_number} mein lyric missing hai."
            )

        if len(lyric.split()) > 8:
            raise RuntimeError(
                f"Short scene {scene_number} ki lyric "
                "8 words se zyada hai."
            )

        scene["lyric"] = lyric
        scene["narration"] = lyric

        action = normalize_text(
            scene.get(
                "action",
                "",
            )
        )

        visual_prompt = normalize_text(
            scene.get(
                "visual_prompt",
                "",
            )
        )

        animation_prompt = normalize_text(
            scene.get(
                "animation_prompt",
                "",
            )
        )

        camera_motion = normalize_text(
            scene.get(
                "camera_motion",
                "",
            )
        )

        if not action:
            raise RuntimeError(
                f"Short scene {scene_number} mein action missing hai."
            )

        if not visual_prompt:
            raise RuntimeError(
                f"Short scene {scene_number} mein "
                "visual_prompt missing hai."
            )

        if not animation_prompt:
            animation_prompt = (
                f"{action}. The characters move continuously "
                "with natural body movement, facial expressions, "
                "eye movement and correct anatomy."
            )

        if not camera_motion:
            camera_motion = (
                "gentle cinematic tracking movement"
            )

        scene["action"] = action
        scene["visual_prompt"] = visual_prompt
        scene["animation_prompt"] = (
            animation_prompt
        )
        scene["camera_motion"] = (
            camera_motion
        )

        learning_goal = normalize_text(
            scene.get(
                "learning_goal",
                "",
            )
        )

        if not learning_goal:
            learning_goal = (
                "follow the song action"
            )

        scene["learning_goal"] = (
            learning_goal
        )

        sound_effects = scene.get(
            "sound_effects",
            [],
        )

        if not isinstance(
            sound_effects,
            list,
        ):
            sound_effects = []

        scene["sound_effects"] = [
            normalize_text(sound)
            for sound in sound_effects
            if normalize_text(sound)
        ][:3]


def validate_long_video(
    story: dict[str, Any],
) -> None:
    long_video = story.get(
        "long_video"
    )

    if not isinstance(long_video, dict):
        raise RuntimeError(
            "long_video planning missing hai."
        )

    segments = long_video.get(
        "segments"
    )

    if not isinstance(segments, list):
        raise RuntimeError(
            "Long video segments list missing hai."
        )

    if len(segments) != LONG_SEGMENT_COUNT:
        raise RuntimeError(
            f"Exactly {LONG_SEGMENT_COUNT} long segments "
            f"expected thay, lekin {len(segments)} mile."
        )

    for index, segment in enumerate(
        segments
    ):
        if not isinstance(segment, dict):
            raise RuntimeError(
                f"Long segment {index + 1} valid object nahi hai."
            )

        segment_number = index + 1

        segment["segment_number"] = (
            segment_number
        )
        segment["duration_seconds"] = (
            LONG_SEGMENT_DURATIONS[index]
        )

        lyrics = segment.get(
            "lyrics",
            [],
        )

        if not isinstance(lyrics, list):
            lyrics = []

        cleaned_lyrics = [
            normalize_text(line)
            for line in lyrics
            if normalize_text(line)
        ]

        if len(cleaned_lyrics) < 2:
            raise RuntimeError(
                f"Long segment {segment_number} mein "
                "kam az kam 2 lyric lines honi chahiye."
            )

        segment["lyrics"] = (
            cleaned_lyrics[:6]
        )

        actions = segment.get(
            "actions",
            [],
        )

        if not isinstance(actions, list):
            actions = []

        cleaned_actions = [
            normalize_text(action)
            for action in actions
            if normalize_text(action)
        ]

        if not cleaned_actions:
            raise RuntimeError(
                f"Long segment {segment_number} mein "
                "movement actions missing hain."
            )

        segment["actions"] = (
            cleaned_actions[:4]
        )

        visual_direction = normalize_text(
            segment.get(
                "visual_direction",
                "",
            )
        )

        animation_prompt = normalize_text(
            segment.get(
                "animation_prompt",
                "",
            )
        )

        camera_motion = normalize_text(
            segment.get(
                "camera_motion",
                "",
            )
        )

        if not visual_direction:
            raise RuntimeError(
                f"Long segment {segment_number} mein "
                "visual_direction missing hai."
            )

        if not animation_prompt:
            animation_prompt = (
                f"{visual_direction}. Characters move continuously "
                "with natural walking, dancing, gestures, facial "
                "expressions and correct anatomy."
            )

        if not camera_motion:
            camera_motion = (
                "smooth preschool cinematic camera movement"
            )

        segment["visual_direction"] = (
            visual_direction
        )
        segment["animation_prompt"] = (
            animation_prompt
        )
        segment["camera_motion"] = (
            camera_motion
        )

    long_video["duration_seconds"] = (
        LONG_DURATION_SECONDS
    )
    long_video["format"] = "16:9"


def normalize_youtube_data(
    youtube_data: Any,
    *,
    is_short: bool,
) -> dict[str, Any]:
    if not isinstance(
        youtube_data,
        dict,
    ):
        youtube_data = {}

    default_title = (
        "Milo & Friends Nursery Rhyme #Shorts"
        if is_short
        else "Milo & Friends Nursery Rhyme"
    )

    title = normalize_text(
        youtube_data.get(
            "title",
            default_title,
        )
    )

    title_limit = (
        70 if is_short else 90
    )

    youtube_data["title"] = (
        title or default_title
    )[:title_limit]

    description = normalize_text(
        youtube_data.get(
            "description",
            "",
        )
    )

    youtube_data["description"] = (
        description
    )

    hashtags = youtube_data.get(
        "hashtags",
        [],
    )

    if not isinstance(hashtags, list):
        hashtags = []

    required_hashtags = (
        [
            "#Shorts",
            "#MiloAndFriends",
            "#NurseryRhymes",
            "#KidsSongs",
        ]
        if is_short
        else [
            "#MiloAndFriends",
            "#NurseryRhymes",
            "#KidsSongs",
            "#PreschoolLearning",
        ]
    )

    final_hashtags: list[str] = []

    for hashtag in (
        hashtags + required_hashtags
    ):
        cleaned_hashtag = normalize_text(
            hashtag
        ).replace(
            " ",
            "",
        )

        if not cleaned_hashtag:
            continue

        if not cleaned_hashtag.startswith(
            "#"
        ):
            cleaned_hashtag = (
                "#" + cleaned_hashtag
            )

        if (
            cleaned_hashtag
            not in final_hashtags
        ):
            final_hashtags.append(
                cleaned_hashtag
            )

    youtube_data["hashtags"] = (
        final_hashtags[:10]
    )

    return youtube_data


def validate_and_normalize_story(
    story: dict[str, Any],
    trend_data: dict[str, Any],
    selected_topic: str,
    topic_category: str,
) -> dict[str, Any]:
    validate_short_scenes(story)
    validate_long_video(story)

    story["selected_trend_topic"] = (
        selected_topic
    )
    story["topic_category"] = (
        topic_category
    )

    story["duration_seconds"] = sum(
        SHORT_SCENE_DURATIONS
    )

    story["content_type"] = (
        "preschool_learning_rhyme"
    )

    chorus = story.get(
        "chorus",
        [],
    )

    if not isinstance(chorus, list):
        chorus = []

    cleaned_chorus = [
        normalize_text(line)
        for line in chorus
        if normalize_text(line)
    ]

    if not cleaned_chorus:
        scenes = story["scenes"]

        cleaned_chorus = [
            scenes[0]["lyric"],
            scenes[-1]["lyric"],
        ]

    story["chorus"] = (
        cleaned_chorus[:2]
    )

    music = story.get("music")

    if not isinstance(music, dict):
        music = {}

    music.update(
        {
            "style": (
                "original cheerful preschool song with "
                "ukulele, toy piano, xylophone, gentle "
                "drums and hand claps"
            ),
            "bpm": 110,
            "mood": (
                "playful and educational"
            ),
            "vocals_required": True,
            "instrumental_only": False,
            "copyrighted_melody": False,
        }
    )

    story["music"] = music

    story["youtube"] = (
        normalize_youtube_data(
            story.get("youtube"),
            is_short=True,
        )
    )

    long_video = story["long_video"]

    long_video["youtube"] = (
        normalize_youtube_data(
            long_video.get("youtube"),
            is_short=False,
        )
    )

    story["trend_metadata"] = {
        "suggested_topic": trend_data.get(
            "selected_topic",
            "",
        ),
        "final_unique_topic": selected_topic,
        "topic_category": topic_category,
        "selected_score": trend_data.get(
            "selected_score",
            0,
        ),
        "region": trend_data.get(
            "region",
            "US",
        ),
        "language": trend_data.get(
            "language",
            "en",
        ),
        "trend_generated_at": trend_data.get(
            "generated_at",
        ),
        "copyright_rule": (
            "Only the general learning topic was used. "
            "No title, lyrics, melody, character or "
            "scene sequence was copied."
        ),
    }

    return story


def generate_story(
    trend_data: dict[str, Any],
    selected_topic: str,
    topic_category: str,
) -> dict[str, Any]:
    client = get_client()
    errors: list[str] = []

    prompt = create_prompt(
        trend_data=trend_data,
        selected_topic=selected_topic,
        topic_category=topic_category,
    )

    system_prompt = """
You are the senior creative director and structured-output engine for
Milo & Friends, an original premium preschool 3D animation channel.

Create catchy, safe and age-appropriate nursery-rhyme plans with:
- powerful first-second hooks
- simple educational lyrics
- continuous animated character movement
- consistent character appearance
- production-ready animation directions
- natural camera motion
- original music direction
- strict valid JSON output

Follow the requested JSON structure exactly.

Return only one valid JSON object.

Never return:
- Markdown
- code fences
- commentary before JSON
- commentary after JSON
- copyrighted lyrics
- copyrighted melodies
- existing cartoon characters
- unsafe content
""".strip()

    for model_name in MODEL_CANDIDATES:
        if not model_name:
            continue

        try:
            print(
                f"Trying Claude model: "
                f"{model_name}"
            )

            response = (
                client.messages.create(
                    model=model_name,
                    system=system_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    temperature=0.72,
                    max_tokens=20000,
                )
            )

            response_text = (
                extract_text_from_response(
                    response
                )
            )

            if not response_text:
                raise RuntimeError(
                    "Claude ne empty response diya."
                )

            story = clean_json(
                response_text
            )

            story = (
                validate_and_normalize_story(
                    story=story,
                    trend_data=trend_data,
                    selected_topic=selected_topic,
                    topic_category=topic_category,
                )
            )

            story["ai_provider"] = (
                "anthropic"
            )
            story["claude_model"] = (
                model_name
            )
            story["generated_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            print(
                f"Success with Claude model: "
                f"{model_name}"
            )

            return story

        except Exception as error:
            print(
                f"Claude model failed: "
                f"{model_name}"
            )
            print(error)

            errors.append(
                f"{model_name}: {error}"
            )

    raise RuntimeError(
        "Sab Claude models fail ho gaye: "
        + " | ".join(errors)
    )


def safe_story_name(
    story_id: str,
) -> str:
    safe_name = "".join(
        character
        if (
            character.isalnum()
            or character in "-_"
        )
        else "-"
        for character in story_id.lower()
    )

    safe_name = safe_name.strip(
        "-_"
    )

    return safe_name or "milo-rhyme"


def save_story(
    story: dict[str, Any],
) -> Path:
    output_dir = Path("output")

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    story_id = str(
        story.get(
            "story_id",
            "milo-rhyme",
        )
    )

    safe_name = safe_story_name(
        story_id
    )

    timestamp = datetime.now(
        timezone.utc
    ).strftime(
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
        "Milo & Friends Claude Nursery Brain "
        "start ho raha hai..."
    )

    trend_data = load_trend_data()

    selected = select_unique_topic(
        trend_data=trend_data,
    )

    selected_topic = selected["topic"]
    topic_category = selected["category"]

    story = generate_story(
        trend_data=trend_data,
        selected_topic=selected_topic,
        topic_category=topic_category,
    )

    output_path = save_story(
        story
    )

    reserve_topic(
        selected=selected,
        source=(
            "trend_suggestion"
            if trend_data.get(
                "trend_source_available",
                False,
            )
            else "topic_pool"
        ),
    )

    print("----------------------------------------")
    print(
        "Claude nursery-rhyme planning "
        "successfully generated."
    )
    print(
        f"Topic: "
        f"{story['selected_trend_topic']}"
    )
    print(
        f"Category: "
        f"{story['topic_category']}"
    )
    print(
        "Short song: "
        f"{story.get('song_title', 'Milo Song')}"
    )
    print(
        "Short duration: "
        f"{story['duration_seconds']} seconds"
    )
    print(
        "Long duration: "
        f"{story['long_video']['duration_seconds']} seconds"
    )
    print(
        "Long duration approximately: "
        "3 minutes 36 seconds"
    )
    print(
        f"Claude model: "
        f"{story.get('claude_model', 'unknown')}"
    )
    print(
        f"Saved file: {output_path}"
    )
    print("----------------------------------------")


if __name__ == "__main__":
    main()
