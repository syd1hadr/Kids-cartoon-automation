import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLENDER_TOOLS_DIR = PROJECT_ROOT / "tools" / "blender"

GENERATE_SCRIPT = BLENDER_TOOLS_DIR / "generate_character.py"
ANIMATE_SCRIPT = BLENDER_TOOLS_DIR / "animate_character.py"
RENDER_SCRIPT = BLENDER_TOOLS_DIR / "render_scene.py"

MILO_BLEND_FILE = PROJECT_ROOT / "assets" / "characters" / "milo.blend"


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


def generate_milo(
    blender_path: str,
) -> None:
    validate_script(GENERATE_SCRIPT)

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

    if not MILO_BLEND_FILE.exists():
        raise RuntimeError(
            f"Milo Blender file create nahi hui: {MILO_BLEND_FILE}"
        )

    if MILO_BLEND_FILE.stat().st_size == 0:
        raise RuntimeError(
            f"Milo Blender file empty hai: {MILO_BLEND_FILE}"
        )


def animate_milo(
    blender_path: str,
) -> None:
    validate_script(ANIMATE_SCRIPT)

    run_command(
        [
            blender_path,
            "--background",
            str(MILO_BLEND_FILE),
            "--python",
            str(ANIMATE_SCRIPT),
        ],
        "Validate and animate Milo",
    )


def render_milo(
    blender_path: str,
) -> None:
    validate_script(RENDER_SCRIPT)

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

    generate_milo(blender_path)
    animate_milo(blender_path)
    render_milo(blender_path)

    print("========================================")
    print("Blender pipeline successfully complete.")
    print("========================================")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("----------------------------------------")
        print(f"BLENDER PIPELINE ERROR: {error}")
        print("----------------------------------------")
        sys.exit(1)
