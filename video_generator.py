import json
from pathlib import Path

from moviepy import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    concatenate_videoclips,
)
from moviepy.video.fx import Crop, Resize


VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30


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


def create_vertical_clip(
    image_path: Path,
    duration: float,
) -> ImageClip:
    if not image_path.exists():
        raise RuntimeError(
            f"Image file nahi mili: {image_path}"
        )

    clip = ImageClip(str(image_path)).with_duration(duration)

    image_ratio = clip.w / clip.h
    target_ratio = VIDEO_WIDTH / VIDEO_HEIGHT

    if image_ratio > target_ratio:
        clip = clip.with_effects(
            [Resize(height=VIDEO_HEIGHT)]
        )

        clip = clip.with_effects(
            [
                Crop(
                    width=VIDEO_WIDTH,
                    height=VIDEO_HEIGHT,
                    x_center=clip.w / 2,
                    y_center=clip.h / 2,
                )
            ]
        )
    else:
        clip = clip.with_effects(
            [Resize(width=VIDEO_WIDTH)]
        )

        clip = clip.with_effects(
            [
                Crop(
                    width=VIDEO_WIDTH,
                    height=VIDEO_HEIGHT,
                    x_center=clip.w / 2,
                    y_center=clip.h / 2,
                )
            ]
        )

    return clip


def build_video(story: dict) -> Path:
    scenes = story.get("scenes", [])

    if not isinstance(scenes, list) or len(scenes) != 6:
        raise RuntimeError(
            "Video banane ke liye exactly 6 scenes chahiye."
        )

    narration_path = Path(
        story.get(
            "narration_file",
            "output/audio/narration.mp3",
        )
    )

    if not narration_path.exists():
        raise RuntimeError(
            f"Narration MP3 nahi mili: {narration_path}"
        )

    audio_clip = AudioFileClip(str(narration_path))

    scene_durations = []

    total_story_duration = sum(
        float(scene.get("duration_seconds", 4))
        for scene in scenes
    )

    if total_story_duration <= 0:
        raise RuntimeError(
            "Story duration valid nahi hai."
        )

    for scene in scenes:
        original_duration = float(
            scene.get("duration_seconds", 4)
        )

        adjusted_duration = (
            original_duration
            / total_story_duration
            * audio_clip.duration
        )

        scene_durations.append(adjusted_duration)

    video_clips = []

    for scene, duration in zip(
        scenes,
        scene_durations,
    ):
        scene_number = int(
            scene.get("scene_number", 0)
        )

        image_path = Path(
            scene.get(
                "image_file",
                f"output/images/scene_{scene_number:02d}.png",
            )
        )

        print(
            f"Scene {scene_number} video mein add ho rahi hai "
            f"for {duration:.2f} seconds..."
        )

        clip = create_vertical_clip(
            image_path=image_path,
            duration=duration,
        )

        video_clips.append(clip)

    final_video = concatenate_videoclips(
        video_clips,
        method="compose",
    )

    final_video = final_video.with_audio(audio_clip)

    output_dir = Path("output/video")
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = output_dir / "final_short.mp4"

    final_video.write_videofile(
        str(output_path),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=2,
    )

    final_video.close()
    audio_clip.close()

    for clip in video_clips:
        clip.close()

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
    print("Milo & Friends video generator start ho raha hai...")

    story_path = get_latest_story_file()
    print(f"Story file: {story_path}")

    story = load_story(story_path)

    video_path = build_video(story)

    story["video_file"] = str(video_path)
    story["video_width"] = VIDEO_WIDTH
    story["video_height"] = VIDEO_HEIGHT
    story["video_fps"] = FPS

    story_path.write_text(
        json.dumps(
            story,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("Video successfully generate ho gayi.")
    print(f"Final video: {video_path}")


if __name__ == "__main__":
    main()
