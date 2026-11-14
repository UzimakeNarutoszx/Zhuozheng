<script setup>
import { computed, defineAsyncComponent, nextTick, onMounted, ref, watch } from 'vue'
import QuestionRecords from './QuestionRecords.vue'
import LocalGallery from './LocalGallery.vue'
import ImageMotion from './ImageMotion.vue'
const GardenMap = defineAsyncComponent(() => import('./GardenMap.vue'))
import { prepareCloudWork } from '../utils/cloud-work.js'
import { sources } from '../data/sources.js'
import { gardenPoints } from '../data/garden-points.js'
import { apiRequest } from '../utils/api.js'
import { community, reviewLabel } from '../utils/community.js'
import ReviewQueue from './ReviewQueue.vue'
import FavoriteWorks from './FavoriteWorks.vue'
import { preloadCharacter } from './RoundWindow3D.vue'
const props = defineProps({ works: Array, user: Object, token: String, tab: { type: String, default: 'works' }, authLoading: Boolean, saveNotice: String })
const emit = defineEmits(['navigate', 'tab', 'edit', 'changed', 'logout', 'session-expired'])
const cloudWorks = ref([]), cloudLoading = ref(false), cloudError = ref(''), cloudMessage = ref(''), importing = ref(false), importPreview = ref(false), previewWork = ref(null), deleting = ref(null)
const previewDialog = ref(null)
async function ensureFullWork(work) {
  if (!work || work.imageDataUrl) return work
  try {
    const full = await apiRequest(`/profile/works/${encodeURIComponent(work.id)}`, { token: props.token })
    if (full && full.imageDataUrl) work.imageDataUrl = full.imageDataUrl
  } catch (error) {}
  return work
}
async function openPreview(work) { await ensureFullWork(work); previewWork.value = work; await nextTick(); previewDialog.value?.showModal() }
/* PURE_HELPERS_START：不依赖 Vue / DOM 的纯函数，tests/mypage.test.mjs 直接抽取求值测试 */
// “我的作品”要能扛住脏数据：localStorage 损坏、云端返回 null / undefined、
// 旧作品缺 id、pointId 不在白名单、甚至超大数组，都不能让整页渲染失败。
function isWorkRecord(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}
function normalizeWorkId(value) {
  if (typeof value === 'string' && value) return value
  if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  return ''
}
function sanitizeWorkList(value) {
  if (!Array.isArray(value)) return []
  return value.filter(isWorkRecord)
}
// 同一作品在本机与云端各有一份：按 id 只记一次，合法点位标注优先；
// 没有 id 的脏数据也单独计入点位，而不是抛异常或整块消失。
function collectWorkPointCounts({ works, cloudWorks, validPointIds } = {}) {
  const validIds = validPointIds instanceof Set ? validPointIds : new Set(Array.isArray(validPointIds) ? validPointIds : [])
  const idToPoint = new Map()
  const anonymousPoints = []
  const add = value => {
    for (const work of sanitizeWorkList(value)) {
      const id = normalizeWorkId(work.id)
      const pointId = validIds.has(work.pointId) ? work.pointId : ''
      if (!id) { if (pointId) anonymousPoints.push(pointId); continue }
      if (pointId || !idToPoint.has(id)) idToPoint.set(id, pointId)
    }
  }
  add(works)
  add(cloudWorks)
  const counts = new Map()
  for (const pointId of [...idToPoint.values(), ...anonymousPoints]) {
    if (pointId) counts.set(pointId, (counts.get(pointId) || 0) + 1)
  }
  return counts
}
function pointTotal(counts) {
  if (!(counts instanceof Map)) return 0
  let total = 0
  for (const value of counts.values()) if (Number.isFinite(value)) total += value
  return total
}
function pointRowsWithCounts(points, counts) {
  if (!Array.isArray(points) || !(counts instanceof Map)) return []
  return points.filter(point => isWorkRecord(point) && counts.has(point.id)).map(point => ({ ...point, count: counts.get(point.id) }))
}
function pointCountObject(counts) {
  if (!(counts instanceof Map)) return {}
  const result = {}
  for (const [pointId, count] of counts) if (typeof pointId === 'string' && pointId) result[pointId] = count
  return result
}
function dedupeLocalWorks(works, cloudWorks) {
  const cloudIds = new Set()
  for (const work of sanitizeWorkList(cloudWorks)) {
    const id = normalizeWorkId(work.id)
    if (id) cloudIds.add(id)
  }
  return sanitizeWorkList(works).filter(work => {
    const id = normalizeWorkId(work.id)
    return !id || !cloudIds.has(id)
  })
}
/* PURE_HELPERS_END */

