import json
from pathlib import Path
from typing import Any

from moviepy import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    concatenate_videoclips,
)
from moviepy.audio.fx import AudioFadeIn, AudioFadeOut
from moviepy.video.fx import FadeIn, FadeOut

SHORT_WIDTH = 1080
SHORT_HEIGHT = 1920
LONG_WIDTH = 1920
LONG_HEIGHT = 1080
FPS = 30

SHORT_FADE_SECONDS = 0.18
LONG_FADE_SECONDS = 0.35
AUDIO_FADE_SECONDS = 0.45

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

def close_clip_safely(clip: Any) -> None:
    if clip is None:
        return

    try:
        clip.close()
    except Exception:
        pass

def get_audio_path(
    story: dict[str, Any],
    *,
    long_video: bool,
) -> Path:
    if long_video:
        long_data = story.get("long_video", {})

        if not isinstance(long_data, dict):
            long_data = {}

        raw_path = long_data.get(
            "song_file",
            "output/audio/long_song.mp3",
        )
    else:
        raw_path = (
            story.get("short_song_file")
            or story.get("narration_file")
            or "output/audio/short_song.mp3"
        )

    audio_path = Path(str(raw_path))

    if not audio_path.exists():
        raise RuntimeError(
            f"Audio file nahi mili: {audio_path}"
        )

    if audio_path.stat().st_size == 0:
        raise RuntimeError(
            f"Audio file empty hai: {audio_path}"
        )

    return audio_path

def fit_cover_dimensions(
    image_width: int,
    image_height: int,
    target_width: int,
    target_height: int,
) -> tuple[int, int]:
    image_ratio = image_width / image_height
    target_ratio = target_width / target_height

    if image_ratio > target_ratio:
        resized_height = target_height
        resized_width = round(
            resized_height * image_ratio
        )
    else:
        resized_width = target_width
        resized_height = round(
            resized_width / image_ratio
        )

    return resized_width, resized_height

def make_motion_clip(
    image_path: Path,
    duration: float,
    target_width: int,
    target_height: int,
    index: int,
    fade_seconds: float,
) -> CompositeVideoClip:
    if not image_path.exists():
        raise RuntimeError(
            f"Image file nahi mili: {image_path}"
        )

    source = ImageClip(
        str(image_path)
    ).with_duration(duration)

    base_width, base_height = fit_cover_dimensions(
        image_width=source.w,
        image_height=source.h,
        target_width=target_width,
        target_height=target_height,
    )

    if index % 2 == 0:
        start_scale = 1.00
        end_scale = 1.10
    else:
        start_scale = 1.10
        end_scale = 1.00

    def scale_at_time(t: float) -> float:
        progress = min(
            max(t / max(duration, 0.001), 0.0),
            1.0,
        )

        return (
            start_scale
            + (end_scale - start_scale) * progress
        )

    animated = source.resized(
        lambda t: (
            round(base_width * scale_at_time(t)),
            round(base_height * scale_at_time(t)),
        )
    ).with_position("center")

    animated = animated.with_effects(
        [
            FadeIn(min(fade_seconds, duration / 4)),
            FadeOut(min(fade_seconds, duration / 4)),
        ]
    )

    return CompositeVideoClip(
        [animated],
        size=(target_width, target_height),
    ).with_duration(duration)

def proportional_durations(
    source_durations: list[float],
    target_duration: float,
) -> list[float]:
    clean_durations = [
        max(float(duration), 0.5)
        for duration in source_durations
    ]

    original_total = sum(clean_durations)

    if original_total <= 0:
        raise RuntimeError(
            "Scene durations valid nahi hain."
        )

    durations = [
        duration / original_total * target_duration
        for duration in clean_durations
    ]

    durations[-1] += target_duration - sum(durations)

    return durations

def write_video(
    clips: list[CompositeVideoClip],
    audio_path: Path,
    output_path: Path,
) -> None:
    if not clips:
        raise RuntimeError(
            "Video banane ke liye clips nahi milin."
        )

    audio_clip = None
    final_video = None

    try:
        audio_clip = AudioFileClip(
            str(audio_path)
        ).with_effects(
            [
                AudioFadeIn(AUDIO_FADE_SECONDS),
                AudioFadeOut(AUDIO_FADE_SECONDS),
            ]
        )

        final_video = concatenate_videoclips(
            clips,
            method="compose",
        )

        final_video = final_video.with_duration(
            audio_clip.duration
        ).with_audio(audio_clip)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
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
        close_clip_safely(audio_clip)

        for clip in clips:
            close_clip_safely(clip)

    if (
        not output_path.exists()
        or output_path.stat().st_size == 0
    ):
        raise RuntimeError(
            f"Final MP4 create nahi hui: {output_path}"
        )

