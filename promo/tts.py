#!/usr/bin/env python3
"""按 promo/lines.txt 逐句合成旁白（Qwen3-TTS / MLX），输出 48kHz 单声道 wav。

两种模式：
  预置音色（默认）——CustomVoice 模型 + --voice（默认 Vivian）；
  声音克隆——给 --ref-audio 和 --ref-text 就走 Base 模型的 ICL 克隆，音色取自参考音频。

缓存键 = 文本 + 模型 + 音色/参考音频内容 + tempo 的哈希：文本没改就不重算，wav 直接从 cache/ 复制。
每句时长受下一句开始秒约束（留 0.15s 交接余量；最后一句预留 0.3s 尾巴），
超限时如实报告各句时长，可用 --tempo 整体提速（上限 1.2）后重跑；不改 lines.txt。

用法:
  promo/tts.py --tempo 1.2
  promo/tts.py --model mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit \\
      --ref-audio output/promo-video/voice_ref/ref.wav \\
      --ref-text output/promo-video/voice_ref/ref.txt --tempo 1.2
（脚本会自己切到 ~/.local/share/qwen3-tts/venv/bin/python 执行。）
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/promo-video/tts"
CACHE = OUT / "cache"
LINES = ROOT / "promo/lines.txt"
VENV_PY = Path.home() / ".local/share/qwen3-tts/venv/bin/python"
MODEL = "mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-4bit"  # --model 可覆盖（克隆模式用 Base 模型）
VOICE = "Vivian"  # 克隆模式下忽略
TOTAL, GAP, TAIL = 30.0, 0.15, 0.3
VERSION = "v3"  # 改动合成流程就 +1，旧缓存自动失效（克隆模式靠 ref_sig 天然区分，不必 +1）
PAD = 0.03  # 去空白后每边留 30ms，避免咬掉字头


def ensure_runtime():
    """不在 qwen3-tts 的 venv 里就用 venv 的解释器重跑自己。"""
    try:
        import mlx.core  # noqa: F401
        import mlx_audio.tts.utils  # noqa: F401
        import numpy  # noqa: F401
        import soundfile  # noqa: F401
        return
    except ImportError:
        if Path(sys.executable).resolve() != VENV_PY.resolve() and VENV_PY.exists():
            os.execv(str(VENV_PY), [str(VENV_PY), str(Path(__file__).resolve()), *sys.argv[1:]])
        raise SystemExit(f"缺 mlx/numpy/soundfile：请用 {VENV_PY} 运行本脚本")


def read_lines():
    rows = []
    for raw in LINES.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 3:
            raise SystemExit(f"lines.txt 格式应为 key|开始秒|文本，这一行是: {raw!r}")
        key, at, text = parts
        rows.append(dict(key=key, start=float(at), text=text))
    if not rows:
        raise SystemExit(f"{LINES} 里没有可用句子")
    for i, row in enumerate(rows):
        if i + 1 < len(rows):
            row["budget"] = round(rows[i + 1]["start"] - row["start"] - GAP, 3)
        else:
            row["budget"] = round(TOTAL - row["start"] - TAIL, 3)
    return rows


def probe(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "default=nw=1:nk=1", str(path)])
    return float(out.strip())


def synth(text, raw, model, mx, np, sf, ref=None):
    """ref 为 (音频路径, 参考文本) 时走 Base 模型的 ICL 克隆，否则用预置音色。"""
    mx.random.seed(42)  # 固定种子，同一句每次都一样，缓存才有意义
    chunks, rate = [], 24000
    kw = dict(lang_code="Chinese", max_tokens=350, temperature=.65)
    if ref:
        kw.update(ref_audio=str(ref[0]), ref_text=ref[1])
    else:
        kw.update(voice=VOICE)
    # Qwen occasionally misreads the garden name; use a phonetic proxy only for
    # synthesis while keeping the displayed transcript and source copy correct.
    spoken_text = text.replace("拙政", "桌政")
    for result in model.generate(text=spoken_text, **kw):
        mx.eval(result.audio)
        chunks.append(np.array(result.audio))
        rate = result.sample_rate
    if not chunks:
        raise RuntimeError(f"Qwen 没有返回音频: {text}")
    sf.write(str(raw), np.concatenate(chunks), rate, format="WAV")


def trim_pad(path):
    """Qwen 的输出两端各带 ~0.4–0.6s 静音，不去掉 adelay 就整体后移，掐掉只留 30ms 余量。"""
    import numpy as np
    import soundfile as sf
    x, sr = sf.read(str(path), dtype="float32", always_2d=True)
    a = np.abs(x).max(axis=1)
    if a.max() <= 0:
        return
    idx = np.nonzero(a > a.max() * 0.01)[0]
    lo = max(int(idx[0]) - int(sr * PAD), 0)
    hi = min(int(idx[-1]) + int(sr * PAD) + 1, len(x))
    sf.write(str(path), x[lo:hi], sr, format="WAV")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tempo", type=float, default=1.0, help="整体语速（0.8–1.2，用 ffmpeg atempo）")
    ap.add_argument("--model", default=MODEL, help="HF 仓库名或本地目录（克隆模式要 Base 模型）")
    ap.add_argument("--voice", default=VOICE, help="预置音色（CustomVoice 模型用；克隆模式忽略）")
    ap.add_argument("--ref-audio", type=Path, help="参考音频，给了就和 --ref-text 一起走克隆模式")
    ap.add_argument("--ref-text", type=Path, help="参考音频的逐字文本（一行）")
    args = ap.parse_args()
    if not 0.8 <= args.tempo <= 1.2:
        ap.error("tempo 必须在 0.8–1.2 之间")
    if bool(args.ref_audio) != bool(args.ref_text):
        ap.error("--ref-audio 和 --ref-text 必须一起给")
    ref = None
    if args.ref_audio:
        for p in (args.ref_audio, args.ref_text):
            if not p.is_file():
                ap.error(f"文件不存在: {p}")
        ref_text = args.ref_text.read_text(encoding="utf-8").strip()
        if not ref_text:
            ap.error(f"{args.ref_text} 是空的，克隆模式需要逐字对应参考音频的文本")
        ref = (args.ref_audio.resolve(), ref_text)
    voice = None if ref else args.voice
    # 参考音频内容也进哈希：换参考片段就重算，不会误命中旧音色
    ref_sig = hashlib.sha256(ref[0].read_bytes()).hexdigest()[:16] + "|" + ref[1] if ref else voice

    rows = read_lines()
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    todo = []
    for row in rows:
        digest = hashlib.sha256(f"{row['text']}|{ref_sig}|{args.tempo:.3f}|{args.model}|{VERSION}".encode()).hexdigest()[:16]
        row["hash"] = digest
        row["cached"] = (CACHE / f"{digest}.wav").exists()
        if not row["cached"]:
            todo.append(row)

    if todo:
        ensure_runtime()
        import mlx.core as mx
        import numpy as np
        import soundfile as sf
        from mlx_audio.tts.utils import load_model
        who = f"克隆参考 {ref[0].name}" if ref else f"音色 {voice}"
        print(f"加载 {args.model}（{who}，tempo {args.tempo}）…", flush=True)
        model = load_model(args.model)
        for row in todo:
            raw = CACHE / f"{row['hash']}.raw.wav"
            dst = CACHE / f"{row['hash']}.wav"
            print(f"  合成 {row['key']}: {row['text']}", flush=True)
            synth(row["text"], raw, model, mx, np, sf, ref)
            # 先 atempo，再统一成 48kHz 单声道，最后掐掉两端静音
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af",
                            f"atempo={args.tempo:.4f}", "-ar", "48000", "-ac", "1", str(dst)], check=True)
            trim_pad(dst)
            raw.unlink()
    else:
        print(f"全部命中缓存（tempo {args.tempo}），跳过合成")

    report = []
    for row in rows:
        dst = OUT / f"{row['key']}.wav"
        shutil.copyfile(CACHE / f"{row['hash']}.wav", dst)
        row["duration"] = round(probe(dst), 3)
        row["headroom"] = round(row["budget"] - row["duration"], 3)
        row["ok"] = row["headroom"] >= 0
        row["file"] = str(dst.relative_to(ROOT))
        report.append(row)

    (OUT / "durations.json").write_text(json.dumps(dict(
        voice=voice, model=args.model, tempo=args.tempo, sample_rate=48000, channels=1,
        ref_audio=str(ref[0].relative_to(ROOT)) if ref and ref[0].is_relative_to(ROOT) else (str(ref[0]) if ref else None),
        ref_text=ref[1] if ref else None,
        total=TOTAL, gap=GAP, tail=TAIL,
        lines=[{k: r[k] for k in ("key", "start", "text", "duration", "budget", "headroom", "ok", "file", "hash")}
               for r in report],
    ), ensure_ascii=False, indent=1) + "\n")

    print(f"\n{'句':<10}{'开始':>6}{'时长':>8}{'可用':>8}{'余量':>8}  状态")
    for r in report:
        flag = "OK" if r["ok"] else "超限"
        print(f"{r['key']:<10}{r['start']:>6.2f}{r['duration']:>8.3f}{r['budget']:>8.3f}{r['headroom']:>+8.3f}  {flag}")

    over = [r for r in report if not r["ok"]]
    if over:
        need = max(r["duration"] / r["budget"] for r in over) * args.tempo
        print(f"\n{len(over)} 句超限：" + "、".join(r["key"] for r in over))
        if args.tempo < 1.2 and need <= 1.2:
            print(f"可整体提速到 tempo={min(need, 1.2):.2f} 再试：promo/tts.py --tempo {min(need, 1.2):.2f}")
        else:
            print("tempo 已到 1.2 上限仍不够，这几句需要改稿（我不擅自改文本）：")
            for r in over:
                print(f"  {r['key']}: {r['duration']:.2f}s > 可用 {r['budget']:.2f}s（多 {r['duration'] - r['budget']:.2f}s）")
        raise SystemExit(2)
    print(f"\n全部在预算内，最紧的一句余量 {min(r['headroom'] for r in report):.3f}s → {OUT}/durations.json")


if __name__ == "__main__":
    main()
