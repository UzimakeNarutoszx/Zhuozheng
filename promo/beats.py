"""《憩》配乐分析：估 BPM、跟踪拍点、算能量曲线，并挑出合适的 30 秒片段起点。

纯 numpy 实现（频谱通量做起拍包络 → 自相关估 BPM → 动态规划跟拍，Ellis 2007 思路）。
片段挑选的约束来自 promo/timeline.json：music.drop_at = 3.5s，即片段内 3.5s 处要落在
明显能量抬升/重拍上；同时 30 秒段整体不能是渐弱收尾。

输出 output/promo-video/beats/憩.json：bpm、推荐 start、前 3 个候选及理由、片段内拍点列表。
用法: python3 promo/beats.py [音频路径]
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/promo-video/beats"
TRACK = Path("/Users/ens/Music/已完成文件/憩.mp3")
SEG, DROP_AT, FADE = 30.0, 3.5, 1.7

SR, HOP, NFFT = 22050, 512, 2048


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def onset_envelope(x):
    win = np.hanning(NFFT).astype(np.float32)
    frames = np.lib.stride_tricks.sliding_window_view(x, NFFT)[::HOP] * win
    mag = np.abs(np.fft.rfft(frames, axis=1))
    logmag = np.log1p(100 * mag)
    flux = np.maximum(np.diff(logmag, axis=0), 0).sum(axis=1)
    flux = np.concatenate([[0], flux])
    k = int(SR / HOP * 0.5)
    trend = np.convolve(flux, np.ones(k) / k, mode="same")
    env = np.maximum(flux - trend, 0)
    rms = np.sqrt((frames ** 2).mean(axis=1))
    return env / (env.std() + 1e-9), rms


def tempo(env):
    fps = SR / HOP
    ac = np.correlate(env, env, "full")[len(env) - 1:]
    lags = np.arange(len(ac)) / fps
    bpm = 60 / np.maximum(lags, 1e-9)
    ok = (bpm > 60) & (bpm < 180)
    prior = np.exp(-0.5 * (np.log2(bpm / 120) / 0.9) ** 2)
    score = np.where(ok, ac * prior, 0)
    lag = int(np.argmax(score))
    return 60 * fps / lag, lag


def track_beats(env, period, tightness=100):
    n = len(env)
    score = env.copy()
    back = np.full(n, -1)
    lo, hi = int(round(period * 0.5)), int(round(period * 2))
    for i in range(hi, n):
        prev = np.arange(i - hi, i - lo)
        pen = -tightness * np.log((i - prev) / period) ** 2
        cand = score[prev] + pen
        j = int(np.argmax(cand))
        score[i] = env[i] + cand[j]
        back[i] = prev[j]
    i = int(np.argmax(score[-hi:])) + n - hi
    beats = []
    while i >= 0:
        beats.append(i)
        i = back[i]
    return np.array(beats[::-1])


def db(v):
    return 20 * np.log10(max(float(v), 1e-9))


def window_db(rms, t0, t1):
    a, b = int(t0 * SR / HOP), int(t1 * SR / HOP)
    a, b = max(a, 0), min(b, len(rms))
    if b <= a:
        return -120.0
    return db(np.sqrt((rms[a:b] ** 2).mean()))


def find_start(rms, env, times, bpm):
    """在拍点网格上滑动 30 秒窗打分。

    drop 要求落在片内 3.5s，所以只测落点上下 0.4s 的局部能量变化——
    跨整段的 RMS 平均会被乐句掩盖，看不出"这里砸了一拍"。
    """
    fps = SR / HOP
    last = times[-1] - SEG - 0.05
    cands = []
    for s in times:
        if s < 0.2 or s > last:
            continue
        d = s + DROP_AT
        # 落点局部能量：前 0.4s vs 后 0.4s（宁可是真实抬升，不是长段平均）
        pre = window_db(rms, d - 0.4, d - 0.05)
        post = window_db(rms, d + 0.05, d + 0.45)
        rise = post - pre
        # 落点 ±80ms 的起拍强度：够大说明这一拍是击打而不是气声
        a, b = int((d - 0.08) * fps), int((d + 0.20) * fps)
        onset_at_drop = float(env[a:b].max()) if b > a else 0.0
        # 收尾健康度：末段（扣掉 1.7s 淡出）不能比中段明显弱
        tail = window_db(rms, s + SEG - FADE - 3.0, s + SEG - FADE)
        mid = window_db(rms, s + 10.0, s + 15.0)
        end_gap = tail - mid
        # 片段弧线：后 10s 不比前 7.5s 掉太多（不要抽一段渐弱结尾）
        arc = window_db(rms, s + 20.0, s + SEG) - window_db(rms, s, s + 7.5)
        level = window_db(rms, s, s + SEG)
        score = (min(rise, 6.0) * 1.6 + min(onset_at_drop, 4.0) * 1.1
                 + max(min(end_gap, 3.0), -5.0) * 0.7 + max(min(arc, 4.0), -5.0) * 0.5
                 + (level + 22) * 0.15)
        cands.append(dict(start=round(float(s), 2), score=round(float(score), 2),
                          drop_time=round(float(d), 2), rise_db=round(float(rise), 1),
                          onset_at_drop=round(float(onset_at_drop), 2), end_gap_db=round(float(end_gap), 1),
                          arc_db=round(float(arc), 1), level_db=round(float(level), 1)))
    cands.sort(key=lambda c: -c["score"])
    picked = []
    for c in cands:  # 候选之间至少隔开 8 秒，避免三强都是同一处
        if all(abs(c["start"] - p["start"]) > 8.0 for p in picked):
            picked.append(c)
        if len(picked) == 3:
            break
    return picked


def reasons(c):
    out = []
    if c["rise_db"] >= 3:
        out.append(f"片内 {DROP_AT:.1f}s 落点局部抬升 {c['rise_db']:+.1f}dB，重拍砸得实")
    elif c["rise_db"] >= 1:
        out.append(f"片内 {DROP_AT:.1f}s 落点局部抬升 {c['rise_db']:+.1f}dB，抬升够用")
    else:
        out.append(f"片内 {DROP_AT:.1f}s 落点只有 {c['rise_db']:+.1f}dB 变化，缺少明显抬升")
    if c["onset_at_drop"] >= 2.0:
        out.append(f"落点起拍强度 {c['onset_at_drop']:.2f}（明显击打）")
    else:
        out.append(f"落点起拍强度偏低 {c['onset_at_drop']:.2f}，冲击感要靠音效补")
    if c["end_gap_db"] >= -1.5:
        out.append(f"末段（扣淡出）相对中段 {c['end_gap_db']:+.1f}dB，收尾不塌")
    else:
        out.append(f"末段（扣淡出）相对中段 {c['end_gap_db']:+.1f}dB，渐弱收尾风险")
    out.append(f"片内弧线 后10s−前7.5s {c['arc_db']:+.1f}dB，整体电平 {c['level_db']:.1f}dBFS")
    return out


def analyse(path):
    x = load(path)
    env, rms = onset_envelope(x)
    bpm, lag = tempo(env)
    beats = track_beats(env, lag)
    t = beats * HOP / SR
    cands = find_start(rms, env, t, bpm)
    for c in cands:
        c["reasons"] = reasons(c)
    best = cands[0]["start"]
    in_seg = [round(float(v - best), 3) for v in t if best <= v <= best + SEG]
    # 落点与最近拍点的偏差：>60ms 就该在报告里点名，音效要对齐拍点而不是死磕 3.5s
    near = min(in_seg, key=lambda v: abs(v - DROP_AT)) if in_seg else DROP_AT
    curve = [dict(t=round(i * HOP / SR, 2),
                  db=round(float(window_db(rms, i * HOP / SR, (i + 50) * HOP / SR)), 1))
             for i in range(0, len(rms), 50)]  # 每格约 1.16s
    return dict(
        file=str(path), duration=round(len(x) / SR, 2), bpm=round(float(bpm), 1),
        beat_count=len(t), beat_interval_median=round(float(np.median(np.diff(t))), 3),
        drop_at=DROP_AT, segment=SEG, recommended_start=best,
        drop_beat_in_segment=round(float(near), 3),
        drop_beat_offset_ms=round(float(near - DROP_AT) * 1000, 1),
        candidates=cands,
        beats_in_segment=in_seg,
        energy_curve=curve,
        note="beats_in_segment 与 energy_curve 的时间轴均为片段内相对秒（以 recommended_start 为 0）；energy_curve 每格 1.16s RMS。",
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else TRACK
    res = analyse(path)
    (OUT / f"{path.stem}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    print(f"{path.stem}: {res['bpm']} BPM, {res['beat_count']} beats, 拍间隔中位数 {res['beat_interval_median']}s, "
          f"时长 {res['duration']}s")
    print(f"推荐 start = {res['recommended_start']}s（片内 {DROP_AT}s 落点 → 原曲 {res['recommended_start'] + DROP_AT:.2f}s，"
          f"最近拍点 {res['drop_beat_in_segment']}s，偏差 {res['drop_beat_offset_ms']:+.0f}ms）")
    for i, c in enumerate(res["candidates"], 1):
        print(f"  候选{i} start={c['start']}s score={c['score']} rise={c['rise_db']:+.1f}dB "
              f"onset={c['onset_at_drop']:.2f} end_gap={c['end_gap_db']:+.1f}dB arc={c['arc_db']:+.1f}dB "
              f"level={c['level_db']:.1f}dBFS")
        for r in c["reasons"]:
            print(f"        · {r}")


if __name__ == "__main__":
    main()
