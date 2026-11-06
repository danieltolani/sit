# RAS: the crowd of silhouettes behind the chair (run after build_ras_scene.py, or on the saved ras_scene.blend).
#
# One ActorCore character, frozen at different moments of its walk-think clip, gives a set of poses. Each person
# in the crowd is a copy of one pose: flat dark grey (no shading), random height, facing, mirroring, and placement
# on the ground behind the grass, with the odd pair. Perspective does the "smaller with distance".
# Re-run to rebuild the crowd; change SEED for a new arrangement. No motion yet (they stand still).
import bpy, math, os, random
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, 'assets', 'dancer-walk.glb')
SCENE = 'RAS 16:9 Close'          # which scene the crowd shows in (its camera is used for placement)

SEED = 4
COUNT = 40                        # people (pairs count as two)
PAIR_CHANCE = 0.22                # chance a person brings a companion standing next to them
DEPTH = (7.0, 30.0)               # how far behind the chair they stand (world y; the sand ends at ~2.1)
MIN_GAP = 1.6                     # minimum distance between people (pairs excepted)
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
HAZE = 0.30                       # how much the farthest people fade into the air (0 = none)
HAZE_RANGE = (12.0, 42.0)          # distance from camera where the haze starts and is full
HAZE_COLOR = '#E9ECEF'            # the air: close to the background
SHADOW_OPACITY = 0.30             # soft cast shadows on the (invisible) ground
SHADOW_COLOR = '#0F1824'
# what the invisible ground renders at in full sun / in shade (measured in this scene's lighting)
GROUND_LIT, GROUND_SHADE = 1.38, 0.55

def lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c) + (1.0,)

scene = bpy.data.scenes[SCENE]
cam = scene.camera
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
def add_person(p, yaw, h, i):
    me = rng.choice(poses)
    ob = bpy.data.objects.new(f'Person {i + 1:02d}', me)
    ob.location = p
    ob.rotation_euler = (0, 0, yaw)
    ob.scale = (h * (-1 if rng.random() < 0.5 else 1), h, h)     # mirrored half the time
    crowd.objects.link(ob)
    placed.append(p)

tries = 0
while len(placed) < COUNT and tries < 20000:
    tries += 1
    y = rng.uniform(*DEPTH)
    x = rng.uniform(-y * 1.3 - 2, y * 1.3 + 2)
    p = Vector((x, y, 0))
    h = HEIGHT * (1 + rng.uniform(-HEIGHT_VAR, HEIGHT_VAR))
    if not in_frame(p, h): continue
    if any((p - q).length < MIN_GAP for q in placed): continue
    to_chair = math.atan2(target.y - y, target.x - x) - math.pi / 2      # the model faces -y after import
    yaw = to_chair + rng.uniform(-0.6, 0.6) if rng.random() < FACE_CHAIR else rng.uniform(-math.pi, math.pi)
    add_person(p, yaw, h, len(placed))
    if rng.random() < PAIR_CHANCE and len(placed) < COUNT:              # a companion, half a step away
        ang = rng.uniform(0, 2 * math.pi); d = rng.uniform(0.38, 0.6)
        q = p + Vector((math.cos(ang) * d, math.sin(ang) * d, 0))
        h2 = HEIGHT * (1 + rng.uniform(-HEIGHT_VAR, HEIGHT_VAR))
        if in_frame(q, h2):
            add_person(q, math.atan2(p.y - q.y, p.x - q.x) - math.pi / 2 + rng.uniform(-0.5, 0.5), h2, len(placed))

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
