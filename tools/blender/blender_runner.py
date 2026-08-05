import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLENDER_TOOLS_DIR = PROJECT_ROOT / "tools" / "blender"

GENERATE_SCRIPT = BLENDER_TOOLS_DIR / "generate_character.py"
ANIMATE_SCRIPT = BLENDER_TOOLS_DIR / "animate_character.py"
RENDER_SCRIPT = BLENDER_TOOLS_DIR / "render_scene.py"

MILO_BLEND_FILE = (
    PROJECT_ROOT
    / "assets"
    / "characters"
    / "milo.blend"
)

SHORT_MOTION_DIR = (
    PROJECT_ROOT
    / "output"
    / "motion"
    / "short"
)

EXPECTED_SHORT_CLIPS = [
    SHORT_MOTION_DIR / f"scene_{number:02d}.mp4"
    for number in range(1, 7)
]


def find_blender() -> str:
    blender_path = shutil.which("blender")

    if not blender_path:
        raise RuntimeError(
            "Blender executable nahi mila. "
            "Workflow mein Blender installation check karo."
        )

    return blender_path


def validate_script(script_path: Path) -> None:
    if not script_path.exists():
        raise RuntimeError(
            f"Blender script missing hai: {script_path}"
        )

    if script_path.stat().st_size == 0:
        raise RuntimeError(
            f"Blender script empty hai: {script_path}"
        )


def validate_file(
    file_path: Path,
    label: str,
) -> None:
    if not file_path.exists():
        raise RuntimeError(
            f"{label} create nahi hui: {file_path}"
        )

    if file_path.stat().st_size == 0:
        raise RuntimeError(
            f"{label} empty hai: {file_path}"
        )


def run_command(
    command: list[str],
    label: str,
) -> None:
    print("----------------------------------------")
    print(f"Running: {label}")
    print(" ".join(command))
    print("----------------------------------------")

    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=False,
        text=True,
    )

    if completed.returncode != 0:
        raise RuntimeError(
            f"{label} fail ho gaya. "
            f"Exit code: {completed.returncode}"
        )

    print(f"{label} successfully complete hua.")


def remove_old_motion_clips() -> None:
    SHORT_MOTION_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for clip_path in EXPECTED_SHORT_CLIPS:
        if clip_path.exists():
            clip_path.unlink()
            print(
                f"Old motion clip removed: {clip_path}"
            )


def generate_milo(
    blender_path: str,
) -> None:
    validate_script(GENERATE_SCRIPT)

    MILO_BLEND_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if MILO_BLEND_FILE.exists():
        MILO_BLEND_FILE.unlink()

    run_command(
        [
            blender_path,
            "--background",
            "--factory-startup",
            "--python",
            str(GENERATE_SCRIPT),
        ],
        "Generate Milo character",
    )

    validate_file(
        MILO_BLEND_FILE,
        "Milo Blender file",
    )

    print(
        "Milo model verified: "
        f"{MILO_BLEND_FILE}"
    )


def animate_milo(
    blender_path: str,
) -> None:
    validate_script(ANIMATE_SCRIPT)
    validate_file(
        MILO_BLEND_FILE,
        "Milo Blender file",
    )

    remove_old_motion_clips()

    run_command(
        [
            blender_path,
            "--background",
            str(MILO_BLEND_FILE),
            "--python",
            str(ANIMATE_SCRIPT),
        ],
        "Generate Milo animated Short clips",
    )

    verify_short_motion_clips()


def verify_short_motion_clips() -> None:
    print("----------------------------------------")
    print("Verifying Blender Short motion clips...")
    print("----------------------------------------")

    missing_files: list[str] = []
    empty_files: list[str] = []

    for clip_path in EXPECTED_SHORT_CLIPS:
        if not clip_path.exists():
            missing_files.append(
                str(clip_path)
            )
            continue

        if clip_path.stat().st_size == 0:
            empty_files.append(
                str(clip_path)
            )
            continue

        file_size_mb = (
            clip_path.stat().st_size
            / (1024 * 1024)
        )

        print(
            f"Verified: {clip_path} "
            f"({file_size_mb:.2f} MB)"
        )

    if missing_files:
        raise RuntimeError(
            "Ye Blender MP4 files missing hain: "
            + ", ".join(missing_files)
        )

    if empty_files:
        raise RuntimeError(
            "Ye Blender MP4 files empty hain: "
            + ", ".join(empty_files)
        )

    print(
        "All 6 Blender Short MP4 clips "
        "successfully verified."
    )


def validate_render_scene(
    blender_path: str,
) -> None:
    validate_script(RENDER_SCRIPT)
    validate_file(
        MILO_BLEND_FILE,
        "Milo Blender file",
    )

    run_command(
        [
            blender_path,
            "--background",
            str(MILO_BLEND_FILE),
            "--python",
            str(RENDER_SCRIPT),
        ],
        "Validate Milo render scene",
    )


def main() -> None:
    print("========================================")
    print("Milo & Friends Blender Runner Start")
    print("========================================")

    blender_path = find_blender()

    print(f"Blender executable: {blender_path}")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Motion output: {SHORT_MOTION_DIR}")

    generate_milo(
        blender_path=blender_path,
    )

    animate_milo(
        blender_path=blender_path,
    )

    validate_render_scene(
        blender_path=blender_path,
    )

    print("========================================")
    print("Blender pipeline successfully complete.")
    print("Milo model: ready")
    print("Short animated MP4 clips: 6 ready")
    print("========================================")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("----------------------------------------")
        print(
            f"BLENDER PIPELINE ERROR: {error}"
        )
        print("----------------------------------------")
        sys.exit(1)
