<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { readingArticle } from '../data/reading.js'

const emit = defineEmits(['navigate'])
const article = readingArticle
const fontSize = ref(Number(localStorage.getItem('garden-reader-font') || 20))
const focused = ref(false)
const tocOpen = ref(true)
const activeId = ref(article.sections[0]?.id || '')
const progress = ref(0)

function setFont(next) {
  fontSize.value = Math.max(17, Math.min(24, next))
  try { localStorage.setItem('garden-reader-font', String(fontSize.value)) } catch (error) {}
}
function jump(id) {
  activeId.value = id
  const target = document.getElementById(`reader-${id}`)
  target?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
function syncNavHeight() {
  const nav = document.querySelector('.site-nav')
  if (nav) document.documentElement.style.setProperty('--reading-nav', `${nav.offsetHeight}px`)
}
function updateProgress() {
  const doc = document.documentElement
  const max = doc.scrollHeight - window.innerHeight
  progress.value = max > 0 ? Math.min(100, Math.max(0, (window.scrollY / max) * 100)) : 0
  let current = article.sections[0]?.id || ''
  for (const section of article.sections) {
    const el = document.getElementById(`reader-${section.id}`)
    if (el && el.getBoundingClientRect().top <= 140) current = section.id
  }
  activeId.value = current
}
onMounted(() => {
  syncNavHeight()
  window.addEventListener('resize', syncNavHeight)
  window.addEventListener('scroll', updateProgress, { passive: true })
  updateProgress()
})
onBeforeUnmount(() => {
  window.removeEventListener('scroll', updateProgress)
  window.removeEventListener('resize', syncNavHeight)
})
const progressStyle = computed(() => ({ width: `${progress.value}%` }))
</script>

<template>
  <section :class="['page reading-page', { 'is-focused': focused, 'toc-hidden': !tocOpen }]">
    <div class="reading-progress" aria-hidden="true"><span :style="progressStyle"></span></div>

    <div class="reading-topline">
      <button class="back-link" type="button" @click="emit('navigate', 'archive')"><span aria-hidden="true">←</span> 返回研学档案</button>
      <span>原文整理 · 江南研学小组</span>
    </div>

    <header class="reading-intro">
      <span class="eyebrow">{{ article.eyebrow }}</span>
      <h1>{{ article.title }}</h1>
      <p>{{ article.subtitle }}</p>
      <div class="reading-meta"><span v-for="item in article.meta" :key="item">{{ item }}</span></div>
    </header>

    <div class="reading-toolbar" role="toolbar" aria-label="阅读设置">
      <div class="reader-font-controls">
        <span>字号</span>
        <button type="button" aria-label="减小字号" :disabled="fontSize <= 17" @click="setFont(fontSize - 1)">A−</button>
        <output>{{ fontSize }}</output>
        <button type="button" aria-label="增大字号" :disabled="fontSize >= 24" @click="setFont(fontSize + 1)">A+</button>
      </div>
      <button type="button" :aria-pressed="tocOpen" @click="tocOpen = !tocOpen">目录</button>
      <button type="button" :aria-pressed="focused" @click="focused = !focused">{{ focused ? '退出专注' : '专注阅读' }}</button>
      <button type="button" @click="emit('navigate', 'archive')">回到档案</button>
    </div>

    <div class="reading-layout">
      <aside v-if="tocOpen" class="reading-sidebar" aria-label="文章目录">
        <div class="reader-toc-heading"><h2>目录</h2><span>{{ article.sections.length }} 节</span></div>
        <nav id="chapter-list">
          <button v-for="(section, index) in article.sections" :key="section.id" type="button" :aria-current="activeId === section.id ? 'true' : undefined" @click="jump(section.id)">
            <span aria-hidden="true">{{ String(index + 1).padStart(2, '0') }}</span> {{ section.title }}
          </button>
        </nav>
        <p class="reading-source">原文：{{ article.meta[0] }}《探究拙政园中的“借景”“框景”及其蕴含的审美追求分析》</p>
      </aside>

      <article class="reading-paper" :style="{ '--reader-font-size': `${fontSize}px` }">
        <section v-for="section in article.sections" :id="`reader-${section.id}`" :key="section.id" class="reading-section">
          <h2>{{ section.title }}</h2>
          <p v-for="(paragraph, index) in section.paragraphs" :key="index">{{ paragraph }}</p>
          <blockquote v-if="section.quote">{{ section.quote }}</blockquote>
        </section>
        <div class="reading-bottom">
          <button class="secondary-button" type="button" @click="emit('navigate', 'archive')">返回研学档案</button>
          <button class="text-link" type="button" @click="emit('navigate', 'studio')">用这个思路创作 ↗</button>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.reading-page { padding-top: 26px; position: relative; }
.reading-progress { position: fixed; top: 0; left: 0; z-index: 30; width: 100%; height: 2px; background: transparent; }
.reading-progress span { display: block; height: 100%; background: var(--clay); transition: width .12s linear; }
.reading-topline { display: flex; justify-content: space-between; gap: 20px; padding-top: 10px; color: var(--ink-soft); font-size: 12px; }
.reading-intro { padding: 34px 0 26px; max-width: 940px; }
.reading-intro h1 { margin: 12px 0 14px; font-size: clamp(38px, 6vw, 72px); line-height: 1.08; font-weight: 400; letter-spacing: -.03em; }
.reading-intro p { margin: 0; max-width: 680px; color: var(--ink-soft); font-size: 18px; line-height: 1.8; }
.reading-meta { display: flex; flex-wrap: wrap; gap: 8px 18px; margin-top: 22px; padding-top: 16px; border-top: 1px solid var(--line); color: var(--ink-soft); font-size: 12px; }
.reading-toolbar { position: sticky; top: var(--reading-nav, 76px); z-index: 6; display: flex; align-items: center; flex-wrap: wrap; gap: 10px; padding: 10px 12px; border: 1px solid var(--line); background: rgba(247,242,231,.92); backdrop-filter: blur(10px); }
.reading-toolbar button { padding: 7px 12px; border: 1px solid var(--line); background: transparent; color: var(--ink); font: 12px system-ui, sans-serif; }
.reading-toolbar button[aria-pressed="true"] { background: rgba(23,58,54,.09); color: var(--clay); }
.reading-toolbar button:disabled { opacity: .35; cursor: default; }
.reader-font-controls { display: flex; align-items: center; gap: 6px; margin-right: 6px; color: var(--ink-soft); font: 12px system-ui, sans-serif; }
.reader-font-controls output { min-width: 26px; text-align: center; font-variant-numeric: tabular-nums; }
.reading-layout { display: grid; grid-template-columns: 248px minmax(0, 1fr); gap: 30px; align-items: start; margin-top: 26px; }
.reading-page.toc-hidden .reading-layout { grid-template-columns: minmax(0, 860px); justify-content: center; }
.reading-page.is-focused .reading-intro, .reading-page.is-focused .reading-topline { display: none; }
.reading-page.is-focused .reading-sidebar { display: none; }
.reading-page.is-focused .reading-layout { grid-template-columns: minmax(0, 860px); justify-content: center; margin-top: 12px; }
.reading-sidebar { position: sticky; top: calc(var(--reading-nav, 76px) + 62px); max-height: calc(100vh - 170px); overflow: auto; padding: 20px 16px; border: 1px solid var(--line); background: rgba(255,255,255,.4); }
.reader-toc-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; padding: 0 4px; }
.reader-toc-heading h2 { margin: 0; font-size: 16px; }
.reader-toc-heading span { color: var(--ink-soft); font-size: 11px; }
#chapter-list { display: grid; gap: 3px; margin-top: 14px; }
#chapter-list button { width: 100%; padding: 9px 8px; border: 0; background: transparent; color: var(--ink-soft); text-align: left; font: 13px/1.6 system-ui, sans-serif; }
#chapter-list button span { display: inline-block; width: 22px; color: rgba(156,77,53,.65); font-variant-numeric: tabular-nums; }
#chapter-list button:hover { background: rgba(23,58,54,.05); }
#chapter-list button[aria-current="true"] { background: rgba(23,58,54,.08); color: var(--ink); box-shadow: inset 2px 0 var(--clay); }
.reading-source { margin: 18px 4px 0; padding-top: 14px; border-top: 1px solid var(--line); color: var(--ink-soft); font-size: 11px; line-height: 1.7; }
.reading-paper { padding: 40px clamp(24px, 4vw, 58px); border: 1px solid var(--line); background: #fbf7ee; box-shadow: 0 18px 40px rgba(23,58,54,.06); min-width: 0; }
.reading-section + .reading-section { margin-top: 34px; padding-top: 30px; border-top: 1px solid var(--line); }
.reading-section { scroll-margin-top: calc(var(--reading-nav, 76px) + 78px); }
.reading-section h2 { margin: 0 0 18px; font-size: clamp(24px, 3vw, 30px); font-weight: 500; line-height: 1.35; }
.reading-section p { margin: 0 0 1.2em; color: #2f3d38; font-family: 'Noto Serif SC', 'Songti SC', Georgia, serif; font-size: var(--reader-font-size, 20px); line-height: 2; text-wrap: pretty; }
.reading-section blockquote { margin: 22px 0; padding: 10px 0 10px 22px; border-left: 2px solid var(--clay); color: var(--clay); font: 400 clamp(19px, 2.4vw, 23px)/1.7 'Noto Serif SC', 'Songti SC', serif; }
.reading-bottom { display: flex; justify-content: space-between; align-items: center; gap: 14px; margin-top: 42px; padding-top: 22px; border-top: 1px solid var(--line); }
@media (max-width: 960px) {
  .reading-layout { grid-template-columns: 1fr; }
  .reading-sidebar { position: static; max-height: none; order: 2; }
  .reading-section { scroll-margin-top: calc(var(--reading-nav, 76px) + 74px); }
}
@media (max-width: 620px) {
  .reading-intro h1 { font-size: 40px; }
  .reading-paper { padding: 26px 20px; }
  .reading-toolbar { gap: 6px; padding: 8px; }
  .reading-toolbar button { padding: 6px 9px; }
  .reading-bottom { flex-direction: column; align-items: flex-start; }
}
</style>
