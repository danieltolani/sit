# RAS — the home-page scene, rebuilt in Blender for quick look revisions.
#
# Run it from Blender's Scripting tab (Open > this file > Run Script), or:  blender -P build_ras_scene.py
# It clears the current file, builds everything from the numbers below (which mirror web/src/lib/scenes.ts and
# web/src/lib/grass.ts), and saves blender/ras_scene.blend next to this script. Re-running rebuilds from scratch,
# so tweak by hand in the .blend, then copy the numbers you like back up here (and into the site).
#
# Where to revise once it's built:
#   Grass       select "Grass" > Modifiers > "RAS Grass": density, height, width, edge fade, tufts, wind, seed
#   Grass tone  Shader editor on "RAS Grass" material: the ROOT/BLADE/TIP/MEADOW colours + "Brightness"
#   Sand        "RAS Sand" material: NEAR/FAR colours, "Fade From", "Streak Roughness"
#   Chair       the "Chair" empty: move / rotate / scale it (child is the Poly Haven mesh)
#   Dancers     "Dancers" collection: hide it with the eye icon; each "Dancer" empty sits on the ring
#   Camera      orthographic, 32° down, same framing maths as the site (Ortho Scale + Shift Y)
#
# Axes: the site is Y-up, Blender is Z-up. site (x, y, z)  ->  Blender (x, -z, y). Site "z = -0.145" (further
# back) is Blender y = +0.145.

import bpy, bmesh, math, os
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))  # the blender/ folder this script lives in
RAS = os.path.dirname(HERE)  # .../RAS
ASSETS = os.path.join(HERE, 'assets')
CHAIR_GLTF = os.path.join(RAS, 'web', 'source-models', 'plastic_monobloc_chair_01_1k.gltf', 'plastic_monobloc_chair_01_1k.gltf')
DANCER_GLB = os.path.join(ASSETS, 'dancer-dance.glb')
OUT_BLEND = os.path.join(HERE, 'ras_scene.blend')

# ---- numbers from the site (scenes.ts "home" preset + grass.ts defaults) -----------------------------------
TILT = 32.0                 # camera elevation, degrees
OVAL = 0.45                 # on-screen height / width of the ring and patch
RADIUS = 1.15               # walkers' ring
PATCH_REACH = 1.24          # grass edge as a multiple of RADIUS
DEPTH = OVAL / math.sin(math.radians(TILT))
RING_A, RING_B = RADIUS, RADIUS * DEPTH
PATCH_A, PATCH_B = RADIUS * PATCH_REACH, RADIUS * PATCH_REACH * DEPTH

BLADES = 220_000            # over the patch; denser than the site (70k) so the toes of a print read
BLADE_HEIGHT = 0.09
BLADE_HALF_WIDTH = 0.008
EDGE_FROM, RIM_SIZE = 0.45, 0.42
TUFT_REACH, TUFT_DENSITY = 1.18, 0.9
WIND_STRENGTH_DEG, WIND_SPEED = 14.0, 0.5
BRIGHTNESS = 0.85           # grass + soil tone, on top of the flag-green palette below

# Footprints: six unseen aspirants pacing round the chair, musical-chairs tension. Only their prints show:
# the grass sinks and darkens where a foot lands, holds, then slowly recovers.
PRINTS = dict(
    walkers=1, duration=23.0, seed=7,
    start=0.62,                                            # where on the ring he starts (0..1 of a lap; 0.62 = front left)
    ring=0.72,                                             # his path, as a share of the walkers' ring: big feet need room inside the rim
    stride=(0.55, 0.68), step_time=(1.15, 1.6),            # one heavy, unhurried step at a time
    shuffle_chance=0.0, shuffle_stride=0.3, shuffle_time=0.45,
    fidget_chance=0.15, fidget_pause=(1.0, 2.0),           # stops, shifts his weight, a foot re-pressed at an angle
    freezes=[(5.2, 7.4), (11.8, 14.6), (18.6, 20.4)],      # stops dead, feet together, turns to face the chair
    freeze_turn=0.5, restart_stagger=0.3,
    gauge=0.17, toe_out=0.12,                              # half the gap between his feet; feet angle outward
    half_length=0.30,                                      # MIGHTY: each foot 0.6 long, three-quarters of the chair
    lift=0.6,                                              # only his two current prints show: the old one recovers
                                                           # over this many seconds once that foot lands again
    flatten=0.97, lie_deg=45.0,                            # pressed nearly flat; blades stay inside the print
)
# Bare-foot print, in units of the half length, u along the foot (heel -1 .. toes +1), v towards the big-toe
# side: (centre u, centre v, radius u, radius v). Traced from the ink-print references (OVRA Figma 636:280).
FOOT_SHAPES = [
    (-0.68, 0.02, 0.32, 0.29),     # heel
    (-0.15, -0.10, 0.45, 0.22),    # outer arch: joins heel and ball along the outside of the foot
    (0.28, 0.03, 0.30, 0.36),      # ball
    (0.76, 0.20, 0.15, 0.14),      # big toe
    (0.84, -0.04, 0.10, 0.095),    # toes 2..5, shrinking towards the outside
    (0.80, -0.20, 0.09, 0.085),
    (0.72, -0.33, 0.085, 0.08),
    (0.61, -0.43, 0.08, 0.075),
]
TRODDEN = '#06261A'
# Nigerian flag greens: #008751 (official) and #1B7339 carry the blades; roots go deeper, meadow patches a touch lighter
COL = dict(root='#0A3A22', blade='#1B7339', tip='#7ED69A', meadow='#2E9A5C', shade='#000000')   # tip: light tint of #008751
TIP_BAND = (0.75, 1.0)      # the tip colour only in the top quarter of each blade (0 = root, 1 = tip)
SAND_REACH, SAND_FADE_FROM = 1.7, 0.5
SAND_NEAR, SAND_FAR = '#dcc48e', '#e2ddd2'

CHAIR = dict(scale=0.9, x=0.0, z=-0.145, turn=-28.0)   # site units (z negative = further back)
CHAIR_DIRT = 0.15          # 0 = spotless white plastic, 1 = the Poly Haven scan as photographed (grimy)
CHAIR_CLEAN = '#C5C5C1'      # off-white: under Standard view (no highlight roll-off) brighter whites clip in full sun
SHOW_DANCERS = False        # they're still built (in the Dancers collection), just hidden
DANCERS = dict(count=6, scale=0.62, outfits=['#e4ad7b', '#ffffff', '#e4ad7b', '#ffffff', '#e4ad7b', '#ffffff'])

