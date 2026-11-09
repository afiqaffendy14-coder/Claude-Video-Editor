"""Blender building blocks for the circuit: pixel materials, a box/quad mesh builder, and instancing.

- Materials are one small pixel image each (16 texels = 1 m on every face, closest-pixel sampling), so the whole
  world shares one pixel size, and they export to glTF/Three.js unchanged (image + KHR_texture_transform).
- MeshBuilder writes boxes and quads with UVs in metres (u along the face, v up), flat-shaded.
- scatter() places a prototype (or one of several variants) on many points with one Geometry Nodes modifier:
  one object per placement group, instanced geometry, editable points (move a point = move that piece).
"""
import math
import os
import zlib
import numpy as np
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
TEX_DIR = os.path.join(HERE, "textures")
PPM = 16   # texels per metre


# ---------------------------------------------------------------- colour helpers
def hexrgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


def srgb_to_lin(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


# ---------------------------------------------------------------- pixel patterns (H x W x 3, sRGB 0..1)
def pattern(kind, col, size=16, seed=0, col2=None):
    rng = np.random.default_rng(seed)
    c = hexrgb(col) if isinstance(col, str) else np.asarray(col, np.float32)
    c2 = (hexrgb(col2) if isinstance(col2, str) else np.asarray(col2, np.float32)) if col2 is not None else None
    n = rng.random((size, size, 1)).astype(np.float32)
    img = np.broadcast_to(c, (size, size, 3)).copy()
    if kind == "flat":
        img *= 0.96 + 0.04 * n
    elif kind == "noise":
        img *= 0.9 + 0.1 * n
    elif kind == "asphalt":
        img *= 0.86 + 0.14 * n
        img[(n[..., 0] > 0.93)] *= 1.35
    elif kind == "grass":
        img *= 0.82 + 0.22 * n
        img[n[..., 0] > 0.9] *= np.array([0.85, 1.12, 0.8], np.float32)
    elif kind == "gravel":
        img *= 0.75 + 0.35 * n
        img[n[..., 0] < 0.12] = img[n[..., 0] < 0.12] * 0.6
    elif kind == "concrete":
        img *= 0.92 + 0.08 * n
        img[0, :] *= 0.86
        img[:, 0] *= 0.86
    elif kind == "tile":      # paving / slabs: 4 px slabs
        img *= 0.9 + 0.1 * n
        img[::4, :] *= 0.85
        img[:, ::4] *= 0.85
    elif kind == "dirtside":  # hill block side: grass cap on dirt (top rows = top of the block)
        img = np.broadcast_to(c2, (size, size, 3)).copy() * (0.8 + 0.25 * n)
        cap = 3 + (rng.random(size) < 0.4).astype(int)
        for x in range(size):
            img[size - cap[x]:, x] = c * (0.85 + 0.2 * n[size - cap[x]:, x])
    elif kind == "metal":
        img *= 0.88 + 0.12 * n
        img[::8, :] *= 0.9
    elif kind == "glass":
        g = np.linspace(1.15, 0.85, size, dtype=np.float32)[:, None, None]
        img = img * g * (0.97 + 0.03 * n)
        for k in range(3):
            img[np.arange(size), (np.arange(size) + k + 3) % size] *= 1.25
    elif kind == "window":    # facade: 1 m bays, a 12 x 10 px window per bay
        img = np.broadcast_to(c, (size, size, 3)).copy() * (0.93 + 0.07 * n)
        win = c2 if c2 is not None else np.array([0.2, 0.28, 0.36], np.float32)
        img[3:13, 2:14] = win * (0.9 + 0.2 * n[3:13, 2:14])
        img[11:13, 2:14] *= 1.3
    elif kind == "stripes":   # vertical stripes of col / col2, 4 px
        img[:, (np.arange(size) // 4) % 2 == 1] = c2
        img *= 0.94 + 0.06 * n
    elif kind == "check":
        m = ((np.arange(size)[:, None] // 4 + np.arange(size)[None, :] // 4) % 2) == 1
        img[m] = c2
    elif kind == "mesh":      # wire fence: thin wires every 4 px (alpha via the material)
        img *= 0.95 + 0.05 * n
    elif kind == "tread":
        img *= 0.85 + 0.15 * n
        img[::3, :] *= 0.7
    elif kind == "leaves":
        img *= 0.7 + 0.45 * n
        img[n[..., 0] > 0.92] = img[n[..., 0] > 0.92] * np.array([1.2, 1.25, 0.9], np.float32)
    elif kind == "bark":
        img *= 0.8 + 0.25 * n
        img[:, ::3] *= 0.85
    elif kind == "water":
        img *= 0.92 + 0.12 * n
        img[n[..., 0] > 0.94] = np.minimum(img[n[..., 0] > 0.94] * 1.6, 1)
    elif kind == "led":       # LED panel: visible diodes
        img *= 0.75 + 0.25 * n
        img[1::2, :] *= 0.55
        img[:, 1::2] *= 0.55
    else:
        raise ValueError(kind)
    return np.clip(img, 0, 1)


def wire_alpha(size=16):
    a = np.zeros((size, size), np.float32)
    a[::4, :] = 1
    a[:, ::4] = 1
    # diamond mesh look: diagonals
    for k in range(size):
        a[k, k % size] = 1
        a[k, (size - 1 - k) % size] = 1
    return a


def save_image(name, rgb, alpha=None):
    """Make (or replace) a packed Blender image from an sRGB array (rows top -> bottom) and save it as PNG."""
    h, w, _ = rgb.shape
    img = bpy.data.images.get(name)
    if img and (img.size[0] != w or img.size[1] != h):
        bpy.data.images.remove(img)
        img = None
    if img is None:
        img = bpy.data.images.new(name, w, h, alpha=alpha is not None)
    a = np.ones((h, w, 1), np.float32) if alpha is None else alpha[..., None].astype(np.float32)
    px = np.concatenate([rgb.astype(np.float32), a], 2)[::-1]       # Blender rows are bottom -> top
    img.pixels.foreach_set(px.ravel())
    os.makedirs(TEX_DIR, exist_ok=True)
    img.filepath_raw = os.path.join(TEX_DIR, name + ".png")
    img.file_format = "PNG"
    img.save()
    img.pack()
    return img


# ---------------------------------------------------------------- materials
MATS = {}


def material(name, col="#808080", kind="noise", rough=0.8, metal=0.0, emit=0.0, seed=None, col2=None, alpha=None,
             image=None, scale=1.0, spec=0.5, coat=0.0):
    """One pixel material. `image` (an sRGB array) overrides the pattern; `scale` = metres per image tile.
    emit > 0 makes it glow with its own colour (lamps, LED panels, screens)."""
    key = "c_" + name
    if key in MATS:
        return MATS[key]
    m = bpy.data.materials.get(key) or bpy.data.materials.new(key)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs[0])
    rgb = image if image is not None else pattern(kind, col, 16, seed if seed is not None else zlib.crc32(name.encode()) % 9973,
                                                   col2)
    img = save_image("tx_" + name, rgb, alpha)
    uv = nt.nodes.new("ShaderNodeUVMap")
    mp = nt.nodes.new("ShaderNodeMapping")
    s = 1.0 / scale if not isinstance(scale, tuple) else (1 / scale[0], 1 / scale[1])
    mp.inputs["Scale"].default_value = (s, s, 1) if not isinstance(s, tuple) else (s[0], s[1], 1)
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = img
    tx.interpolation = "Closest"
    nt.links.new(uv.outputs[0], mp.inputs[0])
    nt.links.new(mp.outputs[0], tx.inputs[0])
    nt.links.new(tx.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = spec
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    if emit:
        nt.links.new(tx.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = emit
        m["emit_base"] = emit
    if alpha is not None:
        nt.links.new(tx.outputs["Alpha"], b.inputs["Alpha"])
        m.surface_render_method = "DITHERED"
        if hasattr(m, "blend_method"):
            m.blend_method = "HASHED"
    m.diffuse_color = (*srgb_to_lin(rgb.reshape(-1, 3).mean(0)), 1.0)   # solid view / thumbnails
    MATS[key] = m
    return m


def image_material(name, rgb, rough=0.6, emit=0.0, metal=0.0, alpha=None):
    """A picture (sign, sponsor board, screen) mapped once across a face whose UVs are 0..1 (uv='fit')."""
    return material(name, image=rgb, rough=rough, emit=emit, metal=metal, alpha=alpha, scale=1.0)


# ---------------------------------------------------------------- pixel font (3x5, from the car library) + text
F35 = {
    "A": [".#.", "#.#", "###", "#.#", "#.#"], "B": ["##.", "#.#", "##.", "#.#", "##."],
    "C": [".##", "#..", "#..", "#..", ".##"], "D": ["##.", "#.#", "#.#", "#.#", "##."],
    "E": ["###", "#..", "##.", "#..", "###"], "F": ["###", "#..", "##.", "#..", "#.."],
    "G": [".##", "#..", "#.#", "#.#", ".##"], "H": ["#.#", "#.#", "###", "#.#", "#.#"],
    "I": ["###", ".#.", ".#.", ".#.", "###"], "J": ["..#", "..#", "..#", "#.#", ".#."],
    "K": ["#.#", "#.#", "##.", "#.#", "#.#"], "L": ["#..", "#..", "#..", "#..", "###"],
    "M": ["#.#", "###", "###", "#.#", "#.#"], "N": ["##.", "#.#", "#.#", "#.#", "#.#"],
    "O": [".#.", "#.#", "#.#", "#.#", ".#."], "P": ["##.", "#.#", "##.", "#..", "#.."],
    "Q": [".#.", "#.#", "#.#", "##.", ".##"], "R": ["##.", "#.#", "##.", "#.#", "#.#"],
    "S": [".##", "#..", ".#.", "..#", "##."], "T": ["###", ".#.", ".#.", ".#.", ".#."],
    "U": ["#.#", "#.#", "#.#", "#.#", "###"], "V": ["#.#", "#.#", "#.#", "#.#", ".#."],
    "W": ["#.#", "#.#", "###", "###", "#.#"], "X": ["#.#", "#.#", ".#.", "#.#", "#.#"],
    "Y": ["#.#", "#.#", ".#.", ".#.", ".#."], "Z": ["###", "..#", ".#.", "#..", "###"],
    "0": ["###", "#.#", "#.#", "#.#", "###"], "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["##.", "..#", ".#.", "#..", "###"], "3": ["##.", "..#", ".#.", "..#", "##."],
    "4": ["#.#", "#.#", "###", "..#", "..#"], "5": ["###", "#..", "##.", "..#", "##."],
    "6": [".##", "#..", "###", "#.#", "###"], "7": ["###", "..#", ".#.", ".#.", ".#."],
    "8": ["###", "#.#", "###", "#.#", "###"], "9": ["###", "#.#", "###", "..#", "##."],
    " ": ["...", "...", "...", "...", "..."], "-": ["...", "...", "###", "...", "..."],
    ".": ["...", "...", "...", "...", ".#."], "/": ["..#", "..#", ".#.", "#..", "#.."],
    "!": [".#.", ".#.", ".#.", "...", ".#."], "+": ["...", ".#.", "###", ".#.", "..."],
}


def text_bitmap(text, scale=1, spacing=1):
    glyphs = [np.array([[c == "#" for c in row] for row in F35.get(ch, F35[" "])]) for ch in text.upper()]
    cols = []
    for i, g in enumerate(glyphs):
        cols.append(g)
        if i < len(glyphs) - 1:
            cols.append(np.zeros((5, spacing), bool))
    bm = np.concatenate(cols, axis=1)
    return np.kron(bm, np.ones((scale, scale), bool)).astype(bool)


def sign_image(text, w_m, h_m, bg, fg, scale=None, border=None, seed=1, ppm=PPM, extra=None):
    """A sign as pixels at 16 px/m: centred pixel-font text on a flat colour (optionally bordered)."""
    W, Hh = max(4, int(round(w_m * ppm))), max(4, int(round(h_m * ppm)))
    img = pattern("flat", bg, 1, seed)[0, 0][None, None, :] * np.ones((Hh, W, 1), np.float32)
    rng = np.random.default_rng(seed)
    img *= (0.96 + 0.04 * rng.random((Hh, W, 1))).astype(np.float32)
    if border:
        bc = hexrgb(border)
        img[:1, :] = bc
        img[-1:, :] = bc
        img[:, :1] = bc
        img[:, -1:] = bc
    if text:
        if scale is None:
            scale = 1
            while True:
                bm = text_bitmap(text, scale + 1, spacing=scale + 1)
                if bm.shape[0] > Hh * 0.72 or bm.shape[1] > W * 0.9:
                    break
                scale += 1
        bm = text_bitmap(text, scale, spacing=scale)
        bh, bw = bm.shape
        y0, x0 = (Hh - bh) // 2, (W - bw) // 2
        if bw <= W and bh <= Hh:
            img[y0:y0 + bh, x0:x0 + bw][bm] = hexrgb(fg)
    if extra is not None:
        extra(img)
    return np.clip(img, 0, 1)


# ---------------------------------------------------------------- mesh builder
FACES = {  # name: (normal axis, sign, corner order) for a unit box centred at 0
    "+x": [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)],
    "-x": [(-1, 1, -1), (-1, -1, -1), (-1, -1, 1), (-1, 1, 1)],
    "+y": [(1, 1, -1), (-1, 1, -1), (-1, 1, 1), (1, 1, 1)],
    "-y": [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)],
    "+z": [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)],
    "-z": [(-1, 1, -1), (1, 1, -1), (1, -1, -1), (-1, -1, -1)],
}


def _rotz(yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], np.float64)


def _rot(rx=0.0, ry=0.0, rz=0.0):
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def _uv_for(p, n):
    """UVs in metres for a quad (4 x 3 points) with normal n: tops use x/y, walls use (along, z)."""
    n = n / (np.linalg.norm(n) + 1e-12)
    if abs(n[2]) > 0.7:
        return p[:, :2] * np.array([1, 1 if n[2] > 0 else -1])
    t = np.array([-n[1], n[0], 0.0])
    t /= np.linalg.norm(t) + 1e-12
    return np.stack([p @ t, p[:, 2]], 1)


class MeshBuilder:
    def __init__(self):
        self.v, self.uv, self.mat = [], [], []
        self.mats = []
        self.boxes = []      # (centre, half size, rotation) of every box, for the QC overlap checks

    def mi(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def quad(self, pts, m, uv=None):
        p = np.asarray(pts, np.float64)
        if uv is None:
            n = np.cross(p[1] - p[0], p[3] - p[0])
            uv = _uv_for(p, n)
        elif isinstance(uv, str) and uv == "fit":
            uv = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], float)
        self.v.append(p)
        self.uv.append(np.asarray(uv, np.float64))
        self.mat.append(self.mi(m))

    def box(self, center, size, m, yaw=0.0, rot=None, faces=None, skip=(), uvfit=(), origin_uv=None):
        """Axis box of `size` at `center`, then rotated (yaw about Z, or rot=(rx, ry, rz)) about its centre.
        faces: {face name: material} overrides; skip: faces not built; uvfit: faces whose UVs span 0..1."""
        c = np.asarray(center, np.float64)
        h = np.asarray(size, np.float64) / 2
        R = _rot(*rot) if rot is not None else (_rotz(yaw) if yaw else None)
        self.boxes.append(np.concatenate([c, h, (R if R is not None else np.eye(3)).ravel()]))
        for f, corners in FACES.items():
            if f in skip:
                continue
            loc = np.array(corners, np.float64) * h          # box-local (unrotated) corners
            mm = (faces or {}).get(f, m)
            if f in uvfit:
                uv = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], float)
            else:
                n = np.cross(loc[1] - loc[0], loc[3] - loc[0])
                uv = _uv_for(loc + (c if R is None else 0) + (0 if origin_uv is None else np.asarray(origin_uv)), n)
            p = loc @ R.T + c if R is not None else loc + c
            self.quad(p, mm, uv)

    def box_minmax(self, lo, hi, m, **kw):
        lo, hi = np.asarray(lo, float), np.asarray(hi, float)
        self.box((lo + hi) / 2, hi - lo, m, **kw)

    def extend(self, other, offset=(0, 0, 0), yaw=0.0):
        R = _rotz(yaw)
        for bx in other.boxes:
            c, h, Rb = bx[:3], bx[3:6], bx[6:].reshape(3, 3)
            self.boxes.append(np.concatenate([R @ c + np.asarray(offset), h, (R @ Rb).ravel()]))
        for p, uv, mi in zip(other.v, other.uv, other.mat):
            self.quad(p @ R.T + np.asarray(offset), other.mats[mi], uv)

    def build(self, name, coll=None, obj=True):
        ob = mesh_from(name, np.array(self.v).reshape(-1, 3) if self.v else np.zeros((0, 3)),
                         np.array(self.uv).reshape(-1, 2) if self.uv else np.zeros((0, 2)),
                         np.array(self.mat, np.int32), self.mats, coll, obj)
        if obj and self.boxes:
            ob["boxes"] = np.array(self.boxes).ravel().tolist()
        return ob

    def __len__(self):
        return len(self.v)


