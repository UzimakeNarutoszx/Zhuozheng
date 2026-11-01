<script setup>
import { computed, ref, watch } from 'vue'
import RoundWindow3D from './RoundWindow3D.vue'
import { assetUrl } from '../utils/assets.js'

const props = defineProps({
  mascot: { type: Object, required: true },
  placement: { type: String, default: 'edge' }
})
const emit = defineEmits(['navigate'])
const messageIndex = ref(0)
const open = ref(false)
const message = computed(() => props.mascot.messages[messageIndex.value % props.mascot.messages.length])
watch(() => props.mascot.id, () => { messageIndex.value = 0; open.value = false })
function toggle() {
  if (open.value) messageIndex.value = (messageIndex.value + 1) % props.mascot.messages.length
  else open.value = true
}
function navigate() { if (props.mascot.target) { emit('navigate', props.mascot.target); open.value = false } }
</script>

<template>
  <aside :class="['mascot-guide', `mascot-guide--${placement}`, { 'is-open': open }]">
    <div v-if="open" class="mascot-guide__copy">
      <span class="mascot-guide__name">{{ mascot.name }}</span>
      <p aria-live="polite">{{ message }}</p>
      <div class="mascot-guide__actions">
        <button v-if="mascot.target && mascot.actionLabel" class="mascot-guide__action" type="button" @click="navigate">{{ mascot.actionLabel }} <span aria-hidden="true">↗</span></button>
        <button class="mascot-guide__close" type="button" aria-label="收起吉祥物提示" @click="open = false">收起</button>
      </div>
    </div>
    <component :is="mascot.model ? 'div' : 'button'" class="mascot-guide__figure" :type="mascot.model ? undefined : 'button'" :aria-label="mascot.model ? undefined : open ? `${mascot.name}：点击换一句提示` : `${mascot.name}：展开导览提示`" :aria-expanded="mascot.model ? undefined : open" @click="toggle">
      <RoundWindow3D v-if="mascot.model" :key="mascot.model" :character="mascot.model" compact />
      <img v-else :src="assetUrl(mascot.asset)" :alt="mascot.alt">
    </component>
  </aside>
</template>

<style scoped>
.mascot-guide { position:fixed; z-index:20; right:0; bottom:18vh; width:min(330px, calc(100vw - 20px)); min-height:190px; pointer-events:none; }
.mascot-guide--left { left:0; right:auto; bottom:28vh; }
.mascot-guide--left .mascot-guide__figure { left:0; right:auto; }
.mascot-guide--left .mascot-guide__copy { left:112px; right:auto; }
.mascot-guide--right-mid { bottom:42vh; }
.mascot-guide--right-bottom { bottom:18vh; }
.mascot-guide { --peek-angle:-8deg; --open-angle:-3deg; --open-shift:-6px; }
.mascot-guide--left { --peek-angle:8deg; --open-angle:3deg; --open-shift:6px; }
.mascot-guide__figure { position:absolute; z-index:1; right:0; bottom:0; width:164px; height:190px; padding:0; border:0; background:transparent; cursor:pointer; pointer-events:auto; transform:translateX(50%); transition:transform .15s; }
.mascot-guide__figure img { display:block; width:100%; height:100%; object-fit:contain; filter:drop-shadow(0 5px 4px rgba(23,58,54,.1)); transform-origin:50% 100%; animation:mascot-breathe 3.8s ease-in-out infinite; transition:transform .2s ease; }
.mascot-guide__figure { transform:translateX(50%) rotate(var(--peek-angle)); }
.mascot-guide--left .mascot-guide__figure { transform:translateX(-50%) rotate(var(--peek-angle)); }
.mascot-guide:focus-within .mascot-guide__figure,.mascot-guide.is-open .mascot-guide__figure { transform:translateX(var(--open-shift)) rotate(var(--open-angle)); }
@media (hover:hover) { .mascot-guide:hover .mascot-guide__figure { transform:translateX(var(--open-shift)) rotate(var(--open-angle)); } }
.mascot-guide__figure:hover img,.mascot-guide__figure:focus-visible img { transform:translateY(-3px) rotate(-4deg); animation-play-state:paused; }
.mascot-guide__copy { position:absolute; z-index:3; right:142px; bottom:16px; width:min(220px, calc(100vw - 162px)); padding:12px 14px; background:rgba(238,229,212,.97); border:1px solid rgba(23,58,54,.14); box-shadow:0 8px 24px rgba(23,58,54,.12); pointer-events:auto; animation:mascot-bubble-in .22s cubic-bezier(.2,.8,.2,1) both; }
.mascot-guide__name { display:block; color:var(--clay); font:600 11px/1.4 system-ui,sans-serif; letter-spacing:.08em; }
.mascot-guide__copy p { margin:6px 0 10px; color:var(--ink); font-size:13px; line-height:1.55; }
.mascot-guide__actions { display:flex; align-items:center; justify-content:space-between; gap:12px; }
.mascot-guide__action { border:0; padding:0; background:none; color:var(--clay); font:600 12px/1.4 system-ui,sans-serif; }
.mascot-guide__action span { display:inline-block; transform:translateY(.08em); }
.mascot-guide__close { border:0; padding:6px 8px; color:var(--ink-soft); background:rgba(23,58,54,.06); cursor:pointer; font:11px system-ui,sans-serif; }
@keyframes mascot-breathe { 0%,100% { transform:translateY(0) rotate(-3deg); } 50% { transform:translateY(-3px) rotate(-2.2deg); } }
@keyframes mascot-bubble-in { from { opacity:0; transform:translateX(8px); } to { opacity:1; transform:translateX(0); } }
@media (max-width:560px) { .mascot-guide { bottom:16vh; min-height:142px; } .mascot-guide__figure { width:116px; height:142px; } .mascot-guide__copy { right:106px; bottom:8px; width:min(210px, calc(100vw - 126px)); padding:10px 11px; } .mascot-guide--left .mascot-guide__copy { left:106px; right:auto; } }
@media (prefers-reduced-motion:reduce) { .mascot-guide__figure,.mascot-guide__figure img { transition:none; animation:none; } .mascot-guide__copy { animation:none; } }
</style>
