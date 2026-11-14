<script setup>
import { computed, ref } from 'vue'
import { comparisons } from '../data/comparisons.js'
import { methods } from '../data/methods.js'
import { assetUrl } from '../utils/assets.js'

defineEmits(['open-method'])

const activeId = ref(comparisons[0].id)
const active = computed(() => comparisons.find(item => item.id === activeId.value) || comparisons[0])
const methodOf = id => methods.find(item => item.id === id) || methods[0]
</script>

<template>
  <section class="comparison-section" aria-labelledby="comparison-title">
    <div class="section-head">
      <div>
        <span class="eyebrow">SAME VIEW, DIFFERENT READINGS</span>
        <h2 id="comparison-title">同一处景色，换一种看法</h2>
      </div>
      <p>选一个场景，对照两三种手法各自把视线放在哪里。</p>
    </div>

    <div class="scene-tabs" role="tablist" aria-label="对照场景">
      <button
        v-for="scene in comparisons"
        :key="scene.id"
        type="button"
        role="tab"
        :aria-selected="scene.id === activeId"
        :class="['scene-tab', scene.id === activeId ? 'is-active' : '']"
        @click="activeId = scene.id"
      >{{ scene.title }}</button>
    </div>

    <article class="scene-panel">
      <header class="scene-head">
        <span class="scene-index">{{ active.subtitle }}</span>
        <h3>{{ active.title }}</h3>
        <p>{{ active.intro }}</p>
      </header>

      <div class="compare-grid">
        <button
          v-for="entry in active.methods"
          :key="entry.methodId"
          type="button"
          class="compare-card"
          @click="$emit('open-method', entry.methodId)"
        >
          <img class="compare-image" :src="assetUrl(methodOf(entry.methodId).image)" :alt="methodOf(entry.methodId).imageAlt" loading="lazy" decoding="async">
          <span class="compare-body">
            <span class="eyebrow">{{ methodOf(entry.methodId).pinyin }}</span>
            <strong>{{ methodOf(entry.methodId).name }}</strong>
            <span class="compare-summary">{{ methodOf(entry.methodId).summary }}</span>
            <span class="compare-observe">{{ entry.observe }}</span>
            <span class="compare-link">看这个手法 ↗</span>
          </span>
        </button>
      </div>
    </article>
  </section>
</template>

<style scoped>
.comparison-section { margin: 84px 0 72px; scroll-margin-top: 96px; padding-top: 36px; border-top: 1px solid var(--line); }
.comparison-section .section-head { align-items: flex-end; gap: 24px; }
.comparison-section .section-head p { max-width: 300px; margin: 0; color: var(--ink-soft); font-size: 14px; line-height: 1.7; }
.scene-tabs { display: flex; flex-wrap: wrap; gap: 10px; margin: 28px 0 22px; }
.scene-tab { border: 1px solid var(--line); background: transparent; color: var(--ink-soft); border-radius: 999px; padding: 9px 16px; font: 600 13px system-ui, sans-serif; cursor: pointer; transition: background .15s ease, color .15s ease; }
.scene-tab:hover { background: rgba(0, 0, 0, .03); }
.scene-tab.is-active { background: var(--ink); border-color: var(--ink); color: #f6f1e7; }
.scene-panel { border: 1px solid var(--line); background: rgba(255, 255, 255, .52); padding: 28px; }
.scene-head { max-width: 620px; margin-bottom: 22px; }
.scene-index { color: var(--clay); font: 600 11px system-ui, sans-serif; letter-spacing: .12em; }
.scene-head h3 { margin: 8px 0 8px; font-size: clamp(24px, 2.6vw, 32px); font-weight: 400; }
.scene-head p { margin: 0; color: var(--ink-soft); font-size: 15px; line-height: 1.7; }
.compare-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1px; background: var(--line); }
.compare-card { display: grid; grid-template-rows: 150px auto; text-align: left; border: 0; padding: 0; background: #f7f2e7; color: var(--ink); cursor: pointer; }
.compare-image { width: 100%; height: 150px; object-fit: cover; }
.compare-body { display: flex; flex-direction: column; gap: 6px; padding: 18px; }
.compare-body strong { font-size: 20px; font-weight: 500; }
.compare-summary { color: var(--ink-soft); font-size: 13px; line-height: 1.6; }
.compare-observe { margin-top: 4px; font-size: 14px; line-height: 1.7; }
.compare-link { margin-top: 8px; color: var(--clay); font: 600 12px system-ui, sans-serif; }
@media (max-width: 640px) {
  .comparison-section { margin-top: 56px; }
  .scene-panel { padding: 18px; }
  .compare-grid { grid-template-columns: 1fr; }
  .compare-card { grid-template-rows: 130px auto; }
  .compare-image { height: 130px; }
}
</style>