const safeWorks = computed(() => sanitizeWorkList(props.works))
const worksCount = computed(() => safeWorks.value.length)
// 登录后“我的作品”标签显示账号里的总数；未登录才显示本机数量。
const tabWorkCount = computed(() => props.user ? (cloudLoading.value ? worksCount.value : cloudWorks.value.length) : worksCount.value)
const newLocalWorks = computed(() => dedupeLocalWorks(props.works, cloudWorks.value))
const pointIds = new Set(gardenPoints.map(point => point.id))
const ownPointCounts = computed(() => {
  try { return collectWorkPointCounts({ works: props.works, cloudWorks: cloudWorks.value, validPointIds: pointIds }) } catch { return new Map() }
})
const mappedPointRows = computed(() => {
  try { return pointRowsWithCounts(gardenPoints, ownPointCounts.value) } catch { return [] }
})
const mappedWorkCount = computed(() => pointTotal(ownPointCounts.value))
const pointCountMap = computed(() => pointCountObject(ownPointCounts.value))
const cloudState = computed(() => cloudLoading.value ? 'loading' : cloudError.value ? 'error' : cloudWorks.value.length ? 'ready' : 'empty')
let requestVersion = 0
// 云端作品加载失败只作为“提示”显示；本机作品列表始终独立渲染，不因这里报错而消失。
function describeCloudError(error) {
  if (error?.status === 401) return '登录状态已过期，账号作品暂时打不开。本机作品仍在这个浏览器里，重新登录后可以继续同步。'
  if (error?.status === 403) return '账号作品暂时没有访问权限。本机作品不受影响。'
  return `账号作品暂时打不开：${error?.message || '请检查网络后重试。'} 本机作品仍可正常查看。`
}
function handleError(error) {
  cloudError.value = describeCloudError(error)
  if (error?.status === 401) emit('session-expired')
}
async function loadCloud() {
  const version = ++requestVersion
  previewDialog.value?.close()
  cloudWorks.value = []; cloudError.value = ''; cloudMessage.value = ''; importPreview.value = false; previewWork.value = null
  if (!props.token) { cloudLoading.value = false; return }
  cloudLoading.value = true
  try {
    const data = await apiRequest('/profile/works', { token: props.token })
    if (version === requestVersion) {
      cloudWorks.value = sanitizeWorkList(data)
    }
  } catch (error) {
    if (version === requestVersion) handleError(error)
  } finally {
    // 401 / 网络错误 / 组件卸载后重试都必须把 loading 落回 false，避免永久“正在打开”。
    if (version === requestVersion) cloudLoading.value = false
  }
}
async function hydrateCloudImages(version) {
  const queue = cloudWorks.value.filter(work => work && work.hasImage && !work.imageDataUrl)
  let cursor = 0
  const worker = async () => {
    while (cursor < queue.length) {
      if (version !== requestVersion) return
      const work = queue[cursor++]
      try {
        const full = await apiRequest(`/profile/works/${encodeURIComponent(work.id)}`, { token: props.token })
        if (version === requestVersion && full && full.imageDataUrl) work.imageDataUrl = full.imageDataUrl
      } catch (error) {}
    }
  }
  await Promise.all([worker(), worker()])
}

