"""The thumbnail's hero shot, rendered on its own: Wolff on the launch stage with the chainsaw raised at the halo
(the end of shot 10), from a low angle in front of him, the red halo and the saw's bar in the foreground, stage
lighting (a warm key from above, a cool rim behind, the LED wall dimmed so he stands out), shallow focus.

Run: blender -b --python blender/thumb_shot.py -- <out.png> [cam_x cam_y cam_z lens]
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import look

V = Vector
argv = sys.argv[sys.argv.index("--") + 1:]
out = os.path.abspath(argv[0])
here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bpy.ops.wm.open_mainfile(filepath=os.path.join(here, "out", "blend6", "s10.blend"))
sc = bpy.context.scene
sc.frame_set(sc.frame_end - 4)  # aimed at the halo, after the follow-through
look.apply(sc, 10)
sc.view_settings.view_transform = "Standard"  # keeps the racing red red (AgX washes bright reds to salmon)
try:
    sc.view_settings.look = "Medium High Contrast"
except TypeError:
    pass
sc.view_settings.exposure = -1.25

W = V((1.30, 3.15, 0.48))
halo = bpy.data.objects["ln_car"].matrix_world @ V((0, 0.12, 0.86))
face = W + V((0, 0, 1.95))
d = (halo - W).normalized()
d.z = 0
d.normalize()
cam_xyz = V([float(v) for v in argv[1:4]]) if len(argv) >= 4 else halo + d * 1.25 + V((0.25, -0.05, -0.25))
lens = float(argv[4]) if len(argv) >= 5 else 26
cam = sc.camera
cam.animation_data_clear()
cam.location = cam_xyz
tgt = halo.lerp(face, 0.62)
cam.rotation_euler = (tgt - cam_xyz).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = lens
cam.data.dof.use_dof = True
cam.data.dof.focus_distance = (face - cam_xyz).length
cam.data.dof.aperture_fstop = 2.0

# stage lighting
def area(name, loc, target, energy, size, col):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy, ld.size, ld.color = energy, size, col
    ld.volume_factor = 0.3
    o = bpy.data.objects.new(name, ld)
    sc.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (V(target) - V(loc)).to_track_quat("-Z", "Y").to_euler()

area("th_key", face + V((-1.6, -1.8, 2.2)), face, 380, 2.0, (1.0, 0.86, 0.7))     # warm key, front-left above
area("th_rim", face + V((1.4, 1.8, 0.8)), face, 1400, 1.0, (0.55, 0.85, 1.0))     # cool rim from behind
area("th_halo", halo + V((-0.6, -1.0, 1.4)), halo, 260, 0.8, (1.0, 0.75, 0.6))    # a kick on the halo
for m in bpy.data.materials:  # the LED wall dimmed: a deep teal backdrop, not a white glare
    if "ledwall" in m.name and m.use_nodes:
        b = m.node_tree.nodes.get("Principled BSDF")
        if b:
            b.inputs["Emission Strength"].default_value = 0.6

hot = bpy.data.materials.new("th_halo_red")  # the halo is the hero: a deep glossy racing red with a faint glow
hot.use_nodes = True
pb = hot.node_tree.nodes["Principled BSDF"]
pb.inputs["Base Color"].default_value = (0.75, 0.01, 0.01, 1)
pb.inputs["Roughness"].default_value = 0.22
pb.inputs["Emission Color"].default_value = (1.0, 0.05, 0.02, 1)
pb.inputs["Emission Strength"].default_value = 0.35
for o in bpy.data.objects["ln_car"].children_recursive:
    if o.get("halo"):
        for sl in o.material_slots:
            sl.material = hot

r = sc.render
r.resolution_x, r.resolution_y, r.resolution_percentage = 1080, 1920, 100
r.use_motion_blur = False
r.filepath = out
r.image_settings.file_format = "PNG"
r.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
e = sc.eevee
for attr, val in (("taa_render_samples", 128), ("use_raytracing", True), ("use_gtao", True), ("shadow_ray_count", 3)):
    if hasattr(e, attr):
        try:
            setattr(e, attr, val)
        except (TypeError, ValueError):
            pass
bpy.ops.render.render(write_still=True)
print("THUMB", out, "cam", tuple(round(v, 2) for v in cam_xyz), "lens", lens, flush=True)
