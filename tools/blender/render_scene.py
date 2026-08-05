import bpy

print("Render Scene Started")

if "Milo_Root" not in bpy.data.objects:
    raise RuntimeError("Milo_Root not found")

bpy.context.scene.render.engine = "BLENDER_EEVEE"

print("Render engine:", bpy.context.scene.render.engine)
print("Render validation completed")
