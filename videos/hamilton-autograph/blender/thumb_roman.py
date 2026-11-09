"""Thumbnail hero shot from Bahrain: the halo big in the foreground on the front half of Grosjean's car (through the
torn barrier, the bent top rail over it), Grosjean vaulting the barrier behind it, the fire's glow around them.
Rendered on its own from shot 17's bake.

Run: blender -b --python blender/thumb_roman.py -- <out.png> <pct> [frame cx cy cz tx ty tz lens]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import look

V = Vector
argv = sys.argv[sys.argv.index("--") + 1:]
out, pct = os.path.abspath(argv[0]), int(argv[1])
f, cx, cy, cz, tx, ty, tz, lens = (float(a) for a in argv[2:10]) if len(argv) >= 10 else (1153, 8.7, -1.8, 1.05, 7.9, 3.0, 1.4, 30)
here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
shot = int(os.environ.get("SHOT", "17"))  # 16: the front half in the barrier, the bent rail over the halo, the fire
bpy.ops.wm.open_mainfile(filepath=os.path.join(here, "out", "blend6", f"s{shot:02d}.blend"))
sc = bpy.context.scene
sc.frame_set(int(f))
look.apply(sc, shot)
sc.frame_set(int(f))  # look.apply jumps to the middle of the shot to place its rim lights: back to our frame
sc.view_settings.view_transform = "Standard"  # keeps the halo racing red and the fire orange
try:
    sc.view_settings.look = "Medium High Contrast"
except TypeError:
    pass
sc.view_settings.exposure = -0.4

cam = sc.camera
cam.animation_data_clear()
cam.location = (cx, cy, cz)
cam.rotation_euler = (V((tx, ty, tz)) - V((cx, cy, cz))).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = lens
cam.data.dof.use_dof = True
halo = bpy.data.objects["gro_front"].matrix_world @ V((0, 0.12, 0.86))
cam.data.dof.focus_distance = (halo - V((cx, cy, cz))).length
cam.data.dof.aperture_fstop = 2.8

hot = bpy.data.materials.new("th_halo_red")
hot.use_nodes = True
pb = hot.node_tree.nodes["Principled BSDF"]
pb.inputs["Base Color"].default_value = (0.75, 0.01, 0.01, 1)
pb.inputs["Roughness"].default_value = 0.22
pb.inputs["Emission Color"].default_value = (1.0, 0.05, 0.02, 1)
pb.inputs["Emission Strength"].default_value = 0.3
for o in bpy.data.objects["gro_front"].children_recursive:
    if o.get("halo"):
        for sl in o.material_slots:
            sl.material = hot
for m in bpy.data.materials:  # flames orange, not blown-out white columns
    if m.name in ("fire", "fire2", "ember") or m.name.startswith(("fire.", "fire2.", "ember.")):
        b = m.node_tree.nodes.get("Principled BSDF") if m.node_tree else None
        if b:
            b.inputs["Emission Strength"].default_value *= 0.3
# a warm fire light raking across the halo and the barrier from behind the camera's left
ld = bpy.data.lights.new("th_fire", "POINT")
ld.energy, ld.color, ld.shadow_soft_size = 1800, (1.0, 0.45, 0.12), 0.6
lo = bpy.data.objects.new("th_fire", ld)
sc.collection.objects.link(lo)
lo.location = (7.2, -2.0, 1.4)

r = sc.render
r.resolution_x, r.resolution_y, r.resolution_percentage = 1080, 1920, pct
r.use_motion_blur = False
r.filepath = out
r.image_settings.file_format = "PNG"
r.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
for attr, val in (("taa_render_samples", 128 if pct == 100 else 16), ("use_raytracing", True), ("use_gtao", True)):
    if hasattr(sc.eevee, attr):
        try:
            setattr(sc.eevee, attr, val)
        except (TypeError, ValueError):
            pass
bpy.ops.render.render(write_still=True)
print("THUMB", out, flush=True)
