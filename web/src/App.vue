<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import SiteNav from './components/SiteNav.vue'
import GardenMap from './components/GardenMap.vue'
import MethodCard from './components/MethodCard.vue'
import CaseViewer from './components/CaseViewer.vue'
import CreationCanvas from './components/CreationCanvas.vue'
import MyPage from './components/MyPage.vue'
import LoginPage from './components/LoginPage.vue'
import AskPage from './components/AskPage.vue'
import ImageMotion from './components/ImageMotion.vue'
import GardenComposition from './components/GardenComposition.vue'
import ComparisonView from './components/ComparisonView.vue'
import CommunityPage from './components/CommunityPage.vue'
import MascotGuide from './components/MascotGuide.vue'
import ReadingPage from './components/ReadingPage.vue'
import RoutesView from './components/RoutesView.vue'
import { methods, getMethod } from './data/methods.js'
import { isRoutesHash } from './data/routes.js'
import { cases } from './data/cases.js'
import { jiangnanPhotos, jiangnanWorks, jiangnanMaterials } from './data/jiangnan.js'
import { mascots, mascotCoin, mascotDesigns } from './data/mascots.js'
import { readWorks } from './utils/local-work.js'
import { formatHash, parseHash } from './utils/navigation.js'
import { apiRequest, clearSession, readSession, saveSession } from './utils/api.js'
import { prepareCloudWork } from './utils/cloud-work.js'
import { assetUrl } from './utils/assets.js'

