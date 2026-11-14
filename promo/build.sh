#!/bin/zsh
# 拙政观景宣传片一键出片：检查素材 → 音轨 → 并行渲染画面 → 拼接 → 合音频 + 封面
# 前置：python3 promo/tts.py --tempo 1.2 已生成旁白；node promo/capture/record.cjs 已录屏
set -euo pipefail
cd "${0:A:h}/.."
V=output/promo-video
for key in $(cut -d'|' -f1 promo/lines.txt); do
  [[ -s $V/tts/$key.wav ]] || { echo "缺少旁白 $V/tts/$key.wav"; exit 1; }
done
for c in $(python3 -c "import json;print(' '.join(s['clip'] for s in json.load(open('promo/timeline.json'))['shots'] if s['clip'].startswith('capture/')))"); do
  [[ -s $V/$c ]] || { echo "缺少录屏 $V/$c"; exit 1; }
done
bash promo/audio.sh
N=${PARTS:-4}
for i in $(seq 0 $(( N - 1 ))); do python3 promo/compose.py --part=$i/$N > $V/part_$i.log 2>&1 & done
wait
: > $V/parts.txt
for i in $(seq 0 $(( N - 1 ))); do
  [[ -s $V/part_${i}of${N}.mp4 ]] || { echo "分段 $i 渲染失败，见 $V/part_$i.log"; exit 1; }
  echo "file 'part_${i}of${N}.mp4'" >> $V/parts.txt
done
ffmpeg -v error -y -f concat -safe 0 -i $V/parts.txt -c copy $V/picture.mp4
python3 promo/cover.py >/dev/null
VER=${VER:-v2}
OUT=$V/zhuozheng-promo-${VER}-30s.mp4
# 封面以 attached_pic 写进 mp4，播放器和部分平台用它做缩略图
ffmpeg -v error -y -i $V/picture.mp4 -i $V/audio.m4a -i $V/cover/cover-9x16.png -map 0:v -map 1:a -map 2 -c copy -c:v:1 png \
  -disposition:v:1 attached_pic -t 30 -movflags +faststart $OUT
rm -f $V/part_*of*.mp4 $V/part_*.log $V/parts.txt
echo $OUT
