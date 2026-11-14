<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import { gardenPoints } from '../data/garden-points.js'
import { assetUrl } from '../utils/assets.js'
const emit = defineEmits(['open'])
const props = defineProps({
  pointList: { type: Boolean, default: true },
  pointCounts: { type: Object, default: () => ({}) },
  label: { type: String, default: '拙政园真实地图与造景观察点' }
})

/* PURE_HELPERS_START：不依赖 Vue / Leaflet / DOM 的纯函数，tests/garden-map.test.mjs 直接抽取求值测试 */
const TILE_SOURCES = [
  { id: 'osm', name: 'OpenStreetMap', url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', attribution: '&copy; OpenStreetMap contributors', maxZoom: 19 },
  { id: 'esri', name: 'ArcGIS World Street Map', url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', attribution: 'Tiles &copy; Esri', maxZoom: 19 }
]
const TILE_PRECONNECT_HOSTS = ['https://tile.openstreetmap.org', 'https://server.arcgisonline.com']
const TILE_ERROR_LIMIT = 3
const TILE_TIMEOUT_MS = 8000
const GARDEN_CENTER = { lat: 31.3238, lng: 120.6307 }
const FALLBACK_PADDING = 0.35

function createTileState() {
  return { status: 'loading', sourceIndex: 0, backupTried: false, errors: 0, generation: 0 }
}

function gardenBounds(points, padding = FALLBACK_PADDING) {
  if (!Array.isArray(points) || points.length === 0) {
    // 空数据兜底：以园区中心造一个可用包围盒，避免 NaN/Infinity 百分比。
    return { latMin: GARDEN_CENTER.lat - 0.001, latMax: GARDEN_CENTER.lat + 0.001, lngMin: GARDEN_CENTER.lng - 0.001, lngMax: GARDEN_CENTER.lng + 0.001 }
  }
  const lats = points.map(point => point.lat)
  const lngs = points.map(point => point.lng)
  const latMin = Math.min(...lats)
  const latMax = Math.max(...lats)
  const lngMin = Math.min(...lngs)
  const lngMax = Math.max(...lngs)
  const latPad = Math.max((latMax - latMin) * padding, 0.0002)
  const lngPad = Math.max((lngMax - lngMin) * padding, 0.0002)
  return { latMin: latMin - latPad, latMax: latMax + latPad, lngMin: lngMin - lngPad, lngMax: lngMax + lngPad }
}

function clampPercent(value) {
  if (!Number.isFinite(value)) return 50
  return Math.min(100, Math.max(0, value))
}

// 经纬度 -> 百分比：等比例线性映射，北在上、东在右，越界夹到 0-100。
function latLngToPercent(point, bounds) {
  const latSpan = bounds.latMax - bounds.latMin
  const lngSpan = bounds.lngMax - bounds.lngMin
  return {
    x: clampPercent(lngSpan ? ((point.lng - bounds.lngMin) / lngSpan) * 100 : 50),
    y: clampPercent(latSpan ? ((bounds.latMax - point.lat) / latSpan) * 100 : 50)
  }
}

// 失败一次后自动换备用源；备用源也失败才进入 failed。
function failOrFallback(state) {
  if (!state.backupTried) {
    return { ...state, status: 'loading', sourceIndex: 1, backupTried: true, errors: 0 }
  }
  return { ...state, status: 'failed' }
}

function advanceTileState(state, event) {
  if (!state || !event) return state
  if (event.type === 'retry') {
    return { status: 'loading', sourceIndex: 0, backupTried: false, errors: 0, generation: (state.generation || 0) + 1 }
  }
  if (state.status === 'ready') return state
  if (event.type === 'tileload') return state.status === 'loading' ? { ...state, status: 'ready', errors: 0 } : state
  if (state.status !== 'loading') return state
  if (event.type === 'tileerror') {
    const errors = state.errors + 1
    return errors >= TILE_ERROR_LIMIT ? failOrFallback({ ...state, errors }) : { ...state, errors }
  }
  if (event.type === 'timeout' || event.type === 'allerror') return failOrFallback(state)
  return state
}
/* PURE_HELPERS_END */

const mapElement = ref(null)
const tileState = ref(createTileState())
const fallbackBounds = gardenBounds(gardenPoints)
const fallbackPoints = gardenPoints.map(point => ({ point, ...latLngToPercent(point, fallbackBounds) }))
const liveText = computed(() => {
  if (tileState.value.status === 'ready') return '地图已加载'
  if (tileState.value.status === 'failed') return '地图加载失败，可点击重试'
  return tileState.value.backupTried ? '主地图源不可用，正在尝试备用地图源' : '地图加载中'
})
let map
let tileLayer = null
let tileTimer = null
let tileGeneration = 0
const markers = []
function pointCount(pointId) {
  const count = Number(props.pointCounts?.[pointId] || 0)
  return Number.isFinite(count) && count > 0 ? Math.floor(count) : 0
}
function tooltipFor(point) {
  const count = pointCount(point.id)
  return count ? `${point.name} · 我的作品 ${count} 幅` : `${point.name} · 点击查看造景手法`
}
function markerIcon(point) {
  const count = pointCount(point.id)
  const highlight = count ? ' style="border-color:#9c4d35;box-shadow:0 0 0 3px rgba(156,77,53,.18)"' : ''
  const badge = count ? `<i style="display:inline-block;margin-left:5px;padding:0 6px;border-radius:999px;background:#9c4d35;color:#f5f0e5;font:600 10px/1.7 system-ui,sans-serif;font-style:normal;font-variant-numeric:tabular-nums">${count}</i>` : ''
  return L.divIcon({ className: 'garden-pin', html: `<span class="garden-point-image"${highlight}><img src="${assetUrl(point.thumb || point.image)}" alt="${point.name}实景" loading="lazy" decoding="async" width="96" height="58" /></span><b>${point.name}${badge}</b>`, iconSize: [96, 58], iconAnchor: [48, 28] })
}
function refreshMarkers() {
  for (const entry of markers) {
    entry.marker.setIcon(markerIcon(entry.point))
    entry.marker.setTooltipContent(tooltipFor(entry.point))
  }
}
function ensurePreconnect(host) {
  if (typeof document === 'undefined' || !host) return
  if (document.head.querySelector(`link[data-garden-map-preconnect="${host}"]`)) return
  const link = document.createElement('link')
  link.rel = 'preconnect'
  link.href = host
  link.setAttribute('data-garden-map-preconnect', host)
  document.head.appendChild(link)
}
function clearTileTimer() {
  if (tileTimer) {
    clearTimeout(tileTimer)
    tileTimer = null
  }
}
function removeTileLayer() {
  clearTileTimer()
  if (tileLayer && map) map.removeLayer(tileLayer)
  tileLayer = null
}
function startTileCycle(sourceIndex) {
  if (!map) return
  removeTileLayer()
  tileGeneration += 1
  const generation = tileGeneration
  const source = TILE_SOURCES[sourceIndex] || TILE_SOURCES[0]
  let loadedTiles = 0
  const layer = L.tileLayer(source.url, { attribution: source.attribution, maxZoom: source.maxZoom })
  tileLayer = layer
  layer.on('tileload', () => {
    if (generation !== tileGeneration) return
    loadedTiles += 1
    applyTileEvent({ type: 'tileload' })
  })
  layer.on('tileerror', () => {
    if (generation !== tileGeneration) return
    applyTileEvent({ type: 'tileerror' })
  })
  layer.on('load', () => {
    // 全部瓦片结束但一张都没成功，基本可判定该源不可用；避免「无报错也无图」卡在 loading。
    if (generation !== tileGeneration || loadedTiles > 0) return
    applyTileEvent({ type: 'allerror' })
  })
  layer.addTo(map)
  clearTileTimer()
  tileTimer = setTimeout(() => {
    if (generation !== tileGeneration) return
    applyTileEvent({ type: 'timeout' })
  }, TILE_TIMEOUT_MS)
}
function applyTileEvent(event) {
  const previous = tileState.value
  const next = advanceTileState(previous, event)
  if (next === previous) return
  tileState.value = next
  if (next.status === 'ready') {
    clearTileTimer()
    return
  }
  if (next.status === 'failed') {
    clearTileTimer()
    tileGeneration += 1
    removeTileLayer()
    return
  }
  if (event.type === 'retry' || next.sourceIndex !== previous.sourceIndex) startTileCycle(next.sourceIndex)
}
function retryTiles() {
  applyTileEvent({ type: 'retry' })
}
onMounted(() => {
  if (typeof document !== 'undefined') TILE_PRECONNECT_HOSTS.forEach(ensurePreconnect)
  map = L.map(mapElement.value, { scrollWheelZoom: false, zoomControl: true }).setView([GARDEN_CENTER.lat, GARDEN_CENTER.lng], 17)
  L.marker([31.32335, 120.63045], { icon: L.divIcon({ className: 'garden-pin main-pin', html: '<span><i>园</i></span>', iconSize: [40, 40], iconAnchor: [20, 40] }) }).addTo(map).bindTooltip('拙政园', { direction: 'top', offset: [0, -34] })
  gardenPoints.forEach(point => {
    const marker = L.marker([point.lat, point.lng], { icon: markerIcon(point) }).addTo(map)
    marker.on('click', () => emit('open', point.methodId))
    marker.bindTooltip(tooltipFor(point), { direction: 'top', offset: [0, -10] })
    markers.push({ point, marker })
  })
  startTileCycle(0)
})
watch(() => props.pointCounts, refreshMarkers, { deep: true })
onBeforeUnmount(() => {
  tileGeneration += 1
  removeTileLayer()
  markers.length = 0
  if (map) map.remove()
  map = undefined
})
</script>
<template>
  <div class="garden-map-shell">
    <div class="garden-map-frame" :class="{ 'is-degraded': tileState.status === 'failed' }">
      <div ref="mapElement" class="garden-map" role="application" :aria-label="props.label" :aria-hidden="tileState.status === 'failed' ? 'true' : undefined"></div>
      <div v-if="tileState.status === 'loading'" class="map-loading" aria-hidden="true"><span class="map-loading-dot"></span>地图加载中…</div>
      <div v-else-if="tileState.status === 'failed'" class="map-fallback" role="group" aria-label="离线地图示意图">
        <svg class="map-fallback-art" viewBox="0 0 400 260" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">
          <rect width="400" height="260" fill="#efe7d8" />
          <path d="M -10 42 C 80 28, 160 56, 240 40 C 310 26, 370 44, 412 34 L 412 18 L -10 12 Z" fill="#e4dbc9" />
          <path d="M 34 92 H 366 V 220 H 34 Z" fill="none" stroke="#b9c8c2" stroke-width="1.4" stroke-dasharray="6 4" />
          <path d="M 44 148 C 70 104, 152 96, 204 126 C 250 152, 292 138, 348 112 C 344 168, 282 202, 198 200 C 128 198, 72 186, 44 148 Z" fill="#d3e2dd" />
          <path d="M 74 150 C 104 128, 158 122, 206 142" fill="none" stroke="#b7cfc8" stroke-width="1" />
          <path d="M 60 128 C 108 138, 148 160, 196 170 C 244 180, 296 170, 330 148" fill="none" stroke="#b7cfc8" stroke-width="1" opacity=".7" />
          <path d="M 214 92 C 226 112, 240 118, 258 120" fill="none" stroke="#b6a98f" stroke-width="3" stroke-linecap="round" />
          <path d="M 214 92 V 118 M 258 120 V 96" fill="none" stroke="#b6a98f" stroke-width="2" />
          <rect x="64" y="58" width="56" height="26" fill="#e6ddcb" stroke="#c9bba2" stroke-width="1" />
          <path d="M 58 58 L 92 40 L 126 58 Z" fill="#d9cdb6" stroke="#c9bba2" stroke-width="1" />
          <rect x="286" y="62" width="48" height="24" fill="#e6ddcb" stroke="#c9bba2" stroke-width="1" />
          <path d="M 280 62 L 310 46 L 340 62 Z" fill="#d9cdb6" stroke="#c9bba2" stroke-width="1" />
          <circle cx="150" cy="76" r="10" fill="#cdd8c7" />
          <circle cx="166" cy="70" r="6" fill="#cdd8c7" opacity=".8" />
          <circle cx="334" cy="196" r="9" fill="#cdd8c7" />
          <circle cx="58" cy="206" r="7" fill="#cdd8c7" opacity=".8" />
        </svg>
        <div class="map-fallback-panel">
          <p class="map-fallback-note">当前网络无法加载在线地图，以下为园内观察点示意图。</p>
          <button type="button" class="map-fallback-retry" @click="retryTiles">地图加载失败，点击重试</button>
        </div>
        <div class="map-fallback-points">
          <button v-for="item in fallbackPoints" :key="item.point.id" type="button" class="fallback-point" :style="{ left: item.x + '%', top: item.y + '%' }" :aria-label="`${item.point.name}：${item.point.text}`" @click="emit('open', item.point.methodId)">
            <span class="fallback-dot" aria-hidden="true"></span>
            <span class="fallback-label">{{ item.point.name }}</span>
          </button>
        </div>
      </div>
      <p class="map-live sr-only" role="status" aria-live="polite">{{ liveText }}</p>
    </div>
    <div v-if="props.pointList" class="map-point-list" aria-label="造景观察点列表"><button v-for="point in gardenPoints" :key="point.id" type="button" @click="emit('open', point.methodId)"><span>{{ point.name }}</span><small>{{ point.text }}</small></button></div>
  </div>
</template>
<style scoped>
.garden-map-frame { position: relative; }
/* 状态类只加在外层：Leaflet 在 .garden-map 上维护自己的 class/内联样式，Vue 不能去 patch 它。 */
.garden-map-frame.is-degraded .garden-map { pointer-events: none; }
.garden-map-frame.is-degraded :deep(.leaflet-control-container) { display: none; }
.map-loading { position: absolute; left: 14px; bottom: 14px; z-index: 800; display: inline-flex; align-items: center; gap: 8px; padding: 7px 12px; background: rgba(245, 240, 229, .92); color: var(--ink-soft); font: 12px/1.4 system-ui, sans-serif; box-shadow: 0 6px 18px rgba(23, 58, 54, .12); pointer-events: none; }
.map-loading-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--clay); animation: map-loading-pulse 1.2s ease-in-out infinite; }
.map-fallback { position: absolute; inset: 0; z-index: 800; overflow: hidden; background: #efe7d8; }
.map-fallback-art { position: absolute; inset: 0; display: block; width: 100%; height: 100%; }
.map-fallback-panel { position: absolute; z-index: 2; top: 14px; left: 50%; transform: translateX(-50%); display: grid; justify-items: center; gap: 8px; width: min(320px, calc(100% - 28px)); padding: 12px 14px; background: rgba(245, 240, 229, .95); box-shadow: 0 10px 30px rgba(23, 58, 54, .14); }
.map-fallback-note { margin: 0; color: var(--ink-soft); font: 12px/1.6 system-ui, sans-serif; text-align: center; text-wrap: pretty; }
.map-fallback-retry { min-height: 40px; padding: 9px 16px; border: 0; background: var(--ink); color: #fdf8ee; font: 600 13px/1.4 system-ui, sans-serif; transition: background .15s; }
.map-fallback-retry:hover { background: #1e4a44; }
.map-fallback-retry:focus-visible { outline: none; box-shadow: 0 0 0 1px rgba(156, 77, 53, .25), 0 0 0 4px rgba(156, 77, 53, .14); }
.map-fallback-points { position: absolute; inset: 0; z-index: 1; pointer-events: none; }
@media (max-width: 600px) {
  /* 窄屏面板左靠：避开右上角的“窗洞”点位，保证 5 个圆点都看得见 */
  .map-fallback-panel { left: 14px; right: auto; transform: none; width: min(300px, calc(100% - 120px)); }
}
.fallback-point { position: absolute; transform: translate(-50%, -50%); display: grid; justify-items: center; gap: 3px; padding: 4px; border: 0; background: none; color: var(--ink); font: 600 11px/1.2 system-ui, sans-serif; pointer-events: auto; }
.fallback-dot { width: 12px; height: 12px; border-radius: 50%; background: var(--clay); border: 2px solid #f5f0e5; box-shadow: 0 2px 6px rgba(23, 58, 54, .25); }
.fallback-label { padding: 1px 4px; background: rgba(245, 240, 229, .8); white-space: nowrap; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }
@keyframes map-loading-pulse { 0%, 100% { opacity: .35; transform: scale(.8); } 50% { opacity: 1; transform: scale(1); } }
@media (prefers-reduced-motion: reduce) { .map-loading-dot { animation: none; } }
</style>
