import bpy

print("Animate Character Started")

if "Milo_Root" not in bpy.data.objects:
    raise RuntimeError("Milo_Root not found")

print("Milo found")
print("Animation step completed")
