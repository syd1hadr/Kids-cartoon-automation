import math
from pathlib import Path

import bpy
import mathutils


PROJECT_ROOT = Path.cwd()
OUTPUT_DIR = PROJECT_ROOT / "output" / "motion" / "short"

FPS = 24
WIDTH = 360
HEIGHT = 640

SCENE_DURATIONS = [4, 4, 4, 4, 4, 5]


def require_milo() -> bpy.types.Object:
    root = bpy.data.objects.get("Milo_Root")

    if root is None:
        raise RuntimeError("Milo_Root not found")

    return root


def remove_object_by_name(name: str) -> None:
    obj = bpy.data.objects.get(name)

    if obj is not None:
        bpy.data.objects.remove(
            obj,
            do_unlink=True,
        )


def remove_existing_scene_helpers() -> None:
    helper_names = [
        "AnimationCamera",
        "AnimationFloor",
        "KeyLight",
        "FillLight",
        "BackLight",
    ]

    for name in helper_names:
        remove_object_by_name(name)


def create_material(
    name: str,
    color: tuple[float, float, float, float],
) -> bpy.types.Material:
    material = bpy.data.materials.get(name)

    if material is None:
        material = bpy.data.materials.new(
            name=name,
        )

    material.diffuse_color = color
    material.use_nodes = True

    if material.node_tree is not None:
        principled = material.node_tree.nodes.get(
            "Principled BSDF"
        )

        if principled is not None:
            principled.inputs[
                "Base Color"
            ].default_value = color

            principled.inputs[
                "Roughness"
            ].default_value = 0.65

    return material


def setup_world() -> None:
    world = bpy.context.scene.world

    if world is None:
        world = bpy.data.worlds.new(
            "MiloAnimationWorld"
        )
        bpy.context.scene.world = world

    world.use_nodes = True

    if world.node_tree is None:
        return

    background = world.node_tree.nodes.get(
        "Background"
    )

    if background is not None:
        background.inputs[
            "Color"
        ].default_value = (
            0.10,
            0.22,
            0.42,
            1.0,
        )

        background.inputs[
            "Strength"
        ].default_value = 0.7


def setup_floor() -> None:
    floor_material = create_material(
        "AnimationFloorMaterial",
        (0.18, 0.62, 0.34, 1.0),
    )

    bpy.ops.mesh.primitive_plane_add(
        size=30,
        location=(0.0, 0.0, -0.05),
    )

    floor = bpy.context.active_object

    if floor is None:
        raise RuntimeError(
            "Animation floor create nahi hua."
        )

    floor.name = "AnimationFloor"
    floor.data.materials.append(
        floor_material
    )


def point_object_at(
    obj: bpy.types.Object,
    target: tuple[float, float, float],
) -> None:
    target_vector = mathutils.Vector(
        target
    )

    direction = (
        target_vector - obj.location
    )

    obj.rotation_euler = (
        direction.to_track_quat(
            "-Z",
            "Y",
        ).to_euler()
    )


def setup_camera() -> bpy.types.Object:
    bpy.ops.object.camera_add(
        location=(0.0, -11.5, 2.45),
    )

    camera = bpy.context.active_object

    if camera is None:
        raise RuntimeError(
            "Animation camera create nahi hua."
        )

    camera.name = "AnimationCamera"
    camera.data.lens = 52

    bpy.context.scene.camera = camera

    point_object_at(
        camera,
        (0.0, 0.0, 2.15),
    )

    return camera


def add_area_light(
    name: str,
    location: tuple[float, float, float],
    energy: float,
    size: float,
) -> None:
    bpy.ops.object.light_add(
        type="AREA",
        location=location,
    )

    light = bpy.context.active_object

    if light is None:
        raise RuntimeError(
            f"{name} create nahi hui."
        )

    light.name = name
    light.data.energy = energy
    light.data.shape = "DISK"
    light.data.size = size

    point_object_at(
        light,
        (0.0, 0.0, 2.0),
    )


def setup_lighting() -> None:
    add_area_light(
        name="KeyLight",
        location=(-4.0, -5.0, 7.0),
        energy=900,
        size=5.0,
    )

    add_area_light(
        name="FillLight",
        location=(4.0, -3.0, 5.0),
        energy=600,
        size=4.0,
    )

    add_area_light(
        name="BackLight",
        location=(0.0, 4.0, 6.0),
        energy=750,
        size=3.5,
    )


def select_render_engine() -> str:
    scene = bpy.context.scene

    engine_candidates = [
        "BLENDER_EEVEE_NEXT",
        "BLENDER_EEVEE",
        "CYCLES",
    ]

    errors: list[str] = []

    for engine_name in engine_candidates:
        try:
            scene.render.engine = engine_name

            if scene.render.engine == engine_name:
                print(
                    f"Selected render engine: "
                    f"{engine_name}"
                )

                return engine_name

        except Exception as error:
            errors.append(
                f"{engine_name}: {error}"
            )

    raise RuntimeError(
        "Koi compatible render engine select nahi hua: "
        + " | ".join(errors)
    )