async function importWorks() {
  if (importing.value) return
  importing.value = true; cloudError.value = ''; cloudMessage.value = ''
  const importToken = props.token, version = requestVersion
  try {
    const prepared = []
    for (const work of newLocalWorks.value) prepared.push(await prepareCloudWork(work))
    if (importToken !== props.token) return
    let data, imported = 0
    for (const work of prepared) { data = await apiRequest('/profile/works/import', { token: importToken, body: { works: [work] } }); imported += data.imported; if (importToken !== props.token) return }
    if (version !== requestVersion) return
    cloudWorks.value = data?.works || cloudWorks.value; cloudMessage.value = `已导入 ${imported} 幅作品，本机原件已保留。`; importPreview.value = false
  } catch (error) { if (version === requestVersion) handleError(error) } finally { importing.value = false }
}
async function deleteCloud(work) {
  if (!window.confirm(`确定从账号中删除“${work.title}”吗？本机原件不会删除。`)) return
  deleting.value = work.id; cloudError.value = ''; cloudMessage.value = ''
  const version = requestVersion
  try { await apiRequest(`/profile/works/${encodeURIComponent(work.id)}`, { token: props.token, method: 'DELETE' }); if (version === requestVersion) { cloudWorks.value = cloudWorks.value.filter(item => item.id !== work.id); cloudMessage.value = '账号中的作品已删除。' } } catch (error) { if (version === requestVersion) handleError(error) } finally { deleting.value = null }
}
const publishing = ref(null)
async function togglePublish(work) {
  const going = work.visibility !== 'public' || work.reviewStatus === 'rejected'
  if (going && !window.confirm(`把“${work.title}”提交到园友作品？审核通过后所有人都能看到图片、标题、说明和你的昵称；手机号不会公开。`)) return
  if (!going && !window.confirm(`从园友作品撤回“${work.title}”？撤回后其他人将看不到它。`)) return
  publishing.value = work.id; cloudError.value = ''; cloudMessage.value = ''
  const version = requestVersion
  try {
    const data = going ? await community.publish(work.id, props.token) : await community.unpublish(work.id, props.token)
    if (version !== requestVersion) return
    Object.assign(work, { visibility: going ? 'public' : 'private', reviewStatus: data.status, rejectReason: '', communityId: data.communityId || '' })
    cloudMessage.value = going ? '已提交审核，通过后会出现在园友作品里。' : '已从园友作品撤回。'
  } catch (error) { if (version === requestVersion) handleError(error) } finally { publishing.value = null }
}
// 进入“我的”页就预热钱钱的 3D：先拉 three.js 代码块与 GLB，等用户切到“关于”
// 或导览吉祥物换成钱钱时，RoundWindow3D 直接从缓存接管，不会长时间停在静态图。
// 用空闲回调避开首屏，失败了也只影响动态形象（静态图始终保留）。
onMounted(() => {
  if (typeof window === 'undefined') return
  const warm = () => { preloadCharacter('coin').catch(() => {}) }
  if (typeof window.requestIdleCallback === 'function') window.requestIdleCallback(warm, { timeout: 2500 })
  else setTimeout(warm, 2500)
})
watch(() => props.token, loadCloud, { immediate: true })
</script>

