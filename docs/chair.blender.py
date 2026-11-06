import bpy, bmesh, math, sys
from mathutils import Vector

out_glb, out_png = sys.argv[sys.argv.index('--') + 1:][:2]

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

def finish(obj, subsurf=0, bevel=0.0):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    if bevel:
        m = obj.modifiers.new('bev', 'BEVEL'); m.width = bevel; m.segments = 4
    if subsurf:
        m = obj.modifiers.new('sub', 'SUBSURF'); m.levels = subsurf; m.render_levels = subsurf
    return obj

def box(name, size, loc):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    return o

def cyl(name, r, depth, loc, rot=(0,0,0), scale=(1,1,1)):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=48)
    o = bpy.context.active_object; o.name = name; o.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    return o

def boolean(target, tool, op):
    m = target.modifiers.new('b', 'BOOLEAN'); m.operation = op; m.object = tool; m.solver = 'EXACT'
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(tool, do_unlink=True)

def apply_all(obj):
    bpy.context.view_layer.objects.active = obj
    for m in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)

# ---- seat: slightly dished, rounded slab (front is -Y)
seat = box('seat', (0.47, 0.46, 0.05), (0, 0, 0.43))
finish(seat, subsurf=2, bevel=0.018); apply_all(seat)

# ---- back: arch (disc on top of a slab), slots cut, then curved around the sitter
back = box('back', (0.44, 0.05, 0.2), (0, 0, 0.1))
disc = cyl('disc', 0.5, 0.05, (0, 0, 0.2), rot=(math.pi/2, 0, 0), scale=(0.46, 0.46, 1))
boolean(back, disc, 'UNION')
def slot(x, z, h, w, tilt):
    # ellipse in the XZ plane, cut straight through Y
    return cyl('slot', 0.5, 0.3, (x, 0, z), rot=(math.pi/2, 0, tilt), scale=(w, h, 1))
for x, z, h, w, t in [(0, 0.25, 0.3, 0.05, 0), (-0.125, 0.23, 0.26, 0.042, -0.2), (0.125, 0.23, 0.26, 0.042, 0.2)]:
    boolean(back, slot(x, z, h, w, t), 'DIFFERENCE')
bpy.context.view_layer.objects.active = back
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.subdivide(number_cuts=5)
bpy.ops.object.mode_set(mode='OBJECT')
for v in back.data.vertices:          # wrap the edges forward (-Y) around the sitter
    v.co.y -= 2.4 * v.co.x ** 2
finish(back, bevel=0.008); apply_all(back)
back.location = (0, 0.215, 0.455)
back.rotation_euler = (math.radians(-13), 0, 0)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# ---- tubes (arms+front legs, rear legs) from curves
def tube(name, pts, r0, r1, bev=0.024):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for i, (p, bp) in enumerate(zip(pts, sp.bezier_points)):
        bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
        bp.radius = r0 + (r1 - r0) * i / (len(pts) - 1)
    cu.bevel_depth = bev; cu.bevel_resolution = 8; cu.resolution_u = 16
    cu.use_fill_caps = True
    ob = bpy.data.objects.new(name, cu); scene.collection.objects.link(ob)
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.convert(target='MESH')
    return bpy.context.active_object

parts = [seat, back]
for sx in (-1, 1):
    arm_leg = [(sx*0.205, 0.14, 0.62), (sx*0.255, -0.02, 0.69), (sx*0.262, -0.16, 0.65),
               (sx*0.245, -0.235, 0.52), (sx*0.235, -0.245, 0.30), (sx*0.27, -0.29, 0.015)]
    parts.append(tube('armleg', arm_leg, 1.2, 0.85, 0.03))
    rear = [(sx*0.195, 0.19, 0.42), (sx*0.215, 0.235, 0.22), (sx*0.235, 0.29, 0.015)]
    parts.append(tube('rear', rear, 1.2, 0.85, 0.03))

bpy.ops.object.select_all(action='DESELECT')
for p in parts:
    p.select_set(True)
bpy.context.view_layer.objects.active = seat
bpy.ops.object.join()
chair = bpy.context.active_object; chair.name = 'MonoblocChair'
bpy.ops.object.shade_smooth()

# ---- dark walnut material
mat = bpy.data.materials.new('walnut'); mat.use_nodes = True
b = mat.node_tree.nodes['Principled BSDF']
b.inputs['Base Color'].default_value = (0.095, 0.04, 0.017, 1)
b.inputs['Roughness'].default_value = 0.38
mat.diffuse_color = (0.16, 0.07, 0.03, 1)
chair.data.materials.clear()
chair.data.materials.append(mat)
for p in chair.data.polygons: p.material_index = 0

# ---- preview render (Workbench, headless-safe)
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'; scene.display.shading.color_type = 'MATERIAL'
scene.world = bpy.data.worlds.new('w'); scene.world.color = (0.88, 0.88, 0.9)
scene.render.resolution_x = 700; scene.render.resolution_y = 900
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scene.collection.objects.link(cam)
cam.location = (1.7, -2.2, 1.1); cam.rotation_euler = (math.radians(76), 0, math.radians(38)); cam.data.lens = 55
scene.camera = cam
scene.render.filepath = out_png
bpy.ops.render.render(write_still=True)

# ---- export
bpy.ops.object.select_all(action='DESELECT'); chair.select_set(True)
bpy.ops.export_scene.gltf(filepath=out_glb, export_format='GLB', use_selection=True, export_apply=True)
print('tris', sum(len(p.vertices) - 2 for p in chair.data.polygons))
