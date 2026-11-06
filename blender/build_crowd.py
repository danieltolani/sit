# RAS: the crowd of silhouettes behind the chair (run after build_ras_scene.py, or on the saved ras_scene.blend).
#
# One ActorCore character, frozen at different moments of its walk-think clip, gives a set of poses. Each person
# in the crowd is a copy of one pose: flat dark grey (no shading), random height, facing, mirroring, and placement
# on the ground behind the grass, with the odd pair. Perspective does the "smaller with distance".
# Re-run to rebuild the crowd; change SEED for a new arrangement. No motion yet (they stand still).
import bpy, math, os, random
from mathutils import Vector, Euler, Matrix
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, 'assets', 'dancer-walk.glb')
SCENE = 'RAS 16:9 Close'          # which scene the crowd shows in
CAMERA = 'Camera Close Wide'      # placement keeps everyone inside this camera's frame

SEED = 4
COUNT = 30                        # people (pairs count as two)
PAIR_CHANCE = 0.22                # chance a person brings a companion standing next to them
DEPTH = (7.0, 30.0)               # how far behind the chair they stand (world y; the sand ends at ~2.1)
MIN_GAP = 2.8                     # minimum distance between people (pairs excepted)
HEIGHT = 1.62                     # average height; the chair is 0.79
HEIGHT_VAR = 0.07                 # +/- share
FACE_CHAIR = 0.75                 # share of people turned roughly towards the chair; the rest face anywhere
POSES = 24                        # distinct poses sampled from the clip
FRAME_MARGIN = 0.03               # keep everyone this far inside the frame edges (0..1 of the frame)
COLOR = '#0F1824'                 # silhouette fill
# Depth on the figures: still a silhouette, but light wraps it a little
FORM = 0.06                       # how much the sun side lifts out of the fill (0 = flat)
RIM = 0.30                        # light bouncing round the edges (0 = none)
RIM_COLOR = '#7C8DA3'             # cool bounce from the sky
RIM_WIDTH = 0.12                  # thinner edge = lower (Layer Weight blend)
HAZE = 0.15                       # how much the farthest people fade into the air (0 = none)
HAZE_RANGE = (12.0, 42.0)          # distance from camera where the haze starts and is full
HAZE_COLOR = '#E9ECEF'            # the air: close to the background
SHADOW_OPACITY = 0.30             # soft cast shadows on the (invisible) ground
SHADOW_COLOR = '#0F1824'
# Who's in the crowd. Outfits are drawn as part of the silhouette, fitted to each person's pose.
OUTFITS = {                       # share of the crowd wearing each (the rest wear what the model has on)
    'kaftan': 0.20,               # kaftan / jalabiya: long robe to the ankles
    'agbada': 0.14,               # agbada with fila: the wide drape off the shoulders
    'fila': 0.12,                 # fila cap only
    'gele': 0.16,                 # gele head-tie with iro wrapper
}
MOTHERS = 2                       # gele and wrapper, a child tied on her back
EYO = 3                           # Eyo masquerade: robe over the head, wide akete hat, staff
WHEELCHAIRS = 1
EYO_COLOR = None                  # None = same fill as everyone; e.g. '#F4F1EA' for Eyo in white
# what the invisible ground renders at in full sun / in shade (measured in this scene's lighting)
GROUND_LIT, GROUND_SHADE = 1.38, 0.55

def lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c) + (1.0,)

scene = bpy.data.scenes[SCENE]
cam = bpy.data.objects.get(CAMERA) or scene.camera
rng = random.Random(SEED)

# ---- clean previous build ------------------------------------------------------------------------------------
for name in ('Crowd', 'Crowd Poses'):
    c = bpy.data.collections.get(name)
    if c:
        for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(c)
for m in [m for m in bpy.data.meshes if m.name.startswith('Pose ') or m.name == 'Crowd Shadow Floor']: bpy.data.meshes.remove(m)

