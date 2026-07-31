import json
import os
from pathlib import Path
from typing import Any

from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    ImageClip,
    concatenate_videoclips,
)
from moviepy.audio.fx import AudioFadeIn, AudioFadeOut, AudioLoop, MultiplyVolume
from moviepy.video.fx import Crop, FadeIn, FadeOut, Resize


VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30

BACKGROUND_MUSIC_PATH = Path(
    os.getenv(
        "BACKGROUND_MUSIC_PATH",
        "assets/music/bg_music.mp3",
    )
)

VOICE_VOLUME = float(
    os.getenv("VOICE_VOLUME", "1.0")
)

MUSIC_VOLUME = float(
    os.getenv("MUSIC_VOLUME", "0.16")
)

SCENE_FADE_SECONDS = 0.18
AUDIO_FADE_SECONDS = 0.60
ENDING_HOLD_SECONDS = 0.60


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


def fit_image_to_vertical(
    clip: ImageClip,
) -> ImageClip:
    image_ratio = clip.w / clip.h
    target_ratio = VIDEO_WIDTH / VIDEO_HEIGHT

    if image_ratio > target_ratio:
        clip = clip.with_effects(
            [Resize(height=VIDEO_HEIGHT)]
        )
    else:
        clip = clip.with_effects(
            [Resize(width=VIDEO_WIDTH)]
        )

    return clip.with_effects(
        [
            Crop(
                width=VIDEO_WIDTH,
                height=VIDEO_HEIGHT,
                x_center=clip.w / 2,
                y_center=clip.h / 2,
            )
        ]
    )


def create_vertical_clip(
    image_path: Path,
    duration: float,
    is_first: bool,
    is_last: bool,
) -> ImageClip:
    if not image_path.exists():
        raise RuntimeError(
            f"Image file nahi mili: {image_path}"
        )

    clip = ImageClip(
        str(image_path)
    ).with_duration(duration)

    clip = fit_image_to_vertical(clip)

    effects = []

    if is_first:
        effects.append(
            FadeIn(SCENE_FADE_SECONDS)
        )

    if is_last:
        effects.append(
            FadeOut(SCENE_FADE_SECONDS)
        )

    if effects:
        clip = clip.with_effects(effects)

    return clip


def get_narration_path(
    story: dict[str, Any],
) -> Path:
    narration_path = Path(
        str(
            story.get(
                "narration_file",
                "output/audio/narration.mp3",
            )
        )
    )

    if not narration_path.exists():
        raise RuntimeError(
            f"Narration MP3 nahi mili: {narration_path}"
        )

    if narration_path.stat().st_size == 0:
        raise RuntimeError(
            "Narration MP3 empty hai."
        )

    return narration_path


def get_scene_durations(
    scenes: list[dict[str, Any]],
    narration_duration: float,
) -> list[float]:
    original_durations = [
        max(
            0.5,
            float(
                scene.get(
                    "duration_seconds",
                    4,
                )
            ),
        )
        for scene in scenes
    ]

    story_duration = sum(original_durations)

    if story_duration <= 0:
        raise RuntimeError(
            "Story duration valid nahi hai."
        )

    target_duration = max(
        story_duration,
        narration_duration + ENDING_HOLD_SECONDS,
    )

    durations = [
        duration
        / story_duration
        * target_duration
        for duration in original_durations
    ]

    return durations


def build_audio_mix(
    narration_clip: AudioFileClip,
    final_duration: float,
) -> tuple[Any, AudioFileClip | None]:
    narration = narration_clip.with_effects(
        [
            MultiplyVolume(VOICE_VOLUME),
            AudioFadeIn(0.15),
            AudioFadeOut(0.35),
        ]
    )

    audio_layers = [narration]
    music_source = None

    if BACKGROUND_MUSIC_PATH.exists():
        print(
            "Background music mil gayi: "
            f"{BACKGROUND_MUSIC_PATH}"
        )

        music_source = AudioFileClip(
            str(BACKGROUND_MUSIC_PATH)
        )

        music = music_source.with_effects(
            [
                AudioLoop(duration=final_duration),
                MultiplyVolume(MUSIC_VOLUME),
                AudioFadeIn(AUDIO_FADE_SECONDS),
                AudioFadeOut(AUDIO_FADE_SECONDS),
            ]
        )

        audio_layers.insert(0, music)
    else:
        print(
            "Warning: background music file nahi mili. "
            f"Expected path: {BACKGROUND_MUSIC_PATH}"
        )
        print(
            "Video voice ke saath banegi. "
            "Music file baad mein add kar sakte ho."
        )

    final_audio = CompositeAudioClip(
        audio_layers
    ).with_duration(final_duration)

    return final_audio, music_source


