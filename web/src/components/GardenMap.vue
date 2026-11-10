<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import L from 'leaflet'
import { gardenPoints } from '../data/garden-points.js'
import { assetUrl } from '../utils/assets.js'
const emit = defineEmits(['open'])
const props = defineProps({ pointList: { type: Boolean, default: true } })
const mapElement = ref(null)
let map
onMounted(() => {
  const center = [31.3238, 120.6307]
  map = L.map(mapElement.value, { scrollWheelZoom: false, zoomControl: true }).setView(center, 17)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap contributors', maxZoom: 19 }).addTo(map)
  L.marker([31.32335, 120.63045], { icon: L.divIcon({ className: 'garden-pin main-pin', html: '<span><i>园</i></span>', iconSize: [40, 40], iconAnchor: [20, 40] }) }).addTo(map).bindTooltip('拙政园', { direction: 'top', offset: [0, -34] })
  gardenPoints.forEach(point => {
    const marker = L.marker([point.lat, point.lng], { icon: L.divIcon({ className: 'garden-pin', html: `<span class="garden-point-image"><img src="${assetUrl(point.thumb || point.image)}" alt="${point.name}实景" loading="lazy" decoding="async" width="96" height="58" /></span><b>${point.name}</b>`, iconSize: [96, 58], iconAnchor: [48, 28] }) }).addTo(map)
    marker.on('click', () => emit('open', point.methodId))
    marker.bindTooltip(`${point.name} · 点击查看造景手法`, { direction: 'top', offset: [0, -10] })
  })
})
onBeforeUnmount(() => { if (map) map.remove() })
</script>
<template><div class="garden-map-shell"><div ref="mapElement" class="garden-map" role="application" aria-label="拙政园真实地图与造景观察点"></div><div v-if="props.pointList" class="map-point-list" aria-label="造景观察点列表"><button v-for="point in gardenPoints" :key="point.id" type="button" @click="emit('open', point.methodId)"><span>{{ point.name }}</span><small>{{ point.text }}</small></button></div></div></template>
