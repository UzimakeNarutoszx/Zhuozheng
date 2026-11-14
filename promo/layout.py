"""拙政观景宣传片版式系统：纸感分层背景 + 宋体标题 + 胶囊标签 + 圆窗遮罩 + 占位块。

只用四个色：宣纸 #f5f0e5、墨绿 #173a36、赭石 #9c4d35、金 #ba8d50（+ 纸深 #e9dfcc / 水 #c7dcd7）。
层级靠 1–3% 明度微差叠出，不用纯黑、不用 1px 黑线。

网格（1080×1920，安全区 top 12% / bottom 22% / right 14%）：
  0–240     顶部平台遮挡区：只有背景
  252       细进度条（9 段）
  292–340   标签行：金色小竖条 + 赭石小字
  372–630   宋体标题块（两行，逐行上浮）
  664–1450  主画面区：录屏卡片（圆角 + 纸感投影）
  1498 起   底部遮挡区
"""
import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
LEFT, RIGHT = 64, 929          # 右侧 14% 留白
SAFE_TOP, SAFE_BOTTOM = 230, 1498
PROGRESS_Y, LABEL_Y, TITLE_TOP = 252, 316, 372
MAIN_BOX = (LEFT, 664, RIGHT, 1450)
CHIPS_Y = 1360


def hexc(s, a=255):
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), a)


INK = hexc("#173a36")
INK_SOFT = hexc("#41645d")
PAPER = hexc("#f5f0e5")
PAPER_DEEP = hexc("#e9dfcc")
PAPER_LIGHT = hexc("#fbf7ee")
WATER = hexc("#c7dcd7")
CLAY = hexc("#9c4d35")
GOLD = hexc("#ba8d50")

FONT_SRC = {
    "song": ("/System/Library/Fonts/Supplemental/Songti.ttc", 0),      # 宋体 Black
    "song_reg": ("/System/Library/Fonts/Supplemental/Songti.ttc", 6),  # 宋体 Regular
    "hei": ("/System/Library/Fonts/STHeiti Medium.ttc", 1),            # 黑体 中黑
    "hei_l": ("/System/Library/Fonts/STHeiti Light.ttc", 1),           # 黑体 细
}


# ---------- 缓动 ----------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_expo(x):
    x = clamp(x)
    return 1 if x == 1 else 1 - 2 ** (-10 * x)


def ease_in_out_cubic(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out_back(x, s=1.7):
    x = clamp(x) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def spring(x, freq=2.2, damp=7.0):
    x = clamp(x)
    return 1 - math.exp(-damp * x) * math.cos(2 * math.pi * freq * x)


# ---------- 字体 ----------
@lru_cache(maxsize=None)
def font(kind, size):
    path, index = FONT_SRC[kind]
    return ImageFont.truetype(path, size, index=index)


def tracked(d, xy, s, f, fill, spacing=0, anchor="lm"):
    """可选字距的一行字；anchor 第二位必须 m/l"""
    if not spacing:
        d.text(xy, s, font=f, fill=fill, anchor=anchor)
        return
    total = sum(d.textlength(ch, font=f) for ch in s) + spacing * (len(s) - 1)
    x = xy[0] - total / 2 if anchor[0] == "m" else xy[0]
    for ch in s:
        d.text((x, xy[1]), ch, font=f, fill=fill, anchor="l" + anchor[1])
        x += d.textlength(ch, font=f) + spacing


# ---------- 合成工具 ----------
def paste(base, im, x, y, alpha=1.0):
    if im is None or alpha <= 0.01:
        return
    if alpha < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    base.paste(im, (int(x), int(y)), im)


def place(base, im, cx, cy, scale=1.0, angle=0.0, alpha=1.0, shadow=0, shadow_dy=None):
    """按中心点缩放旋转贴图；投影用墨绿低透明度，不用纯黑"""
    if im is None or scale <= 0.01 or alpha <= 0.01:
        return base
    w, h = max(1, int(im.width * scale)), max(1, int(im.height * scale))
    out = im.resize((w, h), Image.BICUBIC)
    if angle:
        out = out.rotate(angle, resample=Image.BICUBIC, expand=True)
    if out.mode != "RGBA":
        out = out.convert("RGBA")
    if alpha < 1:
        out.putalpha(out.getchannel("A").point(lambda v: int(v * alpha)))
    x, y = int(cx - out.width / 2), int(cy - out.height / 2)
    if shadow:
        # 先四周留出模糊半径再模糊，避免阴影被裁成硬边矩形
        pad = shadow * 2
        sh = Image.new("RGBA", (out.width + pad * 2, out.height + pad * 2), (*INK[:3], 0))
        mask = Image.new("L", sh.size, 0)
        mask.paste(out.getchannel("A").point(lambda v: int(v * 0.30)), (pad, pad))
        sh.putalpha(mask.filter(ImageFilter.GaussianBlur(shadow)))
        dy = shadow // 2 if shadow_dy is None else shadow_dy
        base.paste(sh, (x - pad, y - pad + dy), sh)
    base.paste(out, (x, y), out)
    return base


def rounded_mask(size, r):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), r, fill=255)
    return m


