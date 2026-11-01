"""Build the real mesh garden-window companion and its looping glTF animation.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --python blender/build_round_window.py
Blender Z-up; front faces -Y. glTF automatically converts to Y-up.
"""
import math
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'web/public/assets/models'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 40
scene.render.fps = 30
scene.frame_start, scene.frame_end = 1, 121

def mat(name, color, roughness=.65):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    shader = m.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    return m

# Preserve the original drawing's white, neutral black and red cheek marks.
ivory = mat('Original white', (.95,.95,.95))
rim = mat('Original black outlines', (.003,.003,.003))
ink = mat('Original black face', (.003,.003,.003))
pink = mat('Original red cheeks', (.96,.16,.16))
light = mat('White eye sparkle', (1,1,1))

def empty(name, location=(0,0,0), parent=None):
    obj = bpy.data.objects.new(name,None)
    scene.collection.objects.link(obj)
    obj.location = location
    obj.parent = parent
    return obj

root = empty('RoundWindow')
body = empty('BreathingBody', parent=root)

def finish(obj,name,material,parent=body):
    obj.name=name
    obj.data.materials.append(material)
    obj.parent=parent
    for p in obj.data.polygons: p.use_smooth=True
    return obj

def ball(name,location,scale,material,parent=body):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, location=location)
    obj=finish(bpy.context.object,name,material,parent)
    obj.scale=scale
    return obj

def line(name,points,radius,material,parent=body,cyclic=False):
    c=bpy.data.curves.new(name,'CURVE'); c.dimensions='3D'
    c.bevel_depth=radius; c.bevel_resolution=3; c.resolution_u=12
    s=c.splines.new('BEZIER'); s.bezier_points.add(len(points)-1)
    for p,co in zip(s.bezier_points,points):
        p.co=co; p.handle_left_type='AUTO'; p.handle_right_type='AUTO'
    s.use_cyclic_u=cyclic
    obj=bpy.data.objects.new(name,c); scene.collection.objects.link(obj)
    obj.parent=parent; c.materials.append(material)
    bpy.context.view_layer.objects.active=obj; obj.select_set(True)
    bpy.ops.object.convert(target='MESH'); obj.select_set(False)
    return obj

def torus(name,radius,tube,y,material):
    bpy.ops.mesh.primitive_torus_add(major_segments=80,minor_segments=12,
        location=(0,y,1.55),rotation=(math.pi/2,0,0),major_radius=radius,minor_radius=tube)
    return finish(bpy.context.object,name,material)

# Only the original contours are modeled; the whole white body stays open.
pts=[]
for i in range(128):
    a=math.tau*i/128; r=.565+.125*math.cos(4*a)
    pts.append((r*math.cos(a),-.175,1.46+r*math.sin(a)))
line('Ink quatrefoil lip',pts,.026,rim,cyclic=True)
edge=[(-1.09,-.15,.51),(1.09,-.15,.51),(1.09,-.15,2.65),(-1.09,-.15,2.65)]
# POLY outline keeps the square silhouette instead of rounding into a circle.
def polygon_line(name,points,radius,material):
    c=bpy.data.curves.new(name,'CURVE'); c.dimensions='3D'; c.bevel_depth=radius; c.bevel_resolution=4
    s=c.splines.new('POLY'); s.points.add(len(points)-1)
    for p,co in zip(s.points,points): p.co=(*co,1)
    s.use_cyclic_u=True
    obj=bpy.data.objects.new(name,c); scene.collection.objects.link(obj); obj.parent=body; c.materials.append(material)
    bpy.context.view_layer.objects.active=obj; obj.select_set(True); bpy.ops.object.convert(target='MESH'); obj.select_set(False)
polygon_line('Square ink perimeter',edge,.043,rim)
for x in (-.76,.76):
    for z in (.87,2.34):
        ornament=[]
        for i in range(48):
            a=math.tau*i/48; r=.19+.035*math.cos(4*a)
            ornament.append((x+r*math.cos(a),-.171,z+1.15*r*math.sin(a)))
        line('Carved diamond flower',ornament,.022,rim,cyclic=True)
