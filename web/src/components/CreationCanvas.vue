<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { downloadCanvas, fitImage } from '../utils/image-export.js'
import { canUseStorage, getSourceImage, writeWork } from '../utils/local-work.js'
import { assetUrl } from '../utils/assets.js'
import { createLatestImageRequest } from '../utils/image-loader.js'
const props = defineProps({ initial: Object })
const emit = defineEmits(['saved'])
const canvas = ref(null), sourceImageDataUrl = ref(''), frame = ref('round'), keepCanvasBorder = ref(true), title = ref('我的园林取景'), method = ref('frame'), note = ref(''), scale = ref(1), offset = ref({ x: 0, y: 0 }), dragging = ref(false), pointer = ref({ x: 0, y: 0 }), image = ref(null), frameImage = ref(null), errorMessage = ref('')
const frameLoading = ref(false), photoLoading = ref(false), frameError = ref(''), photoError = ref('')
const imageBusy = computed(() => frameLoading.value || photoLoading.value)
const imageUnavailable = computed(() => imageBusy.value || !image.value || Boolean(frameError.value) || Boolean(photoError.value))
const frameRequest = createLatestImageRequest(), photoRequest = createLatestImageRequest()
let fileReader = null, fileSequence = 0
const frames = [{ id: 'round', label: '月洞花窗', detail: '圆融 · 聚焦', shape: 'circle', asset: '/assets/frames/frame-4.png' }, { id: 'square', label: '几何漏窗', detail: '疏朗 · 通透', shape: 'square', asset: '/assets/frames/frame-1.png' }, { id: 'fan', label: '六角景窗', detail: '端庄 · 收束', shape: 'fan', asset: '/assets/frames/frame-3.png' }, { id: 'moon', label: '海棠套窗', detail: '含蓄 · 回环', shape: 'moon', asset: '/assets/frames/frame-5.png' }, { id: 'open', label: '宫灯窗', detail: '轻盈 · 借景', shape: 'open', asset: '/assets/frames/frame-2.png' }]
const methods = [{ id: 'frame', label: '框景' }, { id: 'borrow', label: '借景' }, { id: 'opposition', label: '对景' }, { id: 'leak', label: '漏景' }, { id: 'screen', label: '障景' }]
function draw() {
  const c = canvas.value
  if (!c) return
  const ctx = c.getContext('2d')
  const border = keepCanvasBorder.value ? 52 : 0
  const frameInsetX = 66
  const frameInsetY = 37
  const innerWidth = c.width - border * 2
  const innerHeight = c.height - border * 2
  ctx.clearRect(0, 0, c.width, c.height)
  ctx.fillStyle = keepCanvasBorder.value ? '#fffdf8' : '#e7dfce'
  ctx.fillRect(0, 0, c.width, c.height)
  if (image.value) {
    const fit = fitImage(image.value, innerWidth, innerHeight)
    const w = fit.width * scale.value
    const h = fit.height * scale.value
    ctx.save()
    ctx.beginPath()
    ctx.rect(border, border, innerWidth, innerHeight)
    ctx.clip()
    ctx.drawImage(image.value, (c.width - w) / 2 + offset.value.x, (c.height - h) / 2 + offset.value.y, w, h)
    ctx.restore()
  }
  if (frameImage.value) {
    const x = frameInsetX
    const y = frameInsetY
    const w = c.width - frameInsetX * 2
    const h = c.height - frameInsetY * 2
    ctx.save()
    ctx.globalAlpha = .2
    ctx.filter = 'blur(10px)'
    ctx.drawImage(frameImage.value, x, y + 8, w, h)
    ctx.restore()
    ctx.save()
    ctx.globalAlpha = .96
    ctx.globalCompositeOperation = 'multiply'
    ctx.drawImage(frameImage.value, x, y, w, h)
    ctx.restore()
    const edge = ctx.createLinearGradient(0, 0, 0, c.height)
    edge.addColorStop(0, 'rgba(38,29,22,.16)')
    edge.addColorStop(.12, 'rgba(38,29,22,0)')
    edge.addColorStop(.86, 'rgba(38,29,22,0)')
    edge.addColorStop(1, 'rgba(38,29,22,.12)')
    ctx.fillStyle = edge
    ctx.fillRect(x, y, w, h)
  }
  if (keepCanvasBorder.value) {
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, c.width, border)
    ctx.fillRect(0, c.height - border, c.width, border)
    ctx.fillRect(0, border, border, c.height - border * 2)
    ctx.fillRect(c.width - border, border, border, c.height - border * 2)
  }
}
async function loadFrame() {
  const selected = frames.find(item => item.id === frame.value)
  if (!selected) return
  frameLoading.value = true; frameError.value = ''
  try {
    const loaded = await frameRequest.load(assetUrl(selected.asset), { cached: true })
    if (!loaded) return
    frameImage.value = loaded; frameLoading.value = false; draw()
  } catch { frameLoading.value = false; frameError.value = '窗框加载失败，请重新加载后再保存' }
}
async function loadPhoto(src, reset = false) {
  photoLoading.value = true; photoError.value = ''
  try {
    const loaded = await photoRequest.load(src)
    if (!loaded) return
    sourceImageDataUrl.value = src; image.value = loaded
    if (reset) { scale.value = 1; offset.value = { x: 0, y: 0 } }
    photoLoading.value = false; draw()
  } catch { photoLoading.value = false; photoError.value = '照片无法解码或加载，请重新选择 JPG、PNG 或 WebP 图片' }
}
function onFile(e) {
  const file = e.target.files?.[0]
  if (!file) return
  errorMessage.value = ''
  if (!file.type.startsWith('image/')) { errorMessage.value = '请选择图片文件'; return }
  if (file.size > 12 * 1024 * 1024) { errorMessage.value = '图片请控制在 12MB 以内'; return }
  const request = ++fileSequence
  fileReader?.abort()
  photoRequest.cancel()
  photoLoading.value = true; photoError.value = ''
  const reader = new FileReader()
  fileReader = reader
  reader.onerror = () => { if (request !== fileSequence) return; photoLoading.value = false; photoError.value = '图片读取失败，请重新选择' }
  reader.onload = () => {
    if (request !== fileSequence) return
    loadPhoto(reader.result, true)
  }
  reader.readAsDataURL(file)
  e.target.value = ''
}
function down(e) { dragging.value = true; pointer.value = { x: e.clientX, y: e.clientY }; e.currentTarget.setPointerCapture?.(e.pointerId) }
function move(e) { if (!dragging.value) return; const rect = canvas.value.getBoundingClientRect(); const ratio = canvas.value.width / rect.width; offset.value.x += (e.clientX - pointer.value.x) * ratio; offset.value.y += (e.clientY - pointer.value.y) * ratio; pointer.value = { x:e.clientX, y:e.clientY }; draw() }
function up(e) { dragging.value = false; if (e?.currentTarget?.hasPointerCapture?.(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId) }
function save() {
  if (imageBusy.value) { errorMessage.value = '图片仍在加载，请稍候再保存'; return }
  if (frameError.value || photoError.value) return
  if (!image.value) { errorMessage.value = '先选择一张图片'; return }
  const id = props.initial?.id || globalThis.crypto?.randomUUID?.() || `work-${Date.now()}-${Math.random().toString(16).slice(2)}`
  const work = { id, title: title.value || '未命名取景', methodId: method.value, note: note.value, sourceImageDataUrl: sourceImageDataUrl.value || props.initial?.sourceImageDataUrl || props.initial?.imageDataUrl, imageDataUrl: canvas.value.toDataURL('image/png'), frameId: frame.value, keepCanvasBorder: keepCanvasBorder.value, scale: scale.value, offset: offset.value, createdAt: props.initial?.createdAt || Date.now() }
  if (!canUseStorage()) { errorMessage.value = '浏览器本地存储不可用，请检查隐私设置或删除旧作品后重试'; return }
  try { writeWork(work); errorMessage.value = ''; emit('saved', work) } catch { errorMessage.value = '作品保存失败，可能是浏览器存储空间不足。请换一张较小的图片或删除旧作品后重试' }
}
function exportImage() { if (imageUnavailable.value) { errorMessage.value = '请等待图片加载完成后再导出'; return }; downloadCanvas(canvas.value, `${title.value || '我的园林取景'}.png`) }
watch(frame, loadFrame)
watch([keepCanvasBorder, scale], draw)
onMounted(() => {
  if (props.initial) {
    title.value = props.initial.title; method.value = props.initial.methodId; frame.value = props.initial.frameId || frame.value; keepCanvasBorder.value = props.initial.keepCanvasBorder ?? true; scale.value = props.initial.scale || 1; offset.value = props.initial.offset || { x: 0, y: 0 }; note.value = props.initial.note || ''
    sourceImageDataUrl.value = getSourceImage(props.initial)
    if (sourceImageDataUrl.value) loadPhoto(sourceImageDataUrl.value)
    else photoError.value = '作品原图不存在，请重新选择照片'
  }
  loadFrame(); draw()
})
onBeforeUnmount(() => { fileSequence += 1; fileReader?.abort(); frameRequest.cancel(); photoRequest.cancel() })
</script>
<template>
  <div class="studio-shell">
    <div class="studio-intro"><div><span class="eyebrow">THE WINDOW IS THE COMPOSITION</span><h2>先选一扇窗，<br><em>再让景色出现。</em></h2></div><p>五种窗格对应五种观看的姿态。拖动照片，让远处的树影、水面或屋檐落进窗心。</p></div>
    <div class="studio-grid">
      <div class="canvas-wrap" :aria-busy="imageBusy"><canvas ref="canvas" width="1200" height="675" @pointerdown="down" @pointermove="move" @pointerup="up" @pointerleave="up"></canvas><div class="canvas-meta"><span>取景台 · {{ frames.find(item => item.id === frame)?.label }}</span><span>{{ imageBusy ? '图片加载中…' : '拖动画面' }} · {{ Math.round(scale * 100) }}%</span></div></div>
      <div class="studio-controls">
        <label class="upload-button"><input type="file" accept="image/*" @change="onFile"><span class="upload-icon">＋</span><span>放入一张园中照片</span><small>JPG / PNG · 最大 12MB</small></label>
        <p v-if="errorMessage" class="studio-error" role="alert">{{ errorMessage }}</p>
        <p v-if="photoError" class="studio-error" role="alert">{{ photoError }}</p>
        <p v-if="frameError" class="studio-error" role="alert">{{ frameError }} <button type="button" class="text-link" @click="loadFrame">重新加载</button></p>
        <div class="control-group"><div class="control-heading"><span class="control-label">窗框样本</span><span class="control-count">{{ frames.findIndex(item => item.id === frame) + 1 }} / 5</span></div><div class="frame-grid"><button v-for="item in frames" :key="item.id" type="button" :class="{ selected: frame === item.id }" @click="frame = item.id"><span class="frame-thumb"><img :src="assetUrl(item.asset)" :alt="item.label" decoding="async"></span><strong>{{ item.label }}</strong><small>{{ item.detail }}</small></button></div></div>
        <div class="range-block"><label class="range-label"><span>画面尺度</span><output>{{ Math.round(scale * 100) }}%</output><input v-model.number="scale" type="range" min="0.7" max="2" step="0.05"></label><label class="check-label"><input v-model="keepCanvasBorder" type="checkbox"><span>保留白色画布边框</span></label></div>
        <div class="field-pair"><label>作品标题<input v-model="title" placeholder="给这幅景取个名字"></label><label>造景手法<select v-model="method"><option v-for="item in methods" :key="item.id" :value="item.id">{{ item.label }}</option></select></label></div>
        <label>一句话记录<textarea v-model="note" rows="3" placeholder="我在哪里发现了这幅景？"></textarea></label>
        <div class="studio-actions"><button type="button" class="primary-button" :disabled="imageUnavailable" @click="save">保存作品</button><button type="button" class="secondary-button" :disabled="imageUnavailable" @click="exportImage">导出 PNG</button></div>
      </div>
    </div>
  </div>
</template>

<style>
.studio-page { max-width: 1440px; padding-top: 54px; }
.studio-shell { display:grid; gap:28px; }
.studio-intro { display:grid; grid-template-columns:1fr 340px; gap:40px; align-items:end; padding:0 4px 18px; border-bottom:1px solid rgba(23,58,54,.12); }
.studio-intro h2 { margin:10px 0 0; font-size:clamp(36px,5vw,66px); }
.studio-intro p { margin:0 0 4px; font-size:15px; max-width:310px; }
.studio-grid { grid-template-columns:minmax(0,1.45fr) minmax(320px,.55fr); gap:0; background:#e8deca; box-shadow:0 22px 60px rgba(55,45,30,.12); border:1px solid rgba(73,53,35,.12); }
.canvas-wrap { background:#d8cdb9; min-width:0; }
.canvas-wrap canvas { width:100%; height:auto; display:block; }
.canvas-meta { display:flex; justify-content:space-between; gap:12px; padding:10px 14px; color:#655d4f; font:11px/1.4 system-ui,sans-serif; letter-spacing:.04em; }
.studio-controls { padding:28px; gap:18px; background:#f0e7d6; border-left:1px solid rgba(73,53,35,.12); }
.upload-button { display:flex !important; align-items:center; gap:10px; text-align:left !important; padding:15px 16px !important; color:#f7f0e4 !important; background:#234943 !important; }
.upload-button .upload-icon { flex:0 0 28px; display:inline-flex; align-items:center; justify-content:center; height:24px; font-size:24px; line-height:24px; font-weight:300; transform:translateY(1px); }
.upload-button > span:not(.upload-icon) { white-space:nowrap; }
.upload-button > span:not(.upload-icon) { line-height:24px; }
.upload-button small { color:rgba(247,240,228,.65); font:10px system-ui,sans-serif; white-space:nowrap; }
.control-heading { display:flex; justify-content:space-between; align-items:center; }
.control-count { color:#9c4d35; font:11px system-ui,sans-serif; }
.frame-grid { grid-template-columns:repeat(3,1fr); gap:8px; }
.frame-grid button { min-height:92px; padding:6px 3px; gap:3px; border:1px solid rgba(73,53,35,.16); background:#f8f1e4; color:#5d5549; transition:transform .15s ease, background .15s ease, border-color .15s ease; }
.frame-grid button:hover { transform:translateY(-2px); background:#f1e5d1; border-color:rgba(156,77,53,.45); }
.frame-grid button.selected { border-color:#9c4d35; background:#eadbc5; box-shadow:inset 0 0 0 1px rgba(156,77,53,.24); color:#7d3e2d; }
.frame-thumb { display:grid; place-items:center; width:100%; height:48px; overflow:hidden; }
.frame-thumb img { width:100%; height:100%; object-fit:cover; }
.frame-grid strong { font-size:10px; font-weight:600; white-space:nowrap; }
.frame-grid small { font-size:9px; color:#847a6a; white-space:nowrap; }
.range-label { grid-template-columns:1fr auto !important; align-items:center; }
.range-label output { color:#9c4d35; font:12px system-ui,sans-serif; font-variant-numeric:tabular-nums; }
.range-label input { grid-column:1/-1; accent-color:#9c4d35; }
.range-block { display:grid; gap:12px; }
.check-label { display:flex !important; grid-template-columns:none !important; align-items:center; gap:9px !important; color:#665c4e; font-size:12px !important; }
.check-label input { width:16px; height:16px; margin:0; accent-color:#9c4d35; }
.field-pair { display:grid; grid-template-columns:1fr; gap:14px; align-items:start; }
.field-pair > label { align-content:start; }
.studio-controls label { color:#665c4e; }
.studio-actions { margin-top:4px; justify-content:flex-start; align-items:center; }
.studio-actions .primary-button { min-width:132px; }
.studio-actions .secondary-button { min-width:118px; }
.studio-actions button:disabled { opacity:.5; cursor:wait; }
.studio-error { margin: -8px 0 0; color: #9b4d3d; font: 12px/1.5 system-ui,sans-serif; }
@media (max-width:900px) { .studio-page { padding-top:38px; } .studio-intro { grid-template-columns:1fr; gap:8px; } .studio-grid { grid-template-columns:1fr; } .studio-controls { border-left:0; border-top:1px solid rgba(73,53,35,.12); } }
@media (max-width:560px) { .frame-grid { grid-template-columns:repeat(3,1fr); } .field-pair { grid-template-columns:1fr; } .studio-controls { padding:18px; } }
</style>
