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
root=empty('IceWindow'); body=empty('BreathingBody',root); held=empty('LatticeTilt',body)
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
# Pixel coordinates follow the original source, with all white window space absent.
def point(x,y,depth=0): return ((x-465)*.0035,depth,1.5+(1222-y)*.0035)
def line(name,coords,r=.021,parent=body,depth=-.03,closed=False,poly=False,mat=black):
    return tube(name,[point(x,y,depth) for x,y in coords],r,mat,parent,closed,poly)
for coords in [[(134,893),(797,893),(797,1550),(134,1550)],[(164,924),(758,924),(758,1518),(164,1518)]]:
    line('Open rectangular black rail',coords,.025,closed=True,poly=True,depth=0)
for x,n in [(410,'EyeLeft'),(524,'EyeRight')]:
    ball(n,point(x,1072,-.055),(.082,.047,.145),black)
for x in [354,378,571,595]:
    ball('Pink cheek',point(x,1140,-.055),(.026,.025,.052),pink)
line('Small smile',[(451,1146),(468,1164),(489,1143)],.017,depth=-.065)
line('Long bent left arm',[(128,1104),(82,1143),(35,1192),(36,1214),(112,1243),(207,1269),(273,1281)],.022,depth=-.09)
line('Long bent right arm',[(810,1120),(861,1150),(898,1185),(895,1220),(852,1289)],.022,depth=-.09)
# White is retained only within the small original glove details.
for x,y,sx,sy in [(303,1266,37,49),(833,1324,29,48)]:
    ball('Mitten black outline',point(x,y,-.12),(sx*.0035,.065,sy*.0035),black)
    ball('Small white mitten',point(x,y,-.18),((sx-10)*.0035,.035,(sy-11)*.0035),white)
line('Left bunny finger',[(272,1230),(256,1178),(259,1152),(278,1160),(289,1190),(290,1217)],.021,depth=-.16)
line('Right bunny finger',[(311,1218),(324,1181),(341,1155),(352,1162),(352,1184),(329,1230)],.021,depth=-.16)
for a,b in [((314,1247),(329,1248)),((315,1266),(330,1266)),((280,1277),(291,1278))]:
    line('Mitten finger mark',[a,b],.017,depth=-.222)
# A diagonal polygon with triangular ice-crack rails, no filled interior faces.
A=(488,1193); B=(585,1213); C=(612,1294); D=(457,1465); E=(348,1464); F=(312,1384)
G=(437,1252); H=(521,1279); I=(461,1337); J=(379,1311); K=(407,1395); L=(546,1360); M=(496,1422)
line('Ice lattice outer perimeter',[A,B,C,D,E,F],.025,parent=held,depth=-.13,closed=True,poly=True)
for coords in [[A,H,B],[G,H,C],[G,I,H,L],[J,I,L],[J,K,I,M],[F,K,M,D],[F,E,K,D],[A,G,J,F],[B,H,I,K,E]]:
    line('Triangular ice lattice',coords,.021,parent=held,depth=-.13,poly=True)
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
bpy.ops.export_scene.gltf(filepath=str(OUT/'ice-window.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_force_sampling=True,export_frame_range=True,export_cameras=False,export_lights=False)
w=bpy.data.worlds.new('Neutral studio'); s.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[1].default_value=.5
for loc,power,size in [((-3,-4,6),450,4),((4,-2,3),250,3),((1,3,5),350,3)]:
    bpy.ops.object.light_add(type='AREA',location=loc); o=bpy.context.object; o.data.energy=power; o.data.size=size; o.rotation_euler=(Vector((0,0,1.5))-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(.65,-10,2.05)); cam=bpy.context.object; cam.rotation_euler=(Vector((0,0,1.5))-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.type='ORTHO'; cam.data.ortho_scale=3.45; s.camera=cam
s.render.film_transparent=True; s.render.resolution_x=900; s.render.resolution_y=900; s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'; s.render.filepath=str(OUT/'ice-window-preview.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/ice-window.blend'))
bpy.ops.render.render(write_still=True)
