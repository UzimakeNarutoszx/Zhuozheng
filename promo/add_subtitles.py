#!/usr/bin/env python3
"""Burn timed Chinese voice subtitles into an existing 1080x1920 promo."""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FPS = 30
W, H = 1080, 1920
FONT = "/System/Library/Fonts/Supplemental/Songti.ttc"


def rows():
    out = []
    for raw in (ROOT / "promo/lines.txt").read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        key, start, text = [p.strip() for p in raw.split("|", 2)]
        out.append((key, float(start), text))
    durations = json.loads((ROOT / "output/promo-video/tts/durations.json").read_text())
    length = {x["key"]: x["duration"] for x in durations["lines"]}
    return [(key, start, start + length[key], text) for key, start, text in out]


def overlay(frame, t, items, font, small_font):
    active = next((x for x in items if x[1] <= t < x[2]), None)
    if not active:
        return frame
    _, start, end, text = active
    edge = min(t - start, end - t, 0.16)
    alpha = max(0.0, min(1.0, edge / 0.16))
    # Keep captions clear of the existing lower slogan and the platform safe edge.
    box = (76, 1550, W - 76, 1748)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(box, radius=28, fill=(245, 240, 229, int(225 * alpha)), outline=(186, 141, 80, int(150 * alpha)), width=2)
    max_width = box[2] - box[0] - 80
    words = []
    line = ""
    for ch in text:
        candidate = line + ch
        if d.textlength(candidate, font=font) <= max_width:
            line = candidate
        else:
            words.append(line)
            line = ch
    if line:
        words.append(line)
    if len(words) > 2:
        words = [text[: len(text) // 2], text[len(text) // 2 :]]
    y = 1600 if len(words) == 1 else 1576
    for line in words:
        d.text((W // 2, y), line, font=font, anchor="ma", fill=(23, 58, 54, int(255 * alpha)), stroke_width=1, stroke_fill=(245, 240, 229, int(210 * alpha)))
        y += 76
    return Image.alpha_composite(frame.convert("RGBA"), layer).convert("RGB")


def main():
    if len(sys.argv) != 3:
        raise SystemExit("用法: add_subtitles.py 输入.mp4 输出.mp4")
    source, output = map(Path, sys.argv[1:])
    items = rows()
    font = ImageFont.truetype(FONT, 52, index=0)
    small_font = ImageFont.truetype(FONT, 44, index=0)
    decoder = subprocess.Popen([
        "ffmpeg", "-v", "error", "-i", str(source), "-map", "0:v:0", "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ], stdout=subprocess.PIPE)
    encoder = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-pix_fmt", "yuv420p", "-g", "60", str(output),
    ], stdin=subprocess.PIPE)
    frame_bytes = W * H * 3
    n = 0
    while True:
        raw = decoder.stdout.read(frame_bytes)
        if len(raw) != frame_bytes:
            break
        frame = Image.frombytes("RGB", (W, H), raw)
        encoder.stdin.write(overlay(frame, n / FPS, items, font, small_font).tobytes())
        n += 1
    decoder.stdout.close()
    decoder.wait()
    encoder.stdin.close()
    if encoder.wait() != 0 or decoder.returncode != 0:
        raise SystemExit("字幕视频编码失败")
    print(f"字幕烧录完成：{n} 帧")


if __name__ == "__main__":
    main()