def close_clip_safely(clip: Any) -> None:
    if clip is None:
        return

    try:
        clip.close()
    except Exception:
        pass


def build_video(
    story: dict[str, Any],
) -> Path:
    raw_scenes = story.get("scenes", [])

    if (
        not isinstance(raw_scenes, list)
        or len(raw_scenes) != 6
    ):
        raise RuntimeError(
            "Video banane ke liye exactly 6 scenes chahiye."
        )

    scenes: list[dict[str, Any]] = []

    for index, raw_scene in enumerate(
        raw_scenes,
        start=1,
    ):
        if not isinstance(raw_scene, dict):
            raise RuntimeError(
                f"Scene {index} valid object nahi hai."
            )

        scenes.append(raw_scene)

    scenes.sort(
        key=lambda scene: int(
            scene.get("scene_number", 0)
        )
    )

    narration_path = get_narration_path(story)
    narration_clip = AudioFileClip(
        str(narration_path)
    )

    scene_durations = get_scene_durations(
        scenes=scenes,
        narration_duration=narration_clip.duration,
    )

    video_clips: list[ImageClip] = []
    final_video = None
    final_audio = None
    music_source = None

    try:
        for index, (scene, duration) in enumerate(
            zip(scenes, scene_durations)
        ):
            scene_number = int(
                scene.get(
                    "scene_number",
                    index + 1,
                )
            )

            image_path = Path(
                str(
                    scene.get(
                        "image_file",
                        (
                            "output/images/"
                            f"scene_{scene_number:02d}.png"
                        ),
                    )
                )
            )

            print(
                f"Scene {scene_number} add ho rahi hai "
                f"for {duration:.2f} seconds..."
            )

            clip = create_vertical_clip(
                image_path=image_path,
                duration=duration,
                is_first=index == 0,
                is_last=index == len(scenes) - 1,
            )

            video_clips.append(clip)

        final_video = concatenate_videoclips(
            video_clips,
            method="compose",
        )

        final_duration = final_video.duration

        final_audio, music_source = build_audio_mix(
            narration_clip=narration_clip,
            final_duration=final_duration,
        )

        final_video = final_video.with_audio(
            final_audio
        )

        output_dir = Path("output/video")
        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = (
            output_dir / "final_short.mp4"
        )

        final_video.write_videofile(
            str(output_path),
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=2,
            ffmpeg_params=[
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
            ],
        )

    finally:
        close_clip_safely(final_video)
        close_clip_safely(final_audio)
        close_clip_safely(music_source)
        close_clip_safely(narration_clip)

        for clip in video_clips:
            close_clip_safely(clip)

    if not output_path.exists():
        raise RuntimeError(
            "Final MP4 create nahi hui."
        )

    if output_path.stat().st_size == 0:
        raise RuntimeError(
            "Final MP4 empty hai."
        )

    return output_path


def main() -> None:
    print(
        "Milo & Friends upgraded video generator "
        "start ho raha hai..."
    )

    story_path = get_latest_story_file()
    print(f"Story file: {story_path}")

    story = load_story(story_path)
    video_path = build_video(story)

    story["video_file"] = str(video_path)
    story["video_width"] = VIDEO_WIDTH
    story["video_height"] = VIDEO_HEIGHT
    story["video_fps"] = FPS
    story["background_music_file"] = (
        str(BACKGROUND_MUSIC_PATH)
        if BACKGROUND_MUSIC_PATH.exists()
        else None
    )
    story["music_volume"] = MUSIC_VOLUME
    story["voice_volume"] = VOICE_VOLUME
    story["ending_style"] = (
        "soft fade with short final hold"
    )

    story_path.write_text(
        json.dumps(
            story,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        "Video successfully generate ho gayi."
    )
    print(f"Final video: {video_path}")


if __name__ == "__main__":
    main()
