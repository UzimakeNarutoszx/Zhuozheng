<script setup>
import { computed, ref, watch } from 'vue'
import { assetUrl, imageSrcset } from '../utils/assets.js'
const props = defineProps({
  src: { type: String, required: true }, alt: { type: String, default: '' },
  className: { type: String, default: '' }, eager: { type: Boolean, default: false },
  sizes: { type: String, default: '' },
  motion: { type: Boolean, default: true }, retryable: { type: Boolean, default: true }
})
const state = ref('loading'), originalOnly = ref(false), attempt = ref(0)
const srcset = computed(() => originalOnly.value ? '' : imageSrcset(props.src))
const resolvedSizes = computed(() => props.sizes || (props.eager ? '(max-width: 900px) 100vw, 60vw' : '(max-width: 560px) 100vw, (max-width: 900px) 50vw, 33vw'))
watch(() => props.src, () => { state.value = 'loading'; originalOnly.value = false; attempt.value += 1 })
function failed() {
  if (srcset.value) { originalOnly.value = true; attempt.value += 1 }
  else state.value = 'error'
}
function retry() { state.value = 'loading'; originalOnly.value = false; attempt.value += 1 }
</script>
<template>
  <div :class="['image-motion', className, { 'image-motion--still': !motion, 'is-loading': state === 'loading', 'is-error': state === 'error' }]" :aria-busy="state === 'loading'">
    <picture :key="`${src}:${attempt}`">
      <source v-if="srcset" type="image/webp" :srcset="srcset" :sizes="resolvedSizes">
      <img :src="assetUrl(src)" :alt="alt" :loading="eager ? 'eager' : 'lazy'" :fetchpriority="eager ? 'high' : 'auto'" decoding="async" @load="state = 'ready'" @error="failed">
    </picture>
    <span v-if="state === 'error'" class="image-status" role="status"><span>图片暂未加载</span><button v-if="retryable" type="button" @click.stop="retry">重新加载</button><small v-else>进入观察后可重新加载</small></span>
    <span v-else-if="state === 'loading'" class="image-loading" aria-hidden="true">正在载入景色</span>
  </div>
</template>
<style scoped>
.image-motion { min-height:80px; }
picture { display:block; width:100%; height:100%; }
.image-motion--still img { animation:none; transform:none; filter:none; }
.is-loading img { opacity:0; }
.is-error picture { visibility:hidden; }
.image-status,.image-loading { position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px; color:var(--ink-soft); font:12px/1.5 system-ui,sans-serif; }
.image-loading { pointer-events:none; }
.image-status button { padding:7px 12px; border:0; color:var(--ink); background:rgba(245,240,229,.9); }
.image-status small { font-size:10px; }
@media(prefers-reduced-motion:reduce) { .image-motion img { animation:none; transform:none; } }
</style>