FIT = dict(width=1.0, pad=0.4, min_height=3.6, lift=-0.2)
RES = (1920, 1080)


# ---- helpers ----------------------------------------------------------------------------------------------
def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def hex_rgba(h):
    h = h.lstrip('#')
    return tuple(srgb_to_linear(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)) + (1.0,)

def inp(node, name):
    for s in node.inputs:
        if (s.name == name or s.identifier == name) and s.enabled:
            return s
    raise KeyError(f'{node.bl_idname} has no enabled input {name!r}')

def out(node, name=None):
    if name is None:
        return next(s for s in node.outputs if s.enabled)
    for s in node.outputs:
        if (s.name == name or s.identifier == name) and s.enabled:
            return s
    raise KeyError(f'{node.bl_idname} has no enabled output {name!r}')

class Graph:
    """Tiny helper so node trees read like expressions: g.math('MULTIPLY', a, 2.0)."""
    def __init__(self, tree, shader):
        self.t, self.shader, self.x = tree, shader, 0

    def node(self, kind, **props):
        n = self.t.nodes.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        n.location = (self.x, 0); self.x += 40
        return n

    def link(self, a, b):
        if isinstance(a, (int, float)):
            b.default_value = a
        elif isinstance(a, tuple):
            b.default_value = a
        else:
            self.t.links.new(a, b)

    def math(self, op, a, b=None, c=None):
        n = self.node('ShaderNodeMath', operation=op)
        self.link(a, n.inputs[0])
        if b is not None: self.link(b, n.inputs[1])
        if c is not None: self.link(c, n.inputs[2])
        return n.outputs[0]

    def smooth(self, x, lo, hi):
        n = self.node('ShaderNodeMapRange', data_type='FLOAT', interpolation_type='SMOOTHSTEP', clamp=True)
        self.link(x, inp(n, 'Value')); self.link(lo, inp(n, 'From Min')); self.link(hi, inp(n, 'From Max'))
        return out(n, 'Result')

    def mixf(self, f, a, b):
        n = self.node('ShaderNodeMix', data_type='FLOAT')
        self.link(f, inp(n, 'Factor_Float')); self.link(a, inp(n, 'A_Float')); self.link(b, inp(n, 'B_Float'))
        return out(n, 'Result_Float')

    def mixc(self, f, a, b):
        n = self.node('ShaderNodeMix', data_type='RGBA', blend_type='MIX')
        self.link(f, inp(n, 'Factor_Float')); self.link(a, inp(n, 'A_Color')); self.link(b, inp(n, 'B_Color'))
        return out(n, 'Result_Color')

    def mulc(self, f, a):
        n = self.node('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
        inp(n, 'Factor_Float').default_value = 1.0
        self.link(a, inp(n, 'A_Color'))
        if isinstance(f, (int, float)):
            inp(n, 'B_Color').default_value = (f, f, f, 1.0)
        else:
            self.link(f, inp(n, 'B_Color'))
        return out(n, 'Result_Color')

    def sep(self, v):
        n = self.node('ShaderNodeSeparateXYZ'); self.link(v, n.inputs[0]); return n.outputs

    def comb(self, x, y, z):
        n = self.node('ShaderNodeCombineXYZ')
        self.link(x, n.inputs[0]); self.link(y, n.inputs[1]); self.link(z, n.inputs[2])
        return n.outputs[0]

    def noise(self, vec, scale, w=None):
        n = self.node('ShaderNodeTexNoise', noise_dimensions='4D' if w is not None else '3D')
        self.link(vec, inp(n, 'Vector')); inp(n, 'Scale').default_value = scale
        inp(n, 'Detail').default_value = 1.0
        if w is not None: self.link(w, inp(n, 'W'))
        return out(n, 'Fac')

    def value(self, v, label):
        n = self.node('ShaderNodeValue'); n.outputs[0].default_value = v; n.label = label; n.name = label
        return n.outputs[0]

    def rgb(self, hexstr, label):
        n = self.node('ShaderNodeRGB'); n.outputs[0].default_value = hex_rgba(hexstr); n.label = label; n.name = label
        return n.outputs[0]


# ---- clean slate ------------------------------------------------------------------------------------------
scene = bpy.context.scene
scene.name = 'RAS'
scene.unit_settings.system = 'METRIC'
# clear everything this script makes (and the default cube/camera/light), keeping the open file itself
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
for coll in (bpy.data.collections, bpy.data.meshes, bpy.data.materials, bpy.data.node_groups, bpy.data.cameras,
             bpy.data.lights, bpy.data.armatures, bpy.data.actions, bpy.data.images, bpy.data.worlds):
    for d in list(coll):
        try: coll.remove(d)
        except Exception: pass

def collection(name):
    c = bpy.data.collections.new(name); scene.collection.children.link(c); return c

def link_to(obj, coll):
    for c in obj.users_collection: c.objects.unlink(obj)
    coll.objects.link(obj)

ground = collection('Ground')
props = collection('Chair')
dancers_coll = collection('Dancers')
rig = collection('Camera & Light')


# ---- ellipse discs ----------------------------------------------------------------------------------------
def ellipse_mesh(name, a, b, segments=160):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    verts = [bm.verts.new((a * math.cos(2 * math.pi * i / segments), b * math.sin(2 * math.pi * i / segments), 0)) for i in range(segments)]
    bm.faces.new(verts)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(me); bm.free()
    return me


# ---- materials --------------------------------------------------------------------------------------------
def new_material(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    return m, Graph(m.node_tree, True)

def principled(g, color, alpha=None, up_normals=True):
    bsdf = g.node('ShaderNodeBsdfPrincipled')
    g.link(color, inp(bsdf, 'Base Color'))
    inp(bsdf, 'Roughness').default_value = 1.0
    if up_normals:  # every blade lit like the ground, as on the site (flat-up normals)
        g.link(g.comb(0.0, 0.0, 1.0), inp(bsdf, 'Normal'))
    if alpha is not None:
        g.link(alpha, inp(bsdf, 'Alpha'))
    o = g.node('ShaderNodeOutputMaterial')
    g.link(out(bsdf, 'BSDF'), inp(o, 'Surface'))
    return bsdf

def meadow_field(g, pos):
    # slow noise sharpened into soft patches of lighter grass (site: smoothstep(.45,.8, n(.9)*.7 + n(2.4)*.3))
    n1 = g.noise(pos, 0.9 * 2.0)
    n2 = g.noise(pos, 2.4 * 2.0)
    mixed = g.math('ADD', g.math('MULTIPLY', n1, 0.7), g.math('MULTIPLY', n2, 0.3))
    return g.smooth(mixed, 0.45, 0.8)

def front_factor(g, world_y, b):
    # site "q.y": +1 at the front of the patch (towards the camera). Blender front = -y.
    q = g.math('DIVIDE', g.math('MULTIPLY', world_y, -1.0), b)
    return g.smooth(q, 0.15, 1.0)

# Grass blades
grass_mat, g = new_material('RAS Grass')
root, blade, tip = g.rgb(COL['root'], 'ROOT'), g.rgb(COL['blade'], 'BLADE'), g.rgb(COL['tip'], 'TIP')
meadow_c, shade = g.rgb(COL['meadow'], 'MEADOW'), g.rgb(COL['shade'], 'SHADE')
bright = g.value(BRIGHTNESS, 'Brightness')
uv = g.node('ShaderNodeUVMap')
t = g.sep(out(uv, 'UV'))[1]                                    # blade mesh: v = 0 at the root, 1 at the tip
geo = g.node('ShaderNodeNewGeometry')
pos = out(geo, 'Position')
px, py, _ = g.sep(pos)
col = g.mixc(g.math('POWER', t, 0.8), root, blade)            # dark at the root...
col = g.mixc(g.math('MULTIPLY', g.smooth(t, *TIP_BAND), 0.9), col, tip)   # ...lighter in the top quarter
light = g.mixc(g.math('MULTIPLY', t, 0.7), meadow_c, tip)
col = g.mixc(g.math('MULTIPLY', meadow_field(g, pos), 0.85), col, light)
var = g.mixf(g.noise(pos, 2.6 * 2.0), 0.9, 1.08)
col = g.mulc(var, col)
col = g.mixc(g.math('MULTIPLY', front_factor(g, py, PATCH_B), 0.3), col, shade)
press_attr = g.node('ShaderNodeAttribute', attribute_type='INSTANCER', attribute_name='press')
trodden = g.rgb(TRODDEN, 'TRODDEN')
col = g.mixc(g.math('MULTIPLY', out(press_attr, 'Fac'), 0.85), col, trodden)   # footprints: darker, flattened grass
col = g.mulc(bright, col)
principled(g, col)

# Soil disc under the blades
soil_mat, g = new_material('RAS Soil')
root, blade = g.rgb(COL['root'], 'ROOT'), g.rgb(COL['blade'], 'BLADE')
meadow_c, shade = g.rgb(COL['meadow'], 'MEADOW'), g.rgb(COL['shade'], 'SHADE')
bright = g.value(BRIGHTNESS, 'Brightness')
tc = g.node('ShaderNodeTexCoord')
loc = g.sep(out(tc, 'Object'))                                 # unit-ish ellipse in object space
geo = g.node('ShaderNodeNewGeometry')
wpos = out(geo, 'Position'); _, wy, _ = g.sep(wpos)
gr = g.math('SQRT', g.math('ADD', g.math('POWER', g.math('DIVIDE', loc[0], PATCH_A), 2.0), g.math('POWER', g.math('DIVIDE', loc[1], PATCH_B), 2.0)))
col = g.mixc(0.55, root, blade)
col = g.mixc(g.math('MULTIPLY', meadow_field(g, wpos), 0.5), col, meadow_c)
col = g.mixc(g.math('MULTIPLY', front_factor(g, wy, PATCH_B), 0.35), col, shade)
col = g.mixc(g.math('MULTIPLY', g.smooth(gr, 0.8, 1.0), 0.25), col, root)
col = g.mulc(bright, col)
alpha = g.math('SUBTRACT', 1.0, g.smooth(gr, 0.9, 1.0))
principled(g, col, alpha)
soil_mat.surface_render_method = 'BLENDED'

# Sand apron: warm by the grass, dusty far out, fading in dry-brush streaks that run horizontally at the sides
# and curve with the rim at the front and back (same idea as streakAt() in grass.ts)
sand_mat, g = new_material('RAS Sand')
near, far = g.rgb(SAND_NEAR, 'NEAR'), g.rgb(SAND_FAR, 'FAR')
shade = g.rgb(COL['shade'], 'SHADE')
fade_from = g.value(SAND_FADE_FROM, 'Fade From')
rough = g.value(0.45, 'Streak Roughness')
tc = g.node('ShaderNodeTexCoord')
lx, ly, _ = g.sep(out(tc, 'Object'))
ux = g.math('DIVIDE', lx, PATCH_A * SAND_REACH); uy = g.math('DIVIDE', ly, PATCH_B * SAND_REACH)   # unit disc
sr = g.math('MAXIMUM', g.math('SQRT', g.math('ADD', g.math('POWER', ux, 2.0), g.math('POWER', uy, 2.0))), 1e-4)
outer = g.smooth(sr, 1.0 / SAND_REACH - 0.02, 1.0)
# stroke direction d: (1,0) at the sides, the rim tangent (sign-flipped to point +x) at the front/back
tx = g.math('DIVIDE', g.math('MULTIPLY', uy, -1.0), sr); ty = g.math('DIVIDE', ux, sr)
sgn = g.math('SIGN', g.math('ADD', tx, 1e-6))
tx = g.math('MULTIPLY', tx, sgn); ty = g.math('MULTIPLY', ty, sgn)
w = g.math('POWER', g.math('DIVIDE', uy, sr), 2.0)
dx = g.mixf(w, 1.0, tx); dy = g.mixf(w, 0.0, ty)
dl = g.math('MAXIMUM', g.math('SQRT', g.math('ADD', g.math('POWER', dx, 2.0), g.math('POWER', dy, 2.0))), 1e-4)
dx = g.math('DIVIDE', dx, dl); dy = g.math('DIVIDE', dy, dl)
along = g.math('ADD', g.math('MULTIPLY', ux, dx), g.math('MULTIPLY', uy, dy))
across = g.math('ADD', g.math('MULTIPLY', ux, g.math('MULTIPLY', dy, -1.0)), g.math('MULTIPLY', uy, dx))
q = g.comb(g.math('MULTIPLY', along, 3.4), g.math('MULTIPLY', across, 16.0), 0.0)
streak = g.math('ADD', g.math('MULTIPLY', g.noise(q, 1.0), 0.6), g.math('MULTIPLY', g.noise(q, 2.4), 0.4))
col = g.mixc(g.smooth(outer, 0.0, 0.85), near, far)
col = g.mulc(g.mixf(streak, 0.88, 1.1), col)
alpha = g.math('SUBTRACT', 1.0, g.smooth(g.math('ADD', outer, g.math('MULTIPLY', g.math('SUBTRACT', streak, 0.5), rough)), fade_from, 1.0))
principled(g, col, alpha, up_normals=True)
sand_mat.surface_render_method = 'BLENDED'


# ---- ground objects ---------------------------------------------------------------------------------------
sand = bpy.data.objects.new('Sand', ellipse_mesh('Sand', PATCH_A * SAND_REACH, PATCH_B * SAND_REACH))
sand.data.materials.append(sand_mat); sand.location.z = 0.0005; ground.objects.link(sand)
soil = bpy.data.objects.new('Soil', ellipse_mesh('Soil', PATCH_A, PATCH_B))
soil.data.materials.append(soil_mat); soil.location.z = 0.001; ground.objects.link(soil)

# One blade: tapered, slightly bowed forward, UV v = 0 root .. 1 tip. Unit height, unit half-width.
blade_me = bpy.data.meshes.new('Blade')
bm = bmesh.new()
rows = [0.0, 0.33, 0.66, 1.0]
ring = []
for tt in rows:
    hw = (1 - tt) * (1 + 0.45 * tt)
    y = 0.18 * tt * tt                         # the bow
    ring.append([bm.verts.new((-hw, y, tt)), bm.verts.new((hw, y, tt))] if tt < 1 else [bm.verts.new((0, y, tt))])
faces = []
for i in range(len(rows) - 1):
    a, b = ring[i], ring[i + 1]
    faces.append(bm.faces.new(a + list(reversed(b))) if len(b) == 2 else bm.faces.new(a + b))
uvl = bm.loops.layers.uv.new('UVMap')
for f in bm.faces:
    for l in f.loops:
        l[uvl].uv = ((l.vert.co.x + 1) / 2, l.vert.co.z)
bm.to_mesh(blade_me); bm.free()
blade_obj = bpy.data.objects.new('Blade (source)', blade_me)
blade_obj.data.materials.append(grass_mat)
ground.objects.link(blade_obj)
blade_obj.hide_render = True; blade_obj.hide_viewport = True; blade_obj.location = (0, 0, -5)

# Grass: a disc out to the tuft reach, with the Geometry Nodes doing everything else
def footsteps(P):
    """Footfalls for each walker: (x, y, yaw, born). The ring is walked anticlockwise seen from above (as on the
    site); yaw is the direction the foot points."""
    import random
    n = 2000
    RA, RB = RING_A * P['ring'], RING_B * P['ring']
    pts = [(RA * math.cos(2 * math.pi * i / n), RB * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]
    cum = [0.0]
    for i in range(1, n + 1): cum.append(cum[-1] + math.dist(pts[i], pts[i - 1]))
    L = cum[-1]
    def at(s):
        s %= L
        lo, hi = 0, n
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if cum[mid] <= s: lo = mid
            else: hi = mid
        f = (s - cum[lo]) / ((cum[hi] - cum[lo]) or 1)
        ph = 2 * math.pi * (lo + f) / n
        x, y = RA * math.cos(ph), RB * math.sin(ph)
        dx, dy = -RA * math.sin(ph), RB * math.cos(ph)
        k = math.hypot(dx, dy); dx, dy = dx / k, dy / k
        return x, y, math.atan2(dy, dx), (-dy, dx)        # position, heading, inward normal (left of travel)
    out_ = []
    for w in range(P['walkers']):
        rng = random.Random(P['seed'] * 101 + w)
        s = (P['start'] + w / P['walkers']) * L
        t = 0.15 * w + rng.uniform(0, 0.3)
        left = rng.random() < 0.5                          # which foot moves next
        last = {}                                          # last print of each foot: (s, side)
        def press(s_, is_left, born, turn=0.0, nudge=0.0):
            x, y, head, (nx, ny) = at(s_)
            side = 1 if is_left else -1
            x += nx * side * P['gauge']; y += ny * side * P['gauge']
            yaw = head + side * P['toe_out'] + turn + nudge
            out_.append((x, y, yaw, born, side)); last[is_left] = s_
        # standing start: both feet down, a while ago (already recovered)
        press(s, True, -60.0); press(s, False, -60.0)
        wi = 0
        while t < P['duration']:
            if wi < len(P['freezes']) and t >= P['freezes'][wi][0]:
                ws, we = P['freezes'][wi]; wi += 1
                lead = not left                            # the foot that last landed
                # trailing foot comes alongside, both turn in towards the chair
                press(last.get(lead, s), not lead, ws + 0.1, turn=P['freeze_turn'])
                press(last.get(lead, s), lead, ws + 0.45, turn=P['freeze_turn'] * 0.8)
                left = rng.random() < 0.5
                t = we + rng.uniform(0, P['restart_stagger'])
                continue
            r = rng.random()
            if r < P['fidget_chance']:                     # hesitate: re-press a foot, slightly twisted
                foot = not left
                press(last.get(foot, s), foot, t + 0.3, nudge=rng.uniform(-0.25, 0.25))
                t += rng.uniform(*P['fidget_pause'])
            elif r < P['fidget_chance'] + P['shuffle_chance']:   # two quick, short, nervous steps
                for _ in range(2):
                    s += P['shuffle_stride']; press(s, left, t); left = not left; t += P['shuffle_time']
            else:                                          # one slow, careful step
                s += rng.uniform(*P['stride']); press(s, left, t); left = not left
                t += rng.uniform(*P['step_time'])
    # each print holds until that same foot lands again, then recovers
    out_.sort(key=lambda p: p[3])
    nxt = {}
    res = []
    for x, y, yaw, born, side in reversed(out_):
        res.append((x, y, yaw, born, side, nxt.get(side, 1e6)))
        nxt[side] = born
    return list(reversed(res))

steps = footsteps(PRINTS)
fp_me = bpy.data.meshes.new('Footprints')
fp_me.from_pydata([(st[0], st[1], 0.0) for st in steps], [], [])
for name, idx in (('yaw', 2), ('born', 3), ('side', 4), ('until', 5)):
    vals = [float(st[idx]) for st in steps]
    a_ = fp_me.attributes.new(name, 'FLOAT', 'POINT'); a_.data.foreach_set('value', vals)
footprints = bpy.data.objects.new('Footprints', fp_me)   # points only: they never render, the grass reads them
ground.objects.link(footprints)
footprints.hide_render = True

grass = bpy.data.objects.new('Grass', ellipse_mesh('GrassArea', PATCH_A * TUFT_REACH, PATCH_B * TUFT_REACH))
ground.objects.link(grass)

ng = bpy.data.node_groups.new('RAS Grass', 'GeometryNodeTree')
iface = ng.interface
def sock(name, kind, default=None, lo=None, hi=None, io='INPUT', desc=''):
    s = iface.new_socket(name, in_out=io, socket_type=kind)
    if default is not None: s.default_value = default
    if lo is not None: s.min_value = lo
    if hi is not None: s.max_value = hi
    s.description = desc
    return s
sock('Geometry', 'NodeSocketGeometry')
sock('Geometry', 'NodeSocketGeometry', io='OUTPUT')
S = {}
S['blade'] = sock('Blade', 'NodeSocketObject', desc='the blade mesh to scatter')
S['count'] = sock('Blades', 'NodeSocketInt', BLADES, 0, 500000, desc='blades over the patch (the site uses 70k)')
S['height'] = sock('Blade Height', 'NodeSocketFloat', BLADE_HEIGHT, 0, 1)
S['width'] = sock('Blade Half Width', 'NodeSocketFloat', BLADE_HALF_WIDTH, 0, 0.1)
S['a'] = sock('Patch A', 'NodeSocketFloat', PATCH_A, 0.01, 20, desc='half-width of the grass (x)')
S['b'] = sock('Patch B', 'NodeSocketFloat', PATCH_B, 0.01, 20, desc='half-depth of the grass (y)')
S['from'] = sock('Edge From', 'NodeSocketFloat', EDGE_FROM, 0, 1, desc='where blades start shrinking (0..1 of the radius)')
S['rim'] = sock('Rim Size', 'NodeSocketFloat', RIM_SIZE, 0, 1, desc='blade size at the rim')
S['treach'] = sock('Tuft Reach', 'NodeSocketFloat', TUFT_REACH, 1, 2, desc='how far stray tufts go past the rim')
S['tdens'] = sock('Tuft Density', 'NodeSocketFloat', TUFT_DENSITY, 0, 1)
S['wind'] = sock('Wind Strength (deg)', 'NodeSocketFloat', WIND_STRENGTH_DEG, 0, 60)
S['speed'] = sock('Wind Speed', 'NodeSocketFloat', WIND_SPEED, 0, 5)
S['lean'] = sock('Random Lean (deg)', 'NodeSocketFloat', 10.0, 0, 45)
S['seed'] = sock('Seed', 'NodeSocketInt', 0)
S['prints'] = sock('Footprints', 'NodeSocketObject', desc='points with born / until (s), yaw, side (+1 left, -1 right)')
S['lift'] = sock('Print Recover (s)', 'NodeSocketFloat', PRINTS['lift'], 0.01, 30, desc='how long a print takes to recover once that foot lands again')
S['flen'] = sock('Foot Half Length', 'NodeSocketFloat', PRINTS['half_length'], 0.01, 2)
S['flat'] = sock('Flatten', 'NodeSocketFloat', PRINTS['flatten'], 0, 1)
S['lie'] = sock('Trodden Lean (deg)', 'NodeSocketFloat', PRINTS['lie_deg'], 0, 90)

G = Graph(ng, False)
gin = G.node('NodeGroupInput'); gout = G.node('NodeGroupOutput')
def I(key): return next(o for o in gin.outputs if o.identifier == S[key].identifier)

area = G.math('MULTIPLY', G.math('MULTIPLY', math.pi, I('a')), I('b'))
density = G.math('DIVIDE', I('count'), area)
dist = G.node('GeometryNodeDistributePointsOnFaces', distribute_method='RANDOM')
G.link(gin.outputs[0], inp(dist, 'Mesh')); G.link(density, inp(dist, 'Density')); G.link(I('seed'), inp(dist, 'Seed'))

posn = G.node('GeometryNodeInputPosition')
x, y, _ = G.sep(out(posn))
r = G.math('SQRT', G.math('ADD', G.math('POWER', G.math('DIVIDE', x, I('a')), 2.0), G.math('POWER', G.math('DIVIDE', y, I('b')), 2.0)))

# keep everything inside the rim; past it, only a thinning scatter of tufts
over = G.math('MINIMUM', G.math('MAXIMUM', G.math('DIVIDE', G.math('SUBTRACT', r, 1.0), G.math('SUBTRACT', I('treach'), 1.0)), 0.0), 1.0)
inside = G.math('LESS_THAN', r, 1.0)
keep = G.mixf(inside, G.math('MULTIPLY', I('tdens'), G.math('SUBTRACT', 1.0, over)), 1.0)
rnd = G.node('FunctionNodeRandomValue', data_type='FLOAT'); G.link(G.math('ADD', I('seed'), 7), inp(rnd, 'Seed'))
cmp = G.node('FunctionNodeCompare', data_type='FLOAT', operation='LESS_THAN')
G.link(out(rnd, 'Value'), inp(cmp, 'A')); G.link(keep, inp(cmp, 'B'))
delete = G.node('GeometryNodeDeleteGeometry', domain='POINT')
G.link(out(dist, 'Points'), inp(delete, 'Geometry'))
notkeep = G.node('FunctionNodeBooleanMath', operation='NOT'); G.link(out(cmp), notkeep.inputs[0])
G.link(out(notkeep), inp(delete, 'Selection'))

# the fade: blades keep their density but shrink towards the rim (site: mix(rim, 1, 1 - smoothstep(from, 1, r)))
edge = G.mixf(G.math('SUBTRACT', 1.0, G.smooth(r, I('from'), 1.0)), I('rim'), 1.0)
edge = G.math('MULTIPLY', edge, G.math('SUBTRACT', 1.0, G.math('MULTIPLY', G.smooth(r, 1.0, I('treach')), 0.6)))
def rand(lo, hi, seed_off):
    n = G.node('FunctionNodeRandomValue', data_type='FLOAT')
    inp(n, 'Min').default_value = lo; inp(n, 'Max').default_value = hi
    G.link(G.math('ADD', I('seed'), seed_off), inp(n, 'Seed'))
    return out(n, 'Value')
# footprints: the prints standing right now (landed, not yet recovered), the nearest one, and a bare-foot mask
fpinfo = G.node('GeometryNodeObjectInfo', transform_space='RELATIVE'); G.link(I('prints'), inp(fpinfo, 'Object'))
tnow = out(G.node('GeometryNodeInputSceneTime'), 'Seconds')
def attr(name):
    n = G.node('GeometryNodeInputNamedAttribute', data_type='FLOAT'); inp(n, 'Name').default_value = name
    return out(n, 'Attribute')
gone = G.node('FunctionNodeBooleanMath', operation='OR')
G.link(G.math('GREATER_THAN', attr('born'), tnow), gone.inputs[0])
G.link(G.math('LESS_THAN', G.math('ADD', attr('until'), I('lift')), tnow), gone.inputs[1])
standing = G.node('GeometryNodeDeleteGeometry', domain='POINT')
G.link(out(fpinfo, 'Geometry'), inp(standing, 'Geometry')); G.link(out(gone), inp(standing, 'Selection'))
live = out(standing)
nprints = G.node('GeometryNodeAttributeDomainSize', component='MESH'); G.link(live, inp(nprints, 'Geometry'))
nearest = G.node('GeometryNodeSampleNearest', domain='POINT')
G.link(live, inp(nearest, 'Geometry')); G.link(out(posn), inp(nearest, 'Sample Position'))
def sample(field, vec=False):
    n = G.node('GeometryNodeSampleIndex', data_type='FLOAT_VECTOR' if vec else 'FLOAT', domain='POINT')
    G.link(live, inp(n, 'Geometry')); G.link(field, inp(n, 'Value')); G.link(out(nearest, 'Index'), inp(n, 'Index'))
    return out(n, 'Value')
fpp = G.sep(sample(out(G.node('GeometryNodeInputPosition')), vec=True))
fyaw, fborn, funtil, fside = sample(attr('yaw')), sample(attr('born')), sample(attr('until')), sample(attr('side'))
ox = G.math('SUBTRACT', x, fpp[0]); oy = G.math('SUBTRACT', y, fpp[1])
cy, sy = G.math('COSINE', fyaw), G.math('SINE', fyaw)
along = G.math('ADD', G.math('MULTIPLY', ox, cy), G.math('MULTIPLY', oy, sy))
across = G.math('SUBTRACT', G.math('MULTIPLY', oy, cy), G.math('MULTIPLY', ox, sy))   # + = the foot's left
fu = G.math('DIVIDE', along, I('flen'))
fv = G.math('DIVIDE', G.math('MULTIPLY', across, G.math('MULTIPLY', fside, -1.0)), I('flen'))   # + = big-toe side
shape = None
for cu, cv, ru, rv in FOOT_SHAPES:
    d = G.math('SQRT', G.math('ADD', G.math('POWER', G.math('DIVIDE', G.math('SUBTRACT', fu, cu), ru), 2.0),
                                     G.math('POWER', G.math('DIVIDE', G.math('SUBTRACT', fv, cv), rv), 2.0)))
    m = G.math('SUBTRACT', 1.0, G.smooth(d, 0.8, 1.05))
    shape = m if shape is None else G.math('MAXIMUM', shape, m)
sink = G.smooth(G.math('SUBTRACT', tnow, fborn), 0.0, 0.18)           # the foot lands, heavy
recover = G.math('SUBTRACT', 1.0, G.smooth(tnow, funtil, G.math('ADD', funtil, I('lift'))))   # lifts as that foot steps again
press = G.math('MULTIPLY', G.math('MULTIPLY', shape, G.math('MULTIPLY', sink, recover)), G.math('GREATER_THAN', out(nprints, 'Point Count'), 0.5))

h = G.math('MULTIPLY', G.math('MULTIPLY', I('height'), rand(0.6, 1.0, 11)), edge)
h = G.math('MULTIPLY', h, G.math('SUBTRACT', 1.0, G.math('MULTIPLY', I('flat'), press)))   # trodden blades sink
wdt = G.math('MULTIPLY', G.math('MULTIPLY', I('width'), rand(0.75, 1.25, 23)), G.mixf(edge, 0.55, 1.0))
scale = G.comb(wdt, wdt, h)

# rotation: random yaw, then (in world space) a little random lean plus the wind
yaw = G.node('FunctionNodeEulerToRotation'); G.link(G.comb(0.0, 0.0, rand(0.0, 2 * math.pi, 37)), yaw.inputs[0])
time = G.node('GeometryNodeInputSceneTime')
w4 = G.math('MULTIPLY', out(time, 'Seconds'), I('speed'))
gust = G.node('ShaderNodeTexNoise', noise_dimensions='4D')
G.link(out(posn), inp(gust, 'Vector')); G.link(w4, inp(gust, 'W')); inp(gust, 'Scale').default_value = 0.9; inp(gust, 'Detail').default_value = 1.0
gustv = G.smooth(out(gust, 'Fac'), 0.3, 0.85)
rip = G.node('ShaderNodeTexNoise', noise_dimensions='4D')
G.link(out(posn), inp(rip, 'Vector')); G.link(G.math('MULTIPLY', w4, 3.0), inp(rip, 'W')); inp(rip, 'Scale').default_value = 4.4
ripv = G.math('SUBTRACT', out(rip, 'Fac'), 0.5)
windamt = G.math('ADD', G.math('ADD', 0.1, G.math('MULTIPLY', gustv, 0.85)), G.math('MULTIPLY', ripv, 0.25))
wind = G.math('MULTIPLY', windamt, G.math('RADIANS', I('wind')))
leanr = G.math('RADIANS', I('lean'))
lx = G.math('MULTIPLY', rand(-1.0, 1.0, 41), leanr); ly = G.math('MULTIPLY', rand(-1.0, 1.0, 53), leanr)
lie_dir = rand(0.0, 2 * math.pi, 61); lie = G.math('MULTIPLY', press, G.math('RADIANS', I('lie')))
lx = G.math('ADD', lx, G.math('MULTIPLY', lie, G.math('COSINE', lie_dir)))
ly = G.math('ADD', G.math('MULTIPLY', ly, G.math('SUBTRACT', 1.0, press)), G.math('MULTIPLY', lie, G.math('SINE', lie_dir)))
wind = G.math('MULTIPLY', wind, G.math('SUBTRACT', 1.0, press))          # a trodden blade doesn't sway
tilt = G.node('FunctionNodeEulerToRotation'); G.link(G.comb(lx, G.math('ADD', ly, wind), 0.0), tilt.inputs[0])
rot = G.node('FunctionNodeRotateRotation', rotation_space='GLOBAL')
G.link(out(yaw), inp(rot, 'Rotation')); G.link(out(tilt), inp(rot, 'Rotate By'))

objinfo = G.node('GeometryNodeObjectInfo', transform_space='ORIGINAL'); G.link(I('blade'), inp(objinfo, 'Object'))
iop = G.node('GeometryNodeInstanceOnPoints')
G.link(out(delete), inp(iop, 'Points')); G.link(out(objinfo, 'Geometry'), inp(iop, 'Instance'))
G.link(out(rot), inp(iop, 'Rotation')); G.link(scale, inp(iop, 'Scale'))
setmat = G.node('GeometryNodeSetMaterial'); setmat.inputs['Material'].default_value = grass_mat
store = G.node('GeometryNodeStoreNamedAttribute', data_type='FLOAT', domain='INSTANCE')
inp(store, 'Name').default_value = 'press'
G.link(out(iop, 'Instances'), inp(store, 'Geometry')); G.link(press, inp(store, 'Value'))
G.link(out(store), inp(setmat, 'Geometry'))
G.link(out(setmat), gout.inputs[0])

mod = grass.modifiers.new('RAS Grass', 'NODES'); mod.node_group = ng
mod[S['blade'].identifier] = blade_obj
mod[S['prints'].identifier] = footprints


# ---- chair -----------------------------------------------------------------------------------------------
chair_root = bpy.data.objects.new('Chair', None)
chair_root.empty_display_type = 'PLAIN_AXES'; chair_root.empty_display_size = 0.3
chair_root.location = (CHAIR['x'], -CHAIR['z'], 0)
chair_root.rotation_euler = (0, 0, math.radians(CHAIR['turn']))
chair_root.scale = (CHAIR['scale'],) * 3
props.objects.link(chair_root)
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=CHAIR_GLTF)
chair_parts = set(bpy.data.objects) - before
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in chair_parts if o.type == 'MESH' for c in o.bound_box]
lo, hi = min(p.z for p in pts), max(p.z for p in pts)
k = 0.88 / (hi - lo)                 # the site's chair.glb is 0.88 tall; the Chair empty then scales it by 0.9
for o in chair_parts:
    link_to(o, props)
    if o.parent is None:
        o.scale = tuple(v * k for v in o.scale)
        o.location = (o.location.x * k, o.location.y * k, (o.location.z - lo) * k)
        o.parent = chair_root


# Clean the chair up: the scan's colour map has real grime baked in; blend it towards clean plastic.
for o in chair_parts:
    for slot in getattr(o, 'material_slots', []):
        m = slot.material
        if not m or not m.node_tree: continue
        nt = m.node_tree; g = Graph(nt, True)
        bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        link = next((l for l in nt.links if bsdf and l.to_socket == inp(bsdf, 'Base Color')), None)
        if not link: continue
        dirt = g.value(CHAIR_DIRT, 'Dirt'); clean = g.rgb(CHAIR_CLEAN, 'Clean Plastic')
        g.link(g.mixc(dirt, clean, link.from_socket), inp(bsdf, 'Base Color'))


# Recolour the clothes, as on the site (SeatScene.astro "dressed"): the character is one texture atlas, so the
# clothes are picked out by UV rectangles and by being dark (never skin); the texture's folds are kept.
# Rectangles are the site's (u0, v0, u1, v1) in glTF UV space; Blender's V is flipped (v -> 1 - v).
CLOTH_RECTS = [(0.0, 0.645, 0.55, 1.0), (0.55, 0.36, 0.77, 1.0), (0.25, 0.36, 0.57, 0.45), (0.76, 0.37, 0.90, 0.69)]
HAIR_RECT = (0.72, 0.22, 1.0, 0.40)
LEG_RECT = (0.22, 0.0, 0.76, 0.35)

def dress(src, jacket_hex, k):
    m = src.copy(); m.name = f'Dancer {k + 1} outfit'
    nt = m.node_tree; g = Graph(nt, True)
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    inp(bsdf, 'Roughness').default_value = 1.0; inp(bsdf, 'Metallic').default_value = 0.0   # matte, like clay
    for l in list(nt.links):
        if l.to_socket == inp(bsdf, 'Roughness') or l.to_socket == inp(bsdf, 'Metallic'): nt.links.remove(l)
    base_link = next((l for l in nt.links if l.to_socket == inp(bsdf, 'Base Color')), None)
    if not base_link: return m
    tex = base_link.from_socket
    uvn = g.node('ShaderNodeUVMap'); u, v, _ = g.sep(out(uvn, 'UV'))
    def rect(r):
        u0, v0, u1, v1 = r
        a = g.math('MULTIPLY', g.math('GREATER_THAN', u, u0), g.math('LESS_THAN', u, u1))
        b = g.math('MULTIPLY', g.math('GREATER_THAN', v, 1 - v1), g.math('LESS_THAN', v, 1 - v0))
        return g.math('MULTIPLY', a, b)
    cloth = rect(CLOTH_RECTS[0])
    for r in CLOTH_RECTS[1:]: cloth = g.math('MAXIMUM', cloth, rect(r))
    cloth = g.math('MULTIPLY', cloth, g.math('SUBTRACT', 1.0, rect(HAIR_RECT)))
    legs = rect(LEG_RECT)
    rgb = g.node('ShaderNodeRGBToBW'); g.link(tex, rgb.inputs[0]); lum = rgb.outputs[0]
    dark = g.math('SUBTRACT', 1.0, g.smooth(lum, 0.08, 0.2))
    shade = g.math('ADD', 0.45, g.math('MULTIPLY', g.math('POWER', lum, 0.45), 2.2))
    jc = hex_rgba(jacket_hex); tc = tuple(c * 0.35 for c in jc[:3]) + (1.0,)
    j = g.node('ShaderNodeRGB'); j.outputs[0].default_value = jc; j.label = 'JACKET'
    t = g.node('ShaderNodeRGB'); t.outputs[0].default_value = tc; t.label = 'TROUSERS'
    col = g.mixc(g.math('MULTIPLY', cloth, dark), tex, g.mulc(shade, out(j)))
    col = g.mixc(g.math('MULTIPLY', legs, dark), col, g.mulc(shade, out(t)))
    g.link(col, inp(bsdf, 'Base Color'))
    return m


# ---- dancers (optional; hide the collection) ---------------------------------------------------------------
if os.path.exists(DANCER_GLB) and DANCERS['count']:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=DANCER_GLB)
    imported = set(bpy.data.objects) - before
    for o in imported: link_to(o, dancers_coll)
    holders = []
    for i in range(DANCERS['count']):
        th = -2 * math.pi * i / DANCERS['count']
        px_, pz_ = RING_A * math.cos(th), RING_B * math.sin(th)          # site ring (x, z)
        dx_, dz_ = RING_A * math.sin(th), -RING_B * math.cos(th)         # walking direction
        e = bpy.data.objects.new(f'Dancer {i + 1}', None)
        e.empty_display_type = 'SINGLE_ARROW'; e.empty_display_size = 0.25
        e.location = (px_, -pz_, 0)
        e.rotation_euler = (0, 0, math.atan2(dx_, dz_))
        e.scale = (DANCERS['scale'],) * 3
        dancers_coll.objects.link(e)
        holders.append(e)
    # first copy is the imported one; the rest are linked duplicates (they share mesh, rig and the dance)
    copies = [list(imported)]
    for i in range(1, DANCERS['count']):
        mapping = {}
        for o in imported:
            c = o.copy(); dancers_coll.objects.link(c); mapping[o] = c
        for o, c in mapping.items():
            if o.parent in mapping: c.parent = mapping[o.parent]
            for m in c.modifiers:
                if m.type == 'ARMATURE' and m.object in mapping: m.object = mapping[m.object]
        copies.append(list(mapping.values()))
    for holder, objs in zip(holders, copies):
        for top in (o for o in objs if o.parent is None):
            top.parent = holder        # keeps the importer's own Y-up -> Z-up handling
        for o in objs:
            if o.type == 'MESH' and not o.data.materials:
                o.hide_render = o.hide_viewport = True   # the importer's bone-shape spheres
    for k, objs in enumerate(copies):
        for o in objs:
            if o.type != 'MESH' or not o.data.materials: continue
            for slot in o.material_slots:
                src = slot.material
                if src:
                    slot.link = 'OBJECT'   # per-dancer material while the mesh stays shared
                    slot.material = dress(src, DANCERS['outfits'][k % len(DANCERS['outfits'])], k)
    # the dance plays in place (in sync); on the site each dancer is 0.3 s behind and travels the ring


