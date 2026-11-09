"""Export the circuit (or chosen parts) to glTF binary for Three.js: web/circuit_<part>.glb

blender -b blend/circuit.blend --python export_gltf.py -- [--parts track,kerbs,barriers,pit] [--name core]

Repeated pieces export as EXT_mesh_gpu_instancing (Three.js GLTFLoader turns them into InstancedMesh); the pixel
textures export as nearest-filtered PNGs. Units are metres, glTF is Y-up (Blender Z-up is converted on export).
"""
import os, sys
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
parts = (argv[argv.index("--parts") + 1] if "--parts" in argv else
         "track,kerbs,ground,barriers,trackside,pit,stands,crowd,operations,paddock,venue,vegetation,vehicles").split(",")
name = argv[argv.index("--name") + 1] if "--name" in argv else "all"
keep = {f"circuit_{p}" for p in parts}
vl = bpy.context.view_layer
for lc in vl.layer_collection.children["circuit"].children:
    lc.exclude = lc.name not in keep
# point instancers must be realised as instances for the exporter: it reads evaluated GN instances
os.makedirs(os.path.join(HERE, "web"), exist_ok=True)
out = os.path.join(HERE, "web", f"circuit_{name}.glb")
kw = dict(filepath=out, export_format="GLB", use_visible=True, export_apply=True, export_cameras=False,
          export_lights=False, export_yup=True, export_image_format="AUTO")
props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
for k in ("export_gpu_instances", "export_gn_mesh"):
    if k in props:
        kw[k] = True
bpy.ops.export_scene.gltf(**kw)
print("EXPORTED", out, round(os.path.getsize(out) / 1e6, 1), "MB", flush=True)
