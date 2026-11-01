<script setup>
import { ref, onBeforeUnmount } from 'vue'
defineProps({ speaking: Boolean, compact: Boolean, character: { type: String, default: 'round' } })
const greeting = ref(false)
let timer
function greet() {
  clearTimeout(timer)
  greeting.value = true
  timer = setTimeout(() => { greeting.value = false }, 2500)
}
onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <div class="public-window" :class="{ compact }">
    <button type="button" class="window-button" aria-label="和园林助手打招呼" @click="greet">
      <svg viewBox="0 0 240 240" role="img" aria-label="公开版抽象花窗">
        <circle cx="120" cy="120" r="88" fill="#eeeadd" stroke="#b5a180" stroke-width="12" />
        <path d="M42 150L85 85L135 150L170 105L200 150" fill="#9caf9b" />
        <path d="M40 160Q120 135 200 160V183Q120 220 40 183Z" fill="#b9cfc5" />
        <path d="M70 42V198M170 42V198M32 120H208" stroke="#b5a180" stroke-width="7" fill="none" />
      </svg>
    </button>
    <p v-if="!compact" role="status">{{ greeting ? '你好，一起看看园林吧！' : speaking ? '正在思考你的问题…' : '从一扇窗，看见一座园。' }}</p>
  </div>
</template>

<style scoped>
.public-window{width:100%;text-align:center}.window-button{display:block;width:100%;height:280px;border:0;background:transparent;cursor:pointer}.window-button svg{height:100%;max-width:100%}.window-button:focus-visible{outline:none;box-shadow:0 0 0 1px rgba(23,58,54,.12),0 0 0 4px rgba(23,58,54,.06)}p{font-size:12px;color:var(--ink-soft)}.compact .window-button{height:190px}@media(max-width:700px){.window-button{height:150px}}
</style>
