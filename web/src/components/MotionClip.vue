<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { motionClips } from '../data/motion-clips.js'

const props = defineProps({ clip: { type: String, required: true }, fallback: { type: String, default: '' }, className: { type: String, default: '' } })
const video = ref(null)
const reduced = ref(false)
const failed = ref(false)
let observer
let mediaQuery
const source = computed(() => motionClips[props.clip])
const poster = computed(() => source.value?.poster || props.fallback)
function updateMotion() { reduced.value = Boolean(mediaQuery?.matches); if (reduced.value) video.value?.pause() }
function onLoaded() { if (!reduced.value) video.value?.play().catch(() => {}) }
onMounted(() => {
  mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
  updateMotion()
  mediaQuery.addEventListener?.('change', updateMotion)
  observer = new IntersectionObserver(([entry]) => {
    if (!video.value || reduced.value) return
    if (entry.isIntersecting) video.value.play().catch(() => {})
    else video.value.pause()
  }, { threshold: 0.35, rootMargin: '120px 0px' })
  if (video.value) observer.observe(video.value)
})
onBeforeUnmount(() => { observer?.disconnect(); mediaQuery?.removeEventListener?.('change', updateMotion) })
</script>
<template>
  <div :class="['motion-clip', className]" :aria-label="source?.alt" role="img">
    <video v-if="source && !failed" ref="video" :poster="poster" muted loop playsinline preload="metadata" @loadeddata="onLoaded" @error="failed = true">
      <source :src="source.mobile" type="video/mp4" media="(max-width: 700px)">
      <source :src="source.desktop" type="video/webm">
      <source :src="source.desktop" type="video/mp4">
    </video>
    <img v-else :src="poster || fallback" :alt="source?.alt || ''">
  </div>
</template>
