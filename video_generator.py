import json
from pathlib import Path
from typing import Any

from moviepy import (
    AudioFileClip,
    CompositeVideoClip,
    VideoFileClip,
    concatenate_videoclips,
)
from moviepy.audio.fx import AudioFadeIn, AudioFadeOut
from moviepy.video.fx import FadeIn, FadeOut, Loop


SHORT_WIDTH = 1080
SHORT_HEIGHT = 1920

LONG_WIDTH = 1920
LONG_HEIGHT = 1080

FPS = 30

SHORT_SCENE_COUNT = 6
LONG_SEGMENT_COUNT = 12

SHORT_FADE_SECONDS = 0.12
LONG_FADE_SECONDS = 0.18
AUDIO_FADE_SECONDS = 0.35


def get_latest_story_file() -> Path:
    output_dir = Path("output")

    if not output_dir.exists():
        raise RuntimeError(
            "output folder nahi mila."
        )

    story_files = [
        path
        for path in output_dir.glob("*.json")
        if path.name != "trend.json"
    ]

    if not story_files:
        raise RuntimeError(
            "Story JSON file nahi mili."
        )

    return max(
        story_files,
        key=lambda path: path.stat().st_mtime,
    )


def load_story(
    story_path: Path,
) -> dict[str, Any]:
    try:
        story = json.loads(
            story_path.read_text(
                encoding="utf-8",
            )
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


def close_clip_safely(
    clip: Any,
) -> None:
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
        long_data = story.get(
            "long_video",
            {},
        )

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

    audio_path = Path(
        str(raw_path)
    )

    if not audio_path.exists():
        raise RuntimeError(
            f"Audio file nahi mili: {audio_path}"
        )

    if audio_path.stat().st_size == 0:
        raise RuntimeError(
            f"Audio file empty hai: {audio_path}"
        )

    return audio_path


def get_audio_duration(
    audio_path: Path,
) -> float:
    audio_clip = AudioFileClip(
        str(audio_path)
    )

    try:
        duration = float(
            audio_clip.duration
        )
    finally:
        close_clip_safely(
            audio_clip
        )

    if duration <= 0:
        raise RuntimeError(
            f"Audio duration valid nahi hai: {audio_path}"
        )

    return duration


def proportional_durations(
    source_durations: list[float],
    target_duration: float,
) -> list[float]:
    clean_durations = [
        max(
            float(duration),
            0.5,
        )
        for duration in source_durations
    ]

    original_total = sum(
        clean_durations
    )

    if original_total <= 0:
        raise RuntimeError(
            "Scene durations valid nahi hain."
        )

    final_durations = [
        duration
        / original_total
        * target_duration
        for duration in clean_durations
    ]

    final_durations[-1] += (
        target_duration
        - sum(final_durations)
    )

    return final_durations


def cover_video(
    clip: VideoFileClip,
    *,
    target_width: int,
    target_height: int,
) -> CompositeVideoClip:
    source_ratio = (
        clip.w / clip.h
    )

    target_ratio = (
        target_width / target_height
    )

    if source_ratio > target_ratio:
        resized = clip.resized(
            height=target_height
        )
    else:
        resized = clip.resized(
            width=target_width
        )

    cropped = resized.cropped(
        x_center=resized.w / 2,
        y_center=resized.h / 2,
        width=target_width,
        height=target_height,
    )

    return CompositeVideoClip(
        [cropped.with_position("center")],
        size=(
            target_width,
            target_height,
        ),
    )


def prepare_motion_clip(
    motion_path: Path,
    *,
    duration: float,
    target_width: int,
    target_height: int,
    fade_seconds: float,
    label: str,
) -> CompositeVideoClip:
    if not motion_path.exists():
        raise RuntimeError(
            f"{label}: Veo MP4 nahi mili: {motion_path}"
        )

    if motion_path.stat().st_size == 0:
        raise RuntimeError(
            f"{label}: Veo MP4 empty hai: {motion_path}"
        )

    source = VideoFileClip(
        str(motion_path),
        audio=False,
    )

    source_duration = float(
        source.duration
    )

    if source_duration <= 0:
        close_clip_safely(source)

        raise RuntimeError(
            f"{label}: motion duration valid nahi hai."
        )

    if source_duration >= duration:
        timed = source.subclipped(
            0,
            duration,
        )
    else:
        timed = source.with_effects(
            [
                Loop(
                    duration=duration
                )
            ]
        ).with_duration(duration)

    timed = timed.without_audio()

    fitted = cover_video(
        timed,
        target_width=target_width,
        target_height=target_height,
    ).with_duration(duration)

    fade_duration = min(
        fade_seconds,
        duration / 5,
    )

    fitted = fitted.with_effects(
        [
            FadeIn(fade_duration),
            FadeOut(fade_duration),
        ]
    )

    print(
        f"{label}: animated MP4 use ho rahi hai "
        f"({duration:.2f}s)"
    )

    return fitted


def write_video(
    clips: list[CompositeVideoClip],
    *,
    audio_path: Path,
    output_path: Path,
) -> None:
    if not clips:
        raise RuntimeError(
            "Animated video banane ke liye clips nahi milin."
        )

    audio_clip = None
    combined_video = None
    final_video = None

    try:
        audio_clip = AudioFileClip(
            str(audio_path)
        ).with_effects(
            [
                AudioFadeIn(
                    AUDIO_FADE_SECONDS
                ),
                AudioFadeOut(
                    AUDIO_FADE_SECONDS
                ),
            ]
        )

        combined_video = concatenate_videoclips(
            clips,
            method="compose",
        )

        final_video = (
            combined_video
            .with_duration(
                audio_clip.duration
            )
            .with_audio(
                audio_clip
            )
        )

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
        close_clip_safely(
            final_video
        )
        close_clip_safely(
            combined_video
        )
        close_clip_safely(
            audio_clip
        )

        for clip in clips:
            close_clip_safely(
                clip
            )

    if (
        not output_path.exists()
        or output_path.stat().st_size == 0
    ):
        raise RuntimeError(
            f"Final MP4 create nahi hui: {output_path}"
        )


def get_short_motion_path(
    scene: dict[str, Any],
    scene_number: int,
) -> Path:
    raw_path = scene.get(
        "motion_file",
        (
            "output/motion/short/"
            f"scene_{scene_number:02d}.mp4"
        ),
    )

    return Path(
        str(raw_path)
    )


def get_long_motion_path(
    segment: dict[str, Any],
    segment_number: int,
) -> Path:
    raw_path = segment.get(
        "motion_file",
        (
            "output/motion/long/"
            f"segment_{segment_number:02d}.mp4"
        ),
    )

    return Path(
        str(raw_path)
    )


def build_short_video(
    story: dict[str, Any],
) -> Path:
    scenes = story.get(
        "scenes",
        [],
    )

    if (
        not isinstance(scenes, list)
        or len(scenes) != SHORT_SCENE_COUNT
    ):
        raise RuntimeError(
            "Short ke liye exactly 6 scenes chahiye."
        )

    ordered_scenes = sorted(
        scenes,
        key=lambda scene: int(
            scene.get(
                "scene_number",
                0,
            )
        ),
    )

    audio_path = get_audio_path(
        story,
        long_video=False,
    )

    audio_duration = get_audio_duration(
        audio_path
    )

    durations = proportional_durations(
        source_durations=[
            float(
                scene.get(
                    "duration_seconds",
                    4,
                )
            )
            for scene in ordered_scenes
        ],
        target_duration=audio_duration,
    )

    clips: list[CompositeVideoClip] = []

    for index, (
        scene,
        duration,
    ) in enumerate(
        zip(
            ordered_scenes,
            durations,
        )
    ):
        scene_number = int(
            scene.get(
                "scene_number",
                index + 1,
            )
        )

        motion_path = get_short_motion_path(
            scene,
            scene_number,
        )

        clips.append(
            prepare_motion_clip(
                motion_path,
                duration=duration,
                target_width=SHORT_WIDTH,
                target_height=SHORT_HEIGHT,
                fade_seconds=SHORT_FADE_SECONDS,
                label=(
                    f"Short scene {scene_number}"
                ),
            )
        )

    output_path = Path(
        "output/video/final_short.mp4"
    )

    write_video(
        clips,
        audio_path=audio_path,
        output_path=output_path,
    )

    return output_path


def long_motion_is_ready(
    story: dict[str, Any],
) -> bool:
    long_data = story.get(
        "long_video"
    )

    if not isinstance(
        long_data,
        dict,
    ):
        return False

    segments = long_data.get(
        "segments",
        [],
    )

    if (
        not isinstance(segments, list)
        or len(segments) != LONG_SEGMENT_COUNT
    ):
        return False

    for index, segment in enumerate(
        segments
    ):
        if not isinstance(
            segment,
            dict,
        ):
            return False

        segment_number = int(
            segment.get(
                "segment_number",
                index + 1,
            )
        )

        motion_path = get_long_motion_path(
            segment,
            segment_number,
        )

        if (
            not motion_path.exists()
            or motion_path.stat().st_size == 0
        ):
            return False

    return True


def build_long_video(
    story: dict[str, Any],
) -> Path | None:
    if not long_motion_is_ready(
        story
    ):
        print(
            "Long Veo motion clips abhi ready nahi hain. "
            "Photo-based long video bilkul generate nahi hogi."
        )

        return None

    long_data = story.get(
        "long_video"
    )

    if not isinstance(
        long_data,
        dict,
    ):
        raise RuntimeError(
            "long_video planning missing hai."
        )

    segments = long_data.get(
        "segments",
        [],
    )

    ordered_segments = sorted(
        segments,
        key=lambda segment: int(
            segment.get(
                "segment_number",
                0,
            )
        ),
    )

    audio_path = get_audio_path(
        story,
        long_video=True,
    )

    audio_duration = get_audio_duration(
        audio_path
    )

    durations = proportional_durations(
        source_durations=[
            float(
                segment.get(
                    "duration_seconds",
                    18,
                )
            )
            for segment in ordered_segments
        ],
        target_duration=audio_duration,
    )

    clips: list[CompositeVideoClip] = []

    for index, (
        segment,
        duration,
    ) in enumerate(
        zip(
            ordered_segments,
            durations,
        )
    ):
        segment_number = int(
            segment.get(
                "segment_number",
                index + 1,
            )
        )

        motion_path = get_long_motion_path(
            segment,
            segment_number,
        )

        clips.append(
            prepare_motion_clip(
                motion_path,
                duration=duration,
                target_width=LONG_WIDTH,
                target_height=LONG_HEIGHT,
                fade_seconds=LONG_FADE_SECONDS,
                label=(
                    f"Long segment {segment_number}"
                ),
            )
        )

    output_path = Path(
        "output/video/final_long.mp4"
    )

    write_video(
        clips,
        audio_path=audio_path,
        output_path=output_path,
    )

    return output_path


def update_story_metadata(
    story: dict[str, Any],
    story_path: Path,
    short_path: Path,
    long_path: Path | None,
) -> None:
    story["video_file"] = str(
        short_path
    )
    story["short_video_file"] = str(
        short_path
    )
    story["short_video_width"] = (
        SHORT_WIDTH
    )
    story["short_video_height"] = (
        SHORT_HEIGHT
    )
    story["short_video_fps"] = FPS
    story["short_video_source"] = (
        "veo_motion_clips"
    )

    long_data = story.get(
        "long_video"
    )

    if not isinstance(
        long_data,
        dict,
    ):
        long_data = {}
        story["long_video"] = long_data

    if long_path is not None:
        long_data["video_file"] = str(
            long_path
        )
        long_data["video_width"] = (
            LONG_WIDTH
        )
        long_data["video_height"] = (
            LONG_HEIGHT
        )
        long_data["video_fps"] = FPS
        long_data["video_source"] = (
            "veo_motion_clips"
        )

        story["video_generation_status"] = (
            "short_and_long_animated_complete"
        )
    else:
        long_data.pop(
            "video_file",
            None,
        )

        long_data["video_generation_status"] = (
            "waiting_for_veo_motion"
        )

        story["video_generation_status"] = (
            "short_animated_complete"
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
        "Milo & Friends real Veo animated "
        "video generator start..."
    )

    story_path = get_latest_story_file()

    print(
        f"Story file: {story_path}"
    )

    story = load_story(
        story_path
    )

    short_path = build_short_video(
        story
    )

    print(
        f"Animated Short ready: {short_path}"
    )

    long_path = build_long_video(
        story
    )

    if long_path is not None:
        print(
            f"Animated Long ready: {long_path}"
        )

    update_story_metadata(
        story=story,
        story_path=story_path,
        short_path=short_path,
        long_path=long_path,
    )

    print("----------------------------------------")
    print("PHOTO SLIDESHOW DISABLED")
    print(f"Animated Short: {short_path}")

    if long_path is None:
        print(
            "Long video skip hui kyun ke long Veo "
            "clips abhi generate nahi ki gayin."
        )
    else:
        print(
            f"Animated Long: {long_path}"
        )

    print("----------------------------------------")


if __name__ == "__main__":
    main()