def circle_mask(size, feather=3):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).ellipse((0, 0, size[0] - 1, size[1] - 1), fill=255)
    return m.filter(ImageFilter.GaussianBlur(feather)) if feather else m


def dash_rect(d, box, color, width=3, dash=18, gap=14):
    """金色虚线框：替代实线黑边框"""
    x0, y0, x1, y1 = box
    for x in range(int(x0), int(x1), dash + gap):
        d.rectangle((x, y0, min(x + dash, x1), y0 + width), fill=color)
        d.rectangle((x, y1 - width, min(x + dash, x1), y1), fill=color)
    for y in range(int(y0), int(y1), dash + gap):
        d.rectangle((x0, y, x0 + width, min(y + dash, y1)), fill=color)
        d.rectangle((x1 - width, y, x1, min(y + dash, y1)), fill=color)


# ---------- 纸感背景 ----------
@lru_cache(maxsize=8)
def _paper_base(seed):
    """静态层：底色 + 两块 2% 明度差的纸块 + 四周极轻的墨色压角，缓存后每帧只 copy"""
    img = Image.new("RGB", (W, H), PAPER[:3])
    m = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(m)
    md.ellipse((-320, int(H * 0.26 + seed * 40), int(W * 0.74), int(H * 0.94)), fill=150)
    md.ellipse((int(W * 0.32), -260, W + 340, int(H * 0.40)), fill=110)
    m = m.filter(ImageFilter.GaussianBlur(170)).point(lambda v: int(v * 0.62))
    img = Image.composite(Image.new("RGB", (W, H), PAPER_DEEP[:3]), img, m)
    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    vd.rectangle((0, 0, W, H), fill=255)
    vd.ellipse((-280, -180, W + 280, H + 200), fill=0)
    vig = vig.filter(ImageFilter.GaussianBlur(150)).point(lambda v: int(v * 0.16))
    img = Image.composite(Image.new("RGB", (W, H), INK[:3]), img, vig)
    return img


@lru_cache(maxsize=8)
def _water_band(seed):
    """斜向柔光带：一条 320×2600 的水色薄雾，逐帧横向漂移"""
    band = Image.new("L", (320, H + 700), 0)
    ImageDraw.Draw(band).polygon([(60, 0), (320, 0), (260, H + 700), (0, H + 700)], fill=64)
    band = band.filter(ImageFilter.GaussianBlur(90))
    out = Image.new("RGBA", band.size, (*WATER[:3], 0))
    out.putalpha(band.point(lambda v: int(v * 0.55)))
    return out


