#!/bin/bash
# 30 秒宣传片音效：全部用 ffmpeg lavfi 现场合成（不联网、不用外部素材）。
#   whoosh  带通噪声扫频 0.35s（11 段相邻频带 acrossfade 拼出真正的 400→3800Hz 扫频）
#   tap     短促木质感 0.08s（两个快衰减谐振峰 + 起手噪声）
#   ding    正弦 + 非整数泛音衰减 0.8s，偏中式磬声
#   hit     低频冲击 0.25s（55→38Hz 下滑的指数衰减正弦 + 120Hz 击体）
# 每个文件真峰值都压到 < -3 dBTP。输出 output/promo-video/sfx/
# 用法: promo/sfx.sh
set -euo pipefail
cd "$(dirname "$0")/.."
SFX=output/promo-video/sfx; W=output/promo-video/sfx_work; mkdir -p "$SFX" "$W"
SR=48000; TP_MAX=-3.0

# 真峰值（dBTP）：取 ebur128 的 True peak / Peak 行
tpeak() { ffmpeg -hide_banner -nostats -i "$1" -af ebur128=peak=true -f null - 2>&1 \
  | awk '/True peak/{s=1} s&&/Peak:/{print $2; exit}'; }

# 32bit float 中间产物落到指定真峰值：真峰值是线性量，按差值缩放即可（带 1 位小数，误差 < 0.05dB）
finish() {  # $1 输入 $2 输出 $3 目标真峰值
  local tp gain
  tp=$(tpeak "$1")
  gain=$(awk -v t="$3" -v p="$tp" 'BEGIN{printf "%.3f", t - p}')
  ffmpeg -v error -y -i "$1" -af "volume=${gain}dB,aresample=${SR}" -ac 1 -c:a pcm_s16le "$2"
  printf "  %-11s %5.3fs  真峰值 %5.1f → %5.1f dBTP（增益 %+.1fdB）\n" \
    "$(basename "$2")" "$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$2")" \
    "$tp" "$(tpeak "$2")" "$gain"
}

echo "合成音效 → $SFX"

# 1) whoosh：11 段粉噪各过窄带通（中心 400→3800Hz 等比），相邻段 acrossfade 交叉，
#    拼出连续上扫；再套 0.35s 抛物线包络（pow(sin,1.6)）压到 0.35s。
N=11; SEG=0.0455; XF=0.0141
ins=(); filters=""
for i in $(seq 0 $((N - 1))); do
  c=$(awk -v i="$i" -v n="$N" -v f0=400 -v f1=3800 'BEGIN{printf "%.1f", f0*exp((i+0.5)/n*log(f1/f0))}')
  ins+=(-f lavfi -i "anoisesrc=color=pink:r=${SR}:d=${SEG}:a=0.9")
  filters+="[${i}:a]bandpass=f=${c}:width_type=q:w=1.1[sf$i];"
done
prev="[sf0]"
for i in $(seq 1 $((N - 1))); do
  filters+="${prev}[sf$i]acrossfade=d=${XF}:c1=tri:c2=tri[cf$i];"
  prev="[cf$i]"
done
filters+="${prev}highpass=f=250,lowpass=f=7000,aformat=sample_fmts=fltp,"
filters+="volume=pow(sin(PI*t/0.3595)\\,1.6):eval=frame,atrim=0:0.35[o]"
ffmpeg -v error -y "${ins[@]}" -filter_complex "$filters" -map "[o]" -c:a pcm_f32le "$W/whoosh_raw.wav"

# 2) tap：木质短促——两个快速衰减的谐振峰（1900/3200Hz）+ 12ms 噪声起手，0.08s
ffmpeg -v error -y -f lavfi -i "sine=frequency=1900:r=${SR}:d=0.08" -f lavfi -i "sine=frequency=3200:r=${SR}:d=0.08" \
  -f lavfi -i "anoisesrc=color=white:r=${SR}:d=0.012:a=0.6" -filter_complex \
  "[0:a]volume='exp(-t*34)':eval=frame[a];[1:a]volume='exp(-t*52)*0.45':eval=frame[b];\
[2:a]bandpass=f=2600:width_type=q:w=2,volume='exp(-t*90)':eval=frame[c];\
[a][b][c]amix=inputs=3:normalize=0,highpass=f=600,aformat=sample_fmts=fltp,atrim=0:0.08[o]" \
  -map "[o]" -c:a pcm_f32le "$W/tap_raw.wav"

