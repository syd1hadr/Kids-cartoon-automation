import math
from pathlib import Path

import bpy


PROJECT_ROOT = Path.cwd()
OUTPUT_DIR = PROJECT_ROOT / "assets" / "characters"
OUTPUT_FILE = OUTPUT_DIR / "milo.blend"


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for collection in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for item in list(collection):
            if item.users == 0:
                collection.remove(item)


def create_material(
    name: str,
    color: tuple[float, float, float, float],
    roughness: float = 0.55,
) -> bpy.types.Material:
    existing = bpy.data.materials.get(name)

    if existing:
        return existing

    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True

    principled = material.node_tree.nodes.get("Principled BSDF")

    if principled:
        principled.inputs["Base Color"].default_value = color
        principled.inputs["Roughness"].default_value = roughness

    return material


def apply_material(
    obj: bpy.types.Object,
    material: bpy.types.Material,
) -> None:
    if obj.data and hasattr(obj.data, "materials"):
        obj.data.materials.append(material)


def add_sphere(
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    material: bpy.types.Material,
    parent: bpy.types.Object,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32,
        ring_count=16,
        radius=1.0,
        location=location,
    )

    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale

    bpy.ops.object.transform_apply(
        location=False,
        rotation=False,
        scale=True,
    )

    apply_material(obj, material)
    bpy.ops.object.shade_smooth()

    obj.parent = parent

    return obj


def add_cone(
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    rotation: tuple[float, float, float],
    material: bpy.types.Material,
    parent: bpy.types.Object,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cone_add(
        vertices=32,
        radius1=1.0,
        radius2=0.05,
        depth=2.0,
        location=location,
        rotation=rotation,
    )

    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale

    bpy.ops.object.transform_apply(
        location=False,
        rotation=False,
        scale=True,
    )

    apply_material(obj, material)
    bpy.ops.object.shade_smooth()

    obj.parent = parent

    return obj


def create_root() -> bpy.types.Object:
    bpy.ops.object.empty_add(
        type="PLAIN_AXES",
        location=(0.0, 0.0, 0.0),
    )

    root = bpy.context.active_object
    root.name = "Milo_Root"

    return root


def create_milo() -> bpy.types.Object:
    root = create_root()

    orange = create_material(
        "Milo_Orange",
        (0.95, 0.32, 0.05, 1.0),
    )
    white = create_material(
        "Milo_White",
        (0.98, 0.98, 0.95, 1.0),
    )
    blue = create_material(
        "Milo_Blue_Shirt",
        (0.02, 0.25, 0.90, 1.0),
    )
    red = create_material(
        "Milo_Red_Shorts",
        (0.90, 0.04, 0.05, 1.0),
    )
    eye_blue = create_material(
        "Milo_Eye_Blue",
        (0.02, 0.42, 1.0, 1.0),
        roughness=0.20,
    )
    black = create_material(
        "Milo_Black",
        (0.01, 0.01, 0.01, 1.0),
        roughness=0.30,
    )
    pink = create_material(
        "Milo_Pink",
        (1.0, 0.40, 0.50, 1.0),
    )

    add_sphere(
        "Milo_Body",
        (0.0, 0.0, 1.90),
        (0.72, 0.58, 0.92),
        blue,
        root,
    )

    add_sphere(
        "Milo_Shorts",
        (0.0, 0.0, 1.22),
        (0.70, 0.58, 0.45),
        red,
        root,
    )

    add_sphere(
        "Milo_Head",
        (0.0, 0.0, 3.25),
        (1.02, 0.90, 0.95),
        orange,
        root,
    )

    add_sphere(
        "Milo_Muzzle",
        (0.0, -0.76, 3.05),
        (0.58, 0.28, 0.36),
        white,
        root,
    )

    for side, x_position in (
        ("Left", -0.38),
        ("Right", 0.38),
    ):
        add_sphere(
            f"Milo_{side}_Eye_White",
            (x_position, -0.78, 3.45),
            (0.28, 0.14, 0.36),
            white,
            root,
        )

        add_sphere(
            f"Milo_{side}_Iris",
            (x_position, -0.90, 3.45),
            (0.15, 0.07, 0.21),
            eye_blue,
            root,
        )

        add_sphere(
            f"Milo_{side}_Pupil",
            (x_position, -0.96, 3.45),
            (0.07, 0.035, 0.11),
            black,
            root,
        )

    add_sphere(
        "Milo_Nose",
        (0.0, -1.02, 3.12),
        (0.13, 0.07, 0.10),
        black,
        root,
    )

    add_cone(
        "Milo_Left_Ear",
        (-0.62, 0.0, 4.05),
        (0.36, 0.28, 0.48),
        (0.0, 0.0, math.radians(-12)),
        orange,
        root,
    )

    add_cone(
        "Milo_Right_Ear",
        (0.62, 0.0, 4.05),
        (0.36, 0.28, 0.48),
        (0.0, 0.0, math.radians(12)),
        orange,
        root,
    )

    add_cone(
        "Milo_Left_Inner_Ear",
        (-0.62, -0.18, 4.02),
        (0.19, 0.09, 0.29),
        (0.0, 0.0, math.radians(-12)),
        pink,
        root,
    )

    add_cone(
        "Milo_Right_Inner_Ear",
        (0.62, -0.18, 4.02),
        (0.19, 0.09, 0.29),
        (0.0, 0.0, math.radians(12)),
        pink,
        root,
    )

    for side, x_position in (
        ("Left", -0.82),
        ("Right", 0.82),
    ):
        add_sphere(
            f"Milo_{side}_Arm",
            (x_position, 0.0, 2.05),
            (0.23, 0.23, 0.65),
            orange,
            root,
        )

        add_sphere(
            f"Milo_{side}_Paw",
            (x_position, -0.02, 1.52),
            (0.27, 0.24, 0.27),
            white,
            root,
        )

    for side, x_position in (
        ("Left", -0.34),
        ("Right", 0.34),
    ):
        add_sphere(
            f"Milo_{side}_Leg",
            (x_position, 0.0, 0.70),
            (0.25, 0.27, 0.58),
            orange,
            root,
        )

        add_sphere(
            f"Milo_{side}_Shoe",
            (x_position, -0.18, 0.20),
            (0.37, 0.52, 0.21),
            white,
            root,
        )

    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.47,
        minor_radius=0.11,
        major_segments=32,
        minor_segments=12,
        location=(0.84, 0.34, 1.66),
        rotation=(
            math.radians(90),
            0.0,
            math.radians(25),
        ),
    )

    tail = bpy.context.active_object
    tail.name = "Milo_Tail"
    apply_material(tail, orange)
    tail.parent = root

    return root


def save_blender_file() -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    bpy.ops.wm.save_as_mainfile(
        filepath=str(OUTPUT_FILE.resolve()),
    )

    if not OUTPUT_FILE.exists():
        raise RuntimeError(
            f"milo.blend create nahi hui: {OUTPUT_FILE}"
        )

    if OUTPUT_FILE.stat().st_size == 0:
        raise RuntimeError(
            f"milo.blend empty hai: {OUTPUT_FILE}"
        )


def main() -> None:
    print("========================================")
    print("Milo Blender Character Generator Start")
    print("========================================")

    clear_scene()
    root = create_milo()

    if root.name not in bpy.data.objects:
        raise RuntimeError("Milo_Root create nahi hua.")

    save_blender_file()

    print(f"Root object: {root.name}")
    print(f"Saved Blender file: {OUTPUT_FILE}")
    print("Milo character generation complete.")


if __name__ == "__main__":
    main()
