#!/bin/bash
# 30 秒宣传片音轨：《憩》30 秒片段 + 本工程合成音效 + Qwen 旁白。
# 依赖 promo/beats.py（拿推荐起点）、promo/tts.py（拿 tts/*.wav）、promo/sfx.sh（拿 sfx/*.wav）。
#
# 音效时间表（对应 promo/timeline.json）：
#   每个 cuts 处 whoosh（提前 0.15s，-10dB）+ tap（+0.3s，-14dB）
#   3.5s hit -4dB ｜ 27.0s ding -8dB ｜ 0.3s ding -12dB
# 旁白按 lines.txt 开始秒 adelay；配乐取 30s，末尾 1.7s 淡出；sidechain 让旁白压低配乐；
# alimiter 后两遍 loudnorm 到 I=-14 TP=-2.2，输出 audio.m4a（AAC 192k / 48kHz / 立体声 / 精确 30.000s）。
#
# 用法: promo/audio.sh [起点秒]   默认取 beats 推荐 start
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$PWD
TRACK="/Users/ens/Music/已完成文件/憩.mp3"
BEATS_JSON=output/promo-video/beats/憩.json
TTS=output/promo-video/tts
SFX=output/promo-video/sfx
W=output/promo-video/audio_work
OUT=output/promo-video/audio.m4a
DUR=30.0; FADE=1.7; SR=48000

[[ -f $BEATS_JSON ]] || { echo "缺 ${BEATS_JSON}，先跑 python3 promo/beats.py"; exit 1; }
[[ -f $TTS/durations.json ]] || { echo "缺 $TTS/durations.json，先跑 promo/tts.py"; exit 1; }
for f in whoosh tap ding hit; do
  [[ -f $SFX/$f.wav ]] || { echo "缺 $SFX/$f.wav，先跑 promo/sfx.sh"; exit 1; }
done
mkdir -p "$W"

START=${1:-$(python3 -c "import json;print(json.load(open('$BEATS_JSON'))['recommended_start'])")}

lufs() { ffmpeg -hide_banner -nostats -i "$1" -af ebur128 -f null - 2>&1 \
  | awk '/Summary/{s=1} s&&/I:/{print $2; exit}'; }
tpeak() { ffmpeg -hide_banner -nostats -i "$1" -af ebur128=peak=true -f null - 2>&1 \
  | awk '/True peak/{s=1} s&&/Peak:/{print $2; exit}'; }
# 秒 → 毫秒（整数），adelay 只吃整数毫秒
ms() { awk -v s="$1" 'BEGIN{printf "%d", s*1000 + 0.5}'; }

echo "起点 ${START}s，原曲 ${TRACK}"

# 旁白超限提醒：lines.txt 改稿前会有句子长过可用时段，混音时就会和下一句叠在一起
python3 - <<'PY'
import json
d = json.load(open('output/promo-video/tts/durations.json'))
over = [r for r in d['lines'] if not r['ok']]
if over:
    print(f"⚠ tempo {d['tempo']}：{len(over)} 句旁白超出可用时长，会与下一句重叠（需改稿，见 tts.py 报告）")
    for r in over:
        print(f"    {r['key']}: {r['duration']:.2f}s > 可用 {r['budget']:.2f}s")
else:
    print(f"旁白全部在可用时长内（tempo {d['tempo']}）")
PY

# ---------- 1. 音效 ----------
cuts=$(python3 -c "import json;print(' '.join(str(c) for c in json.load(open('promo/timeline.json'))['cuts']))")
names=(); ats=(); gains=()
add() { names+=("$1"); ats+=("$2"); gains+=("$3"); }
for c in $cuts; do
  add whoosh "$(awk -v c="$c" 'BEGIN{printf "%.3f", c-0.15}')" -10
  add tap    "$(awk -v c="$c" 'BEGIN{printf "%.3f", c+0.30}')" -14
done
add hit  3.5   -4
add ding 27.0  -8
add ding 0.3   -12

ins=(); filt=""; i=0
for k in "${!names[@]}"; do
  ins+=(-i "$SFX/${names[$k]}.wav")
  filt+="[${i}:a]aresample=${SR},aformat=sample_fmts=fltp:channel_layouts=stereo,volume=${gains[$k]}dB,adelay=$(ms "${ats[$k]}"):all=1[e$i];"
  i=$((i + 1))
done
mix=""; for j in $(seq 0 $((i - 1))); do mix+="[e$j]"; done
filt+="${mix}amix=inputs=${i}:normalize=0,apad=whole_dur=${DUR},atrim=0:${DUR}[o]"
ffmpeg -v error -y "${ins[@]}" -filter_complex "$filt" -map "[o]" -ar "$SR" "$W/sfx.wav"
echo "音效 ${#names[@]} 个 → $W/sfx.wav"