<template>
  <section class="page my-page">
    <header class="my-heading"><div><span class="eyebrow">把观察留在身边</span><h1>我的</h1></div><div class="my-account"><template v-if="user"><strong>{{ user.nickname || user.phone || '园中来客' }}</strong><span>欢迎回来，继续发现一窗一景。</span><button class="text-link" type="button" @click="emit('logout')">退出登录</button></template><template v-else><strong>{{ authLoading ? '正在确认登录状态…' : '一位园中来客' }}</strong><span>登录后，与梅梅一起聊聊园林。</span><button class="text-link" type="button" @click="emit('navigate', 'login')">登录 / 注册</button></template></div></header>
    <div class="my-tabs" role="tablist" aria-label="我的页面内容">
      <button id="my-works-tab" type="button" role="tab" :aria-selected="tab === 'works'" aria-controls="my-works" :class="{ selected: tab === 'works' }" @click="emit('tab', 'works')">我的作品 <span>{{ tabWorkCount }}</span></button>
      <button id="my-favorites-tab" type="button" role="tab" :aria-selected="tab === 'favorites'" aria-controls="my-favorites" :class="{ selected: tab === 'favorites' }" @click="emit('tab', 'favorites')">收藏的作品</button>
      <button id="my-records-tab" type="button" role="tab" :aria-selected="tab === 'records'" aria-controls="my-records" :class="{ selected: tab === 'records' }" @click="emit('tab', 'records')">问答记录</button>
      <button id="my-about-tab" type="button" role="tab" :aria-selected="tab === 'about'" aria-controls="my-about" :class="{ selected: tab === 'about' }" @click="emit('tab', 'about')">关于拙政观景</button>
      <button v-if="user?.role === 'admin' && !authLoading" id="my-review-tab" type="button" role="tab" :aria-selected="tab === 'review'" aria-controls="my-review" :class="{ selected: tab === 'review' }" @click="emit('tab', 'review')">社区审核</button>
    </div>
    <div v-if="tab === 'favorites'" id="my-favorites" role="tabpanel" aria-labelledby="my-favorites-tab"><FavoriteWorks :token="token" @navigate="(...args) => emit('navigate', ...args)" @session-expired="emit('session-expired')" /></div>
    <div v-else-if="tab === 'works'" id="my-works" role="tabpanel" aria-labelledby="my-works-tab">
      <section class="works-map" aria-labelledby="works-map-heading">
        <div class="my-works-heading"><div><h2 id="works-map-heading">作品地图</h2><p>按创作时标注的园内点位，看看自己的观察落在园里的哪一处。</p></div><button class="secondary-button" type="button" @click="emit('navigate', 'studio')">去创作 ↗</button></div>
        <template v-if="mappedPointRows.length">
          <GardenMap :point-counts="pointCountMap" label="我的作品点位" :point-list="false" />
          <p class="works-map-summary" role="status">共 {{ mappedWorkCount }} 幅作品标注在 {{ mappedPointRows.length }} 个点位上。</p>
          <ul class="works-map-legend" aria-label="我的作品点位统计"><li v-for="point in mappedPointRows" :key="point.id"><span>{{ point.name }}</span><strong>{{ point.count }} 幅</strong></li></ul>
        </template>
        <p v-else class="works-map-empty">作品地图还是空的。创作时选择一个园内点位，作品就会标注在这里。</p>
      </section>

      <section v-if="user" class="cloud-archive" :data-cloud-state="cloudState">
        <div class="my-works-heading"><div><h2>账号中的作品</h2><p>保存在你的账号里，换一台设备也能继续创作。</p></div><button class="primary-button" type="button" @click="emit('navigate', 'studio')">新建作品 ↗</button></div>
        <p v-if="cloudLoading" role="status">正在打开你的作品册…</p>
        <div v-if="cloudError" class="cloud-error" role="alert">{{ cloudError }} <button class="text-link" type="button" :disabled="cloudLoading" @click="loadCloud">{{ cloudLoading ? '正在重试…' : '重新加载' }}</button></div>
        <p v-if="cloudMessage" class="cloud-message" role="status">{{ cloudMessage }}</p>
        <div v-if="cloudWorks.length" class="local-gallery">
          <article v-for="work in cloudWorks" :key="work.id" class="work-card cloud-work">
            <button class="cloud-work-preview" type="button" :aria-label="`预览${work.title}`" @click="openPreview(work)">
              <ImageMotion v-if="work.thumbDataUrl || work.imageDataUrl" :src="work.thumbDataUrl || work.imageDataUrl" :alt="work.title" :motion="false" :retryable="false" />
              <span v-else class="cloud-thumb-loading">图片准备中</span>
            </button>
            <div>
              <span v-if="reviewLabel(work.reviewStatus)" :class="['review-badge', `review-badge--${work.reviewStatus}`]">{{ reviewLabel(work.reviewStatus) }}</span>
              <h3>{{ work.title }}</h3>
              <p>{{ work.note || '一幅来自你的观察。' }}</p>
              <div class="work-actions">
                <button class="text-link" type="button" @click="emit('edit', { ...work, cloud: true })">继续编辑</button>
                <button v-if="work.communityId" class="text-link" type="button" @click="emit('navigate', 'community', work.communityId)">查看</button>
                <button class="text-link" type="button" :disabled="publishing === work.id" @click="togglePublish(work)">{{ publishing === work.id ? '处理中…' : work.visibility === 'public' ? '撤回公开' : '发布到社区' }}</button>
                <button class="danger-link" type="button" :disabled="deleting === work.id" @click="deleteCloud(work)">{{ deleting === work.id ? '删除中…' : '删除' }}</button>
              </div>
            </div>
          </article>
        </div>
        <div v-else-if="!cloudLoading && !cloudError" class="cloud-empty"><p>账号里还没有作品。</p></div>
      </section>

      <div class="my-works-heading"><div><h2>本机作品</h2><p>这些原件只保存在当前浏览器里。</p></div><button v-if="!user" class="primary-button" type="button" @click="emit('navigate', 'studio')">新建作品 ↗</button></div>
      <LocalGallery :works="safeWorks" @changed="emit('changed', $event)" @edit="emit('edit', $event)" />
    </div>
    <div v-else-if="tab === 'review' && user?.role === 'admin' && !authLoading" id="my-review" role="tabpanel" aria-labelledby="my-review-tab"><ReviewQueue :token="token" @session-expired="emit('session-expired')" /></div>
    <div v-else-if="tab === 'review'" role="status">{{ authLoading ? '正在确认管理员身份…' : '请使用管理员账号登录后查看社区审核。' }}</div>
    <div v-else-if="tab === 'records'" id="my-records" role="tabpanel" aria-labelledby="my-records-tab"><QuestionRecords :user="user" :token="token" @navigate="emit('navigate', $event)" @session-expired="emit('session-expired')" /></div>
    <div v-else id="my-about" role="tabpanel" aria-labelledby="my-about-tab"><div class="my-about-intro"><h2>一份可以走进去的<br>园林读本。</h2><p>“拙政观景”把拙政园的造景手法整理成一条可观察、可创作的路径。带着一个问题走近一扇窗，再把发现留在自己的作品里。</p></div><div class="my-about-grid"><section><h3>从观察，到创作</h3><p>读懂框景、借景、对景、漏景与障景，在游园图里找到观察点，上传照片，让自己的视线落进一扇窗。梅梅也会陪你了解网站功能与拙政园。</p><button class="text-link" type="button" @click="emit('navigate', 'ask')">和梅梅聊一聊 <span aria-hidden="true">↗</span></button><h3 class="my-about-subhead">关于图片与作品</h3><p>园林照片来自 Wikimedia Commons，按来源标注的许可使用。研学照片、设计与材料来自本项目的江南研学档案。游客作品保存在当前浏览器。登录后新保存的作品会同步到账号，已有本机作品由你确认后导入；问答内容会发送到 AI 服务处理。</p></section><section><h3 id="sources">资料来源与署名</h3><div class="source-list"><a v-for="source in sources" :key="source.id" :href="source.url" target="_blank" rel="noreferrer">{{ source.title }}<small>{{ source.author }} · {{ source.license }}</small></a></div></section></div></div>
    <dialog ref="previewDialog" class="cloud-preview-dialog" @close="previewWork = null" @click="$event.target === previewDialog && previewDialog.close()"><template v-if="previewWork"><div class="cloud-preview-heading"><h2>{{ previewWork.title }}</h2><button class="secondary-button" type="button" autofocus @click="previewDialog.close()">关闭预览</button></div><img :src="previewWork.imageDataUrl" :alt="previewWork.title"><p>{{ previewWork.note }}</p></template></dialog>
  </section>
