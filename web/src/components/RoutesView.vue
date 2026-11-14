<script setup>
import { computed, nextTick, ref } from 'vue'
import { gardenRoutes } from '../data/routes.js'
import { gardenPoints } from '../data/garden-points.js'
import { getMethod } from '../data/methods.js'

const emit = defineEmits(['open-method'])
const activeId = ref(gardenRoutes[0].id)
const activeRoute = computed(() => gardenRoutes.find(route => route.id === activeId.value) || gardenRoutes[0])
const pointsById = new Map(gardenPoints.map(point => [point.id, point]))
const methodOf = stop => getMethod(pointsById.get(stop.pointId)?.methodId)

function selectRoute(id) {
  activeId.value = id
}

async function moveTab(event) {
  const step = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0
  if (!step) return
  event.preventDefault()
  const index = gardenRoutes.findIndex(route => route.id === activeId.value)
  activeId.value = gardenRoutes[(index + step + gardenRoutes.length) % gardenRoutes.length].id
  await nextTick()
  document.getElementById(`route-tab-${activeId.value}`)?.focus()
}
</script>

<template>
  <div class="routes-view">
    <header class="routes-head">
      <div>
        <span class="eyebrow">GARDEN ROUTES</span>
        <h1>园内路线</h1>
      </div>
      <p>三条走法：先看最少的东西，还是把每一处视线都走完，取决于你留给园子的时间。</p>
    </header>

    <div class="route-tabs" role="tablist" aria-label="园内路线" @keydown="moveTab">
      <button
        v-for="route in gardenRoutes"
        :id="`route-tab-${route.id}`"
        :key="route.id"
        class="route-tab"
        :class="{ active: route.id === activeId }"
        type="button"
        role="tab"
        :aria-selected="route.id === activeId"
        :aria-controls="`route-panel-${route.id}`"
        :tabindex="route.id === activeId ? 0 : -1"
        @click="selectRoute(route.id)"
      >
        <span class="route-tab-title">{{ route.title }}</span>
        <span class="route-tab-meta">{{ route.duration }}</span>
      </button>
    </div>

    <section
      :id="`route-panel-${activeRoute.id}`"
      :key="activeRoute.id"
      class="route-panel"
      role="tabpanel"
      :aria-labelledby="`route-tab-${activeRoute.id}`"
    >
      <p class="route-subtitle">{{ activeRoute.subtitle }}</p>
      <ol class="route-stops">
        <li v-for="(stop, index) in activeRoute.stops" :key="`${stop.pointId}-${index}`" class="route-stop">
          <span class="route-stop-index">{{ String(index + 1).padStart(2, '0') }}</span>
          <div class="route-stop-body">
            <div class="route-stop-head">
              <h3>{{ stop.name }}</h3>
              <button type="button" class="route-method" @click="emit('open-method', methodOf(stop).id)">
                {{ methodOf(stop).name }} <span aria-hidden="true">↗</span>
              </button>
            </div>
            <p>{{ stop.note }}</p>
          </div>
        </li>
      </ol>
      <p class="route-footnote">站点按步行顺序排列；点击手法名，可以回看这种手法的观察提示。</p>
    </section>
  </div>
</template>

<style>
.routes-view { padding-top:6px; }
.routes-head { display:flex; justify-content:space-between; align-items:end; gap:24px; margin-bottom:40px; }
.routes-head h1 { margin:10px 0 0; }
.routes-head > p { max-width:340px; margin-bottom:6px; }
.route-tabs { display:flex; gap:4px; flex-wrap:wrap; border-bottom:1px solid var(--line); }
.route-tab { display:grid; gap:7px; text-align:left; padding:15px 22px 17px; border:0; border-bottom:2px solid transparent; background:transparent; color:var(--ink-soft); transition:background .15s ease, color .15s ease, border-color .15s ease; }
.route-tab:hover { background:#eee5d4; color:var(--ink); }
.route-tab.active { color:var(--clay); border-bottom-color:var(--clay); }
.route-tab-title { font-size:20px; line-height:1.25; }
.route-tab-meta { color:var(--ink-soft); font:12px system-ui,sans-serif; font-variant-numeric:tabular-nums; }
.route-panel { padding-top:32px; }
.route-subtitle { max-width:640px; margin-bottom:0; font-size:17px; }
.route-stops { display:grid; grid-template-columns:1fr 1fr; gap:14px; margin:34px 0 0; padding:0; list-style:none; }
.route-stop { display:grid; grid-template-columns:auto 1fr; gap:16px; align-items:start; padding:22px 22px 24px; background:#eee5d4; transition:background .15s ease, transform .15s ease; }
.route-stop:hover { background:#e7dac3; transform:translateY(-2px); }
.route-stop-index { padding-top:4px; color:var(--clay); font:600 12px system-ui,sans-serif; letter-spacing:.12em; font-variant-numeric:tabular-nums; }
.route-stop-body { min-width:0; }
.route-stop-head { display:flex; align-items:baseline; justify-content:space-between; gap:12px; }
.route-stop-head h3 { margin:0; font-size:21px; line-height:1.3; font-weight:500; }
.route-method { flex:none; padding:4px 0; border:0; background:none; color:var(--clay); font:600 12px system-ui,sans-serif; transition:color .12s ease; }
.route-method:hover { color:var(--ink); }
.route-stop-body p { margin:9px 0 0; font-size:14px; line-height:1.8; }
.route-footnote { margin:26px 0 0; color:var(--ink-soft); font:12px/1.7 system-ui,sans-serif; }
@media (max-width:900px) {
  .routes-head { flex-direction:column; align-items:flex-start; gap:10px; }
  .routes-head > p { margin-bottom:0; }
  .route-stops { grid-template-columns:1fr; }
}
@media (max-width:560px) {
  .route-tabs { display:grid; grid-template-columns:1fr; gap:0; border-bottom:0; }
  .route-tab { display:flex; justify-content:space-between; align-items:baseline; gap:12px; padding:14px 2px; border-bottom:1px solid var(--line); border-left:2px solid transparent; }
  .route-tab.active { border-bottom-color:var(--line); border-left-color:var(--clay); padding-left:12px; }
  .route-panel { padding-top:24px; }
  .route-stop { padding:18px; gap:12px; }
  .route-stop-head { flex-wrap:wrap; gap:4px 12px; }
  .route-stop-head h3 { font-size:19px; }
}
</style>
