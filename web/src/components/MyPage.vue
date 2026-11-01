<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import LocalGallery from './LocalGallery.vue'
import ImageMotion from './ImageMotion.vue'
import QuestionRecords from './QuestionRecords.vue'
import { sources } from '../data/sources.js'
import { apiRequest } from '../utils/api.js'
import { prepareCloudWork } from '../utils/cloud-work.js'
import { community, reviewLabel } from '../utils/community.js'
import ReviewQueue from './ReviewQueue.vue'
const props = defineProps({ works: Array, user: Object, token: String, tab: { type: String, default: 'works' }, authLoading: Boolean, saveNotice: String })
const emit = defineEmits(['navigate', 'tab', 'edit', 'changed', 'logout', 'session-expired'])
const cloudWorks = ref([]), cloudLoading = ref(false), cloudError = ref(''), cloudMessage = ref(''), importing = ref(false), importPreview = ref(false), previewWork = ref(null), deleting = ref(null)
const previewDialog = ref(null)
async function openPreview(work) { previewWork.value = work; await nextTick(); previewDialog.value?.showModal() }
const newLocalWorks = computed(() => (props.works || []).filter(work => !cloudWorks.value.some(cloud => cloud.id === work.id)))
let requestVersion = 0
function handleError(error) { cloudError.value = error.message; if (error.status === 401) emit('session-expired') }
async function loadCloud() {
  const version = ++requestVersion
  previewDialog.value?.close()
  cloudWorks.value = []; cloudError.value = ''; cloudMessage.value = ''; importPreview.value = false; previewWork.value = null
  if (!props.token) { cloudLoading.value = false; return }
  cloudLoading.value = true
  try { const data = await apiRequest('/profile/works', { token: props.token }); if (version === requestVersion) cloudWorks.value = Array.isArray(data) ? data : [] } catch (error) { if (version === requestVersion) handleError(error) } finally { if (version === requestVersion) cloudLoading.value = false }
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
watch(() => props.token, loadCloud, { immediate: true })
</script>

<template>
  <section class="page my-page">
    <header class="my-heading"><div><span class="eyebrow">把观察留在身边</span><h1>我的</h1></div><div class="my-account"><template v-if="user"><strong>{{ user.nickname || user.phone || '园中来客' }}</strong><span>欢迎回来，继续发现一窗一景。</span><button class="text-link" type="button" @click="emit('logout')">退出登录</button></template><template v-else><strong>{{ authLoading ? '正在确认登录状态…' : '一位园中来客' }}</strong><span>登录后，与梅梅一起聊聊园林。</span><button class="text-link" type="button" @click="emit('navigate', 'login')">登录 / 注册</button></template></div></header>
    <div class="my-tabs" role="tablist" aria-label="我的页面内容"><button id="my-works-tab" type="button" role="tab" :aria-selected="tab === 'works'" aria-controls="my-works" :class="{ selected: tab === 'works' }" @click="emit('tab', 'works')">我的作品 <span>{{ works?.length || 0 }}</span></button><button id="my-records-tab" type="button" role="tab" :aria-selected="tab === 'records'" aria-controls="my-records" :class="{ selected: tab === 'records' }" @click="emit('tab', 'records')">问答记录</button><button id="my-about-tab" type="button" role="tab" :aria-selected="tab === 'about'" aria-controls="my-about" :class="{ selected: tab === 'about' }" @click="emit('tab', 'about')">关于拙政观景</button><button v-if="user?.role === 'admin'" id="my-review-tab" type="button" role="tab" :aria-selected="tab === 'review'" aria-controls="my-review" :class="{ selected: tab === 'review' }" @click="emit('tab', 'review')">社区审核</button></div>
    <div v-if="tab === 'works'" id="my-works" role="tabpanel" aria-labelledby="my-works-tab">
      <p v-if="saveNotice" class="cloud-message" role="status">{{ saveNotice }}</p>
      <section v-if="user" class="cloud-archive"><div class="my-works-heading"><div><h2>账号中的作品</h2><p>保存在你的账号里，换一台设备也能继续创作。</p></div><button class="primary-button" type="button" @click="emit('navigate', 'studio')">新建作品 ↗</button></div><p v-if="cloudLoading" role="status">正在打开你的作品册…</p><div v-if="cloudError" class="cloud-error" role="alert">{{ cloudError }} <button class="text-link" type="button" @click="loadCloud">重新加载</button></div><p v-if="cloudMessage" class="cloud-message" role="status">{{ cloudMessage }}</p><div v-if="cloudWorks.length" class="local-gallery"><article v-for="work in cloudWorks" :key="work.id" class="work-card cloud-work"><button class="cloud-work-preview" type="button" :aria-label="`预览${work.title}`" @click="openPreview(work)"><ImageMotion :src="work.imageDataUrl" :alt="work.title" :motion="false" :retryable="false" /></button><div><span v-if="reviewLabel(work.reviewStatus)" :class="['review-badge', `review-badge--${work.reviewStatus}`]">{{ reviewLabel(work.reviewStatus) }}</span><h3>{{ work.title }}</h3><p>{{ work.note || '一幅来自你的观察。' }}</p><p v-if="work.reviewStatus === 'rejected'" class="review-reason">未通过原因：{{ work.rejectReason }}。修改后可以重新提交。</p><p v-else-if="work.reviewStatus === 'pending'" class="review-reason">编辑已公开的作品会重新进入审核。</p><div class="work-actions"><button class="text-link" type="button" @click="emit('edit', { ...work, cloud: true })">继续编辑</button><a v-if="work.communityId" class="text-link" :href="`#community/${work.communityId}`">查看</a><button class="text-link" type="button" :disabled="publishing === work.id" @click="togglePublish(work)">{{ publishing === work.id ? '处理中…' : work.reviewStatus === 'rejected' ? '重新提交' : work.visibility === 'public' ? '撤回公开' : '发布到社区' }}</button><button class="danger-link" type="button" :disabled="deleting === work.id" @click="deleteCloud(work)">{{ deleting === work.id ? '删除中…' : '删除' }}</button></div></div></article></div><div v-else-if="!cloudLoading && !cloudError" class="cloud-empty"><p>账号里还没有作品。从本机导入，或去创作一幅新的园林取景。</p></div><div v-if="newLocalWorks.length && !cloudLoading && !cloudError" class="cloud-import"><div><strong>这台设备上还有 {{ newLocalWorks.length }} 幅作品</strong><p>导入前会压缩图片，本机原件保留；账号中已有的同名编号不会覆盖。</p></div><button v-if="!importPreview" class="secondary-button" type="button" @click="importPreview = true">查看待导入作品</button><div v-else class="import-confirm"><ul><li v-for="work in newLocalWorks" :key="work.id">{{ work.title || '未命名取景' }}</li></ul><div class="work-actions"><button class="primary-button" type="button" :disabled="importing" @click="importWorks">{{ importing ? '正在压缩并导入…' : `确认导入 ${newLocalWorks.length} 幅` }}</button><button class="text-link" type="button" :disabled="importing" @click="importPreview = false">取消</button></div></div></div></section>
      <div class="my-works-heading"><div><h2>本机作品</h2><p>这些原件只保存在当前浏览器里。</p></div><button v-if="!user" class="primary-button" type="button" @click="emit('navigate', 'studio')">新建作品 ↗</button></div><LocalGallery :works="works" @changed="emit('changed', $event)" @edit="emit('edit', $event)" />
    </div>
    <div v-else-if="tab === 'review' && user?.role === 'admin'" id="my-review" role="tabpanel" aria-labelledby="my-review-tab"><ReviewQueue :token="token" @session-expired="emit('session-expired')" /></div>
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
.my-tabs { display:flex; gap:30px; box-shadow:0 1px 0 var(--line); margin-bottom:42px; }
.my-tabs button { padding:16px 0; border:0; background:transparent; color:var(--ink-soft); position:relative; }
.my-tabs button.selected { color:var(--clay); }
.my-tabs button.selected::after { content:''; position:absolute; height:2px; bottom:0; left:0; right:0; background:var(--clay); }
.my-tabs span { margin-left:7px; font:12px system-ui,sans-serif; font-variant-numeric:tabular-nums; }
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
.cloud-work-preview { display:block; border:0; background:transparent; padding:0; width:100%; }
.cloud-work-preview .image-motion { width:100%; aspect-ratio:1.25; }
.cloud-import { padding:22px; margin-top:24px; background:rgba(23,58,54,.035); }
.cloud-import strong { font-weight:500; }
.cloud-import p,.cloud-empty p { margin:8px 0 16px; font-size:14px; }
.import-confirm ul { padding-left:20px; color:var(--ink-soft); line-height:1.8; font-size:14px; }
.cloud-error { color:#9b4d3d; margin:16px 0; font-size:14px; line-height:1.8; }
.cloud-message { font-size:14px; }
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
@media (max-width:700px) { .my-heading { align-items:stretch; flex-direction:column; gap:24px; } .my-account { min-width:0; } .my-tabs { gap:24px; } .my-works-heading { align-items:flex-start; flex-direction:column; } .my-about-intro,.my-about-grid { grid-template-columns:1fr; gap:28px; } .my-about-intro p { font-size:17px; } }
</style>
