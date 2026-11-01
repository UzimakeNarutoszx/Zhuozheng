<script setup>
import { ref, watch } from 'vue'
import { apiRequest } from '../utils/api.js'
import MarkdownAnswer from './MarkdownAnswer.vue'

const props = defineProps({ user: Object, token: String })
const emit = defineEmits(['navigate', 'session-expired'])
const records = ref([]), loading = ref(false), error = ref(''), hasMore = ref(false), expanded = ref(new Set())
let version = 0
const dateFormat = new Intl.DateTimeFormat('zh-CN', { timeZone: 'Asia/Shanghai', dateStyle: 'medium', timeStyle: 'short' })
function dateLabel(value) { return dateFormat.format(new Date(/[zZ]$|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`)) }
function toggle(id) { const next = new Set(expanded.value); next.has(id) ? next.delete(id) : next.add(id); expanded.value = next }
async function loadMore() {
  if (!props.token || loading.value) return
  const current = version, token = props.token
  const before = records.value.at(-1)?.id
  loading.value = true; error.value = ''
  try {
    const data = await apiRequest(`/profile/ai-records?limit=20${before ? `&before=${before}` : ''}`, { token })
    if (current !== version) return
    records.value.push(...data); hasMore.value = data.length === 20
  } catch (failure) {
    if (current !== version) return
    error.value = failure.message
    if (failure.status === 401) emit('session-expired')
  } finally { if (current === version) loading.value = false }
}
watch(() => props.token, () => { version++; records.value = []; expanded.value = new Set(); loading.value = false; error.value = ''; hasMore.value = false; loadMore() }, { immediate: true })
</script>

<template>
  <section class="question-records">
    <div class="records-heading"><div><h2>问答记录</h2><p>问过的问题和梅梅的回答，都保存在你的账号里。</p></div><button class="primary-button" type="button" @click="emit('navigate', user ? 'ask' : 'login')">{{ user ? '继续提问' : '登录查看记录' }}</button></div>
    <p v-if="!user">登录后可以查看自己的问答记录，换一台设备也能接着看。</p>
    <template v-else>
      <p v-if="error" class="records-error" role="alert">{{ error }} <button class="text-link" type="button" @click="loadMore">重新加载</button></p>
      <p v-if="!records.length && !loading && !error">还没有问答记录。带着一个园林问题，去和梅梅聊聊吧。</p>
      <article v-for="record in records" :key="record.id" class="question-record">
        <button class="record-toggle" type="button" :aria-expanded="expanded.has(record.id)" :aria-controls="`answer-${record.id}`" @click="toggle(record.id)">
          <span><time :datetime="`${record.created_at}Z`">{{ dateLabel(record.created_at) }}</time><span v-if="record.status !== 'complete'" class="record-status">回答未完成</span><strong>{{ record.question }}</strong></span><span class="record-indicator" aria-hidden="true">{{ expanded.has(record.id) ? '−' : '+' }}</span>
        </button>
        <div :id="`answer-${record.id}`" class="record-answer" :class="{ expanded: expanded.has(record.id) }" :inert="!expanded.has(record.id)"><div><div class="record-answer-body"><MarkdownAnswer :text="record.answer" /></div></div></div>
      </article>
      <p v-if="loading" role="status">正在读取问答记录…</p>
      <button v-else-if="hasMore && !error" class="secondary-button records-more" type="button" @click="loadMore">查看更多记录</button>
    </template>
  </section>
</template>

<style scoped>
.records-heading { display:flex; justify-content:space-between; align-items:center; gap:24px; margin-bottom:28px; }
.records-heading h2 { font-size:30px; margin:0 0 10px; }
.records-heading p { margin:0; font-size:14px; }
.records-heading button { flex-shrink:0; }
.question-record { box-shadow:0 1px 0 var(--line); }
.record-toggle { display:flex; justify-content:space-between; gap:24px; width:100%; padding:24px 12px; border:0; background:transparent; color:var(--ink); text-align:left; }
.record-toggle:focus-visible { outline:none; box-shadow:0 0 0 1px rgba(23,58,54,.12),0 0 0 4px rgba(23,58,54,.06); }
.record-toggle time,.record-status { font:12px/1.6 system-ui,sans-serif; color:var(--ink-soft); font-variant-numeric:tabular-nums; }
.record-status { margin-left:14px; color:var(--clay); }
.record-toggle strong { display:block; margin-top:8px; font-size:19px; font-weight:500; overflow-wrap:anywhere; text-wrap:pretty; }
.record-indicator { color:var(--clay); font-size:24px; }
.record-answer { display:grid; grid-template-rows:0fr; visibility:hidden; transition:grid-template-rows 150ms,visibility 150ms; }
.record-answer.expanded { grid-template-rows:1fr; visibility:visible; }
.record-answer > div { overflow:hidden; min-height:0; }
.record-answer-body { padding:20px; margin:0 12px 24px; background:rgba(23,58,54,.035); overflow-wrap:anywhere; }
.records-more { margin-top:28px; }
.records-error { color:#9b4d3d; }
@media(max-width:700px) { .records-heading { align-items:flex-start; flex-direction:column; } .record-toggle { padding:20px 0; } .record-toggle strong { font-size:17px; } .record-answer-body { margin:0 0 20px; padding:16px; } }
@media(prefers-reduced-motion:reduce) { .record-answer { transition:none; } }
</style>