def mesh_from(name, verts, uvs, mat_idx, mats, coll=None, obj=True):
    """Quads only: verts (4N x 3), uvs (4N x 2), one material index per quad. Flat shaded, no shared vertices."""
    nq = len(mat_idx)
    me = bpy.data.meshes.new(name)
    me.vertices.add(4 * nq)
    me.vertices.foreach_set("co", np.asarray(verts, np.float32).ravel())
    me.loops.add(4 * nq)
    me.loops.foreach_set("vertex_index", np.arange(4 * nq, dtype=np.int32))
    me.polygons.add(nq)
    me.polygons.foreach_set("loop_start", np.arange(0, 4 * nq, 4, dtype=np.int32))
    me.polygons.foreach_set("loop_total", np.full(nq, 4, np.int32))
    me.polygons.foreach_set("material_index", np.asarray(mat_idx, np.int32))
    me.polygons.foreach_set("use_smooth", np.zeros(nq, bool))
    uvl = me.uv_layers.new(name="UVMap")
    uvl.data.foreach_set("uv", np.asarray(uvs, np.float32).ravel())
    for m in mats:
        me.materials.append(m)
    me.update(calc_edges=True)
    me.validate(clean_customdata=False)
    if not obj:
        return me
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


# ---------------------------------------------------------------- collections
def collection(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


PROTO_ROOT = "circuit_protos"


def proto_collection(name):
    """A collection of prototype objects (variants, sorted by name). Not linked to the scene: only instanced."""
    root = bpy.data.collections.get(PROTO_ROOT) or bpy.data.collections.new(PROTO_ROOT)
    root.use_fake_user = True
    c = bpy.data.collections.get("proto_" + name)
    if c is None:
        c = bpy.data.collections.new("proto_" + name)
        root.children.link(c)
    return c


def proto(name, builder, variant=0):
    """Register a prototype mesh object (builder: MeshBuilder) as variant `variant` of proto group `name`."""
    c = proto_collection(name)
    ob = builder.build(f"{name}__v{variant:02d}", c)
    ob["proto"] = name
    return ob


# ---------------------------------------------------------------- instancing (Geometry Nodes)
def _scatter_group(proto_name):
    """One small node group per prototype group (Collection Info points at its collection)."""
    name = "scatter_" + proto_name
    ng = bpy.data.node_groups.get(name)
    if ng:
        return ng
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N = ng.nodes
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    ci = N.new("GeometryNodeCollectionInfo")
    ci.transform_space = "ORIGINAL"
    ci.inputs["Separate Children"].default_value = True
    ci.inputs["Reset Children"].default_value = True
    iop = N.new("GeometryNodeInstanceOnPoints")
    iop.inputs["Pick Instance"].default_value = True
    ra = N.new("GeometryNodeInputNamedAttribute")
    ra.data_type = "FLOAT_VECTOR"
    ra.inputs["Name"].default_value = "rot"
    sa = N.new("GeometryNodeInputNamedAttribute")
    sa.data_type = "FLOAT_VECTOR"
    sa.inputs["Name"].default_value = "scl"
    va = N.new("GeometryNodeInputNamedAttribute")
    va.data_type = "INT"
    va.inputs["Name"].default_value = "var"
    er = N.new("FunctionNodeEulerToRotation") if hasattr(bpy.types, "FunctionNodeEulerToRotation") else None
    L = ng.links
    L.new(gi.outputs[0], iop.inputs["Points"])
    ci.inputs["Collection"].default_value = proto_collection(proto_name)
    L.new(ci.outputs[0], iop.inputs["Instance"])
    if er:
        L.new(ra.outputs["Attribute"], er.inputs[0])
        L.new(er.outputs[0], iop.inputs["Rotation"])
    else:
        L.new(ra.outputs["Attribute"], iop.inputs["Rotation"])
    L.new(sa.outputs["Attribute"], iop.inputs["Scale"])
    L.new(va.outputs["Attribute"], iop.inputs["Instance Index"])
    L.new(iop.outputs[0], go.inputs[0])
    return ng


def scatter(name, proto_name, pos, yaw=None, scale=None, var=None, coll=None, rot=None):
    """One object instancing proto group `proto_name` on len(pos) points. yaw (radians) or rot (N x 3 euler);
    scale (N x 3 or N), var (N ints, variant index). Returns the object (edit its points to adjust pieces)."""
    pos = np.asarray(pos, np.float32).reshape(-1, 3)
    n = len(pos)
    me = bpy.data.meshes.new(name)
    me.vertices.add(n)
    me.vertices.foreach_set("co", pos.ravel())
    if rot is None:
        rot = np.zeros((n, 3), np.float32)
        if yaw is not None:
            rot[:, 2] = np.asarray(yaw, np.float32)
    sc = np.ones((n, 3), np.float32) if scale is None else np.asarray(scale, np.float32)
    if sc.ndim == 1:
        sc = np.repeat(sc[:, None], 3, 1)
    va = np.zeros(n, np.int32) if var is None else np.asarray(var, np.int32)
    for an, data, kind, field in (("rot", rot, "FLOAT_VECTOR", "vector"), ("scl", sc, "FLOAT_VECTOR", "vector"),
                                  ("var", va, "INT", "value")):
        a = me.attributes.new(an, kind, "POINT")
        a.data.foreach_set(field, np.asarray(data).ravel())
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    mod = ob.modifiers.new("scatter", "NODES")
    mod.node_group = _scatter_group(proto_name)
    ob["proto"] = proto_name
    ob["count"] = n
    return ob


def place(name, src, loc, yaw=0.0, coll=None, scale=None):
    """A linked duplicate of an object (shares its mesh): for pieces that need their own animation/state."""
    ob = bpy.data.objects.new(name, src.data)
    ob.location = loc
    ob.rotation_euler = (0, 0, yaw)
    if scale is not None:
        ob.scale = scale
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob
