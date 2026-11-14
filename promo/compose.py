"""拙政观景 30 秒竖屏宣传片：逐帧合成。

画面只用纸/墨/赭/金四色，版式全部走 layout.py 的网格；时间轴来自 promo/timeline.json。
素材缺位（录屏未就绪 / 图片缺失）时画占位块，脚本可独立跑通。

用法：
  python3 promo/compose.py --preview          # 每个镜头取中段一帧，540×960 存 preview/
  python3 promo/compose.py --frame=12.5       # 指定秒数单帧，存 preview/
  python3 promo/compose.py --part=0/4         # 只渲染第 0 段（共 4 段），直接编码 part_0of4.mp4
  python3 promo/compose.py                    # 整片无声画面
"""
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from layout import (CHIPS_Y, CLAY, GOLD, H, INK, INK_SOFT, LEFT, MAIN_BOX, PAPER, PAPER_DEEP,  # noqa: E402
                    PAPER_LIGHT, RIGHT, TITLE_TOP, W, WATER, badge, card, chips, circle_mask,
                    clamp, ease_in_out_cubic, ease_out_back, ease_out_expo, font, label_row,
                    paper_bg, paste, place, placeholder, progress, rounded_mask, spring,
                    title_text, tracked)

ROOT = Path(__file__).resolve().parents[1]
V = ROOT / "output/promo-video"
CAP = V / "capture"
FRAMES = V / "frames"
PREVIEW = V / "preview"
SPEC = json.loads((ROOT / "promo/timeline.json").read_text())
FPS, DUR = SPEC["fps"], SPEC["duration"]
TOTAL = int(round(DUR * FPS))
CUTS = SPEC["cuts"]
SHOTS = SPEC["shots"]
MAIN_CY = 1060                      # 主画面卡片中心
CARD_W, CARD_H = 800, 760           # 卡片可用区（录屏按此比例裁上半屏，保证网站文字可读）

# 每段录屏从就绪点后第几秒开始看、播放速度（画面节奏：慢一点更克制）
CLIP_IN = {"brand": (0.3, 0.9), "methods": (0.2, 0.85), "detail": (0.2, 0.85), "explore": (0.4, 0.9),
           "studio": (0.3, 0.85), "ask": (0.5, 0.9), "community": (0.3, 0.9)}


# ---------- 素材 ----------
def ready_offsets():
    """录屏就绪点：ready.json 里每个 key 之后才是可用画面（录屏分片写在 capture/ 下）"""
    out = {}
    for p in (CAP / "ready.json", V / "ready.json"):
        if not p.exists():
            continue
        try:
            raw = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        for k, v in raw.items():
            if isinstance(v, (int, float)):
                out[k] = float(v)
            elif isinstance(v, dict):
                for kk in ("ready", "at", "offset", "t"):
                    if isinstance(v.get(kk), (int, float)):
                        out[k] = float(v[kk])
                        break
    return out


READY = ready_offsets()


def asset_path(spec):
    p = Path(spec)
    return (V / p) if spec.startswith("capture/") else (ROOT / p)


@lru_cache(maxsize=16)
def image(spec):
    p = asset_path(spec)
    if not p.exists():
        return None
    im = Image.open(p)
    # 透明 PNG（园徽）保留 alpha，照片转 RGB
    return im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")


def ensure_frames(key, path):
    """把录屏按 30fps 抽成 jpg 序列缓存，供 4 个并行进程共用。
    录屏可能还在写（半截文件），抽帧失败就返回 None，由调用方画占位块。"""
    d = FRAMES / key
    if (d / "done").exists():
        return d
    FRAMES.mkdir(parents=True, exist_ok=True)
    lock = FRAMES / f"{key}.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
    except FileExistsError:
        for _ in range(600):
            if (d / "done").exists():
                return d
            if not lock.exists():
                return ensure_frames(key, path)
            time.sleep(0.2)
        return None
    tmp = FRAMES / f".{key}.tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    print(f"抽帧 {key} …", flush=True)
    res = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-vf", "fps=30", "-q:v", "2",
                          str(tmp / "f_%05d.jpg")], capture_output=True, text=True)
    if res.returncode != 0 or not list(tmp.glob("f_*.jpg")):
        print(f"抽帧失败 {key}：{res.stderr.strip().splitlines()[-1] if res.stderr.strip() else res.returncode}",
              flush=True)
        shutil.rmtree(tmp, ignore_errors=True)
        lock.unlink(missing_ok=True)
        return None
    shutil.rmtree(d, ignore_errors=True)
    tmp.rename(d)
    (d / "done").write_text("ok")
    lock.unlink(missing_ok=True)
    return d


class Clip:
    def __init__(self, spec):
        self.spec = spec
        self.key = Path(spec).stem
        self.path = asset_path(spec)
        self.offset = READY.get(self.key, 0.0)
        usable = self.path.exists() and self.path.stat().st_size > 4096
        self.dir = ensure_frames(self.key, self.path) if usable else None
        self.n = len(list(self.dir.glob("f_*.jpg"))) if self.dir else 0
        self.cache = {}

    def at(self, t):
        if not self.n:
            return None
        i = max(0, min(self.n - 1, int(round((self.offset + t) * FPS))))
        if i not in self.cache:
            if len(self.cache) > 24:
                self.cache.clear()
            self.cache[i] = Image.open(self.dir / f"f_{i + 1:05d}.jpg").convert("RGB")
        return self.cache[i]


CLIPS = {}


def clip(spec):
    if spec not in CLIPS:
        CLIPS[spec] = Clip(spec)
    return CLIPS[spec]


def cover_crop(im, size, zoom=1.0, focus=(0.5, 0.5)):
    """等比填满 size 后居中裁切，focus 控制取景中心"""
    tw, th = size
    s = max(tw / im.width, th / im.height) * zoom
    w, h = max(1, int(im.width * s)), max(1, int(im.height * s))
    im = im.resize((w, h), Image.BICUBIC)
    x = int(clamp(focus[0] * w - tw / 2, 0, max(0, w - tw)))
    y = int(clamp(focus[1] * h - th / 2, 0, max(0, h - th)))
    out = im.crop((x, y, x + tw, y + th))
    return out.convert("RGBA")


def round_window(base, im, cx, cy, r, zoom=1.0, alpha=1.0, focus=(0.5, 0.45)):
    """圆窗（月洞门）：图片被圆形遮罩裁切，外加赭金细环与纸色内圈"""
    d = max(16, int(2 * r))
    box = (int(cx - r), int(cy - r), int(cx + r), int(cy + r))
    shadow = Image.new("RGBA", (d, d), (*INK[:3], 0))
    ImageDraw.Draw(shadow).ellipse((6, 10, d - 6, d - 2), fill=(*INK[:3], 70))
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(6, r * 0.09)))
    paste(base, shadow, box[0], box[1])
    if im is None:
        placeholder(base, box, "garden-001", "等待图片")
    else:
        src = cover_crop(im, (d, d), zoom=zoom, focus=focus)
        src.putalpha(circle_mask((d, d), feather=2))
        paste(base, src, box[0], box[1], alpha=alpha)
    ring = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rd.ellipse((2, 2, d - 3, d - 3), outline=(*GOLD[:3], int(235 * alpha)), width=max(3, int(r * 0.016)))
    rd.ellipse((int(r * 0.10), int(r * 0.10), d - int(r * 0.10) - 1, d - int(r * 0.10) - 1),
               outline=(*PAPER_LIGHT[:3], int(150 * alpha)), width=2)
    paste(base, ring, box[0], box[1])


def clip_card(base, spec, t_src, alpha=1.0, dy=0.0, scale=1.0, cy=MAIN_CY, max_w=CARD_W, max_h=CARD_H,
              radius=44, shadow=44):
    """把录屏放进圆角卡片；卡片区固定，靠内部缓推制造运动"""
    im = clip(spec).at(t_src) if asset_path(spec).exists() else None
    if im is None:
        half_w, half_h = max_w / 2, min(max_h, max_w / 1.6) / 2
        box = (W / 2 - half_w, cy - half_h, W / 2 + half_w, cy + half_h)
        placeholder(base, box, Path(spec).stem, "等待录屏")
        return
    # 竖长录屏按卡片比例裁掉下半屏，避免整屏缩小后文字看不清
    want_h = int(im.width * max_h / max_w)
    if im.height > want_h:
        im = im.crop((0, 0, im.width, want_h))
    s = min(max_w / im.width, max_h / im.height)
    scr = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS).convert("RGBA")
    scr.putalpha(rounded_mask(scr.size, radius))
    card(base, scr, cy=cy + dy, radius=radius, shadow=shadow, scale=scale, alpha=alpha)


# ---------- 镜头 ----------
def s_hook(t, d):
    """0–3.5s：月洞门里的园林照片缓推，标题淡入"""
    img = paper_bg(t, 0)
    label_row(img, "ZHUOZHENG", t)
    title_text(img, ["换个位置", "换一幅画"], t, size=104)
    k = ease_out_back(clamp(t / 0.6), 1.2)
    r = 372 * (0.90 + 0.10 * k)
    round_window(img, image(SHOTS[0]["clip"]), W / 2, 1000, r,
                 zoom=1.02 + 0.13 * clamp(t / d), alpha=clamp(k * 1.4))
    a = clamp((t - 0.55) / 0.5)
    if a > 0:
        fd = ImageDraw.Draw(img, "RGBA")
        tracked(fd, (W / 2, 1452), "同一座园 · 不同位置", font("hei_l", 34),
                (*INK_SOFT[:3], int(255 * a)), spacing=3, anchor="mm")
    return img


