<script setup>
import { ref, watch } from 'vue'
import { community, methodLabel } from '../utils/community.js'
import { assetUrl } from '../utils/assets.js'
const props = defineProps({ token: String })
const emit = defineEmits(['navigate', 'session-expired'])
const items = ref([]), cursor = ref(null), loading = ref(false), error = ref(''), busy = ref('')
let version = 0
async function load(more = false) {
  const current = more ? version : ++version
  if (!more) { items.value = []; cursor.value = null }
  if (!props.token) return
  loading.value = true; error.value = ''
  try { const result = await community.favorites(more ? cursor.value : null, props.token); if (current === version) { items.value = more ? [...items.value, ...result.items] : result.items; cursor.value = result.nextCursor } }
  catch (e) { if (current === version) { error.value = e.message; if (e.status === 401) emit('session-expired') } }
  finally { if (current === version) loading.value = false }
}
async function remove(item) {
  if (busy.value) return
  busy.value = item.id; error.value = ''
  try { await community.favorite(item.id, false, props.token); items.value = items.value.filter(x => x.id !== item.id) }
  catch (e) { error.value = e.message; if (e.status === 401) emit('session-expired') }
  finally { busy.value = '' }
}
watch(() => props.token, () => load(), { immediate: true })
</script>
<template>
  <section aria-labelledby="favorite-heading">
    <h2 id="favorite-heading">收藏的作品</h2>
    <p v-if="!token">登录后可保存喜欢的作品，并在其他设备查看。 <button class="text-link" type="button" @click="emit('navigate', 'login')">登录 / 注册</button></p>
    <template v-else>
      <p v-if="error" role="alert">{{ error }} <button type="button" class="text-link" @click="load()">重试</button></p>
      <p v-if="loading" role="status">正在打开收藏…</p>
      <p v-else-if="!items.length && !error">还没有收藏作品。去园友作品看看吧。</p>
      <div class="favorites-grid"><article v-for="item in items" :key="item.id" class="favorite-card"><button class="favorite-image" type="button" :aria-label="`查看《${item.title}》`" @click="emit('navigate', 'community', item.id)"><img :src="assetUrl(item.thumbUrl)" :alt="item.title" loading="lazy"></button><div><span class="eyebrow">{{ methodLabel(item.methodId) }}</span><h3>{{ item.title }}</h3><p>{{ item.author.nickname }}</p><button class="text-link" type="button" :disabled="busy === item.id" @click="remove(item)">取消收藏</button></div></article></div>
      <button v-if="cursor && !loading" class="secondary-button" type="button" @click="load(true)">查看更多</button>
    </template>
  </section>
</template>
<style scoped>
.favorites-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:20px; margin:24px 0; }
.favorite-card { background:rgba(23,58,54,.035); }
.favorite-image { display:block; width:100%; padding:0; border:0; background:transparent; }
.favorite-image img { display:block; width:100%; aspect-ratio:4/3; object-fit:cover; }
.favorite-card > div { padding:16px; }
.favorite-card h3 { margin:8px 0; font-size:20px; }
.favorite-card p { margin:0 0 12px; font-size:14px; }
</style>
