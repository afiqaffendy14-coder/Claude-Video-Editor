"""Rigged block characters: the same blocky body as voxel.block_person, but every part is a rigid block parented
to a bone of an armature, so it can be keyframed without deforming. Hands and feet are driven by IK targets
(empties), so hands can grip props and feet can stay planted on the ground.

Actor(name) gives a small keyframing API used by choreo.py.
"""
import json, math
import bpy
from mathutils import Vector, Matrix
import voxel
from lib import link

V = Vector
REST = dict(crouch=0, lean=0, twist=0, head=(0, 0), armL=(0, 0, 12), armR=(0, 0, 12), legL=(3, 0, 8), legR=(3, 0, 8))
FOOT_LEN = 0.14


def _bone_for(part, name):
    s = part[len(name) + 1:]
    for k in "LR":
        if s == "shoe" + k:
            return "foot." + k
        if s == "ua" + k:
            return "upperarm." + k
        if s == "fa" + k:
            return "forearm." + k
        if s == "hand" + k:
            return "hand." + k
        if s == "th" + k:
            return "thigh." + k
        if s == "sh" + k:
            return "shin." + k
    if s in ("torso", "belt"):
        return "spine"
    return "head"  # head block and everything on it (eyes, mask, cap, helmet, visor...)


def _empty(name, loc, size=0.05, shape="SPHERE"):
    e = link(bpy.data.objects.new(name, None))
    e.empty_display_type = shape
    e.empty_display_size = size
    e.location = loc
    return e


def build(name, outfit, scale=1.0):
    """Create the armature + rigid parts + IK targets at the origin, facing +Y. Returns the armature object."""
    body = voxel.block_person(name + "__rest", (0, 0, 0), 0, REST, outfit)
    J = {k: V(v) for k, v in json.loads(body["joints"]).items()}
    data = bpy.data.armatures.new(name + "_arm")
    arm = link(bpy.data.objects.new(name, data))
    arm["person"] = True
    arm["rig"] = True
    arm["outfit"] = outfit
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = data.edit_bones

    def bone(n, head, tail, parent=None, connect=False, inherit_rot=True):
        b = eb.new(n)
        b.head, b.tail = head, tail
        b.roll = 0
        if parent:
            b.parent = eb[parent]
            b.use_connect = connect
        b.use_inherit_rotation = inherit_rot
        return b

    bone("hips", J["pelvis"], J["pelvis"] + V((0, 0, 0.1)))
    bone("spine", J["pelvis"], J["neck"], "hips")
    bone("head", J["neck"], J["neck"] + V((0, 0, 0.36)), "spine")
    for k in "LR":
        bone("upperarm." + k, J["sh" + k], J["el" + k], "spine")
        bone("forearm." + k, J["el" + k], J["wr" + k], "upperarm." + k, True)
        d = (J["wr" + k] - J["el" + k]).normalized()
        bone("hand." + k, J["wr" + k], J["wr" + k] + d * 0.1, "forearm." + k, True)
        bone("thigh." + k, J["hp" + k], J["kn" + k], "hips")
        bone("shin." + k, J["kn" + k], J["an" + k], "thigh." + k, True)
        bone("foot." + k, J["an" + k], J["an" + k] + V((0, FOOT_LEN, 0)), "shin." + k, True, inherit_rot=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()
    # parts -> bones, keeping where they are
    parts = list(body.children)
    keep = {p.name: p.matrix_world.copy() for p in parts}
    for p in parts:
        p.parent = arm
        p.parent_type = "BONE"
        p.parent_bone = _bone_for(p.name, name + "__rest")
    bpy.context.view_layer.update()
    for p in parts:
        p.matrix_world = keep[p.name]
        p.name = p.name.replace("__rest", "")
        p["part_of"] = name
    bpy.data.objects.remove(body, do_unlink=True)
    # IK targets (world space) for wrists and ankles
    for k in "LR":
        th = _empty(f"{name}_ik_hand.{k}", J["wr" + k], 0.04)
        tf = _empty(f"{name}_ik_foot.{k}", J["an" + k], 0.05, "CUBE")
        c = arm.pose.bones["forearm." + k].constraints.new("IK")
        c.target, c.chain_count, c.use_tail = th, 2, True
        c = arm.pose.bones["shin." + k].constraints.new("IK")
        c.target, c.chain_count, c.use_tail = tf, 2, True
        for t in (th, tf):
            t["part_of"] = name
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
    arm.scale = (scale, scale, scale)
    voxel.texture_person(arm)
    return arm


class Actor:
    """Keyframing helper around one rigged character. Times are in frames."""

    def __init__(self, arm):
        self.arm = arm
        self.name = arm.name
        self.hand = {k: bpy.data.objects[f"{self.name}_ik_hand.{k}"] for k in "LR"}
        self.foot = {k: bpy.data.objects[f"{self.name}_ik_foot.{k}"] for k in "LR"}

    # -- placement -------------------------------------------------------------------------------------------
    def place(self, loc, rot_deg, crouch=0.0):
        """Put the rig at loc/heading with the hips dropped by crouch. Its IK targets move with it (by the change in
        placement, on the ground plane, so feet stay on the floor); targets gripping a prop stay with the prop."""
        bpy.context.view_layer.update()
        a = self.arm

        def planar(x, y, r):
            return Matrix.Translation(V((x, y, 0))) @ Matrix.Rotation(r, 4, "Z")
        old = planar(a.location.x, a.location.y, a.rotation_euler.z)
        new = planar(loc[0], loc[1], math.radians(rot_deg))
        delta = new @ old.inverted()
        a.location = (loc[0], loc[1], loc[2] - crouch)
        a.rotation_euler = (0, 0, math.radians(rot_deg))
        for t in list(self.hand.values()) + list(self.foot.values()):
            if t.parent is None:
                t.location = delta @ t.location
        bpy.context.view_layer.update()
        return self

    @property
    def heading(self):
        r = self.arm.rotation_euler.z
        return V((-math.sin(r), math.cos(r), 0))

    @property
    def right(self):
        r = self.arm.rotation_euler.z
        return V((math.cos(r), math.sin(r), 0))

    # -- keys ------------------------------------------------------------------------------------------------
    def key_root(self, f, loc=None, rot_deg=None):
        if loc is not None:
            self.arm.location = loc
            self.arm.keyframe_insert("location", frame=f)
        if rot_deg is not None:
            self.arm.rotation_euler.z = math.radians(rot_deg)
            self.arm.keyframe_insert("rotation_euler", index=2, frame=f)

    def key_bone(self, b, f, rot=None, loc=None):
        pb = self.arm.pose.bones[b]
        if rot is not None:
            pb.rotation_euler = tuple(math.radians(a) for a in rot)
            pb.keyframe_insert("rotation_euler", frame=f)
        if loc is not None:
            pb.location = loc
            pb.keyframe_insert("location", frame=f)

    def key_spine(self, f, lean=0.0, twist=0.0, side=0.0):
        """lean > 0 bends forward (toward the way the person faces)."""
        self.key_bone("spine", f, rot=(-lean * LEAN_SIGN, twist, side))

    def key_head(self, f, yaw=0.0, pitch=0.0):
        """pitch > 0 looks down."""
        self.key_bone("head", f, rot=(-pitch * LEAN_SIGN, yaw, 0))

    def key_target(self, t, f, loc):
        t.location = loc
        t.keyframe_insert("location", frame=f)

    def grip(self, k, obj, f=None):
        """Parent the hand target to a prop so the hand follows it (keeps the current world position)."""
        t = self.hand[k]
        bpy.context.view_layer.update()  # the prop (or the target) may have just been moved
        mw = t.matrix_world.copy()
        t.parent = obj
        t.matrix_parent_inverse = obj.matrix_world.inverted()
        t.matrix_world = mw


LEAN_SIGN = 1.0  # set by calibrate(): +1 means a negative X rotation of the spine bends it forward


def calibrate():
    """Find which way a spine X rotation bends a bone that points up (bone axes depend on Blender's roll rules)."""
    global LEAN_SIGN
    arm = build("calib", "scrubs")
    a = Actor(arm)
    pb = arm.pose.bones["spine"]
    pb.rotation_euler = (math.radians(-20), 0, 0)
    bpy.context.view_layer.update()
    tip = arm.matrix_world @ pb.tail
    LEAN_SIGN = 1.0 if tip.y > 0 else -1.0  # forward is +Y at rot 0
    for ob in [arm] + list(arm.children_recursive) + [o for o in bpy.data.objects if o.name.startswith("calib_ik")]:
        bpy.data.objects.remove(ob, do_unlink=True)
    return LEAN_SIGN
