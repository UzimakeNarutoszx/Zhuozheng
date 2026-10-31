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

ivory = mat('Warm porcelain', (.88,.82,.67))
rim = mat('Weathered ink green', (.075,.17,.145))
wood = mat('Warm carved lattice', (.40,.25,.135))
ink = mat('Facial ink', (.035,.065,.052))
pink = mat('Coral blush', (.88,.28,.23))
light = mat('Eye sparkle', (1,.97,.85))

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

# All openings are actual empty space between three-dimensional carved bars.
torus('Porcelain circular window',1.02,.16,0,ivory)
torus('Outer ink edge',1.13,.035,-.035,rim)
torus('Inner carved rim',.88,.045,-.065,wood)
for x in (-.57,.57):
    h=math.sqrt(.85**2-x*x)
    line('Vertical lattice',[(x,0,1.55-h),(x,0,1.55+h)],.035,wood)
for z in (-.57,.57):
    h=math.sqrt(.85**2-z*z)
    line('Horizontal lattice',[(-h,0,1.55+z),(h,0,1.55+z)],.035,wood)
pts=[]
for i in range(64):
    a=math.tau*i/64; r=.47+.105*math.cos(4*a)
    pts.append((r*math.cos(a),-.035,1.49+r*math.sin(a)))
line('Four petal central opening',pts,.045,wood,cyclic=True)
# Face sits on a softly sculpted brow bridge, retaining open lattice below it.
ball('Brow porcelain bridge',(0,-.02,2.08),(.55,.12,.22),ivory)
for x in (-.25,.25):
    ball('Eye',(x,-.149,2.10),(.043,.033,.080),ink)
    ball('Eye glint',(x-.009,-.180,2.124),(.011,.009,.017),light)
    ball('Blushing cheek',(x*1.5,-.127,1.97),(.095,.025,.037),pink)
line('Happy smile',[(-.065,-.16,1.98),(0,-.18,1.935),(.065,-.16,1.98)],.019,ink)

left=empty('LeftArmPivot',(-1.02,0,1.53),body)
right=empty('WaveHandPivot',(1.02,0,1.53),body)
line('Left arm',[(0,0,0),(-.20,-.025,-.17),(-.28,-.04,-.08)],.055,rim,left)
ball('Left mitten',(-.29,-.04,-.05),(.10,.075,.14),ivory,left)
line('Right arm',[(0,0,0),(.20,-.02,.12),(.25,-.04,.38)],.055,rim,right)
ball('Waving mitten',(.25,-.04,.43),(.115,.08,.16),ivory,right)
ball('Thumb',(.15,-.05,.41),(.065,.065,.08),ivory,right)
for x in (-.38,.38):
    line('Leg',[(x,0,.52),(x,-.01,.23),(x*1.15,-.07,.17)],.057,rim)
    ball('Rounded shoe',(x*1.17,-.07,.16),(.18,.14,.09),rim)

# One coherent four-second clip, exported as a single AnimationMixer action.
for f,z,tilt,s in [(1,0,-.025,1),(31,.065,.025,1.018),(61,0,-.025,1),(91,.065,.025,1.018),(121,0,-.025,1)]:
    body.location.z=z; body.rotation_euler[1]=tilt; body.scale=(s,1,s)
    for p in ('location','rotation_euler','scale'): body.keyframe_insert(p,frame=f)
for f,a in [(1,-.12),(16,.23),(31,-.2),(46,.23),(61,-.12),(91,-.12),(121,-.12)]:
    right.rotation_euler[1]=a; right.keyframe_insert('rotation_euler',frame=f)
for obj in (body,right):
    obj.animation_data.action.name = 'GardenGreeting'
    track=obj.animation_data.nla_tracks.new(); track.name='GardenGreeting'
    track.strips.new('GardenGreeting',1,obj.animation_data.action)
    obj.animation_data.action=None
scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT')
for obj in scene.objects:
    if obj.type in ('MESH','EMPTY'): obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'round-window.glb'),export_format='GLB',
    use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',
    export_force_sampling=True,export_frame_range=True,export_cameras=False,export_lights=False)

world=bpy.data.worlds.new('Soft studio'); scene.world=world; world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.80,.85,.82,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.45
for name,loc,power,size in [('Key',(-3,-4,6),450,4),('Fill',(4,-2,3),220,3),('Rim',(1,3,5),350,3)]:
    bpy.ops.object.light_add(type='AREA',location=loc)
    obj=bpy.context.object; obj.name=name; obj.data.energy=power; obj.data.shape='DISK'; obj.data.size=size
    obj.rotation_euler=(Vector((0,0,1.5))-obj.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(3,-9,3.1))
cam=bpy.context.object; cam.rotation_euler=(Vector((0,0,1.4))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO'; cam.data.ortho_scale=3.7; scene.camera=cam
scene.render.film_transparent=True; scene.render.resolution_x=900; scene.render.resolution_y=900
scene.render.resolution_percentage=100; scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(OUT/'round-window-preview.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/round-window.blend'))
bpy.ops.render.render(write_still=True)
print('ROUND_WINDOW_COMPLETE', OUT)
