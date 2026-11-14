<script setup>
import { computed, defineAsyncComponent, nextTick, onMounted, ref, watch } from 'vue'
import { apiRequest } from '../utils/api.js'
import { reviewLabel } from '../utils/community.js'
import { gardenPoints } from '../data/garden-points.js'
import { getMethod } from '../data/methods.js'
const GardenMap = defineAsyncComponent(() => import('./GardenMap.vue'))

const props = defineProps({ works: { type: Array, default: () => [] }, user: Object, token: String })
const emit = defineEmits(['navigate', 'edit', 'session-expired'])

const cloudWorks = ref([])
const cloudLoading = ref(false)
const cloudError = ref('')
const previewWork = ref(null)
const previewSrc = ref('')
const previewDialog = ref(null)

const pointName = id => (gardenPoints.find(item => item.id === id) || {}).name || ''
const methodName = id => getMethod(id).name
const localWorks = computed(() => (Array.isArray(props.works) ? props.works : []).filter(work => work && work.id))
const pointIds = new Set(gardenPoints.map(point => point.id))
const pointCounts = computed(() => {
  const counts = {}
  for (const work of allWorks.value) if (work && pointIds.has(work.pointId)) counts[work.pointId] = (counts[work.pointId] || 0) + 1
  return counts
})
const pointRows = computed(() => gardenPoints.filter(point => pointCounts.value[point.id]).map(point => ({ ...point, count: pointCounts.value[point.id] })))
const allWorks = computed(() => {
  const seen = new Set()
  const rows = []
  for (const work of [...cloudWorks.value, ...localWorks.value]) {
    if (!work || !work.id || seen.has(work.id)) continue
    seen.add(work.id)
    rows.push(work)
  }
  return rows
})

async function loadCloud() {
  cloudWorks.value = []
  cloudError.value = ''
  if (!props.token) return
  cloudLoading.value = true
  try {
    const data = await apiRequest('/profile/works', { token: props.token })
    cloudWorks.value = (Array.isArray(data) ? data : []).filter(work => work && work.id)
  } catch (error) {
    cloudError.value = error?.status === 401 ? '登录状态已过期，先展示本机作品。' : '账号作品暂时打不开，先展示本机作品。'
    if (error?.status === 401) emit('session-expired')
  } finally {
    cloudLoading.value = false
  }
}

watch(() => props.token, loadCloud, { immediate: true })

async function openPreview(work) {
  let src = work.imageDataUrl || ''
  if (!src && work.hasImage && props.token) {
    try {
      const full = await apiRequest(`/profile/works/${encodeURIComponent(work.id)}`, { token: props.token })
      src = full?.imageDataUrl || ''
    } catch (error) {}
  }
  if (!src) return
  previewWork.value = work
  previewSrc.value = src
  await nextTick()
  previewDialog.value?.showModal()
}
function closePreview() { previewDialog.value?.close() }
function edit(work) { emit('edit', work) }
</script>

<template>
  <section class="page works-book-page">
    <header class="works-book-head">
      <div>
        <span class="eyebrow">MY COLLECTION</span>
        <h1>作品集</h1>
        <p>所有作品都收在这里。图片按书页排开，点击查看大图。</p>
      </div>
      <div class="works-book-actions">
        <button class="secondary-button" type="button" @click="emit('navigate', 'mine')">返回我的</button>
        <button class="primary-button" type="button" @click="emit('navigate', 'studio')">去创作 ↗</button>
      </div>
    </header>

    <p v-if="cloudError" class="book-notice" role="status">{{ cloudError }} <button class="text-link" type="button" @click="loadCloud">重新加载</button></p>
    <p v-else-if="cloudLoading" class="book-notice" role="status">正在打开账号里的作品…</p>

    <div v-if="allWorks.length" class="works-grid" :data-count="allWorks.length">
      <article v-for="work in allWorks" :key="work.id" class="work-card work-card--page">
        <button class="work-cover" type="button" :aria-label="`查看《${work.title}》大图`" @click="openPreview(work)">
          <img v-if="work.thumbDataUrl || work.imageDataUrl" :src="work.thumbDataUrl || work.imageDataUrl" :alt="work.title" loading="lazy" decoding="async">
          <span v-else class="work-cover-empty">图片准备中</span>
          <span class="work-cover-mask">查看大图 ↗</span>
        </button>
        <div class="work-page-copy">
          <span class="book-meta">{{ methodName(work.methodId) }}<template v-if="pointName(work.pointId)"> · {{ pointName(work.pointId) }}</template></span>
          <h3>{{ work.title || '未命名取景' }}</h3>
          <p>{{ work.note || '一幅来自你的观察。' }}</p>
          <span v-if="reviewLabel(work.reviewStatus)" class="book-badge">{{ reviewLabel(work.reviewStatus) }}</span>
          <div class="book-work-actions">
            <button class="text-link" type="button" @click="openPreview(work)">查看大图</button>
            <button class="text-link" type="button" @click="edit(work)">继续编辑</button>
          </div>
        </div>
      </article>
    </div>

    <section v-if="pointRows.length" class="works-map" aria-labelledby="works-map-title">
      <div class="works-map-head"><div><span class="eyebrow">ON THE MAP</span><h2 id="works-map-title">作品地图</h2><p>按创作时标注的园内点位，看看自己的观察落在园里的哪一处。</p></div></div>
      <GardenMap :point-counts="pointCounts" label="我的作品点位" />
      <ul class="works-map-legend"><li v-for="point in pointRows" :key="point.id"><span>{{ point.name }}</span><strong>{{ point.count }} 幅</strong></li></ul>
    </section>

    <div v-else class="book-empty">
      <p>还没有作品。去创作页拍一张照片，给它加上一扇取景窗。</p>
      <button class="primary-button" type="button" @click="emit('navigate', 'studio')">去创作 ↗</button>
    </div>

    <dialog ref="previewDialog" class="book-preview" aria-label="作品大图" @click="$event.target === previewDialog && closePreview()">
      <template v-if="previewWork">
        <div class="book-preview-head"><h2>{{ previewWork.title }}</h2><button class="secondary-button" type="button" autofocus @click="closePreview">关闭</button></div>
        <img :src="previewSrc" :alt="previewWork.title">
        <p>{{ previewWork.note }}</p>
      </template>
    </dialog>
  </section>