# ---- poses: import the walking character, freeze it at evenly spaced moments -----------------------------------
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=SOURCE)
imported = set(bpy.data.objects) - before
arm = next(o for o in imported if o.type == 'ARMATURE')
body = next(o for o in imported if o.type == 'MESH' and o.data.materials)
action = arm.animation_data.action
f0, f1 = (int(v) for v in action.frame_range)
deps = bpy.context.evaluated_depsgraph_get()
poses = []
for k in range(POSES):
    f = f0 + (f1 - f0 - 1) * (k + 0.5) / POSES
    scene.frame_set(int(f), subframe=f % 1)
    deps = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(deps)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=False, depsgraph=deps)
    me.transform(body.matrix_world)
    zs = [v.co.z for v in me.vertices]
    zmin, zmax = min(zs), max(zs)
    low = [v.co for v in me.vertices if v.co.z < zmin + 0.06]        # feet
    cx = sum(c.x for c in low) / len(low); cy = sum(c.y for c in low) / len(low)
    s = 1.0 / (zmax - zmin)                                             # unit height, feet at the origin
    from mathutils import Matrix
    me.transform(Matrix.Scale(s, 4) @ Matrix.Translation((-cx, -cy, -zmin)))
    me.materials.clear()
    me.name = f'Pose {k + 1:02d}'
    me.use_fake_user = True
    poses.append(me)
# seated: the rest pose with thighs forward, shins down and arms by the sides (checked on this rig:
# thighs fold forward on +X, calves back on -X, left arm comes down on -Z and the right on +Z)
arm.animation_data.action = None
pb = arm.pose.bones
for n, ax, deg in (('CC_Base_L_Thigh', 0, 88), ('CC_Base_R_Thigh', 0, 88), ('CC_Base_L_Calf', 0, -88), ('CC_Base_R_Calf', 0, -88),
                   ('CC_Base_L_Upperarm', 2, -68), ('CC_Base_R_Upperarm', 2, 68),
                   ('CC_Base_L_Forearm', 0, 35), ('CC_Base_R_Forearm', 0, 35)):
    if n in pb:
        b = pb[n]; b.rotation_mode = 'XYZ'; e = [0.0, 0.0, 0.0]; e[ax] = math.radians(deg); b.rotation_euler = e
bpy.context.view_layer.update()
deps = bpy.context.evaluated_depsgraph_get()
ev = body.evaluated_get(deps)
seated = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=False, depsgraph=deps)
seated.transform(body.matrix_world)
zs = [v.co.z for v in seated.vertices]
from mathutils import Matrix
stand_h = max(zs) - min(zs)
hip_z = (arm.matrix_world @ pb['CC_Base_Hip'].head).z
seat_z = hip_z - 0.10 * stand_h                       # bottom of the pelvis, roughly
# unit scale relative to a standing person; seat surface at the origin
k = 1.0 / (stand_h * 1.18)
SEAT_H = 0.29
seated.transform(Matrix.Translation((0, 0.02, SEAT_H)) @ Matrix.Scale(k, 4) @ Matrix.Translation((0, 0, -seat_z)))
seated.materials.clear(); seated.name = 'Pose Seated'; seated.use_fake_user = True
for o in imported: bpy.data.objects.remove(o, do_unlink=True)
scene.frame_set(1)

# ---- material: flat fill ------------------------------------------------------------------------------------
mat = bpy.data.materials.get('RAS Silhouette') or bpy.data.materials.new('RAS Silhouette')
mat.use_nodes = True
nt = mat.node_tree; nt.nodes.clear()
N = nt.nodes.new; L = nt.links.new
def rgb(h, label):
    n = N('ShaderNodeRGB'); n.outputs[0].default_value = lin(h); n.label = n.name = label; return n.outputs[0]
def val(v, label):
    n = N('ShaderNodeValue'); n.outputs[0].default_value = v; n.label = n.name = label; return n.outputs[0]
def mix(f, a, b):
    m = N('ShaderNodeMix'); m.data_type = 'RGBA'
    L(f, m.inputs['Factor']) if not isinstance(f, float) else setattr(m.inputs['Factor'], 'default_value', f)
    L(a, m.inputs[6]); L(b, m.inputs[7]); return m.outputs[2]
def mop(op, a, b):
    m = N('ShaderNodeMath'); m.operation = op
    for i, x in enumerate((a, b)):
        if isinstance(x, float): m.inputs[i].default_value = x
        else: L(x, m.inputs[i])
    return m.outputs[0]
fill = rgb(COLOR, 'FILL')
# form: how lit each point is, from a plain diffuse, remapped to 0..1 and scaled down
dif = N('ShaderNodeBsdfDiffuse'); s2r = N('ShaderNodeShaderToRGB'); L(dif.outputs[0], s2r.inputs[0])
bw = N('ShaderNodeRGBToBW'); L(s2r.outputs['Color'], bw.inputs[0])
mr = N('ShaderNodeMapRange'); mr.clamp = True; mr.inputs['From Min'].default_value = 0.5; mr.inputs['From Max'].default_value = 1.4
L(bw.outputs[0], mr.inputs['Value'])
col = mix(mop("MULTIPLY", mr.outputs['Result'], val(FORM, 'Form')), fill, rgb('#FFFFFF', 'FORM LIGHT'))
# rim: light passing round the edges
lw = N('ShaderNodeLayerWeight'); L(val(RIM_WIDTH, 'Rim Width'), lw.inputs['Blend'])
col = mix(mop("MULTIPLY", lw.outputs['Facing'], val(RIM, 'Rim')), col, rgb(RIM_COLOR, 'RIM COLOUR'))
# haze: far people fade into the air
cd = N('ShaderNodeCameraData')
hz = N('ShaderNodeMapRange'); hz.clamp = True; hz.interpolation_type = 'SMOOTHSTEP'
hz.inputs['From Min'].default_value, hz.inputs['From Max'].default_value = HAZE_RANGE
L(cd.outputs['View Distance'], hz.inputs['Value'])
col = mix(mop("MULTIPLY", hz.outputs['Result'], val(HAZE, 'Haze')), col, rgb(HAZE_COLOR, 'HAZE COLOUR'))
em = N('ShaderNodeEmission'); L(col, em.inputs['Color']); em.inputs['Strength'].default_value = 1.0
o_ = N('ShaderNodeOutputMaterial'); L(em.outputs[0], o_.inputs['Surface'])
mat.use_backface_culling = False
for me in poses: me.materials.append(mat)
seated.materials.append(mat)
eyo_mat = mat
if EYO_COLOR:
    eyo_mat = mat.copy(); eyo_mat.name = 'RAS Silhouette Eyo'; eyo_mat.node_tree.nodes['FILL'].outputs[0].default_value = lin(EYO_COLOR)

# ---- outfit shapes (unit height; the walking poses face +y, so their back is -y; the seated pose faces -y) ---------------------------------------
import bmesh
def pose_info(me):
    vs = [v.co for v in me.vertices]
    legs = [c for c in vs if c.z < 0.45]
    head = [c for c in vs if c.z > 0.90]
    lx = max(abs(c.x) for c in legs); ly = max(abs(c.y) for c in legs)
    hx = sum(c.x for c in head) / len(head); hy = sum(c.y for c in head) / len(head)
    hr = max(max(abs(c.x - hx), abs(c.y - hy)) for c in head)
    chest = [c for c in vs if 0.62 < c.z < 0.78 and abs(c.x) < 0.2]
    cx = sum(c.x for c in chest) / len(chest); cy = sum(c.y for c in chest) / len(chest)
    return dict(legs=(lx, ly), head=(hx, hy, hr), chest=(cx, cy))
INFO = {me.name: pose_info(me) for me in poses}

def lathe(name, rings, centre=(0, 0), seg=28, cap_top=True):
    """rings: [(z, rx, ry), ...] bottom to top; an elliptical robe around `centre`."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    loops = []
    for z, rx, ry in rings:
        loops.append([bm.verts.new((centre[0] + rx * math.cos(2 * math.pi * i / seg), centre[1] + ry * math.sin(2 * math.pi * i / seg), z)) for i in range(seg)])
    for a, b in zip(loops, loops[1:]):
        for i in range(seg):
            bm.faces.new((a[i], a[(i + 1) % seg], b[(i + 1) % seg], b[i]))
    if cap_top: bm.faces.new(loops[-1])
    bm.faces.new(list(reversed(loops[0])))
    bm.to_mesh(me); bm.free(); return me

def blob(name, c, r, seg=16):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    for v in bm.verts: v.co = Vector((c[0] + v.co.x * r[0], c[1] + v.co.y * r[1], c[2] + v.co.z * r[2]))
    bm.to_mesh(me); bm.free(); return me

def rod(name, a, b, r, seg=8):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    a, b = Vector(a), Vector(b); d = b - a
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=d.length)
    rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation((a + b) / 2) @ rot, verts=bm.verts)
    bm.to_mesh(me); bm.free(); return me

def ring(name, c, R, r, axis='X', seg=32):
    # torus via primitive operator-free construction
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    rings_ = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        rr = []
        for j in range(8):
            b = 2 * math.pi * j / 8
            p = Vector(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b)))
            if axis == 'X': p = Vector((p.z, p.x, p.y))
            rr.append(bm.verts.new(Vector(c) + p))
        rings_.append(rr)
    for i in range(seg):
        A, B = rings_[i], rings_[(i + 1) % seg]
        for j in range(8):
            bm.faces.new((A[j], A[(j + 1) % 8], B[(j + 1) % 8], B[j]))
    bm.to_mesh(me); bm.free(); return me

def attach(person, me, material=None):
    me.materials.append(material or mat)
    for f in me.polygons: f.use_smooth = True
    o = bpy.data.objects.new(person.name + ' / ' + me.name, me)
    o.parent = person
    crowd.objects.link(o); return o

def legs_hem(info, extra=1.15):
    lx, ly = info['legs']; return max(lx * extra + 0.02, 0.15), max(ly * extra + 0.02, 0.11)

def dress(person, kind):
    me = person.data; info = INFO.get(me.name)
    if not info: return
    hx, hy, hr = info['head']; cx, cy = info['chest']; bx, by = legs_hem(info)
    top = 0.995
    if kind == 'kaftan':
        attach(person, lathe('Kaftan', [(0.03, bx, by), (0.30, bx * 0.82, by * 0.85), (0.58, 0.14, 0.085), (0.80, 0.115, 0.075)], (cx, cy)))
    elif kind == 'agbada':
        attach(person, lathe('Agbada robe', [(0.03, bx, by), (0.35, bx * 0.8, by * 0.85), (0.6, 0.13, 0.085)], (cx, cy)))
        attach(person, lathe('Agbada', [(0.22, 0.24, 0.07), (0.45, 0.33, 0.085), (0.60, 0.34, 0.09), (0.72, 0.22, 0.085), (0.82, 0.12, 0.075)], (cx, cy)))
        dress(person, 'fila')
    elif kind == 'fila':
        cap = lathe('Fila', [(top - 0.04, hr * 1.06, hr * 1.06), (top + 0.008, hr * 1.12, hr * 1.08)], (hx, hy))
        pivot = Vector((hx, hy, top - 0.03))
        tilt = Euler((math.radians(8), math.radians(-12), 0)).to_matrix().to_4x4()
        cap.transform(Matrix.Translation(pivot) @ tilt @ Matrix.Translation(-pivot))   # tilted on the head itself
        attach(person, cap)
        attach(person, blob('Fila fold', (hx + hr * 0.75, hy + hr * 0.1, top + 0.0), (hr * 0.75, hr * 0.85, hr * 0.38)))
    elif kind == 'gele':
        attach(person, blob('Gele', (hx, hy + hr * 0.15, top + 0.02), (hr * 1.8, hr * 1.35, hr * 0.85)))
        attach(person, blob('Gele fan', (hx - hr * 0.5, hy + hr * 0.5, top + 0.06), (hr * 1.3, hr * 0.5, hr * 0.7)))
        attach(person, lathe('Iro', [(0.03, max(bx * 0.95, 0.13), max(by * 0.95, 0.10)), (0.30, 0.13, 0.095), (0.56, 0.12, 0.085)], (cx, cy)))
    elif kind == 'mother':
        dress(person, 'gele')
        attach(person, blob('Child', (cx, cy - 0.12, 0.60), (0.10, 0.085, 0.13)))          # tied on her back
        attach(person, blob('Child head', (cx + 0.04, cy - 0.14, 0.775), (0.05, 0.05, 0.055)))
        attach(person, blob('Child legs', (cx, cy - 0.09, 0.50), (0.12, 0.06, 0.04)))       # little legs round her waist
    elif kind == 'eyo':
        m = eyo_mat
        attach(person, lathe('Eyo robe', [(0.0, 0.30, 0.22), (0.25, 0.24, 0.17), (0.55, 0.22, 0.14), (0.78, 0.20, 0.12), (0.90, 0.11, 0.10), (0.99, 0.07, 0.07)], (hx, hy)), m)
        attach(person, lathe('Akete hat', [(1.00, 0.23, 0.23), (1.02, 0.23, 0.23)], (hx, hy)), m)
        attach(person, lathe('Akete crown', [(1.01, 0.07, 0.07), (1.07, 0.05, 0.05)], (hx, hy)), m)
        attach(person, rod('Opambata', (hx + 0.24, hy - 0.04, 0.0), (hx + 0.27, hy - 0.06, 1.12), 0.010), m)
        person.hide_render = True   # fully covered: only the robe, hat and staff show

def wheelchair(person):
    # unit = one standing person's height; seat surface at z = seat
    seat = SEAT_H - 0.01
    for side in (-1, 1):
        attach(person, ring('Wheel', (side * 0.17, 0.05, 0.185), 0.18, 0.012, axis='X'))
        attach(person, ring('Caster', (side * 0.15, -0.20, 0.045), 0.045, 0.008, axis='X'))
        attach(person, rod('Frame', (side * 0.15, -0.20, 0.09), (side * 0.15, 0.10, seat), 0.008))
        attach(person, rod('Push handle', (side * 0.15, 0.13, seat), (side * 0.15, 0.17, seat + 0.33), 0.008))
    attach(person, lathe('Seat', [(seat - 0.02, 0.15, 0.13), (seat, 0.15, 0.13)], (0, -0.04)))
    attach(person, lathe('Back', [(seat, 0.14, 0.012), (seat + 0.26, 0.14, 0.012)], (0, 0.14)))

# ---- placement ----------------------------------------------------------------------------------------------
crowd = bpy.data.collections.new('Crowd'); scene.collection.children.link(crowd)
chair = bpy.data.objects.get('Chair')
target = chair.matrix_world.translation.copy() if chair else Vector((0, 0, 0))

def in_frame(p, h):
    a = world_to_camera_view(scene, cam, p)
    b = world_to_camera_view(scene, cam, p + Vector((0, 0, h)))
    m = FRAME_MARGIN
    return a.z > 0 and m < a.x < 1 - m and m < b.x < 1 - m and b.y < 1 - m and a.y > m

placed = []
people = []
def add_person(p, yaw, h, i):
    me = rng.choice(poses)
    ob = bpy.data.objects.new(f'Person {i + 1:02d}', me)
    ob.location = p
    ob.rotation_euler = (0, 0, yaw)
    ob.scale = (h * (-1 if rng.random() < 0.5 else 1), h, h)     # mirrored half the time
    crowd.objects.link(ob)
    placed.append(p)
    people.append(ob)
    return ob

tries = 0
while len(placed) < COUNT and tries < 20000:
    tries += 1
    y = rng.uniform(*DEPTH)
    x = rng.uniform(-y * 1.3 - 2, y * 1.3 + 2)
    p = Vector((x, y, 0))
    h = HEIGHT * (1 + rng.uniform(-HEIGHT_VAR, HEIGHT_VAR))
    if not in_frame(p, h): continue
    if any((p - q).length < MIN_GAP for q in placed): continue
    to_chair = math.atan2(target.y - y, target.x - x) - math.pi / 2      # the walking poses face +y
    yaw = to_chair + rng.uniform(-0.6, 0.6) if rng.random() < FACE_CHAIR else rng.uniform(-math.pi, math.pi)
    add_person(p, yaw, h, len(placed))
    if rng.random() < PAIR_CHANCE and len(placed) < COUNT:              # a companion, half a step away
        ang = rng.uniform(0, 2 * math.pi); d = rng.uniform(0.38, 0.6)
        q = p + Vector((math.cos(ang) * d, math.sin(ang) * d, 0))
        h2 = HEIGHT * (1 + rng.uniform(-HEIGHT_VAR, HEIGHT_VAR))
        if in_frame(q, h2):
            add_person(q, math.atan2(p.y - q.y, p.x - q.x) - math.pi / 2 + rng.uniform(-0.5, 0.5), h2, len(placed))

# ---- who wears what: the special figures go to the nearer half so they read ----------------------------------
near = sorted(people, key=lambda o: (o.location - cam.location).length)
specials = near[: max(1, len(near) * 2 // 3)]
rng.shuffle(specials)
for o in specials[:WHEELCHAIRS]:
    o.data = seated; o.name = o.name + ' (wheelchair)'
    wheelchair(o)
for o in specials[WHEELCHAIRS:WHEELCHAIRS + MOTHERS]:
    to_cam = math.atan2(cam.location.y - o.location.y, cam.location.x - o.location.x)
    o.rotation_euler.z = to_cam + rng.choice((0.0, math.pi)) + rng.uniform(-0.25, 0.25)   # side-on to the camera
    dress(o, 'mother'); o.name += ' (mother)'
for o in specials[WHEELCHAIRS + MOTHERS:WHEELCHAIRS + MOTHERS + EYO]:
    o.data = min(poses, key=lambda me: INFO[me.name]['legs'][0])   # the narrowest stance under the robe
    dress(o, 'eyo'); o.name += ' (Eyo)'
taken = set(specials[:WHEELCHAIRS + MOTHERS + EYO])
for o in people:
    if o in taken: continue
    r = rng.random(); acc = 0
    for kind, share in OUTFITS.items():
        acc += share
        if r < acc:
            dress(o, kind); o.name += f' ({kind})'; break

# ---- shadows on an invisible ground ------------------------------------------------------------------------
# A floor that is transparent except where a shadow falls, so the crowd's shadows land on the white page.
floor_me = bpy.data.meshes.new('Crowd Shadow Floor')
floor_me.from_pydata([(-40, DEPTH[0] - 0.6, 0), (40, DEPTH[0] - 0.6, 0), (40, DEPTH[1] + 15, 0), (-40, DEPTH[1] + 15, 0)], [], [(0, 1, 2, 3)])
floor = bpy.data.objects.new('Crowd Shadow Floor', floor_me); crowd.objects.link(floor)
floor.location.z = 0.0003
sm = bpy.data.materials.get('RAS Crowd Shadow') or bpy.data.materials.new('RAS Crowd Shadow')
sm.use_nodes = True; snt = sm.node_tree; snt.nodes.clear()
dif = snt.nodes.new('ShaderNodeBsdfDiffuse'); dif.inputs['Color'].default_value = (1, 1, 1, 1)
s2r = snt.nodes.new('ShaderNodeShaderToRGB'); snt.links.new(dif.outputs[0], s2r.inputs[0])
bw = snt.nodes.new('ShaderNodeRGBToBW'); snt.links.new(s2r.outputs['Color'], bw.inputs[0])
mr = snt.nodes.new('ShaderNodeMapRange'); mr.clamp = True
mr.inputs['From Min'].default_value = GROUND_LIT; mr.inputs['From Max'].default_value = GROUND_SHADE
snt.links.new(bw.outputs[0], mr.inputs['Value'])
mul = snt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = SHADOW_OPACITY
snt.links.new(mr.outputs['Result'], mul.inputs[0])
tr = snt.nodes.new('ShaderNodeBsdfTransparent'); col = snt.nodes.new('ShaderNodeEmission'); col.inputs['Color'].default_value = lin(SHADOW_COLOR)
mix = snt.nodes.new('ShaderNodeMixShader'); snt.links.new(mul.outputs[0], mix.inputs[0])
snt.links.new(tr.outputs[0], mix.inputs[1]); snt.links.new(col.outputs[0], mix.inputs[2])
out = snt.nodes.new('ShaderNodeOutputMaterial'); snt.links.new(mix.outputs[0], out.inputs['Surface'])
sm.surface_render_method = 'BLENDED'
floor_me.materials.append(sm)
floor.visible_shadow = False

print(f'Crowd: {len(placed)} people from {len(poses)} poses')
