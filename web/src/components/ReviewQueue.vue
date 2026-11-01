<script setup>
import { ref, watch } from 'vue'
import { community, formatDate, methodLabel } from '../utils/community.js'
const props = defineProps({ token: String })
const emit = defineEmits(['session-expired'])
const type = ref('work'), items = ref([]), loading = ref(false), error = ref(''), busy = ref(null)
const tabs = [{ id: 'work', label: '待审作品' }, { id: 'comment', label: '待审评论' }, { id: 'report', label: '举报' }]
let version = 0
async function load() {
  const current = ++version
  loading.value = true; error.value = ''; items.value = []
  try { const data = await community.queue(type.value, props.token); if (current === version) items.value = data.items }
  catch (e) { if (current === version) { error.value = e.message; if (e.status === 401) emit('session-expired') } }
  finally { if (current === version) loading.value = false }
}
async function act(item, run) {
  busy.value = item.id; error.value = ''
  try { await run(); items.value = items.value.filter(entry => entry.id !== item.id) } catch (e) { error.value = e.message } finally { busy.value = null }
}
function reviewWork(item, action) {
  const reason = action === 'reject' ? window.prompt('请写下不通过的原因，作者会看到：', '内容与园林观察无关') : ''
  if (reason === null) return
  act(item, () => community.reviewWork(item.id, action, reason, props.token))
}
watch(type, load, { immediate: true })
</script>

<template>
  <div class="review-queue">
    <div class="review-tabs" role="group" aria-label="审核类型"><button v-for="tab in tabs" :key="tab.id" type="button" :class="['chip', { selected: type === tab.id }]" :aria-pressed="type === tab.id" @click="type = tab.id">{{ tab.label }}</button><button type="button" class="text-link" :disabled="loading" @click="load">刷新</button></div>
    <p v-if="error" class="cloud-error" role="alert">{{ error }}</p>
    <p v-if="loading" role="status">正在读取审核队列…</p>
    <p v-else-if="!items.length && !error" class="review-empty">队列是空的，暂时没有需要处理的内容。</p>
    <ul class="review-list">
      <li v-for="item in items" :key="item.id">
        <template v-if="type === 'work'">
          <img :src="item.imageUrl" :alt="item.title" loading="lazy">
          <div><span class="eyebrow">{{ methodLabel(item.methodId) }}</span><h3>{{ item.title }}</h3><p class="review-meta">{{ item.author.nickname }}</p><p v-if="item.note">{{ item.note }}</p></div>
          <div class="review-actions"><button class="primary-button" type="button" :disabled="busy === item.id" @click="reviewWork(item, 'approve')">通过</button><button class="secondary-button" type="button" :disabled="busy === item.id" @click="reviewWork(item, 'reject')">不通过</button></div>
        </template>
        <template v-else-if="type === 'comment'">
          <div class="review-wide"><p class="review-meta">{{ item.author.nickname }} 评论《<a :href="`#community/${item.workId}`">{{ item.workTitle }}</a>》· {{ formatDate(item.createdAt) }}</p><p>{{ item.content }}</p></div>
          <div class="review-actions"><button class="primary-button" type="button" :disabled="busy === item.id" @click="act(item, () => community.reviewComment(item.id, 'approve', token))">公开</button><button class="secondary-button" type="button" :disabled="busy === item.id" @click="act(item, () => community.reviewComment(item.id, 'reject', token))">隐藏</button></div>
        </template>
        <template v-else>
          <div class="review-wide"><p class="review-meta">举报{{ item.targetType === 'work' ? '作品' : '评论' }} · {{ formatDate(item.createdAt) }}<template v-if="item.targetType === 'work'"> · <a :href="`#community/${item.targetId}`">查看</a></template></p><p><strong>{{ item.preview }}</strong></p><p>原因：{{ item.reason }}</p></div>
          <div class="review-actions"><button class="primary-button" type="button" :disabled="busy === item.id" @click="act(item, () => community.resolveReport(item.id, 'remove', token))">{{ item.targetType === 'work' ? '下架作品' : '隐藏评论' }}</button><button class="secondary-button" type="button" :disabled="busy === item.id" @click="act(item, () => community.resolveReport(item.id, 'dismiss', token))">驳回举报</button></div>
        </template>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.review-tabs { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-bottom:24px; }
.chip { border:0; padding:8px 16px; min-height:40px; border-radius:999px; background:rgba(23,58,54,.04); color:var(--ink-soft); font:14px system-ui,sans-serif; transition:background-color .15s, color .15s; }
.chip.selected { background:var(--ink); color:#fdf8ee; }
.review-empty { font-size:14px; }
.review-list { list-style:none; padding:0; margin:0; display:grid; gap:16px; }
.review-list li { display:grid; grid-template-columns:160px 1fr auto; gap:22px; align-items:start; padding:18px; background:rgba(23,58,54,.03); }
.review-list img { width:160px; aspect-ratio:4/3; object-fit:cover; display:block; }
.review-list h3 { font-size:20px; margin:6px 0; }
.review-list p { margin:4px 0; font-size:14px; overflow-wrap:anywhere; }
.review-wide { grid-column:1 / 3; }
.review-meta { color:var(--ink-soft); font:13px system-ui,sans-serif; }
.review-actions { display:flex; flex-direction:column; gap:8px; }
@media (max-width:700px) { .review-list li { grid-template-columns:1fr; } .review-list img { width:100%; } .review-wide { grid-column:auto; } .review-actions { flex-direction:row; } }
</style>