def configure_render() -> None:
    scene = bpy.context.scene

    selected_engine = select_render_engine()

    if selected_engine == "BLENDER_EEVEE_NEXT":
        if hasattr(scene, "eevee"):
            try:
                scene.eevee.taa_render_samples = 16
            except Exception:
                pass

    if selected_engine == "CYCLES":
        scene.cycles.samples = 16

        try:
            scene.cycles.device = "CPU"
        except Exception:
            pass

    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100

    scene.render.image_settings.file_format = (
        "FFMPEG"
    )

    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = (
        "MEDIUM"
    )

    scene.render.ffmpeg.ffmpeg_preset = (
        "GOOD"
    )

    scene.render.fps = FPS
    scene.render.fps_base = 1.0

    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    scene.render.use_overwrite = True
    scene.render.use_placeholder = False

    scene.render.image_settings.color_mode = (
        "RGB"
    )

    try:
        scene.render.ffmpeg.audio_codec = "NONE"
    except Exception:
        pass

    print(
        f"Render size: {WIDTH}x{HEIGHT}"
    )
    print(f"Render FPS: {FPS}")


def clear_animation(
    root: bpy.types.Object,
) -> None:
    root.animation_data_clear()

    root.location = (
        0.0,
        0.0,
        0.0,
    )

    root.rotation_euler = (
        0.0,
        0.0,
        0.0,
    )

    root.scale = (
        1.0,
        1.0,
        1.0,
    )


def insert_transform_keyframe(
    root: bpy.types.Object,
    frame: int,
    location: tuple[float, float, float],
    rotation: tuple[float, float, float],
    scale: tuple[float, float, float],
) -> None:
    root.location = location
    root.rotation_euler = rotation
    root.scale = scale

    root.keyframe_insert(
        data_path="location",
        frame=frame,
    )

    root.keyframe_insert(
        data_path="rotation_euler",
        frame=frame,
    )

    root.keyframe_insert(
        data_path="scale",
        frame=frame,
    )


def set_smooth_interpolation(
    root: bpy.types.Object,
) -> None:
    if root.animation_data is None:
        return

    action = root.animation_data.action

    if action is None:
        return

    for fcurve in action.fcurves:
        for point in fcurve.keyframe_points:
            point.interpolation = "BEZIER"


def make_scene_animation(
    root: bpy.types.Object,
    scene_number: int,
    duration_seconds: int,
) -> int:
    clear_animation(root)

    total_frames = duration_seconds * FPS
    middle_frame = max(
        2,
        total_frames // 2,
    )

    if scene_number == 1:
        insert_transform_keyframe(
            root=root,
            frame=1,
            location=(-0.30, 0.0, 0.0),
            rotation=(
                0.0,
                0.0,
                math.radians(-7),
            ),
            scale=(0.96, 0.96, 0.96),
        )

        insert_transform_keyframe(
            root=root,
            frame=middle_frame,
            location=(0.20, 0.0, 0.18),
            rotation=(
                0.0,
                0.0,
                math.radians(8),
            ),
            scale=(1.05, 1.05, 1.05),
        )

        insert_transform_keyframe(
            root=root,
            frame=total_frames,
            location=(0.0, 0.0, 0.0),
            rotation=(0.0, 0.0, 0.0),
            scale=(1.0, 1.0, 1.0),
        )

    elif scene_number == 2:
        insert_transform_keyframe(
            root=root,
            frame=1,
            location=(0.0, 0.0, 0.0),
            rotation=(
                0.0,
                0.0,
                math.radians(-12),
            ),
            scale=(1.0, 1.0, 1.0),
        )

        insert_transform_keyframe(
            root=root,
            frame=middle_frame,
            location=(0.0, 0.0, 0.12),
            rotation=(
                0.0,
                0.0,
                math.radians(12),
            ),
            scale=(1.03, 1.03, 1.03),
        )

        insert_transform_keyframe(
            root=root,
            frame=total_frames,
            location=(0.0, 0.0, 0.0),
            rotation=(
                0.0,
                0.0,
                math.radians(-12),
            ),
            scale=(1.0, 1.0, 1.0),
        )

    elif scene_number == 3:
        insert_transform_keyframe(
            root=root,
            frame=1,
            location=(-0.55, 0.0, 0.0),
            rotation=(0.0, 0.0, 0.0),
            scale=(1.0, 1.0, 1.0),
        )

        insert_transform_keyframe(
            root=root,
            frame=middle_frame,
            location=(0.55, 0.0, 0.10),
            rotation=(
                0.0,
                0.0,
                math.radians(9),
            ),
            scale=(1.0, 1.0, 1.0),
        )

        insert_transform_keyframe(
            root=root,
            frame=total_frames,
            location=(-0.55, 0.0, 0.0),
            rotation=(
                0.0,
                0.0,
                math.radians(-9),
            ),
            scale=(1.0, 1.0, 1.0),
        )

    elif scene_number == 4:
        insert_transform_keyframe(
            root=root,
            frame=1,
            location=(0.0, 0.0, 0.0),
            rotation=(0.0, 0.0, 0.0),
            scale=(1.0, 1.0, 1.0),
        )

        insert_transform_keyframe(
            root=root,
            frame=middle_frame,
            location=(0.0, 0.0, 0.48),
            rotation=(
                math.radians(5),
                0.0,
                math.radians(10),
            ),
            scale=(1.03, 1.03, 1.03),
        )

        insert_transform_keyframe(
            root=root,
            frame=total_frames,
            location=(0.0, 0.0, 0.0),
            rotation=(0.0, 0.0, 0.0),
            scale=(1.0, 1.0, 1.0),
        )

    elif scene_number == 5:
        insert_transform_keyframe(
            root=root,
            frame=1,
            location=(0.0, 0.0, 0.0),
            rotation=(
                0.0,
                math.radians(-10),
                math.radians(-8),
            ),
            scale=(1.0, 1.0, 1.0),
        )

        insert_transform_keyframe(
            root=root,
            frame=middle_frame,
            location=(0.20, 0.0, 0.15),
            rotation=(
                0.0,
                math.radians(10),
                math.radians(8),
            ),
            scale=(1.04, 1.04, 1.04),
        )

        insert_transform_keyframe(
            root=root,
            frame=total_frames,
            location=(0.0, 0.0, 0.0),
            rotation=(
                0.0,
                math.radians(-10),
                math.radians(-8),
            ),
            scale=(1.0, 1.0, 1.0),
        )

    else:
        insert_transform_keyframe(
            root=root,
            frame=1,
            location=(0.0, 0.0, 0.0),
            rotation=(
                0.0,
                0.0,
                math.radians(-10),
            ),
            scale=(0.96, 0.96, 0.96),
        )

        insert_transform_keyframe(
            root=root,
            frame=middle_frame,
            location=(0.0, 0.0, 0.32),
            rotation=(
                0.0,
                0.0,
                math.radians(10),
            ),
            scale=(1.08, 1.08, 1.08),
        )

        insert_transform_keyframe(
            root=root,
            frame=total_frames,
            location=(0.0, 0.0, 0.0),
            rotation=(0.0, 0.0, 0.0),
            scale=(1.0, 1.0, 1.0),
        )

    set_smooth_interpolation(root)

    return total_frames


