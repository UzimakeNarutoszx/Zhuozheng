<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { apiRequest, chatHistory, streamChat } from '../utils/api.js'
import RoundWindow3D from './RoundWindow3D.vue'
import MarkdownAnswer from './MarkdownAnswer.vue'
import { createTextReveal } from '../utils/text-reveal.js'
const props = defineProps({ user: Object, token: String })
const emit = defineEmits(['navigate', 'session-expired'])
const suggestions = ref(['这个网站可以怎么玩？', '框景和漏景有什么区别？', '第一次逛拙政园，应该观察什么？', '怎样用一张照片创作自己的园林？'])
const question = ref(''), messages = ref([]), sending = ref(false), error = ref(''), thread = ref(null), copied = ref(null)
const accountLoading = ref(Boolean(props.token)), accountError = ref(''), quota = ref(null)
let controller = null, copyTimer = null, reveal = null, disposed = false, dayTimer
let followLatest = true
async function loadQuota() {
  if (!props.token || disposed) return
  const data = await apiRequest('/profile/me', { token: props.token })
  if (!disposed) quota.value = data
  return data
}
async function loadAccount() {
  if (!props.token) return
  accountLoading.value = true; accountError.value = ''
  try {
    const [records] = await Promise.all([apiRequest('/profile/ai-records?limit=7', { token: props.token }), loadQuota()])
    if (disposed) return
    messages.value = records.slice().reverse().flatMap(record => [
      { role: 'user', content: record.question },
      { role: 'assistant', content: record.answer, failed: record.status !== 'complete', interrupted: record.status !== 'complete' }
    ])
    scrollToLatest()
  } catch (failure) { if (!disposed) { accountError.value = failure.message; if (failure.status === 401) emit('session-expired') } }
  finally { if (!disposed) accountLoading.value = false }
}
function refreshQuota() { loadQuota().catch(failure => { if (!disposed && failure.status === 401) emit('session-expired') }) }
function scrollToLatest() { nextTick(() => { if (thread.value && followLatest) thread.value.scrollTop = thread.value.scrollHeight }) }
function trackScroll() { const element = thread.value; if (element) followLatest = element.scrollHeight - element.scrollTop - element.clientHeight < 80 }
function stopAnswer() { controller?.abort(); reveal?.flush() }
async function ask(text = question.value) {
  if (sending.value || accountLoading.value || !text.trim()) return
  if (!props.user) { emit('navigate', 'login'); return }
  sending.value = true
  try {
    const current = await loadQuota()
    if (disposed) return
    if (!current || current.ai_remaining <= 0) { error.value = '今天的 20 条问答额度已用完，北京时间明天零点恢复。'; return }
  } catch (failure) { if (!disposed) { error.value = failure.message; if (failure.status === 401) emit('session-expired') }; return }
  finally { if (!disposed) sending.value = false }
  if (disposed) return
  const content = text.trim()
  const history = chatHistory(messages.value)
  question.value = ''; error.value = ''; sending.value = true; followLatest = true
  messages.value = messages.value.slice(-12)
  copied.value = null
  messages.value.push({ role: 'user', content })
  const response = { role: 'assistant', content: '', failed: false, streaming: true }
  messages.value.push(response)
  const index = messages.value.length - 1
  controller = new AbortController(); scrollToLatest()
  reveal = createTextReveal(text => { if (!disposed) { messages.value[index].content = text; scrollToLatest() } })
  try {
    await streamChat(content, history, { token: props.token, signal: controller.signal, onDelta: delta => reveal.push(delta) })
    await reveal.finish()
    if (disposed) return
    if (!messages.value[index].content) throw new Error('梅梅还没有回答，请再试一次。')
  } catch (failure) {
    if (disposed) return
    reveal.flush()
    if (failure.name !== 'AbortError') { messages.value[index].failed = true; error.value = failure.message; if (failure.status === 401) emit('session-expired') }
    else { messages.value[index].failed = true; messages.value[index].interrupted = true; error.value = messages.value[index].content ? '回答已停止，已生成的内容保留。你可以重新提问。' : '已停止，可以重新提问。' }
  } finally { if (!disposed) { messages.value[index].streaming = false; sending.value = false; scrollToLatest(); refreshQuota() }; reveal?.cancel(); reveal = null; controller = null }
}
function retry() { if (sending.value) return; const previous = [...messages.value].reverse().find(item => item.role === 'user'); if (!previous) return; const content = previous.content; if (messages.value.at(-1)?.failed && !messages.value.at(-1)?.content) { messages.value.pop(); messages.value.pop() }; ask(content) }
async function copy(text, index) {
  try { await navigator.clipboard.writeText(text); copied.value = index; clearTimeout(copyTimer); copyTimer = setTimeout(() => { copied.value = null }, 2500) } catch { error.value = '复制失败，请长按选中回答后复制。' }
}
function handleKeydown(event) { if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); ask() } }
onMounted(() => {
  loadAccount()
  apiRequest('/content/ask/bootstrap').then(data => { if (!disposed && Array.isArray(data.prompts) && data.prompts.length) suggestions.value = data.prompts.map(item => typeof item === 'string' ? item : item.question || item.title).filter(Boolean) }).catch(() => {})
  window.addEventListener('focus', refreshQuota)
  dayTimer = setInterval(() => { if (quota.value && quota.value.ai_usage_day !== new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai' }).format(new Date())) refreshQuota() }, 60000)
})
onBeforeUnmount(() => { disposed = true; controller?.abort(); reveal?.cancel(); clearTimeout(copyTimer); clearInterval(dayTimer); window.removeEventListener('focus', refreshQuota) })
</script>

<template>
  <section class="page ask-page"><div class="ask-companion"><span class="eyebrow">园中有问，梅梅来答</span><h1>和梅梅<br>聊聊园林。</h1><div class="ask-portrait"><RoundWindow3D :speaking="sending" /></div><p>我是梅梅。网站怎么用、造景手法怎么看、拙政园有什么值得留意，都可以问我。</p><span class="ask-disclosure">AI 回答供观察与学习参考，游园信息请以园方公布为准。</span></div><div class="ask-conversation"><header class="ask-header"><div><strong>梅梅</strong><span>{{ sending ? (messages.at(-1)?.content ? '正在回答…' : '正在思考…') : '陪你从一扇窗，看懂一座园' }}</span></div><div class="ask-header-actions"><button class="text-link" type="button" @click="emit('navigate', 'mine', 'records')">全部记录</button><button v-if="messages.length" class="text-link" type="button" :disabled="sending || accountLoading" @click="messages = []; error = ''">新对话</button></div></header><div class="ask-history-notice"><span>仅显示最近 7 组问答，完整记录在“我的”中查看。</span><span v-if="user && quota" class="ask-quota" role="status">今日已用 {{ quota.ai_used_today }} / {{ quota.ai_daily_limit }} 条，剩余 {{ quota.ai_remaining }} 条 · 北京时间零点恢复</span></div><p v-if="accountLoading" class="ask-account-status" role="status">正在读取最近的问答…</p><p v-if="accountError" class="ask-error" role="alert">{{ accountError }} <button class="text-link" type="button" @click="loadAccount">重新加载</button></p><div ref="thread" class="ask-thread" @scroll="trackScroll" aria-live="polite" aria-relevant="additions text"><div v-if="!messages.length && !accountLoading" class="ask-welcome"><h2>今天，想从哪里看起？</h2><p>选一个问题，或把你的发现告诉我。</p><div class="ask-suggestions"><button v-for="item in suggestions" :key="item" type="button" :disabled="sending || accountLoading || (user && quota?.ai_remaining === 0)" @click="ask(item)">{{ item }}<span aria-hidden="true">↗</span></button></div></div><article v-for="(message, index) in messages" :key="index" :class="['ask-message', `ask-message--${message.role}`]"><span class="ask-speaker">{{ message.role === 'user' ? '你' : '梅梅' }}</span><div class="ask-message-body"><MarkdownAnswer v-if="message.role === 'assistant' && message.content" :text="message.content" :streaming="message.streaming" /><p v-else-if="message.content">{{ message.content }}</p><p v-else class="ask-thinking">{{ message.failed ? '这次回答没有完成。' : '让我想一想…' }}</p><button v-if="message.role === 'assistant' && message.content && !sending" class="ask-copy" type="button" @click="copy(message.content, index)">{{ copied === index ? '✓ 已复制' : '复制回答' }}</button></div></article></div><div v-if="error" class="ask-error" role="alert"><span>{{ error }}</span><button v-if="user" type="button" class="text-link" @click="retry">重新提问</button><button v-else type="button" class="text-link" @click="emit('navigate', 'login')">重新登录</button></div><form class="ask-composer" @submit.prevent="ask()"><template v-if="user"><label for="garden-question" class="sr-only">向梅梅提问</label><textarea id="garden-question" v-model="question" rows="2" maxlength="2000" placeholder="问问梅梅，或分享你看到的景色…" :disabled="sending || accountLoading || quota?.ai_remaining === 0" @keydown="handleKeydown"></textarea><div class="ask-composer-actions"><span>Enter 发送 · Shift + Enter 换行</span><button v-if="sending" type="button" class="secondary-button" @click="stopAnswer">停止回答</button><button v-else type="submit" class="primary-button" :disabled="!question.trim() || accountLoading || quota?.ai_remaining === 0">{{ quota?.ai_remaining === 0 ? '今日额度已用完' : '发送' }} <span aria-hidden="true">↗</span></button></div></template><div v-else class="ask-login"><div><strong>登录后，开始和梅梅对话</strong><p>你的作品和园中疑问，都值得慢慢聊。</p></div><button type="button" class="primary-button" @click="emit('navigate', 'login')">登录 / 注册</button></div></form></div></section>
</template>

<style scoped>
.ask-page { display:grid; grid-template-columns:340px minmax(0,1fr); gap:64px; max-width:1360px; padding-top:48px; padding-bottom:64px; align-items:start; }
.ask-companion h1 { font-size:clamp(42px,4.5vw,62px); margin:18px 0 0; }
.ask-portrait { margin:20px 0 8px; position:relative; display:grid; place-items:center; }
.ask-portrait img { position:relative; width:260px; height:280px; object-fit:contain; }
.ask-companion > p { max-width:300px; font-size:15px; }
.ask-disclosure { color:var(--ink-soft); opacity:.8; font:11px/1.8 system-ui,sans-serif; display:block; max-width:290px; }
.ask-conversation { display:flex; flex-direction:column; min-height:640px; height:calc(100dvh - 190px); max-height:900px; background:rgba(255,255,255,.24); box-shadow:0 12px 40px rgba(23,58,54,.055); }
.ask-header { padding:22px 26px; display:flex; justify-content:space-between; align-items:center; box-shadow:0 1px 0 rgba(23,58,54,.07); gap:16px; }
.ask-header strong { display:block; font-size:19px; font-weight:500; }
.ask-header span { display:block; margin-top:6px; font-size:12px; color:var(--ink-soft); }
.ask-header-actions { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:16px; }
.ask-history-notice { display:grid; gap:6px; padding:12px 26px; color:var(--ink-soft); background:rgba(23,58,54,.025); font:12px/1.7 system-ui,sans-serif; }
.ask-quota { font-variant-numeric:tabular-nums; }
.ask-account-status { padding:12px 26px; margin:0; font-size:13px; }
.ask-thread { flex:1; overflow-y:auto; padding:30px 26px; }
.ask-welcome { padding:32px 0; }
.ask-welcome h2 { font-size:30px; line-height:1.4; }
.ask-welcome > p { font-size:14px; }
.ask-suggestions { display:grid; gap:10px; margin-top:28px; }
.ask-suggestions button { display:flex; justify-content:space-between; gap:14px; text-align:left; padding:15px 16px; border:0; background:rgba(23,58,54,.035); color:var(--ink-soft); font-size:14px; line-height:1.6; transition:background .15s; }
.ask-suggestions button:hover { background:rgba(23,58,54,.07); }
.ask-suggestions span { color:var(--clay); }
.ask-message { display:grid; grid-template-columns:32px minmax(0,1fr); gap:12px; margin-bottom:25px; }
.ask-speaker { color:var(--clay); font:12px/2 system-ui,sans-serif; padding-top:10px; }
.ask-message-body { min-width:0; padding:12px 16px; background:rgba(23,58,54,.035); overflow-wrap:anywhere; }
.ask-message--user .ask-message-body { background:rgba(156,77,53,.055); }
.ask-message-body p { margin:0; font-size:15px; line-height:1.9; white-space:pre-wrap; }
.ask-thinking { opacity:.65; }
.ask-copy { margin-top:14px; border:0; padding:0; color:var(--ink-soft); background:transparent; font:11px system-ui,sans-serif; }
.ask-error { padding:12px 26px; background:rgba(156,77,53,.05); color:#9b4d3d; font-size:13px; display:flex; flex-wrap:wrap; gap:12px; line-height:1.6; }
.ask-composer { padding:18px 22px; background:rgba(23,58,54,.025); }
.ask-composer textarea { border:0; background:rgba(255,255,255,.45); font-size:14px; resize:none; min-height:80px; }
.ask-composer-actions { display:flex; justify-content:space-between; align-items:center; gap:14px; margin-top:12px; }
.ask-composer-actions > span { color:var(--ink-soft); font-size:10px; }
.ask-composer-actions button { min-height:40px; padding:10px 18px; }
.ask-login { display:flex; gap:20px; align-items:center; justify-content:space-between; }
.ask-login strong { font-size:15px; font-weight:500; }
.ask-login p { font-size:12px; margin:6px 0 0; }
.ask-login button { flex-shrink:0; }
button:disabled { opacity:.5; cursor:default; }
.sr-only { position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; border:0; }
@media (max-width:1000px) { .ask-page { grid-template-columns:240px minmax(0,1fr); gap:30px; } .ask-portrait img { width:210px; height:230px; } }
@media (max-width:700px) { .ask-page { grid-template-columns:1fr; gap:24px; padding-top:30px; } .ask-companion { position:relative; padding-right:110px; min-height:150px; } .ask-companion h1 { font-size:36px; margin-top:10px; } .ask-companion h1 br { display:none; } .ask-portrait { position:absolute; right:-10px; top:10px; margin:0; } .ask-portrait img { width:130px; height:155px; } .ask-companion > p { font-size:13px; margin-top:15px; } .ask-disclosure { display:none; } .ask-conversation { height:620px; min-height:520px; max-height:none; } .ask-header { padding:18px; } .ask-thread { padding:24px 16px; } .ask-composer { padding:16px; } .ask-message { grid-template-columns:26px minmax(0,1fr); gap:6px; } .ask-message-body { min-width:0; padding:10px 12px; } .ask-login { align-items:flex-start; flex-direction:column; gap:14px; } .ask-composer-actions > span { font-size:9px; } }
@media (prefers-reduced-motion:reduce) { .ask-thread { scroll-behavior:auto; } }
</style>
