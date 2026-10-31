"""Shared helpers for the garden 2.5D motion scenes."""
from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "web/public/assets"
MOTION = ROOT / "web/public/assets/motion"
FPS = 30
PAPER = (0.96, 0.94, 0.88, 1)
INK = (0.09, 0.22, 0.20, 1)
CLAY = (0.61, 0.30, 0.21, 1)
WATER = (0.42, 0.66, 0.64, 1)
GOLD = (0.73, 0.55, 0.28, 1)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.fps = FPS
    scene.render.film_transparent = False
    if "AgX - Medium High Contrast" in {item.name for item in scene.view_settings.bl_rna.properties["look"].enum_items}:
        scene.view_settings.look = "AgX - Medium High Contrast"
    return scene


def material(name, color, emission=False, strength=1.0, image=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    if image:
        shader = nodes.new("ShaderNodeEmission")
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = image
        tex.interpolation = "Linear"
        links.new(tex.outputs["Color"], shader.inputs["Color"])
        shader.inputs["Strength"].default_value = 0.75
    else:
        shader = nodes.new("ShaderNodeEmission" if emission else "ShaderNodeBsdfPrincipled")
        shader.inputs["Color" if emission else "Base Color"].default_value = color
        if emission:
            shader.inputs["Strength"].default_value = strength
        else:
            shader.inputs["Roughness"].default_value = 0.75
    links.new(shader.outputs[0], output.inputs["Surface"])
    return mat


def load_garden_image(index=1):
    path = ASSETS / "garden" / f"garden-{index:03d}.jpg"
    return bpy.data.images.load(str(path), check_existing=True)


def plane(name, size, location, mat, rotation=(math.pi / 2, 0, 0)):
    bpy.ops.mesh.primitive_plane_add(size=1, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.scale = (size[0], size[1], 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return obj


def curve_line(name, points, bevel, mat):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = bevel
    curve.bevel_resolution = 2
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, co in zip(spline.bezier_points, points):
        point.co = co
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def add_camera(scene, portrait=False):
    bpy.ops.object.camera_add(location=(0, -12, 0.15))
    cam = bpy.context.object
    cam.name = "RIG_Camera"
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 10.0 if portrait else 6.2
    target = bpy.data.objects.new("RIG_CameraTarget", None)
    bpy.context.collection.objects.link(target)
    target.location = (0, 0, 0.15)
    constraint = cam.constraints.new("TRACK_TO")
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
    scene.camera = cam
    return cam


def animate(camera, frames, portrait=False):
    start_x = -0.22 if portrait else -0.35
    end_x = 0.22 if portrait else 0.35
    camera.location.x = start_x
    camera.keyframe_insert("location", frame=1)
    camera.location.x = end_x
    camera.keyframe_insert("location", frame=frames)
    curves = getattr(camera.animation_data.action, "fcurves", ())
    for curve in curves:
        for key in curve.keyframe_points:
            key.interpolation = "BEZIER"


def animate_loop(obj, frames, prop, start, end):
    setattr(obj, prop, start)
    obj.keyframe_insert(prop, frame=1)
    setattr(obj, prop, end)
    obj.keyframe_insert(prop, frame=frames // 2)
    setattr(obj, prop, start)
    obj.keyframe_insert(prop, frame=frames)
    curves = getattr(obj.animation_data.action, "fcurves", ())
    for curve in curves:
        for key in curve.keyframe_points:
            key.interpolation = "BEZIER"


def setup_render(scene, clip, portrait=False, preview=False):
    scene.frame_start = 1
    scene.frame_end = FPS * 4
    scene.render.resolution_x = 1080 if portrait else 1920
    scene.render.resolution_y = 1920 if portrait else 1080
    scene.render.resolution_percentage = 25 if preview else 100
    scene.render.image_settings.file_format = "PNG"
    out = MOTION / clip
    out.mkdir(parents=True, exist_ok=True)
    frames = out / ("mobile-frames" if portrait else "desktop-frames")
    frames.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(frames / "f_")
    return out


def add_water(name="ENV_Water"):
    bpy.ops.mesh.primitive_circle_add(vertices=64, radius=3.0, fill_type="NGON", location=(0, 0.4, -0.65), rotation=(math.pi / 2, 0, 0))
    water = bpy.context.object
    water.name = name
    water.data.materials.append(material(name + "Material", WATER, emission=True, strength=0.9))
    animate_loop(water, FPS * 4, "scale", (0.95, 0.95, 0.95), (1.04, 1.0, 1.0))
    return water


def add_frame(name="PROP_Frame", kind="round"):
    data = bpy.data.curves.new(name, "CURVE")
    frame = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(frame)
    frame.location = (0, -0.2, 0.0)
    frame.name = name
    frame.data.dimensions = "3D"
    frame.data.bevel_depth = 0.045
    frame.data.bevel_resolution = 3
    spline = frame.data.splines.new("POLY")
    points = []
    if kind == "round":
        for i in range(48):
            a = math.tau * i / 48
            points.append((1.75 * math.cos(a), 0, 1.75 * math.sin(a), 1))
    elif kind == "fan":
        points = [(-2.2, 0, -1.7, 1), (-1.3, 0, 0.7, 1), (0, 0, 1.65, 1), (1.3, 0, 0.7, 1), (2.2, 0, -1.7, 1)]
    else:
        points = [(-2.1, 0, -1.7, 1), (-2.1, 0, 1.7, 1), (2.1, 0, 1.7, 1), (2.1, 0, -1.7, 1), (-2.1, 0, -1.7, 1)]
    spline.points.add(len(points) - 1)
    for point, co in zip(spline.points, points):
        point.co = co
    frame.data.materials.append(material(name + "Material", CLAY, emission=True, strength=1.2))
    frame.scale = (0.1, 0.1, 0.1)
    frame.keyframe_insert("scale", frame=1)
    frame.scale = (1, 1, 1)
    frame.keyframe_insert("scale", frame=FPS)
    return frame


def add_panel(name, location, size, color, start=0.0, end=1.0):
    obj = plane(name, size, location, material(name + "Material", color, emission=True, strength=0.9))
    obj.scale.x = start
    obj.keyframe_insert("scale", frame=1)
    obj.scale.x = end
    obj.keyframe_insert("scale", frame=FPS * 2)
    return obj