def render_scene_clip(
    root: bpy.types.Object,
    scene_number: int,
    duration_seconds: int,
) -> Path:
    total_frames = make_scene_animation(
        root=root,
        scene_number=scene_number,
        duration_seconds=duration_seconds,
    )

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = total_frames
    scene.frame_set(1)

    output_path = OUTPUT_DIR / (
        f"scene_{scene_number:02d}.mp4"
    )

    if output_path.exists():
        output_path.unlink()

    scene.render.filepath = str(
        output_path.resolve()
    )

    print("----------------------------------------")
    print(
        f"Rendering Short scene {scene_number}"
    )
    print(
        f"Duration: {duration_seconds} seconds"
    )
    print(f"Frames: {total_frames}")
    print(f"Output: {output_path}")
    print("----------------------------------------")

    bpy.ops.render.render(
        animation=True,
    )

    if not output_path.exists():
        raise RuntimeError(
            f"Scene MP4 create nahi hui: {output_path}"
        )

    if output_path.stat().st_size == 0:
        raise RuntimeError(
            f"Scene MP4 empty hai: {output_path}"
        )

    size_mb = (
        output_path.stat().st_size
        / (1024 * 1024)
    )

    print(
        f"Scene {scene_number} ready: "
        f"{size_mb:.2f} MB"
    )

    return output_path


def purge_unused_data() -> None:
    try:
        bpy.ops.outliner.orphans_purge(
            do_recursive=True,
        )
    except Exception:
        pass


def main() -> None:
    print("========================================")
    print("Milo Blender Animation Generator Start")
    print("========================================")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    root = require_milo()

    remove_existing_scene_helpers()
    setup_world()
    setup_floor()
    setup_camera()
    setup_lighting()
    configure_render()

    generated_files: list[Path] = []

    for scene_number, duration in enumerate(
        SCENE_DURATIONS,
        start=1,
    ):
        output_path = render_scene_clip(
            root=root,
            scene_number=scene_number,
            duration_seconds=duration,
        )

        generated_files.append(
            output_path
        )

        purge_unused_data()

    if bpy.data.filepath:
        bpy.ops.wm.save_as_mainfile(
            filepath=bpy.data.filepath,
        )

    print("========================================")
    print("Blender Short animations complete")
    print(
        f"Generated clips: "
        f"{len(generated_files)}"
    )

    for file_path in generated_files:
        print(file_path)

    print("========================================")


if __name__ == "__main__":
    main()