for x,z in [(0,2.49),(0,.64),(-.92,1.55),(.92,1.55)]:
    polygon_line('Small diamond',[(x,-.177,z+.10),(x+.065,-.177,z),(x,-.177,z-.10),(x-.065,-.177,z)],.016,rim)
for x,name in [(-.36,'EyeLeft'),(.36,'EyeRight')]:
    ball(name,(x,-.177,2.28),(.028,.021,.067),ink)
    ball(name+' glint',(x-.006,-.198,2.303),(.007,.005,.012),light)
    for j in range(3):
        ball('Coral cheek',(x*1.42+(j-1)*.044,-.172,2.13),(.014,.014,.044),pink)
line('Mouth',[(-.047,-.18,2.24),(0,-.19,2.205),(.047,-.18,2.24)],.017,ink)

left=empty('LeftArmPivot',(-1.13,0,1.51),body)
right=empty('WaveHandPivot',(1.13,0,1.51),body)
line('Left arm',[(0,0,0),(-.20,-.025,-.17),(-.28,-.04,-.08)],.055,rim,left)
ball('Left mitten',(-.29,-.04,-.05),(.10,.075,.14),ivory,left)
line('Right arm',[(0,0,0),(.17,-.025,-.17),(.20,-.04,-.08)],.047,rim,right)
ball('Right mitten',(.18,-.05,-.10),(.09,.075,.19),ivory,right)
ball('Thumb',(.10,-.10,-.06),(.055,.055,.08),ivory,right)
for x in (-.38,.38):
    line('Leg',[(x,0,.52),(x,-.01,.23),(x*1.15,-.07,.17)],.057,rim)
    ball('Rounded shoe',(x*1.17,-.07,.16),(.18,.14,.09),rim)

# One coherent four-second clip, exported as a single AnimationMixer action.
for f,z,tilt,s in [(1,0,-.008,1),(31,.018,.008,1.003),(61,0,-.008,1),(91,.018,.008,1.003),(121,0,-.008,1)]:
    body.location.z=z; body.rotation_euler[1]=tilt; body.scale=(s,1,s)
    for p in ('location','rotation_euler','scale'): body.keyframe_insert(p,frame=f)
for obj in (body,):
    obj.animation_data.action.name = 'Idle'
    track=obj.animation_data.nla_tracks.new(); track.name='Idle'
    track.strips.new('Idle',1,obj.animation_data.action)
    obj.animation_data.action=None
for f,a in [(1,0),(15,-.95),(24,-1.25),(33,-.93),(42,-1.25),(51,-.93),(66,0),(121,0)]:
    right.rotation_euler[1]=a; right.keyframe_insert('rotation_euler',frame=f)
right.animation_data.action.name='Greeting'
track=right.animation_data.nla_tracks.new(); track.name='Greeting'
track.strips.new('Greeting',1,right.animation_data.action)
right.animation_data.action=None
track.mute=True
scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT')
for obj in scene.objects:
    if obj.type in ('MESH','EMPTY'): obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'round-window.glb'),export_format='GLB',
    use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',
    export_force_sampling=True,export_frame_range=True,export_cameras=False,export_lights=False)

world=bpy.data.worlds.new('Soft studio'); scene.world=world; world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.8,.8,.8,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.45
for name,loc,power,size in [('Key',(-3,-4,6),450,4),('Fill',(4,-2,3),220,3),('Rim',(1,3,5),350,3)]:
    bpy.ops.object.light_add(type='AREA',location=loc)
    obj=bpy.context.object; obj.name=name; obj.data.energy=power; obj.data.shape='DISK'; obj.data.size=size
    obj.rotation_euler=(Vector((0,0,1.5))-obj.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(2.7,-10,3.0))
cam=bpy.context.object; cam.rotation_euler=(Vector((0,0,1.4))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO'; cam.data.ortho_scale=3.7; scene.camera=cam
scene.render.film_transparent=True; scene.render.resolution_x=900; scene.render.resolution_y=900
scene.render.resolution_percentage=100; scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(OUT/'round-window-preview.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/round-window.blend'))
bpy.ops.render.render(write_still=True)
print('ROUND_WINDOW_COMPLETE', OUT)