</template>

<style scoped>
.works-book-page { padding-top: 28px; }
.works-book-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 24px; margin-bottom: 34px; }
.works-book-head h1 { margin: 8px 0 10px; font-size: clamp(38px, 5vw, 64px); font-weight: 400; }
.works-book-head p { margin: 0; max-width: 420px; color: var(--ink-soft); line-height: 1.8; }
.works-book-actions { display: flex; gap: 10px; flex: 0 0 auto; }
.book-notice { margin: 0 0 16px; color: var(--ink-soft); font-size: 13px; }

/* 一行最多 4 个；窄屏自动降列 */
.works-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 18px; }
.work-card--page { display: flex; flex-direction: column; min-width: 0; border: 1px solid var(--line); background: #f7f2e7; }
.work-cover { position: relative; display: block; width: 100%; aspect-ratio: 4 / 3; border: 0; padding: 0; overflow: hidden; background: #e7ddcb; cursor: pointer; }
.work-cover img { display: block; width: 100%; height: 100%; object-fit: cover; transition: transform .25s ease; }
.work-cover:hover img { transform: scale(1.03); }
.work-cover-empty { display: flex; width: 100%; height: 100%; align-items: center; justify-content: center; color: var(--ink-soft); font-size: 12px; }
.work-cover-mask { position: absolute; right: 8px; bottom: 8px; padding: 4px 8px; border-radius: 999px; background: rgba(20,33,43,.78); color: #fff; font: 11px system-ui, sans-serif; opacity: 0; transition: opacity .2s ease; }
.work-cover:hover .work-cover-mask { opacity: 1; }
.work-page-copy { padding: 14px 16px 16px; }
.book-meta { color: var(--clay); font: 600 10px system-ui, sans-serif; letter-spacing: .08em; }
.work-page-copy h3 { margin: 7px 0 5px; font-size: 19px; font-weight: 500; line-height: 1.3; }
.work-page-copy p { margin: 0; color: var(--ink-soft); font-size: 12px; line-height: 1.6; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.book-badge { display: inline-block; margin-top: 7px; padding: 2px 7px; border-radius: 999px; background: rgba(23,58,54,.08); font-size: 10px; }
.book-work-actions { display: flex; gap: 12px; margin-top: 10px; }
.works-map { margin-top: 44px; padding-top: 30px; border-top: 1px solid var(--line); }
.works-map-head h2 { margin: 8px 0; font-size: 30px; font-weight: 400; }
.works-map-head p { margin: 0 0 18px; color: var(--ink-soft); max-width: 520px; }
.works-map-legend { display: flex; flex-wrap: wrap; gap: 10px 18px; margin: 14px 0 0; padding: 0; list-style: none; color: var(--ink-soft); font-size: 13px; }
.works-map-legend strong { margin-left: 6px; color: var(--clay); }
.book-empty { padding: 60px 0; text-align: center; color: var(--ink-soft); }
.book-preview { width: min(1000px, calc(100vw - 32px)); max-height: 92dvh; border: 0; padding: 22px; background: var(--paper); color: var(--ink); }
.book-preview::backdrop { background: rgba(23,58,54,.55); }
.book-preview-head { display: flex; align-items: center; justify-content: space-between; gap: 20px; margin-bottom: 14px; }
.book-preview-head h2 { margin: 0; font-size: 22px; }
.book-preview img { display: block; width: 100%; max-height: 68dvh; object-fit: contain; background: #e7ddcb; }
.book-preview p { margin: 12px 0 0; color: var(--ink-soft); }
@media (max-width: 1100px) { .works-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 820px) { .works-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 760px) {
  .works-book-head { flex-direction: column; align-items: flex-start; }
  .works-book-actions { width: 100%; }
  .works-book-actions .primary-button, .works-book-actions .secondary-button { flex: 1; }
}
@media (max-width: 520px) { .works-grid { grid-template-columns: 1fr; } }
</style>