// 先用 hash 初始化页面，避免深链到 #login/#mine 时先渲染首页、把首页大图也加载一遍。
const initialLocation = typeof window !== 'undefined' ? parseHash(window.location.hash) : { page: 'home' }
const page = ref(initialLocation.page || 'home')
const selectedMethod = ref(initialLocation.methodId || 'frame')
const works = ref(readWorks())
const editingWork = ref(null)
const mineTab = ref(initialLocation.mineTab || 'works')
const communityId = ref(null)
const session = readSession()
const token = ref(session.token)
const user = ref(session.token ? session.user : null)
const authLoading = ref(Boolean(session.token))
const loginReturnHash = ref('#mine/works')
const savingCloud = ref(false), saveNotice = ref('')
const currentMethod = computed(() => getMethod(selectedMethod.value))
const currentMascot = computed(() => ['methods', 'method-detail'].includes(page.value) || (page.value === 'mine' && mineTab.value === 'about') ? mascotCoin : page.value === 'studio' ? mascots.ice : page.value === 'explore' ? mascots.flower : mascots.round)
const mascotPlacement = computed(() => page.value === 'mine' || page.value === 'explore' || page.value === 'methods' ? 'left' : page.value === 'studio' ? 'right-mid' : 'right-bottom')
function applyLocation() {
  if (isRoutesHash(window.location.hash)) { page.value = 'routes'; window.scrollTo({ top: 0, behavior: 'smooth' }); return }
  const location = parseHash(window.location.hash)
  page.value = location.page
  if (location.mineTab) mineTab.value = location.mineTab
  communityId.value = location.communityId || null
  if (location.methodId) selectedMethod.value = location.methodId
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
function navigate(next, methodId = null) {
  if (next === 'login' && page.value !== 'login') loginReturnHash.value = window.location.hash || '#mine/works'
  if (next === 'studio') editingWork.value = null
  if (next === 'method-detail' && !methodId) methodId = selectedMethod.value
  if (next === 'method-detail' && methodId) selectedMethod.value = methodId
  const hash = formatHash(next, methodId)
  if (window.location.hash !== hash) window.history.pushState({}, '', hash)
  applyLocation()
}
function openMethod(id) { navigate('method-detail', id) }
function startStudio(work = null) { navigate('studio'); editingWork.value = work }
async function saved(work) {
  if (savingCloud.value) return
  works.value = readWorks(); saveNotice.value = ''
  if (token.value) {
    savingCloud.value = true
    const savingToken = token.value
    try { const prepared = await prepareCloudWork(work); if (token.value !== savingToken) return; await apiRequest('/profile/works', { token: savingToken, body: prepared }); if (token.value !== savingToken) return; saveNotice.value = '作品已保存到账号，本机原件也已保留。' }
    catch (error) { if (token.value !== savingToken) return; saveNotice.value = `作品已保存在本机，账号保存未完成：${error.message}`; if (error.status === 401) { savingCloud.value = false; sessionExpired(); return } }
    finally { savingCloud.value = false }
  }
  if (page.value === 'studio') navigate('mine', 'works')
}
function authenticated(data) { token.value = data.access_token; user.value = data.user; saveSession({ token: token.value, user: user.value }); window.history.pushState({}, '', loginReturnHash.value); applyLocation() }
function logout() { token.value = ''; user.value = null; saveNotice.value = ''; clearSession() }
function sessionExpired() { logout(); navigate('login') }
async function restoreSession() {
  if (!token.value) return
  const restoringToken = token.value
  try { const restoredUser = await apiRequest('/profile/me', { token: restoringToken }); if (token.value === restoringToken) { user.value = restoredUser; saveSession({ token: token.value, user: user.value }) } } catch (error) { if (error.status === 401 && token.value === restoringToken) sessionExpired() } finally { authLoading.value = false }
}
onMounted(() => { applyLocation(); restoreSession(); window.addEventListener('popstate', applyLocation); window.addEventListener('hashchange', applyLocation) })
onBeforeUnmount(() => { window.removeEventListener('popstate', applyLocation); window.removeEventListener('hashchange', applyLocation) })
</script>

<template>
  <div class="site">
    <SiteNav :current="page === 'method-detail' ? 'methods' : page" @navigate="navigate" />
    <main>
      <section v-if="page === 'home'" class="page home-page">
        <div class="hero">
          <div class="hero-copy"><span class="eyebrow">A FIELD GUIDE TO GARDEN VIEWS</span><h1>拙政观景，<br><em>看见景色如何发生。</em></h1><p class="hero-slogan">邂逅拙政巧景，若见江南芳华</p><p>拙政园把有限的园墙变成了无尽的视线。跟着五种造景手法，走近一扇窗、一座桥和一片水面。</p><div class="hero-actions"><button class="primary-button" @click="navigate('explore')">开始游园 <span>↗</span></button><button class="secondary-button" @click="navigate('methods')">先读懂手法</button><button class="secondary-button" @click="navigate('routes')">园内路线</button></div></div>
          <div class="hero-image"><ImageMotion src="/assets/garden/garden-001.jpg" alt="拙政园水院与建筑" eager /><span class="image-credit">King of Hearts / Wikimedia Commons · CC BY-SA 4.0</span></div>
        </div>
        <section class="promo-video-section" aria-labelledby="promo-video-title">
          <div class="section-head"><div><span class="eyebrow">WATCH THE GARDEN</span><h2 id="promo-video-title">从一扇窗，走进拙政园。</h2></div><p>用半分钟看见框景、借景与水岸如何把园林变成一套观看的安排。</p></div>
          <div class="promo-layout">
            <video class="promo-video" controls preload="none" :poster="assetUrl('/assets/promo/zhuozheng-promo-poster.jpg')" playsinline>
              <source :src="assetUrl('/assets/promo/zhuozheng-promo-web-720.mp4')" type="video/mp4">
            </video>
            <div class="promo-notes"><p class="promo-lead">从一扇窗开始，<br>看见一座园林。</p><p>园墙、漏窗、水面与亭阁，改变着我们看风景的方式。跟随短片走进拙政园，再到地图上寻找这些视线。</p><button class="text-link" type="button" @click="navigate('explore')">去地图观察 <span aria-hidden="true">↗</span></button></div>
          </div>
        </section>
        <div class="intro-band"><div><span class="eyebrow">WHY LOOK CLOSER</span><h2>园林不是一张风景照，<br>而是一套观看的安排。</h2><ImageMotion src="/assets/garden/garden-002.jpg" alt="拙政园水面与建筑" class-name="observation-motion" /></div><p>古典园林用遮挡、引导、呼应和借取组织人的目光。你看到的每一处“自然”，都可能是建筑、植物和路径共同完成的构图。正如研学报告所写：“窗框，不仅是建筑实体上的一道开口，更是一道哲学界限。”</p></div>
        <section class="map-section"><div class="section-head"><div><span class="eyebrow">WALK THE GARDEN</span><h2>在真实地图上观察</h2></div><p>地图定位拙政园园区范围，点击观察点，看看它对应哪一种造景手法。</p></div><GardenMap @open="openMethod" /></section>
        <section><div class="section-head"><div><span class="eyebrow">FIVE WAYS OF SEEING</span><h2>五种让空间变深的方法</h2></div><button class="text-link" @click="navigate('methods')">查看全部 <span>↗</span></button></div><div class="methods-grid"><MethodCard v-for="method in methods" :key="method.id" :method="method" @open="openMethod" /></div></section>
        <section class="case-section"><div class="section-head"><div><span class="eyebrow">FROM THE ARCHIVE</span><h2>先看三幅画面</h2></div></div><div class="case-grid"><CaseViewer v-for="item in cases" :key="item.id" :item="item" @open="openMethod" /></div></section>
        <section class="archive-teaser"><div class="archive-teaser-copy"><span class="eyebrow">FROM THE JIANGNAN FIELDWORK</span><h2>一次研学，也可以成为继续观察的起点。</h2><p>八年级研学小组留下的现场照片与窗框设计，正好成为这份园林读本里的另一组视线。</p><button class="secondary-button archive-teaser-button" type="button" @click="navigate('archive')">走进研学档案 ↗</button></div><div class="archive-strip"><ImageMotion v-for="item in [...jiangnanPhotos.slice(0, 2), jiangnanWorks[0]]" :key="item.src" :src="item.src" :alt="item.alt" :motion="false" sizes="(max-width: 900px) 50vw, 25vw" /></div></section>
      </section>

      <section v-else-if="page === 'methods'" class="page"><div class="section-head page-heading"><div><span class="eyebrow">FIELD NOTES</span><h1>造景手法</h1></div><p>五种方法，五种与景色相处的距离。</p></div><div class="methods-grid methods-list"><MethodCard v-for="method in methods" :key="method.id" :method="method" @open="openMethod" /></div><ComparisonView @open-method="openMethod" /><div class="reading-note"><span class="eyebrow">READING NOTE</span><p>这些名称来自中国古典园林的常用术语。具体园林中的一处景色，往往同时包含多种手法。</p></div></section>

      <section v-else-if="page === 'method-detail'" class="page detail-page"><div class="detail-topline"><button class="back-link" @click="navigate('methods')"><span aria-hidden="true">←</span> 返回手法</button><span class="detail-count">FIELD NOTE / 0{{ methods.findIndex(item => item.id === currentMethod.id) + 1 }}</span></div><div class="detail-hero"><div class="detail-intro"><span class="eyebrow">{{ currentMethod.pinyin }}</span><h1>{{ currentMethod.name }}</h1><p class="lead">{{ currentMethod.summary }}</p></div><figure class="detail-reference"><ImageMotion :src="currentMethod.image" :alt="currentMethod.imageAlt" class-name="detail-motion" :motion="false" eager /><figcaption><strong>{{ currentMethod.imageTitle }}</strong><span>{{ currentMethod.imageCaption }}</span><small>江南研学小组 · 现场摄影</small></figcaption></figure></div><article class="detail-body"><div class="observation-box"><div><span class="eyebrow">现场观察</span><strong>先停下来，再看见。</strong></div><p>{{ currentMethod.observe }}</p></div><div class="detail-reading"><div><span class="eyebrow">构景解析</span><h2>景色如何被组织</h2></div><p>{{ currentMethod.detail }}</p></div><GardenComposition :method="currentMethod" /><div class="detail-actions"><button class="primary-button" @click="startStudio()">用这个思路创作 <span>↗</span></button><button class="secondary-button" @click="navigate('explore')">回到游园图</button></div><div class="source-note">内容为面向公众的观察性整理，图片来源见<a href="#sources" @click.prevent="navigate('mine', 'about')">资料说明</a>。</div></article></section>

      <section v-else-if="page === 'explore'" class="page"><div class="section-head page-heading"><div><span class="eyebrow">OBSERVATION WALK</span><h1>游园观察</h1></div><p>不需要记住所有名字，只要找到视线的变化。</p></div><GardenMap @open="openMethod" /></section>

      <section v-else-if="page === 'routes'" class="page"><RoutesView @open-method="openMethod" /></section>

      <section v-else-if="page === 'reading'" class="page reading-route"><ReadingPage @navigate="navigate" /></section>
      <section v-else-if="page === 'archive'" class="page archive-page"><div class="section-head page-heading"><div><span class="eyebrow">JIANGNAN FIELD ARCHIVE</span><h1>研学档案</h1></div><p>八年级江南研学小组的照片、作品与研究报告。</p></div><div class="archive-intro"><div><h2>从现场出发，<br>再回到一扇窗。</h2></div><p>研究报告把一次游园拆成了可复用的方法：查资料、带着问题观察、拍摄与测量，最后把发现整理成文字和设计。下面的材料可以直接作为继续观察拙政园的入口。</p></div><div class="archive-block"><div class="section-head"><div><span class="eyebrow">FIELD PHOTOGRAPHS</span><h2>现场照片</h2></div><span class="archive-meta">精选 05 张</span></div><div class="archive-photo-grid"><figure v-for="photo in jiangnanPhotos" :key="photo.src"><ImageMotion :src="photo.src" :alt="photo.alt" :motion="false" sizes="(max-width: 560px) 50vw, (max-width: 900px) 33vw, 20vw" /><figcaption>{{ photo.label }}</figcaption></figure></div></div><div class="archive-block mascot-design-block"><div class="section-head"><div><span class="eyebrow">MASCOT DESIGN</span><h2>吉祥物设计原图</h2></div><span class="archive-meta">三张原案</span></div><div class="mascot-design-grid"><article v-for="item in mascotDesigns" :key="item.id"><ImageMotion :src="item.src" :alt="item.alt" :motion="false" sizes="(max-width: 700px) 100vw, 33vw" /><div><h3>{{ item.name }}</h3><p>{{ item.note }}</p></div></article></div></div><div class="archive-block reading-block"><div class="section-head"><div><span class="eyebrow">READING</span><h2>研学文章</h2></div><span class="archive-meta">约 8 分钟</span></div><article class="archive-reading-card"><div><span class="eyebrow">FIELD REPORT</span><h3>窗框里的拙政园</h3><p>从一扇窗开始，重新学习如何观看。原文来自八年级江南研学小组的研究报告，已整理润色为一篇可连续阅读的文章。</p></div><button class="primary-button" type="button" @click="navigate('reading')">开始阅读 ↗</button></article></div></section>

      <section v-else-if="page === 'studio'" class="page studio-page"><div class="section-head page-heading"><div><span class="eyebrow">MAKE YOUR OWN VIEW</span><h1>我的造景</h1></div><p>上传一张照片，给它选择一个观看的边界。</p></div><p v-if="savingCloud" class="save-notice" role="status">本机已保存，正在同步到账号…</p><div :inert="savingCloud || undefined"><CreationCanvas :key="editingWork?.id || 'new-work'" :initial="editingWork" @saved="saved" /></div></section>

      <MyPage v-else-if="page === 'mine'" :works="works" :user="user" :token="token" :tab="mineTab" :auth-loading="authLoading" :save-notice="saveNotice" @navigate="navigate" @tab="navigate('mine', $event)" @edit="startStudio" @changed="works = $event" @logout="logout" @session-expired="sessionExpired" />

      <CommunityPage v-else-if="page === 'community'" :user="user" :token="token" :community-id="communityId" @navigate="navigate" @session-expired="sessionExpired" />
      <LoginPage v-else-if="page === 'login'" @navigate="navigate" @authenticated="authenticated" />
      <AskPage v-else-if="page === 'ask'" :key="token" :user="user" :token="token" @navigate="navigate" @session-expired="sessionExpired" />
    </main>
    <MascotGuide v-if="page !== 'ask' && page !== 'login'" :key="currentMascot.id" :mascot="currentMascot" :placement="mascotPlacement" :model-delay="page === 'mine' ? 900 : 0" @navigate="navigate" />
    <footer class="page-footer"><span>拙政观景 · 拙政园造景手法</span><span>独立网页出版物 · 资料访问 2026</span><a class="site-icp" href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">京ICP备2026077702号-1</a></footer>
  </div>
</template>

<style>
em { color:var(--clay); font-style:normal; } .page-heading { align-items:center; margin-bottom:54px; } .page-heading h1 { margin:10px 0 0; } .page-heading > p { max-width:300px; } .lead { font-size:20px; } .back-link { border:0; background:none; padding:0; color:var(--clay); font:600 13px system-ui,sans-serif; display:block; } .back-link span { display:inline-block; margin-right:8px; font-size:18px; vertical-align:-.1em; } .case-section { padding-top:110px; } .methods-list { margin-bottom:90px; } .reading-note { border-top:1px solid var(--line); padding:28px 0; max-width:600px; } .reading-note p { margin:8px 0 0; } .detail-page { padding-top:38px; } .detail-topline { display:flex; justify-content:space-between; align-items:center; padding-bottom:22px; border-bottom:1px solid var(--line); } .detail-count { color:var(--ink-soft); font:11px system-ui,sans-serif; letter-spacing:.14em; } .detail-hero { margin-top:48px; margin-bottom:76px; } .detail-intro { padding-bottom:28px; } .detail-intro h1 { margin:12px 0 18px; } .detail-intro .lead { max-width:520px; margin-bottom:0; } .detail-body { max-width:900px; } .observation-box { display:grid; grid-template-columns:220px 1fr; gap:36px; align-items:start; margin:0 0 64px; padding:24px 0 26px; border-top:1px solid var(--ink); border-bottom:1px solid var(--line); background:transparent; } .observation-box strong { display:block; margin-top:12px; font-size:23px; font-weight:500; } .observation-box p { margin:0; max-width:560px; font-size:17px; } .detail-reading { display:grid; grid-template-columns:1fr 1.25fr; gap:40px; align-items:start; margin-bottom:28px; } .detail-reading h2 { max-width:9em; margin:10px 0 0; font-size:clamp(26px,3vw,36px); line-height:1.4; font-weight:400; } .detail-reading p { margin:0; font-size:17px; } .detail-actions { display:flex; gap:12px; margin-top:42px; } .explore-points { display:grid; grid-template-columns:repeat(5,1fr); gap:1px; background:var(--line); margin-top:42px; } .explore-points button { min-height:150px; border:0; background:#eee5d4; color:var(--ink); text-align:left; padding:18px; position:relative; } .explore-points button:hover { background:#e7dac3; } .explore-points span { display:block; font-size:21px; margin-bottom:10px; } .explore-points small { display:block; color:var(--ink-soft); line-height:1.6; padding-right:18px; } .explore-points b { position:absolute; right:16px; bottom:16px; color:var(--clay); } .gallery-sample { border-top:1px solid var(--line); margin-top:100px; padding-top:48px; } .about-bottom { margin-top:100px; padding-top:30px; border-top:1px solid var(--line); max-width:640px; } @media (max-width:900px) { .explore-points { grid-template-columns:1fr 1fr; } .observation-box,.detail-reading { grid-template-columns:1fr; gap:16px; } } @media (max-width:560px) { .explore-points { grid-template-columns:1fr; } .detail-actions { flex-direction:column; } .detail-page { padding-top:24px; } .detail-hero { margin-top:32px; margin-bottom:52px; } .detail-count { font-size:9px; } }
.hero-slogan { margin:20px 0 8px; color:var(--clay); font-size:22px; line-height:1.5; letter-spacing:.04em; }
.promo-video-section { margin-top:84px; padding:54px 0 0; border-top:1px solid var(--line); }
.promo-video-section .section-head { max-width:680px; }
.promo-layout { display:grid; grid-template-columns:minmax(0, 360px) minmax(0, 1fr); gap:clamp(32px, 8vw, 120px); align-items:center; }
.promo-video { display:block; width:100%; aspect-ratio:9 / 16; max-height:680px; margin:0; background:transparent; object-fit:contain; }
.promo-notes { max-width:470px; padding:24px 0; }
.promo-notes .promo-lead { color:var(--ink); font-size:clamp(28px, 3vw, 42px); line-height:1.45; }
.promo-notes > p:not(.promo-lead) { max-width:32em; margin:24px 0; font-size:16px; }
@media (max-width:700px) { .promo-layout { grid-template-columns:1fr; gap:16px; } .promo-video { width:min(100%, 320px); } .promo-notes { padding:12px 0 32px; } }
.archive-teaser { display:grid; grid-template-columns:.9fr 1.1fr; gap:48px; align-items:center; margin-top:110px; padding:58px 0; border-top:1px solid var(--line); border-bottom:1px solid var(--line); }
.archive-teaser h2 { margin:10px 0 16px; max-width:520px; }
.archive-teaser-copy p { max-width:480px; }
.archive-teaser-button { margin-top:22px; }
.archive-strip { display:grid; grid-template-columns:1.2fr .8fr .8fr; gap:10px; height:260px; }
.archive-strip img { width:100%; height:100%; object-fit:cover; filter:saturate(.82) sepia(.08); }
.archive-strip img:first-child { grid-row:span 2; }
.archive-strip > .image-motion:first-child { grid-row:span 2; }
.archive-strip > .image-motion { height:100%; }
.archive-photo-grid .image-motion { aspect-ratio:1.1; }
.archive-work-grid .image-motion { height:220px; }
.archive-page { padding-top:54px; }
.archive-intro { display:grid; grid-template-columns:1fr 1fr; gap:60px; padding:8px 0 70px; }
.archive-intro h2 { margin:0; }
.archive-intro p { max-width:520px; font-size:18px; }
.mascot-design-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:22px; }
.mascot-design-grid article { padding:18px; background:rgba(255,255,255,.45); }
.mascot-design-grid .image-motion { height:260px; background:rgba(23,58,54,.04); }
.mascot-design-grid .image-motion img { object-fit:contain; }
.mascot-design-grid h3 { margin:14px 0 6px; font-size:22px; }
.mascot-design-grid p { margin:0; color:var(--ink-soft); font-size:13px; line-height:1.7; }
@media (max-width:820px) { .mascot-design-grid { grid-template-columns:1fr; } }
.archive-reading-card { display:flex; align-items:center; justify-content:space-between; gap:32px; padding:34px 36px; border:1px solid var(--line); background:linear-gradient(135deg,rgba(23,58,54,.05),rgba(212,170,78,.08)); }
.archive-reading-card h3 { margin:10px 0 8px; font-size:clamp(26px,3vw,36px); font-weight:400; }
.archive-reading-card p { margin:0; max-width:560px; color:var(--ink-soft); line-height:1.8; }
.archive-download { display:flex; flex-wrap:wrap; gap:8px 14px; margin:16px 0 0; color:var(--ink-soft); font-size:12px; }
.archive-download a { color:var(--clay); }
@media (max-width:700px) { .archive-reading-card { flex-direction:column; align-items:flex-start; padding:24px; } }
.archive-block { padding:58px 0 0; border-top:1px solid var(--line); margin-top:24px; }
.archive-meta { color:var(--ink-soft); font:12px system-ui,sans-serif; }
.archive-photo-grid { display:grid; grid-template-columns:repeat(5,1fr); gap:10px; }
.archive-photo-grid figure { margin:0; }
.archive-photo-grid img { display:block; width:100%; aspect-ratio:1.1; object-fit:cover; filter:saturate(.82) sepia(.08); }
.archive-photo-grid figcaption { padding-top:10px; color:var(--ink-soft); font:11px system-ui,sans-serif; }
.archive-work-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; }
.archive-work-grid article { background:#eee5d4; }
.archive-work-grid img { display:block; width:100%; height:220px; object-fit:cover; }
.archive-work-grid article:first-child img { object-position:center 28%; }
.archive-work-grid div { padding:16px; }
.archive-work-grid h3 { margin:0 0 6px; font-size:20px; }
.archive-work-grid p { margin:0; font:12px system-ui,sans-serif; }
.material-block { padding-bottom:60px; }
.material-list { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; }
.material-list a { display:flex; flex-direction:column; min-height:220px; padding:22px; background:#eee5d4; color:var(--ink); text-decoration:none; transition:transform .15s ease, background .15s ease; }
.material-list a:hover { transform:translateY(-3px); background:#e7dac3; }
.material-type { color:var(--clay); font:600 11px system-ui,sans-serif; letter-spacing:.12em; }
.material-list strong { margin-top:24px; font-size:20px; line-height:1.35; }
.material-list p { margin:12px 0 22px; font-size:14px; }
.material-link { margin-top:auto; color:var(--clay); font:600 12px system-ui,sans-serif; }
@media (max-width:900px) { .archive-teaser,.archive-intro { grid-template-columns:1fr; gap:24px; } .archive-photo-grid { grid-template-columns:repeat(3,1fr); } .archive-work-grid { grid-template-columns:repeat(2,1fr); } .material-list { grid-template-columns:1fr; } }
@media (max-width:560px) { .archive-strip { height:190px; } .archive-photo-grid { grid-template-columns:repeat(2,1fr); } .archive-photo-grid figure:last-child { grid-column:span 2; } .archive-work-grid { grid-template-columns:1fr; } }
</style>