@lru_cache(maxsize=1)
def _dots():
    """点阵层：整屏多画一格，逐帧按偏移裁切，避免每帧重画 500 个点"""
    layer = Image.new("RGBA", (W + 96, H + 96), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for y in range(0, H + 96, 96):
        for x in range(0, W + 96, 96):
            d.ellipse((x - 1.6, y - 1.6, x + 1.6, y + 1.6), fill=(*INK[:3], 13))
    return layer


def paper_bg(t=0.0, seed=0):
    img = _paper_base(seed % 4).copy()
    off = int((t * 6.0) % 96)
    img.paste(_dots().crop((off, off, off + W, off + H)), (0, 0), _dots().crop((off, off, off + W, off + H)))
    band = _water_band(seed % 4)
    bx = int(-200 + ((t * 46 + seed * 260) % (W + 620)))
    paste(img, band, bx, -320, alpha=0.9)
    return img


# ---------- 文字与标签 ----------
def progress(base, idx, total, t):
    """顶部细进度：9 段，当前段赭石，其后纸深"""
    d = ImageDraw.Draw(base, "RGBA")
    seg = (RIGHT - LEFT) / total
    for i in range(total):
        c = (*CLAY[:3], 210) if i < idx else ((*INK_SOFT[:3], 60) if i == idx else (*INK_SOFT[:3], 34))
        d.rounded_rectangle((LEFT + i * seg + 3, PROGRESS_Y, LEFT + (i + 1) * seg - 3, PROGRESS_Y + 5), 3, fill=c)


def label_row(base, label, t, y=LABEL_Y):
    """标签行：金色小竖条 + 赭石黑体小字 + 一道金色细线"""
    k = ease_out_expo(t / 0.3)
    if k <= 0:
        return
    d = ImageDraw.Draw(base, "RGBA")
    d.rectangle((LEFT, y - 15, LEFT + 5, y + 15), fill=(*GOLD[:3], int(255 * k)))
    f = font("hei", 36)
    tracked(d, (LEFT + 22, y), label, f, (*CLAY[:3], int(245 * k)), spacing=4)
    tw = sum(d.textlength(ch, font=f) for ch in label) + 4 * (len(label) - 1)
    x0 = LEFT + 22 + tw + 24
    d.rectangle((x0, y - 1, x0 + int(120 * k), y + 1), fill=(*GOLD[:3], int(150 * k)))


def title_text(base, lines, t, size=100, top=TITLE_TOP, color=INK, stagger=0.1):
    """宋体标题：逐行上浮渐显，左对齐到 LEFT，末行加金色短下划"""
    d = ImageDraw.Draw(base, "RGBA")
    f = font("song", size)
    lh = int(size * 1.2)
    y = top
    for i, line in enumerate(lines):
        lt = clamp((t - 0.06 - i * stagger) / 0.42)
        if lt > 0:
            k = ease_out_expo(lt)
            rise = int((1 - k) * 46)
            a = int(255 * clamp(lt * 2.2))
            layer = Image.new("RGBA", (int(d.textlength(line, font=f)) + 60, lh + 30), (0, 0, 0, 0))
            ImageDraw.Draw(layer).text((0, 0), line, font=f, fill=(*color[:3], a))
            base.paste(layer, (LEFT - 6, y + rise), layer)
        y += lh
    last = clamp((t - 0.06 - (len(lines) - 1) * stagger) / 0.5)
    if last > 0:
        k = ease_out_expo(last)
        d.rectangle((LEFT, y + 6, LEFT + int(96 * k), y + 9), fill=(*GOLD[:3], 220))
    return y


def chips(base, items, t, start=0.35, y=CHIPS_Y, size=34, accent_first=True):
    """胶囊标签行：纸深底 + 墨绿字，第一个描金环；逐个弹入"""
    d = ImageDraw.Draw(base, "RGBA")
    f = font("hei", size)
    widths = [int(d.textlength(s, font=f) + 62) for s in items]
    gap = 16
    total = sum(widths) + gap * (len(items) - 1)
    x = max(LEFT, int((W - total) / 2))
    for i, s in enumerate(items):
        k = ease_out_back(clamp((t - start - i * 0.09) / 0.34), 1.5)
        w, h = widths[i], size + 44
        if k > 0:
            chip = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            cd = ImageDraw.Draw(chip)
            cd.rounded_rectangle((0, 0, w - 1, h - 1), h // 2, fill=(*PAPER_DEEP[:3], 236))
            if accent_first and i == 0:
                cd.rounded_rectangle((0, 0, w - 1, h - 1), h // 2, outline=(*GOLD[:3], 255), width=3)
            cd.text((w / 2, h / 2 - 1), s, font=f, fill=INK, anchor="mm")
            place(base, chip, x + w / 2, y + h / 2, scale=max(0.02, 0.72 + 0.28 * k), alpha=clamp(k * 1.6))
        x += w + gap


def badge(base, x, y, label, t, delay=0.0, size=88):
    """圆窗式小徽章：墨绿圆 + 纸色字，弹入后轻浮动"""
    k = ease_out_back(clamp((t - delay) / 0.32), 1.6)
    if k <= 0.02:
        return
    s = max(2, int(size * (0.6 + 0.4 * k)))
    bob = 6 * math.sin(2 * math.pi * (t * 0.7 + delay))
    disc = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    dd = ImageDraw.Draw(disc)
    dd.ellipse((0, 0, s - 1, s - 1), fill=(*INK[:3], 240))
    dd.ellipse((0, 0, s - 1, s - 1), outline=(*GOLD[:3], 200), width=max(2, s // 34))
    if label:
        dd.text((s / 2, s / 2 - 1), label[0], font=font("song", max(10, int(s * 0.42))), fill=PAPER_LIGHT, anchor="mm")
    base.paste(disc, (int(x - s / 2), int(y - s / 2 + bob)), disc)


def placeholder(base, box, key, note="等待录屏"):
    """素材缺位时的占位块：纸深底色 + 金色虚线框 + 键名，保证脚本可独立跑通"""
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = max(40, x1 - x0), max(40, y1 - y0)
    panel = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    pd.rounded_rectangle((0, 0, w - 1, h - 1), 36, fill=(*PAPER_DEEP[:3], 244))
    dash_rect(pd, (18, 18, w - 18, h - 18), (*GOLD[:3], 210), width=3, dash=20, gap=14)
    pd.text((w / 2, h / 2 - 18), key, font=font("hei", 34), fill=(*CLAY[:3], 245), anchor="mm")
    pd.text((w / 2, h / 2 + 30), note, font=font("hei_l", 26), fill=(*INK_SOFT[:3], 235), anchor="mm")
    base.paste(panel, (x0, y0), panel)


def card(base, screen, cx=None, cy=None, radius=44, shadow=42, scale=1.0, alpha=1.0):
    """屏幕卡片：外层纸白衬边（比底色亮 2%）+ 墨绿投影，内层圆角录屏"""
    if screen is None:
        return
    if scale != 1.0:
        screen = screen.resize((max(1, int(screen.width * scale)), max(1, int(screen.height * scale))), Image.BICUBIC)
    w, h = screen.width, screen.height
    frame = Image.new("RGBA", (w + 14, h + 14), (0, 0, 0, 0))
    ImageDraw.Draw(frame).rounded_rectangle((0, 0, w + 13, h + 13), radius + 7, fill=(*PAPER_LIGHT[:3], 255))
    frame.paste(screen, (7, 7), screen)
    cx = W / 2 if cx is None else cx
    cy = (MAIN_BOX[1] + MAIN_BOX[3]) / 2 if cy is None else cy
    place(base, frame, cx, cy, alpha=alpha, shadow=shadow)
