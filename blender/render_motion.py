"""Build and render the garden motion clips.

Usage:
  Blender.app/.../Blender -b --factory-startup --python blender/render_motion.py -- hero desktop --preview
  Blender.app/.../Blender -b --factory-startup --python blender/render_motion.py -- all desktop
"""
from __future__ import annotations

import sys
import subprocess
import shutil
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (ASSETS, CLAY, FPS, GOLD, INK, PAPER, WATER, add_camera, add_frame,
                    add_panel, add_water, animate, curve_line, load_garden_image, material, plane,
                    reset_scene, setup_render)

CLIPS = {
    "hero": (1, "round", "首页水院与窗框"),
    "observation": (2, "open", "视点、视线与景物"),
    "map": (3, "open", "游园地图水面与路径"),
    "frame": (2, "round", "框景"),
    "borrow": (1, "open", "借景"),
    "opposition": (3, "open", "对景"),
    "leak": (2, "round", "漏景"),
    "screen": (3, "fan", "障景"),
    "cases": (1, "round", "案例画面"),
    "studio": (2, "round", "创作板窗框切换"),
}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    clip = argv[0] if argv else "hero"
    orientation = argv[1] if len(argv) > 1 else "desktop"
    preview = "--preview" in argv
    return clip, orientation, preview


def build_clip(scene, clip, portrait):
    image_index, frame_kind, _ = CLIPS[clip]
    bg = material(f"ENV_Photo_{image_index}", PAPER, image=load_garden_image(image_index))
    plane("ENV_Photo_Background", (10.0 if portrait else 14.0, 10.0), (0, 1.1, 0), bg)
    if clip not in {"observation", "map"}:
        add_water()
    frame = add_frame(kind=frame_kind)
    accent = material("GUIDE_Accent", CLAY, emission=True, strength=1.5)
    gold = material("GUIDE_Gold", (0.74, 0.52, 0.19, 1), emission=True, strength=1.3)
    if clip == "frame":
        frame.location.y = -0.8
        frame.scale = (0.7, 0.7, 0.7)
    elif clip == "borrow":
        frame.location.x = -1.35
        frame.scale = (0.62, 0.62, 0.62)
        curve_line("GUIDE_Borrowing", [(-1.0, -0.3, 0.2), (0.0, -0.3, 1.4), (1.8, -0.3, 0.5)], 0.035, gold)
    elif clip == "opposition":
        frame.location.x = -1.4
        frame.scale = (0.58, 0.58, 0.58)
        add_panel("PROP_OppositePoint", (1.35, -0.25, 0.55), (0.22, 0.22), CLAY, 0.2, 1.0)
        curve_line("GUIDE_Opposition", [(-1.1, -0.32, 0.2), (0, -0.32, 0.2), (1.35, -0.32, 0.55)], 0.025, accent)
    elif clip == "leak":
        add_panel("PROP_LeakWall", (0.0, -0.6, 0.0), (0.18, 3.7), PAPER, 0.1, 1.0)
        frame.location.x = 0.75
        frame.scale = (0.58, 0.58, 0.58)
        curve_line("GUIDE_Leak", [(0.55, -0.72, -0.8), (0.55, -0.72, 0.2), (0.55, -0.72, 1.0)], 0.04, gold)
    elif clip == "screen":
        add_panel("PROP_ScreenWall", (-0.15, -0.7, 0.0), (0.34, 3.9), PAPER, 0.1, 1.0)
        frame.location.x = 1.25
        frame.scale = (0.5, 0.5, 0.5)
    elif clip == "observation":
        add_panel("GUIDE_Sight", (-2.4, -0.5, -0.1), (0.07, 0.07), CLAY, 0.1, 1.0)
        curve_line("GUIDE_SightLine", [(-2.3, -0.5, -0.1), (0.0, -0.5, 0.65), (2.3, -0.5, 1.0)], 0.035, accent)
        add_panel("GUIDE_Target", (2.3, -0.5, 1.0), (0.26, 0.26), GOLD, 0.1, 1.0)
    elif clip == "map":
        add_panel("MAP_WaterShape", (0, -0.55, -0.1), (3.8, 1.0), WATER, 0.2, 1.0)
        curve_line("MAP_Path", [(-3.2, -0.7, -0.8), (-1.3, -0.7, 0.55), (0.2, -0.7, -0.15), (2.8, -0.7, 0.7)], 0.045, gold)
    elif clip == "studio":
        frame.location.x = -0.1
        frame.scale = (0.65, 0.65, 0.65)
        frame.rotation_euler.z = 0.0
        frame.keyframe_insert("rotation_euler", frame=FPS)
        frame.rotation_euler.z = 0.35
        frame.keyframe_insert("rotation_euler", frame=FPS * 3)
    elif clip == "cases":
        frame.location.x = 0.8
        frame.scale = (0.56, 0.56, 0.56)
    if clip in {"map", "observation"}:
        line = material("GUIDE_Line", CLAY, emission=True, strength=1.4)
        guide = plane("GUIDE_Paper", (4.4, 0.035), (0, -0.35, 0), material("GUIDE_Fill", PAPER, emission=True, strength=0.8))
        guide.rotation_euler[1] = 0.12
        guide.data.materials.clear()
        guide.data.materials.append(line)
        guide.scale.x = 0.05
        guide.keyframe_insert("scale", frame=1)
        guide.scale.x = 1.0
        guide.keyframe_insert("scale", frame=FPS * 2)
    if clip == "hero":
        frame.location.z = 0.2
        frame.rotation_euler.z = -0.12
    frame.keyframe_insert("location", frame=1)
    frame.location.x += 0.25
    frame.keyframe_insert("location", frame=FPS * 4)
    camera = add_camera(scene, portrait)
    animate(camera, FPS * 4, portrait)


def render(clip, orientation, preview):
    if clip == "all":
        for name in CLIPS:
            render(name, orientation, preview)
        return
    if clip not in CLIPS:
        raise SystemExit(f"unknown clip: {clip}")
    scene = reset_scene()
    portrait = orientation == "mobile"
    build_clip(scene, clip, portrait)
    out = setup_render(scene, clip, portrait, preview)
    scene.frame_set(1)
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_percentage = 50 if preview else 100
    scene.render.filepath = str(out / ("mobile-poster.png" if portrait else "desktop-poster.png"))
    bpy.ops.render.render(write_still=True)
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_percentage = 25 if preview else 100
    frames_dir = out / ("mobile-frames" if portrait else "desktop-frames")
    scene.render.filepath = str(frames_dir / "f_")
    bpy.ops.render.render(animation=True)
    stem = "mobile" if portrait else "desktop"
    pattern = str(frames_dir / "f_%04d.png")
    mp4 = out / f"{stem}.mp4"
    webm = out / f"{stem}.webm"
    scale = "scale=1080:1920" if portrait else "scale=1920:1080"
    subprocess.run(["ffmpeg", "-y", "-framerate", str(FPS), "-i", pattern, "-vf", scale, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(mp4)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["ffmpeg", "-y", "-framerate", str(FPS), "-i", pattern, "-vf", scale, "-c:v", "libvpx-vp9", "-pix_fmt", "yuv420p", "-b:v", "2M", "-an", str(webm)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    shutil.rmtree(frames_dir, ignore_errors=True)
    blend_path = out / f"{clip}-{orientation}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(f"RENDERED {clip} {orientation} -> {out}")


if __name__ == "__main__":
    render(*parse_args())