# ---------- 2. 旁白 ----------
ins=(); filt=""; i=0; keys=()
while IFS='|' read -r key at txt; do
  key=${key%% }; at=${at## }; [[ -z $key || $key == \#* ]] && continue
  ins+=(-i "$TTS/$key.wav")
  filt+="[${i}:a]aresample=${SR},aformat=sample_fmts=fltp:channel_layouts=stereo,adelay=$(ms "$at"):all=1[v$i];"
  keys+=("$key")
  i=$((i + 1))
done < promo/lines.txt
mix=""; for j in $(seq 0 $((i - 1))); do mix+="[v$j]"; done
filt+="${mix}amix=inputs=${i}:normalize=0,apad=whole_dur=${DUR},atrim=0:${DUR}[o]"
ffmpeg -v error -y "${ins[@]}" -filter_complex "$filt" -map "[o]" -ar "$SR" "$W/voice_raw.wav"
voice_i=$(lufs "$W/voice_raw.wav")
ffmpeg -v error -y -i "$W/voice_raw.wav" -af "volume=$(awk -v t=-15 -v m="$voice_i" 'BEGIN{printf "%.2f", t-m}')dB" -ar "$SR" "$W/voice.wav"
echo "旁白 ${#keys[@]} 句 → $W/voice.wav（原始 ${voice_i} LUFS，归一到 -15 LUFS）"

# ---------- 3. 配乐 ----------
# 原曲是流媒体母带，真峰值过 0；先降 4dB 再做后续处理，避免在 30s 截取段就削波
bed_tp=$(ffmpeg -hide_banner -nostats -ss "$START" -t "$DUR" -i "$TRACK" -vn -af "ebur128=peak=true" -f null - 2>&1 \
  | awk '/True peak/{s=1} s&&/Peak:/{print $2; exit}')
preamp=0
awk -v p="$bed_tp" 'BEGIN{exit !(p+0 > -0.1)}' && preamp=-4
ffmpeg -v error -y -ss "$START" -t "$DUR" -i "$TRACK" -vn -af \
  "aresample=${SR},aformat=sample_fmts=fltp:channel_layouts=stereo,volume=${preamp}dB,afade=t=out:st=$(awk -v d=$DUR -v f=$FADE 'BEGIN{printf "%.3f", d-f}'):d=${FADE}" \
  "$W/bed_raw.wav"
bed_i=$(lufs "$W/bed_raw.wav")
ffmpeg -v error -y -i "$W/bed_raw.wav" -af "volume=$(awk -v t=-19 -v m="$bed_i" 'BEGIN{printf "%.2f", t-m}')dB" -ar "$SR" "$W/bed.wav"
echo "配乐 ${START}s 起 30s → $W/bed.wav（截取段真峰值 ${bed_tp} dBTP，预降 ${preamp}dB，原始 ${bed_i} LUFS → -19 LUFS）"

# ---------- 4. 混音 ----------
# sidechaincompress：旁白当键信号，压配乐；再把旁白和音效平行叠回来。
# threshold 0.08/ratio 2.5 实测在旁白段压掉约 3.7dB（最深 10dB）——旁白几乎铺满整片，
# 压更深（例如 0.02/ratio 4 会压到 13.8dB）后侧链一直在工作，配乐会被抽空、失去呼吸。
ffmpeg -v error -y -i "$W/bed.wav" -i "$W/voice.wav" -i "$W/sfx.wav" -filter_complex \
  "[0:a][1:a]sidechaincompress=threshold=0.08:ratio=2.5:attack=15:release=300:makeup=1[d];\
[d][1:a][2:a]amix=inputs=3:normalize=0[o]" \
  -map "[o]" -ar "$SR" "$W/mix_raw.wav"
ffmpeg -v error -y -i "$W/mix_raw.wav" -af "alimiter=limit=0.7:level=0:attack=1:release=60" -ar "$SR" "$W/mix_lim.wav"

# ---------- 5. 两遍 loudnorm → I=-14 TP=-2.2 ----------
measure() {  # 输出 "I TP LRA thresh offset"
  ffmpeg -hide_banner -nostats -i "$1" -af "loudnorm=I=-14:TP=-2.2:LRA=11:print_format=json" -f null - 2>&1 \
    | python3 -c "import sys,json,re; d=json.loads(re.search(r'\{.*\}', sys.stdin.read(), re.S).group()); print(d['input_i'], d['input_tp'], d['input_lra'], d['input_thresh'], d['target_offset'])"
}
encode() {  # $1 输入 wav $2 输出 m4a $3 额外预增益 dB
  local extra=${3:-0}
  ffmpeg -v error -y -i "$1" -af \
    "loudnorm=I=-14:TP=-2.2:LRA=11:measured_I=${mi}:measured_TP=${mtp}:measured_LRA=${mlra}:measured_thresh=${mth}:offset=${moff}:linear=true,volume=${extra}dB,aresample=${SR}" \
    -t "$DUR" -c:a aac -b:a 192k -ar "$SR" -ac 2 "$2"
}

read -r mi mtp mlra mth moff <<< "$(measure "$W/mix_lim.wav")"
echo "第一遍测量：I=${mi} TP=${mtp} LRA=${mlra} thresh=${mth} offset=${moff}"
encode "$W/mix_lim.wav" "$OUT" 0

# AAC 编码会把真峰值顶高（实测约 +0.8dB），编码后再测一次，超出 TP 就按差值补偿重编
tp_out=$(tpeak "$OUT"); i_out=$(lufs "$OUT")
fix=$(awk -v p="$tp_out" -v lim=-2.3 'BEGIN{ d=lim-p; if (d<0) printf "%.2f", d; else print "0" }')
if [[ $fix != 0 ]]; then
  echo "编码后真峰值 ${tp_out} dBTP 超目标，按 ${fix}dB 补偿重编"
  encode "$W/mix_lim.wav" "$OUT" "$fix"
  tp_out=$(tpeak "$OUT"); i_out=$(lufs "$OUT")
fi
echo "编码后实测：I=${i_out} LUFS，真峰值 ${tp_out} dBTP"

echo
echo "输出 $OUT"
ffprobe -v error -show_entries format=duration:stream=sample_rate,channels,codec_name,bit_rate -of default=nw=1 "$OUT"
echo "实测 ebur128："
ffmpeg -hide_banner -nostats -i "$OUT" -af ebur128=peak=true -f null - 2>&1 | sed -n '/Summary/,$p' | head -18