dancers_coll.hide_viewport = dancers_coll.hide_render = not SHOW_DANCERS


# ---- camera + light --------------------------------------------------------------------------------------
cam_data = bpy.data.cameras.new('Camera'); cam_data.type = 'ORTHO'
cam = bpy.data.objects.new('Camera', cam_data); rig.objects.link(cam)
tilt_r = math.radians(TILT)
cam.location = (0, -10 * math.cos(tilt_r), 10 * math.sin(tilt_r) + 0.25)
cam.rotation_euler = (math.radians(90 - TILT), 0, 0)
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = RES
aspect = RES[0] / RES[1]
need_w = PATCH_A * 2 * SAND_REACH * FIT['width'] + FIT['pad']
view_h = max(FIT['min_height'], need_w / aspect)
view_w = view_h * aspect
cam_data.ortho_scale = max(view_w, view_h)
cam_data.shift_y = FIT['lift'] / cam_data.ortho_scale
cam_data.clip_end = 50

sun_data = bpy.data.lights.new('Sun', 'SUN'); sun_data.energy = 2.6; sun_data.angle = math.radians(12)
sun = bpy.data.objects.new('Sun', sun_data); rig.objects.link(sun)
sun.location = (-4, -1.5, 3.5)                       # site sun (-4, 3.5, 1.5)
sun.rotation_euler = (-sun.location).to_track_quat('-Z', 'Y').to_euler()