</template>

<style scoped>
.my-page { padding-top:54px; }
.my-heading { display:flex; align-items:center; justify-content:space-between; gap:32px; margin-bottom:40px; }
.my-heading h1 { margin:12px 0 0; }
.my-account { display:grid; gap:9px; padding:22px 26px; background:rgba(23,58,54,.035); min-width:280px; }
.my-account strong { font-size:20px; font-weight:500; }
.my-account span { color:var(--ink-soft); font-size:13px; line-height:1.6; }
.my-account button { text-align:left; margin-top:4px; }
.my-tabs { display:flex; flex-wrap:wrap; gap:0 30px; box-shadow:0 1px 0 var(--line); margin-bottom:42px; }
.my-tabs button { padding:16px 0; border:0; background:transparent; color:var(--ink-soft); position:relative; }
.my-tabs button.selected { color:var(--clay); }
.my-tabs button.selected::after { content:''; position:absolute; height:2px; bottom:0; left:0; right:0; background:var(--clay); }
.my-tabs span { margin-left:7px; font:12px system-ui,sans-serif; font-variant-numeric:tabular-nums; }
.works-book-entry { padding:34px; border:1px solid var(--line); background:linear-gradient(135deg, rgba(23,58,54,.06), rgba(212,170,78,.08)); }
.works-book-entry h2 { margin:10px 0 8px; font:400 clamp(34px,4vw,52px)/1.1 Georgia,'Songti SC',serif; }
.works-book-entry p { margin:0 0 18px; color:var(--ink-soft); }
.works-book-entry-actions { display:flex; align-items:center; gap:18px; flex-wrap:wrap; }
.works-manage { margin-top:34px; }
.my-works-heading { display:flex; justify-content:space-between; align-items:center; gap:24px; margin-bottom:28px; }
.my-works-heading h2 { font-size:30px; margin:0 0 10px; }
.my-works-heading p { font-size:14px; margin:0; }
.my-about-intro { display:grid; grid-template-columns:1fr 1fr; gap:64px; align-items:center; padding-bottom:48px; }
.my-about-intro h2 { margin:0; }
.my-about-intro p { margin:0; font-size:19px; }
.my-about-grid { display:grid; grid-template-columns:1fr 1fr; gap:64px; padding-top:34px; box-shadow:0 -1px 0 var(--line); }
.my-about-subhead { margin-top:42px; }
.my-about-grid p { font-size:15px; }
.cloud-archive { margin-bottom:50px; padding-bottom:42px; box-shadow:0 1px 0 var(--line); }
.cloud-work-preview--text { display:flex; align-items:center; justify-content:center; min-height:56px; padding:12px; border:1px solid var(--line); background:rgba(23,58,54,.04); color:var(--clay); font:600 12px system-ui,sans-serif; }
.work-card--text { grid-template-columns:1fr; }
.cloud-thumb-loading { display:flex; align-items:center; justify-content:center; min-height:140px; color:var(--ink-soft); font:12px system-ui,sans-serif; background:rgba(23,58,54,.04); }
.cloud-work-preview { display:block; border:0; background:transparent; padding:0; width:100%; }
.cloud-work-preview .image-motion { width:100%; aspect-ratio:1.25; }
.cloud-import { padding:22px; margin-top:24px; background:rgba(23,58,54,.035); }
.cloud-import strong { font-weight:500; }
.cloud-import p,.cloud-empty p { margin:8px 0 16px; font-size:14px; }
.import-confirm ul { padding-left:20px; color:var(--ink-soft); line-height:1.8; font-size:14px; }
.cloud-error { color:#9b4d3d; margin:16px 0; font-size:14px; line-height:1.8; }
.cloud-message { font-size:14px; }
.works-map { margin-bottom:46px; padding-bottom:42px; box-shadow:0 1px 0 var(--line); }
.works-map-summary { margin:12px 0 18px; color:var(--ink-soft); font:13px/1.7 system-ui,sans-serif; font-variant-numeric:tabular-nums; }
.works-map :deep(.garden-map) { min-height:440px; }
.works-map-legend { display:flex; flex-wrap:wrap; gap:8px; margin:14px 0 0; padding:0; list-style:none; }
.works-map-legend li { display:flex; align-items:center; gap:8px; padding:8px 12px; background:#eee5d4; color:var(--ink-soft); font:12px system-ui,sans-serif; }
.works-map-legend strong { color:var(--clay); font-weight:600; font-variant-numeric:tabular-nums; }
.works-map-empty { margin:0; padding:26px 24px; background:rgba(23,58,54,.035); font-size:14px; }
.review-badge { display:inline-block; margin-bottom:8px; padding:3px 10px; border-radius:999px; font:600 11px/1.6 system-ui,sans-serif; letter-spacing:.06em; background:rgba(23,58,54,.06); color:var(--ink-soft); }
.review-badge--approved { background:rgba(23,58,54,.1); color:var(--ink); }
.review-badge--pending { background:rgba(186,141,80,.16); color:#7a5a2c; }
.review-badge--rejected { background:rgba(156,77,53,.12); color:var(--clay); }
.review-reason { font-size:13px; margin:-4px 0 12px; }
.work-actions a.text-link { text-decoration:none; }
.cloud-preview-dialog { border:0; width:min(1100px, calc(100vw - 32px)); max-height:90dvh; padding:26px; color:var(--ink); background:var(--paper); box-shadow:var(--shadow); }
.cloud-preview-dialog::backdrop { background:rgba(23,58,54,.4); }
.cloud-preview-heading { display:flex; justify-content:space-between; align-items:center; gap:20px; margin-bottom:20px; }
.cloud-preview-heading h2 { margin:0; font-size:28px; }
.cloud-preview-dialog img { width:100%; max-height:65dvh; object-fit:contain; display:block; }
.cloud-preview-dialog p { margin:18px 0 0; }
@media (max-width:700px) { .my-heading { align-items:stretch; flex-direction:column; gap:24px; } .my-account { min-width:0; } .my-tabs { gap:24px; } .my-works-heading { align-items:flex-start; flex-direction:column; } .my-about-intro,.my-about-grid { grid-template-columns:1fr; gap:28px; } .my-about-intro p { font-size:17px; } .works-map :deep(.garden-map) { min-height:340px; } .works-map-summary { margin-top:-4px; } }
</style>