def slam_line(base, text, cy, t, size=118, color=INK, delay=0.0):
    """居中砸入的一行宋体：缩放弹簧 + 淡入"""
    k = clamp((t - delay) / 0.42)
    if k <= 0:
        return
    s = 1.42 - 0.42 * spring(k, freq=2.2, damp=7)
    f = font("song", size)
    w = int(ImageDraw.Draw(base).textlength(text, font=f)) + 80
    layer = Image.new("RGBA", (w, int(size * 1.5)), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((w / 2, layer.height / 2), text, font=f, fill=(*color[:3], 255), anchor="mm")
    place(base, layer, W / 2, cy, scale=s, alpha=clamp(k * 2.2))


def s_brand(t, d):
    """3.5–7s：月洞门收拢成园徽，品牌名砸入，随后首页录屏卡片弹出"""
    img = paper_bg(t, 1)
    contract = ease_in_out_cubic(clamp(t / 0.75))
    r = 372 - (372 - 96) * contract
    round_window(img, image(SHOTS[0]["clip"]), W / 2, 640, r,
                 zoom=1.15 - 0.1 * contract, alpha=clamp(1 - (t - 0.3) / 0.35))
    logo = image(SHOTS[8]["clip"])
    lk = clamp((t - 0.42) / 0.4)
    if logo is not None and lk > 0:
        place(img, logo.convert("RGBA").resize((200, 200), Image.LANCZOS), W / 2, 640,
              scale=(0.82 + 0.18 * spring(lk, 2.0, 6)) * clamp(lk * 2.6), shadow=22)
    slam_line(img, "拙政观景", 830, t, size=124, delay=0.55)
    a = clamp((t - 0.95) / 0.4)
    if a > 0:
        fd = ImageDraw.Draw(img, "RGBA")
        tracked(fd, (W / 2, 925), "邂逅拙政巧景，若见江南芳华", font("hei", 40), (*INK_SOFT[:3], int(250 * a)),
                spacing=4, anchor="mm")
    pk = ease_out_back(clamp((t - 1.35) / 0.55), 1.15)
    if pk > 0:
        clip_card(img, SHOTS[1]["clip"], CLIP_IN["brand"][0] + max(0.0, t - 1.35) * CLIP_IN["brand"][1],
                  alpha=clamp(pk * 1.5), dy=(1 - pk) * 120, scale=0.88 + 0.12 * pk, cy=1250,
                  max_w=CARD_W, max_h=500, shadow=40)
    return img


def feature(spec, lines, start, speed, max_h=CARD_H, cy=MAIN_CY):
    """通用功能镜头：标签 + 宋体标题 + 居中录屏卡片（轻微弹入 + 全程缓推）"""
    def shot(t, d):
        img = paper_bg(t, hash(spec["key"]) % 4)
        label_row(img, spec["label"], t)
        title_text(img, lines, t, size=104)
        k = ease_out_back(clamp(t / 0.5), 1.1)
        clip_card(img, spec["clip"], start + t * speed, alpha=clamp(k * 1.8),
                  dy=(1 - k) * 70, scale=0.94 + 0.06 * k, cy=cy, max_h=max_h)
        return img
    return shot


def title_lines(title, width=6):
    """标题按逗号断行；没有逗号时按字数对半"""
    parts = [p for p in title.replace("，", "|").split("|") if p]
    if len(parts) == 1 and len(parts[0]) > width:
        s = parts[0]
        mid = (len(s) + 1) // 2
        parts = [s[:mid], s[mid:]]
    return parts


def s_methods(t, d):
    """7–10.5s：手法页 + 五个手法徽章逐个弹出（底部胶囊行）"""
    img = paper_bg(t, 2)
    label_row(img, "造景手法", t)
    title_text(img, ["五种手法", "一页看懂"], t, size=104)
    k = ease_out_back(clamp(t / 0.5), 1.1)
    clip_card(img, SHOTS[2]["clip"], CLIP_IN["methods"][0] + t * CLIP_IN["methods"][1],
              alpha=clamp(k * 1.8), dy=(1 - k) * 70, scale=0.94 + 0.06 * k, cy=1010, max_h=640)
    chips(img, SHOTS[2]["badges"], t, start=0.55, y=CHIPS_Y + 40)
    return img


def s_outro(t, d):
    """27–30s：园徽 + 品牌 + 一句话，不出现网址"""
    img = paper_bg(t, 3)
    logo = image(SHOTS[8]["clip"])
    k = ease_out_back(clamp(t / 0.6), 1.15)
    if logo is not None:
        place(img, logo.convert("RGBA").resize((188, 188), Image.LANCZOS), W / 2, 800,
              scale=0.86 + 0.14 * k, alpha=clamp(k * 2.0), shadow=24)
    slam_line(img, "拙政观景", 1040, t, size=136, delay=0.22)
    a = clamp((t - 0.6) / 0.45)
    if a > 0:
        fd = ImageDraw.Draw(img, "RGBA")
        # slogan 两行：13 字一行会超出右侧安全区
        for j, line in enumerate(("邂逅拙政巧景", "若见江南芳华")):
            tracked(fd, (W / 2, 1170 + j * 96), line, font("song_reg", 72),
                    (*INK[:3], int(252 * a)), spacing=6, anchor="mm")
    b = clamp((t - 0.85) / 0.4)
    if b > 0:
        fd = ImageDraw.Draw(img, "RGBA")
        fd.rectangle((W / 2 - int(72 * b), 1346, W / 2 + int(72 * b), 1349), fill=(*GOLD[:3], 230))
        tracked(fd, (W / 2, 1410), "拙政观景 · 造景手法观察", font("hei", 38), (*INK_SOFT[:3], int(240 * b)),
                spacing=3, anchor="mm")
    return img


def build_shots():
    idx = {s["key"]: i for i, s in enumerate(SHOTS)}
    out = []
    for i, s in enumerate(SHOTS):
        key, d = s["key"], s["end"] - s["start"]
        if key == "hook":
            fn = s_hook
        elif key == "brand":
            fn = s_brand
        elif key == "methods":
            fn = s_methods
        elif key == "outro":
            fn = s_outro
        else:
            start, speed = CLIP_IN.get(key, (0.2, 0.9))
            fn = feature(s, title_lines(s["title"]), start, speed)
        out.append((key, i, s["start"], d, fn))
    return out


SHOT_FNS = build_shots()


def dynamic(img, t, d, push=0.028):
    """整帧缓推 + 极轻横向摆动：比甩镜克制，只留一点呼吸"""
    u = clamp(t / d)
    z = 1 + push * u
    big = img.resize((int(W * z), int(H * z)), Image.BICUBIC)
    dx = int(4 * math.sin(2 * math.pi * u))
    x0 = (big.width - W) // 2 + dx
    y0 = (big.height - H) // 2
    x0 = max(0, min(big.width - W, x0))
    return big.crop((x0, y0, x0 + W, y0 + H))


def cut_flash(img, t, peak=0.34, span=0.12):
    """切点 0.1 秒的极轻白闪，替代硬切"""
    a = 0.0
    for c in CUTS:
        if 0 <= t - c < span:
            a = max(a, peak * (1 - (t - c) / span) ** 2)
    if a <= 0.003:
        return img
    return Image.blend(img, Image.new("RGB", img.size, (250, 246, 238)), a)


def render(t):
    idx, start, d = 0, 0.0, 1.0
    for key, i, s0, sd, fn in SHOT_FNS:
        if s0 <= t < s0 + sd + 1e-6:
            idx, start, d = i, s0, sd
            img = fn(t - s0, sd)
            break
    else:
        idx, start, d, fn = SHOT_FNS[-1][1], SHOT_FNS[-1][2], SHOT_FNS[-1][3], SHOT_FNS[-1][4]
        img = fn(d - 1e-3, d)
    img = dynamic(img, t - start, d)
    progress(img, idx, len(SHOT_FNS), t)
    return cut_flash(img, t)


def encode(path, first, last, step=1, size=(W, H), crf=14):
    path.parent.mkdir(parents=True, exist_ok=True)
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{size[0]}x{size[1]}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-crf", str(crf), "-preset", "medium",
                           "-pix_fmt", "yuv420p", "-g", "60", str(path)], stdin=subprocess.PIPE)
    t0 = time.time()
    for n in range(first, last, step):
        img = render(n / FPS)
        if size != (W, H):
            img = img.resize(size, Image.LANCZOS)
        ff.stdin.write(img.convert("RGB").tobytes())
        if (n - first) % 120 == 0:
            print(f"{n}/{last} {time.time() - t0:.1f}s", flush=True)
    ff.stdin.close()
    ff.wait()
    return time.time() - t0


def main():
    args = sys.argv[1:]
    PREVIEW.mkdir(parents=True, exist_ok=True)
    if "--preview" in args:
        for key, i, start, d, fn in SHOT_FNS:
            t = start + d * 0.55
            img = render(t).resize((W // 2, H // 2), Image.LANCZOS)
            img.save(PREVIEW / f"{key}.png")
            print(f"{key} @ {t:.2f}s → preview/{key}.png", flush=True)
        return
    frame = next((a.split("=", 1)[1] for a in args if a.startswith("--frame=")), None)
    if frame:
        t = float(frame)
        render(t).save(PREVIEW / f"frame_{t:05.2f}.png")
        print(PREVIEW / f"frame_{t:05.2f}.png")
        return
    part = next((a.split("=", 1)[1] for a in args if a.startswith("--part=")), None)
    if part:
        i, n = map(int, part.split("/"))
        first, last = TOTAL * i // n, TOTAL * (i + 1) // n
        out = V / f"part_{i}of{n}.mp4"
    else:
        first, last = 0, TOTAL
        out = V / "picture.mp4"
    dt = encode(out, first, last)
    print(f"{out}  帧 {first}–{last}  用时 {dt:.1f}s")


if __name__ == "__main__":
    main()
