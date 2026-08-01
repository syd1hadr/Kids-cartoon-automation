import subprocess

SCRIPTS = [
    "generate_character.py",
    "animate_character.py",
    "render_scene.py",
    "export_assets.py",
]

print("Starting Blender automation...")

for script in SCRIPTS:
    print(f"Running {script}")
    subprocess.run(["python", script], check=True)

print("3D pipeline completed successfully.")