# 3) ding：磬声 = 基频 660Hz + 非整数泛音（997/1340/1841Hz，金属感）+ 极短击打噪声，分级衰减，0.8s
ffmpeg -v error -y -f lavfi -i "sine=frequency=660:r=${SR}:d=0.8" -f lavfi -i "sine=frequency=997:r=${SR}:d=0.8" \
  -f lavfi -i "sine=frequency=1340:r=${SR}:d=0.8" -f lavfi -i "sine=frequency=1841:r=${SR}:d=0.8" \
  -f lavfi -i "anoisesrc=color=white:r=${SR}:d=0.02:a=0.5" -filter_complex \
  "[0:a]volume='exp(-t*3.6)':eval=frame[a];[1:a]volume='exp(-t*5.4)*0.42':eval=frame[b];\
[2:a]volume='exp(-t*7.0)*0.26':eval=frame[c];[3:a]volume='exp(-t*9.5)*0.14':eval=frame[d];\
[4:a]highpass=f=3000,volume='exp(-t*140)*0.35':eval=frame[e];\
[a][b][c][d][e]amix=inputs=5:normalize=0,aformat=sample_fmts=fltp,\
afade=t=in:st=0:d=0.002,afade=t=out:st=0.55:d=0.25,atrim=0:0.8[o]" \
  -map "[o]" -c:a pcm_f32le "$W/ding_raw.wav"

# 4) hit：低频冲击——55Hz 下滑到 38Hz 的指数衰减正弦（相位用 aeval 积分算，避免瞬时跳变），
#    再叠 120Hz 击体；0.25s，起点 4ms 起音防爆音。
#    φ(t)=2π·f0·T/k·(1−e^(−k t/T))，f0=55, f1=38, T=0.25 → 2π·37.1876·(1−e^(−1.47902 t))
ffmpeg -v error -y -f lavfi -i "sine=frequency=55:r=${SR}:d=0.25" \
  -f lavfi -i "sine=frequency=120:r=${SR}:d=0.25" -filter_complex \
  "[0:a]aeval=exprs=0.9*exp(-11*t)*sin(2*PI*37.1876*(1-exp(-1.47902*t))):c=mono[sw];\
[1:a]volume='exp(-t*26)*0.30':eval=frame[b];\
[sw][b]amix=inputs=2:normalize=0,lowpass=f=240,aformat=sample_fmts=fltp,\
volume='min(1,t/0.004)':eval=frame,atrim=0:0.25[o]" \
  -map "[o]" -c:a pcm_f32le "$W/hit_raw.wav"

# 统一落到真峰值 < -3 dBTP（各自留余量）
finish "$W/whoosh_raw.wav" "$SFX/whoosh.wav" -4.0
finish "$W/tap_raw.wav"    "$SFX/tap.wav"    -5.0
finish "$W/ding_raw.wav"   "$SFX/ding.wav"   -4.0
finish "$W/hit_raw.wav"    "$SFX/hit.wav"    -3.2

# 硬校验：任何一个真峰值 >= -3 dBTP 就报错退出
fail=0
for f in "$SFX"/*.wav; do
  tp=$(tpeak "$f")
  awk -v p="$tp" -v n="$(basename "$f")" -v lim="$TP_MAX" \
    'BEGIN{ if (p+0 >= lim+0) { printf "  ✗ %s 真峰值 %s dBTP 不够低\n", n, p; exit 1 } }' || fail=1
done
if [[ $fail == 0 ]]; then echo "全部音效真峰值 < ${TP_MAX} dBTP"; else echo "有音效真峰值超标"; fi
exit $fail