world = bpy.data.worlds.new('RAS World'); scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes['Background']
bg.inputs['Color'].default_value = (1.0, 0.98, 0.95, 1.0)   # the site's hemisphere light: white sky...
bg.inputs['Strength'].default_value = 0.9

scene.render.engine = 'BLENDER_EEVEE'
scene.render.film_transparent = True                 # drop renders straight onto the page grey in Figma
scene.render.image_settings.color_mode = 'RGBA'
scene.view_settings.view_transform = 'Standard'      # the site doesn't tone-map either
scene.frame_start, scene.frame_end = 1, int(24 * PRINTS['duration'])
scene.render.fps = 24

scene.render.filepath = '//renders/ras_16x9_'

# ---- second format: 9:16 portrait at 4K, as a linked scene (same objects; its own camera and resolution) ---
PORTRAIT = dict(res=(2160, 3840), fill=0.72, headroom=0.15)   # fill: share of the sand-apron width that fits across
bpy.context.window.scene = scene
bpy.ops.scene.new(type='LINK_COPY')
portrait = bpy.context.scene; portrait.name = 'RAS 9:16'
portrait.render.resolution_x, portrait.render.resolution_y = PORTRAIT['res']
portrait.render.resolution_percentage = 100
portrait.render.filepath = '//renders/ras_9x16_'
pcam_data = cam_data.copy(); pcam_data.name = 'Camera 9:16'
pcam = bpy.data.objects.new('Camera 9:16', pcam_data); rig.objects.link(pcam)
pcam.location = cam.location.copy(); pcam.rotation_euler = cam.rotation_euler.copy()
p_need_w = PATCH_A * 2 * SAND_REACH * PORTRAIT['fill']
pcam_data.ortho_scale = p_need_w / (PORTRAIT['res'][0] / PORTRAIT['res'][1])
pcam_data.shift_y = PORTRAIT['headroom'] / pcam_data.ortho_scale
portrait.camera = pcam
scene.camera = cam
bpy.context.window.scene = scene

bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print('RAS scene saved to', OUT_BLEND)