def build_short_video(
    story: dict[str, Any],
) -> Path:
    scenes = story.get("scenes", [])

    if not isinstance(scenes, list) or len(scenes) != 6:
        raise RuntimeError(
            "Short ke liye exactly 6 scenes chahiye."
        )

    ordered_scenes = sorted(
        scenes,
        key=lambda scene: int(
            scene.get("scene_number", 0)
        ),
    )

    audio_path = get_audio_path(
        story,
        long_video=False,
    )

    audio_probe = AudioFileClip(str(audio_path))

    try:
        target_duration = audio_probe.duration
    finally:
        close_clip_safely(audio_probe)

    durations = proportional_durations(
        source_durations=[
            float(scene.get("duration_seconds", 4))
            for scene in ordered_scenes
        ],
        target_duration=target_duration,
    )

    clips: list[CompositeVideoClip] = []

    for index, (scene, duration) in enumerate(
        zip(ordered_scenes, durations)
    ):
        scene_number = int(
            scene.get("scene_number", index + 1)
        )

        image_path = Path(
            str(
                scene.get(
                    "image_file",
                    (
                        "output/images/short/"
                        f"scene_{scene_number:02d}.png"
                    ),
                )
            )
        )

        print(
            f"Short scene {scene_number}: "
            f"{duration:.2f} seconds"
        )

        clips.append(
            make_motion_clip(
                image_path=image_path,
                duration=duration,
                target_width=SHORT_WIDTH,
                target_height=SHORT_HEIGHT,
                index=index,
                fade_seconds=SHORT_FADE_SECONDS,
            )
        )

    output_path = Path(
        "output/video/final_short.mp4"
    )

    write_video(
        clips=clips,
        audio_path=audio_path,
        output_path=output_path,
    )

    return output_path

def build_long_video(
    story: dict[str, Any],
) -> Path:
    long_data = story.get("long_video")

    if not isinstance(long_data, dict):
        raise RuntimeError(
            "long_video planning missing hai."
        )

    segments = long_data.get("segments", [])

    if not isinstance(segments, list) or len(segments) != 12:
        raise RuntimeError(
            "Long video ke liye exactly 12 segments chahiye."
        )

    ordered_segments = sorted(
        segments,
        key=lambda segment: int(
            segment.get("segment_number", 0)
        ),
    )

    audio_path = get_audio_path(
        story,
        long_video=True,
    )

    audio_probe = AudioFileClip(str(audio_path))

    try:
        target_duration = audio_probe.duration
    finally:
        close_clip_safely(audio_probe)

    durations = proportional_durations(
        source_durations=[
            float(
                segment.get("duration_seconds", 18)
            )
            for segment in ordered_segments
        ],
        target_duration=target_duration,
    )

    clips: list[CompositeVideoClip] = []

    for index, (segment, duration) in enumerate(
        zip(ordered_segments, durations)
    ):
        segment_number = int(
            segment.get(
                "segment_number",
                index + 1,
            )
        )

        image_path = Path(
            str(
                segment.get(
                    "image_file",
                    (
                        "output/images/long/"
                        f"segment_{segment_number:02d}.png"
                    ),
                )
            )
        )

        print(
            f"Long segment {segment_number}: "
            f"{duration:.2f} seconds"
        )

        clips.append(
            make_motion_clip(
                image_path=image_path,
                duration=duration,
                target_width=LONG_WIDTH,
                target_height=LONG_HEIGHT,
                index=index,
                fade_seconds=LONG_FADE_SECONDS,
            )
        )

    output_path = Path(
        "output/video/final_long.mp4"
    )

    write_video(
        clips=clips,
        audio_path=audio_path,
        output_path=output_path,
    )

    return output_path

def update_story_metadata(
    story: dict[str, Any],
    story_path: Path,
    short_path: Path,
    long_path: Path,
) -> None:
    story["video_file"] = str(short_path)
    story["short_video_file"] = str(short_path)
    story["short_video_width"] = SHORT_WIDTH
    story["short_video_height"] = SHORT_HEIGHT
    story["short_video_fps"] = FPS

    long_data = story.get("long_video")

    if not isinstance(long_data, dict):
        long_data = {}
        story["long_video"] = long_data

    long_data["video_file"] = str(long_path)
    long_data["video_width"] = LONG_WIDTH
    long_data["video_height"] = LONG_HEIGHT
    long_data["video_fps"] = FPS

    story["video_generation_status"] = (
        "short_and_long_complete"
    )

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
        "Milo & Friends final Short and Long "
        "video generator start ho raha hai..."
    )

    story_path = get_latest_story_file()
    print(f"Story file: {story_path}")

    story = load_story(story_path)

    short_path = build_short_video(story)
    print(f"Short ready: {short_path}")

    long_path = build_long_video(story)
    print(f"Long video ready: {long_path}")

    update_story_metadata(
        story=story,
        story_path=story_path,
        short_path=short_path,
        long_path=long_path,
    )

    print("----------------------------------------")
    print("Short aur Long dono MP4 ready hain.")
    print(f"Short: {short_path}")
    print(f"Long: {long_path}")
    print("----------------------------------------")

if __name__ == "__main__":
    main()
