import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLENDER_TOOLS_DIR = PROJECT_ROOT / "tools" / "blender"

BLENDER_SCRIPTS = [
    BLENDER_TOOLS_DIR / "generate_character.py",
    BLENDER_TOOLS_DIR / "animate_character.py",
    BLENDER_TOOLS_DIR / "render_scene.py",
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


def run_blender_script(
    blender_path: str,
    script_path: Path,
) -> None:
    validate_script(script_path)

    command = [
        blender_path,
        "--background",
        "--factory-startup",
        "--python",
        str(script_path),
    ]

    print("----------------------------------------")
    print(f"Running Blender script: {script_path.name}")
    print("Command:")
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
            f"{script_path.name} fail ho gayi. "
            f"Exit code: {completed.returncode}"
        )

    print(
        f"{script_path.name} successfully complete hui."
    )


def main() -> None:
    print("========================================")
    print("Milo & Friends Blender Runner Start")
    print("========================================")

    blender_path = find_blender()

    print(f"Blender executable: {blender_path}")
    print(f"Project root: {PROJECT_ROOT}")

    for script_path in BLENDER_SCRIPTS:
        run_blender_script(
            blender_path=blender_path,
            script_path=script_path,
        )

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
