"""Repeatable faithful open-frame coin mascot. Run with Blender --background --python."""
import math
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'web/public/assets/models'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene
s.render.engine='CYCLES'; s.cycles.samples=32
s.render.fps=30; s.frame_start=1; s.frame_end=121
def material(name,col):
    m=bpy.data.materials.new(name); m.diffuse_color=(*col,1); m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*col,1); p.inputs['Roughness'].default_value=.65
    return m
white=material('Original white',(1,1,1))
black=material('Original black',(.003,.003,.003))
pink=material('Original pink blush',(.78,.28,.48))
def empty(name,parent=None):
    o=bpy.data.objects.new(name,None); s.collection.objects.link(o); o.parent=parent; return o
root=empty('CoinWindow'); body=empty('BreathingBody',root); held=empty('HeldCoinAndArms',body)
def tube(name,pts,r=.022,mat=black,parent=body,closed=False,poly=False):
    c=bpy.data.curves.new(name,'CURVE'); c.dimensions='3D'; c.bevel_depth=r; c.bevel_resolution=4
    sp=c.splines.new('POLY' if poly else 'BEZIER')
    if poly:
        sp.points.add(len(pts)-1)
        for p,co in zip(sp.points,pts): p.co=(*co,1)
    else:
        sp.bezier_points.add(len(pts)-1)
        for p,co in zip(sp.bezier_points,pts): p.co=co; p.handle_left_type='AUTO'; p.handle_right_type='AUTO'
    sp.use_cyclic_u=closed
    o=bpy.data.objects.new(name,c); s.collection.objects.link(o); o.parent=parent; c.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o; bpy.ops.object.convert(target='MESH')
    for f in o.data.polygons: f.use_smooth=True
    return o
def ball(name,loc,scale,mat,parent=body):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=16,location=loc)
    o=bpy.context.object; o.name=name; o.parent=parent; o.scale=scale; o.data.materials.append(mat)
    for f in o.data.polygons: f.use_smooth=True
    return o
# Two genuine square rails, with the source's narrow white channel between them.
for h in (1.16,1.075):
    tube('Square black rail', [(-h,0,1.5-h),(h,0,1.5-h),(h,0,1.5+h),(-h,0,1.5+h)],.025,closed=True,poly=True)
for h in (1.118,):
    tube('White frame channel',[(-h,.006,1.5-h),(h,.006,1.5-h),(h,.006,1.5+h),(-h,.006,1.5+h)],.027,white,closed=True,poly=True)
for x,n in [(-.23,'EyeLeft'),(.14,'EyeRight')]:
    ball(n,(x,-.065,2.04),(.059,.048,.135),black)
for x in (-.47,-.395,.295,.365):
    o=ball('Original pink cheek',(x,-.065,1.895),(.024,.026,.04),pink); o.rotation_euler[1]=-.3
tube('Tiny mouth',[(-.085,-.075,1.9),(-.05,-.08,1.84),(-.015,-.075,1.9)],.016)
# Arms loop around from the side of the square and hold the circular window.
for sign in (-1,1):
    tube('Holding arm',[(sign*1.16,.02,1.83),(sign*1.24,-.04,1.47),(sign*1.15,-.12,1.34),(sign*.76,-.18,1.27)],.024,parent=held)
    ball('Mitten ink outline',(sign*.755,-.23,1.25),(.135,.07,.20),black,held)
    ball('White mitten',(sign*.755,-.285,1.25),(.099,.043,.162),white,held)
# Circular coin/window is entirely open, including its concave diamond center.
cx,cz=0,1.14
pts=[(.64*math.cos(a),-.20,cz+.64*math.sin(a)) for a in [math.tau*i/128 for i in range(128)]]
tube('Circular coin outline',pts,.024,parent=held,closed=True,poly=True)
# Four quarter-circle arcs form the source's inward-curved diamond opening.
for ax,az,start in [(-.64,.64,-math.pi/2),(.64,.64,math.pi),(.64,-.64,math.pi/2),(-.64,-.64,0)]:
    pts=[(ax+.64*math.cos(start+math.pi/2*i/40),-.20,cz+az+.64*math.sin(start+math.pi/2*i/40)) for i in range(41)]
    tube('Curved diamond opening',pts,.021,parent=held,poly=True)
def clip(obj,name,keys):
    for frame,z,angle in keys:
        obj.location.z=z; obj.rotation_euler[1]=angle
        obj.keyframe_insert('location',frame=frame); obj.keyframe_insert('rotation_euler',frame=frame)
    action=obj.animation_data.action; action.name=name
    tr=obj.animation_data.nla_tracks.new(); tr.name=name; tr.strips.new(name,1,action); obj.animation_data.action=None
    return tr
clip(body,'Idle',[(1,0,-.006),(31,.012,.006),(61,0,-.006),(91,.012,.006),(121,0,-.006)])
tr=clip(held,'Greeting',[(1,0,0),(20,.075,-.018),(40,.105,.018),(60,.075,-.018),(85,0,0),(121,0,0)])
tr.mute=True
s.frame_set(1)
bpy.ops.object.select_all(action='DESELECT')
for o in s.objects:
    if o.type in ('MESH','EMPTY'): o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'coin-window.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_force_sampling=True,export_frame_range=True,export_cameras=False,export_lights=False)
w=bpy.data.worlds.new('Neutral studio'); s.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[1].default_value=.5
for loc,power,size in [((-3,-4,6),450,4),((4,-2,3),250,3),((1,3,5),350,3)]:
    bpy.ops.object.light_add(type='AREA',location=loc); o=bpy.context.object; o.data.energy=power; o.data.size=size; o.rotation_euler=(Vector((0,0,1.5))-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(1.2,-10,2.6)); cam=bpy.context.object; cam.rotation_euler=(Vector((0,0,1.5))-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.type='ORTHO'; cam.data.ortho_scale=3.25; s.camera=cam
s.render.film_transparent=True; s.render.resolution_x=900; s.render.resolution_y=900; s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'; s.render.filepath=str(OUT/'coin-window-preview.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/coin-window.blend'))
bpy.ops.render.render(write_still=True)
