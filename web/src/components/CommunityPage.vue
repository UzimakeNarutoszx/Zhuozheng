<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import { community, formatDate, likePop, methodFilters, methodLabel, shareUrl } from '../utils/community.js'
const props = defineProps({ user: Object, token: String, communityId: String })
const emit = defineEmits(['navigate', 'session-expired'])

// ---- feed ----
const method = ref(''), sort = ref('latest'), items = ref([]), nextCursor = ref(null), feedLoading = ref(false), feedError = ref('')
let feedVersion = 0
async function loadFeed(more = false) {
  const version = more ? feedVersion : ++feedVersion
  if (!more) { items.value = []; nextCursor.value = null }
  feedLoading.value = true; feedError.value = ''
  try {
    const data = await community.feed({ method: method.value, sort: sort.value, cursor: more ? nextCursor.value : '' }, props.token)
    if (version !== feedVersion) return
    items.value = more ? [...items.value, ...data.items] : data.items; nextCursor.value = data.nextCursor
  } catch (error) { if (version === feedVersion) feedError.value = error.message } finally { if (version === feedVersion) feedLoading.value = false }
}

// ---- detail ----
const work = ref(null), detailLoading = ref(false), detailError = ref(''), comments = ref([]), commentsCursor = ref(null), draft = ref(''), posting = ref(false), notice = ref(''), liking = ref(new Set())
let detailVersion = 0
async function loadDetail(id) {
  const version = ++detailVersion
  work.value = null; comments.value = []; detailError.value = ''; notice.value = ''; draft.value = ''
  detailLoading.value = true
  try {
    const [detail, list] = await Promise.all([community.detail(id, props.token), community.comments(id, null, props.token)])
    if (version !== detailVersion) return
    work.value = detail; comments.value = list.items; commentsCursor.value = list.nextCursor
  } catch (error) { if (version === detailVersion) detailError.value = error.message } finally { if (version === detailVersion) detailLoading.value = false }
}
async function moreComments() {
  const id = work.value.id, data = await community.comments(id, commentsCursor.value, props.token).catch(error => { notice.value = error.message })
  if (data && work.value?.id === id) { comments.value = [...comments.value, ...data.items]; commentsCursor.value = data.nextCursor }
}
function requireLogin() { if (props.user) return true; emit('navigate', 'login'); return false }
function failed(error) { notice.value = error.message; if (error.status === 401) emit('session-expired') }

async function toggleLike(target, event) {
  if (!requireLogin() || liking.value.has(target.id)) return
  const next = !target.likedByMe
  // Optimistic update; the server's count wins once it answers.
  Object.assign(target, { likedByMe: next, likeCount: target.likeCount + (next ? 1 : -1) })
  if (next) likePop(event?.currentTarget?.querySelector('.like-mark'))
  liking.value = new Set([...liking.value, target.id])
  try { const data = await community.like(target.id, next, props.token); Object.assign(target, { likedByMe: data.liked, likeCount: data.likeCount }); syncFeed(target) }
  catch (error) { Object.assign(target, { likedByMe: !next, likeCount: target.likeCount + (next ? -1 : 1) }); failed(error); if (!props.communityId) feedError.value = error.message }
  finally { const rest = new Set(liking.value); rest.delete(target.id); liking.value = rest }
}
function syncFeed(target) { const card = items.value.find(item => item.id === target.id); if (card && card !== target) Object.assign(card, { likedByMe: target.likedByMe, likeCount: target.likeCount }) }

async function submitComment() {
  const content = draft.value.trim()
  if (!content || posting.value || !requireLogin()) return
  posting.value = true; notice.value = ''
  try {
    const comment = await community.comment(work.value.id, content, props.token)
    comments.value = [comment, ...comments.value]; draft.value = ''
    if (comment.status === 'visible') work.value.commentCount += 1
    else notice.value = '评论已提交，审核通过后其他人才能看到。'
  } catch (error) { failed(error) } finally { posting.value = false }
}
function canDelete(comment) { return props.user && (comment.author.id === props.user.id || work.value?.author.id === props.user.id || props.user.role === 'admin') }
async function deleteComment(comment) {
  if (!window.confirm('确定删除这条评论吗？')) return
  try { await community.removeComment(comment.id, props.token); comments.value = comments.value.filter(item => item.id !== comment.id); if (comment.status === 'visible') work.value.commentCount = Math.max(0, work.value.commentCount - 1) } catch (error) { failed(error) }
}
async function report(type, id) {
  if (!requireLogin()) return
  const reason = window.prompt(type === 'work' ? '请简要说明举报这幅作品的原因：' : '请简要说明举报这条评论的原因：')
  if (reason === null) return
  if (!reason.trim()) { notice.value = '请填写举报原因。'; return }
  try { notice.value = (await community.report(type, id, reason.trim().slice(0, 200), props.token)).message } catch (error) { failed(error) }
}

// Copy feedback: one timer, reset on every click, back to idle after 2.5s.
const copied = ref(false)
let copyTimer = 0
async function share() {
  const url = shareUrl(work.value.id)
  try { await navigator.clipboard.writeText(url) } catch { window.prompt('复制这个链接分享给朋友：', url); return }
  copied.value = true; clearTimeout(copyTimer); copyTimer = setTimeout(() => { copied.value = false }, 2500)
}
onBeforeUnmount(() => clearTimeout(copyTimer))

watch([method, sort], () => loadFeed())
// A new token changes likedByMe and pending visibility, so reload what is on screen.
watch(() => props.token, () => { if (props.communityId) loadDetail(props.communityId); loadFeed() })
watch(() => props.communityId, id => { if (id) loadDetail(id); else if (!items.value.length) loadFeed() }, { immediate: true })
</script>

<template>
  <section class="page community-page">
    <template v-if="!communityId">
      <div class="section-head page-heading"><div><span class="eyebrow">VIEWS FROM VISITORS</span><h1>园友作品</h1></div><p>每一幅都经过审核后公开。看看别人是怎样给园子取景的。</p></div>
      <div class="community-toolbar">
        <div class="chip-row" role="group" aria-label="按造景手法筛选"><button v-for="item in methodFilters" :key="item.id" type="button" :class="['chip', { selected: method === item.id }]" :aria-pressed="method === item.id" @click="method = item.id">{{ item.label }}</button></div>
        <div class="chip-row" role="group" aria-label="排序"><button type="button" :class="['chip', { selected: sort === 'latest' }]" :aria-pressed="sort === 'latest'" @click="sort = 'latest'">最新</button><button type="button" :class="['chip', { selected: sort === 'popular' }]" :aria-pressed="sort === 'popular'" @click="sort = 'popular'">最受喜欢</button></div>
      </div>
      <p v-if="feedError" class="cloud-error" role="alert">{{ feedError }} <button class="text-link" type="button" @click="loadFeed()">重新加载</button></p>
      <div v-if="items.length" class="community-grid">
        <article v-for="item in items" :key="item.id" class="community-card">
          <a class="community-thumb" :href="`#community/${item.id}`" :aria-label="`查看《${item.title}》`"><img :src="item.thumbUrl" :alt="item.title" loading="lazy" decoding="async"></a>
          <div class="community-card-body">
            <span class="eyebrow">{{ methodLabel(item.methodId) }}</span>
            <h3><a :href="`#community/${item.id}`">{{ item.title }}</a></h3>
            <div class="community-meta"><span>{{ item.author.nickname }} · {{ formatDate(item.publishedAt) }}</span><span class="community-stats"><button type="button" :class="['like-button', { liked: item.likedByMe }]" :aria-pressed="item.likedByMe" :aria-label="item.likedByMe ? '取消喜欢' : '喜欢'" :disabled="liking.has(item.id)" @click="toggleLike(item, $event)"><span class="like-mark" aria-hidden="true">{{ item.likedByMe ? '♥' : '♡' }}</span><span class="num">{{ item.likeCount }}</span></button><span class="comment-count"><span aria-hidden="true">◌</span> <span class="num">{{ item.commentCount }}</span><span class="sr-only">条评论</span></span></span></div>
          </div>
        </article>
      </div>
      <p v-if="feedLoading" class="community-status" role="status">正在翻开作品册…</p>
      <div v-else-if="!items.length && !feedError" class="empty-state"><span class="empty-mark">○</span><h3>这里还没有公开作品</h3><p>在“我的”里把账号中的作品提交到社区，审核通过后就会出现在这里。</p><button class="primary-button" type="button" @click="emit('navigate', user ? 'mine' : 'login')">{{ user ? '去发布我的作品' : '登录后发布' }}</button></div>
      <div v-if="nextCursor && !feedLoading" class="community-more"><button class="secondary-button" type="button" @click="loadFeed(true)">再看一些</button></div>
    </template>

    <template v-else>
      <a class="back-link" href="#community"><span aria-hidden="true">←</span>回到园友作品</a>
      <p v-if="detailLoading" class="community-status" role="status">正在打开作品…</p>
      <div v-else-if="detailError" class="empty-state"><span class="empty-mark">○</span><h3>{{ detailError }}</h3><p>作品可能已被作者撤回，或仍在审核中。</p></div>
      <article v-else-if="work" class="community-detail">
        <figure class="community-figure"><img :src="work.imageUrl" :alt="work.title"></figure>
        <div class="community-side">
          <p v-if="work.reviewStatus !== 'approved'" class="review-banner" role="status">{{ work.reviewStatus === 'pending' ? '审核中：只有你和管理员能看到这幅作品。' : `未通过审核：${work.rejectReason}` }}</p>
          <span class="eyebrow">{{ methodLabel(work.methodId) }}</span>
          <h1 class="community-title">{{ work.title }}</h1>
          <p class="community-byline">{{ work.author.nickname }} · {{ formatDate(work.publishedAt) || '尚未公开' }}</p>
          <p v-if="work.note" class="community-note">{{ work.note }}</p>
          <div v-if="work.reviewStatus === 'approved'" class="community-actions">
            <button type="button" :class="['like-button', 'like-large', { liked: work.likedByMe }]" :aria-pressed="work.likedByMe" :disabled="liking.has(work.id)" @click="toggleLike(work, $event)"><span class="like-mark" aria-hidden="true">{{ work.likedByMe ? '♥' : '♡' }}</span>{{ work.likedByMe ? '已喜欢' : '喜欢' }} <span class="num">{{ work.likeCount }}</span></button>
            <button type="button" :class="['secondary-button', 'copy-button', { copied }]" @click="share"><span aria-hidden="true">{{ copied ? '✓' : '↗' }}</span> {{ copied ? '链接已复制' : '分享' }}</button>
            <button type="button" class="text-link" @click="report('work', work.id)">举报</button>
          </div>
          <p v-if="notice" class="community-notice" role="status">{{ notice }}</p>
          <section v-if="work.reviewStatus === 'approved'" class="community-comments" aria-labelledby="comments-heading">
            <h2 id="comments-heading">评论 <span class="num">{{ work.commentCount }}</span></h2>
            <form v-if="user" class="comment-form" @submit.prevent="submitComment"><label for="comment-input" class="sr-only">写下评论</label><textarea id="comment-input" v-model="draft" rows="3" maxlength="500" placeholder="说说你从这扇窗里看到了什么…" :disabled="posting"></textarea><div class="comment-form-actions"><span class="num">{{ draft.length }} / 500</span><button class="primary-button" type="submit" :disabled="posting || !draft.trim()">{{ posting ? '发送中…' : '发表评论' }}</button></div></form>
            <div v-else class="comment-login"><span>登录后可以点赞和评论。</span><button class="text-link" type="button" @click="emit('navigate', 'login')">登录 / 注册</button></div>
            <ol class="comment-list">
              <li v-for="comment in comments" :key="comment.id" :class="{ pending: comment.status === 'pending' }">
                <div class="comment-head"><strong>{{ comment.author.nickname }}</strong><span>{{ formatDate(comment.createdAt) }}</span><span v-if="comment.status === 'pending'" class="comment-pending">待审核，仅你可见</span></div>
                <p>{{ comment.content }}</p>
                <div class="comment-tools"><button v-if="canDelete(comment)" type="button" class="danger-link" @click="deleteComment(comment)">删除</button><button v-if="user && comment.author.id !== user.id && comment.status === 'visible'" type="button" class="text-link" @click="report('comment', comment.id)">举报</button></div>
              </li>
            </ol>
            <p v-if="!comments.length" class="community-status">还没有评论，来写第一条吧。</p>
            <button v-if="commentsCursor" class="secondary-button" type="button" @click="moreComments">更早的评论</button>
          </section>
        </div>
      </article>
    </template>
  </section>
</template>

<style scoped>
.community-page { padding-top:54px; }
.community-toolbar { display:flex; justify-content:space-between; gap:16px; flex-wrap:wrap; margin-bottom:34px; }
.chip-row { display:flex; gap:8px; flex-wrap:wrap; }
.chip { border:0; padding:8px 16px; min-height:40px; border-radius:999px; background:rgba(23,58,54,.04); color:var(--ink-soft); font:14px system-ui,sans-serif; transition:background-color .15s, color .15s; }
.chip:hover { background:rgba(23,58,54,.07); }
.chip.selected { background:var(--ink); color:#fdf8ee; }
.community-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:28px; }
.community-card { background:rgba(23,58,54,.025); transition:background-color .15s; }
.community-card:hover { background:rgba(23,58,54,.045); }
.community-thumb { display:block; aspect-ratio:4/3; overflow:hidden; background:rgba(23,58,54,.06); }
.community-thumb img { width:100%; height:100%; object-fit:cover; display:block; transition:transform .4s; }
.community-card:hover .community-thumb img { transform:scale(1.025); }
.community-card-body { padding:18px 20px 20px; }
.community-card-body h3 { font-size:20px; margin:8px 0 12px; text-wrap:balance; }
.community-card-body h3 a { color:inherit; text-decoration:none; }
.community-meta { display:flex; justify-content:space-between; align-items:center; gap:12px; color:var(--ink-soft); font:13px system-ui,sans-serif; }
.community-stats { display:flex; align-items:center; gap:12px; }
.num { font-variant-numeric:tabular-nums; }
.like-button { display:inline-flex; align-items:center; gap:5px; border:0; background:none; padding:4px 2px; color:var(--ink-soft); font:13px system-ui,sans-serif; }
.like-button.liked, .like-button.liked .like-mark { color:var(--clay); }
.like-mark { display:inline-block; font-size:1.15em; line-height:1; transform:translateY(.125em); }
.like-large { min-height:48px; padding:12px 18px; background:rgba(23,58,54,.04); font-size:14px; font-weight:600; }
.community-status { color:var(--ink-soft); font-size:14px; margin:24px 0; }
.community-more { display:flex; justify-content:center; margin-top:40px; }
.community-detail { display:grid; grid-template-columns:minmax(0,1.35fr) minmax(300px,.9fr); gap:56px; margin-top:28px; align-items:start; }
.community-figure { margin:0; background:rgba(23,58,54,.05); position:sticky; top:100px; }
.community-figure img { width:100%; max-height:78dvh; object-fit:contain; display:block; }
.community-title { font-size:clamp(32px,4vw,48px); margin:10px 0 12px; }
.community-byline { font:14px system-ui,sans-serif; margin:0 0 20px; }
.community-note { font-size:17px; white-space:pre-line; }
.community-actions { display:flex; align-items:center; gap:12px; flex-wrap:wrap; margin:24px 0 8px; }
.copy-button.copied { color:var(--clay); }
.review-banner { padding:12px 16px; background:rgba(186,141,80,.12); color:var(--ink); font-size:14px; }
.community-notice { font-size:14px; }
.community-comments { margin-top:38px; padding-top:28px; box-shadow:0 -1px 0 var(--line); }
.community-comments h2 { font-size:24px; margin-bottom:18px; }
.comment-form textarea { width:100%; border:0; padding:14px 16px; background:rgba(23,58,54,.04); color:var(--ink); resize:vertical; line-height:1.7; transition:box-shadow .15s, background-color .15s; }
.comment-form textarea:focus, .comment-form textarea:focus-visible { outline:none; background:rgba(23,58,54,.055); box-shadow:0 0 0 1px rgba(156,77,53,.18),0 0 0 4px rgba(156,77,53,.08); }
.comment-form-actions { display:flex; justify-content:space-between; align-items:center; margin-top:10px; color:var(--ink-soft); font:12px system-ui,sans-serif; }
.comment-login { display:flex; gap:12px; align-items:center; padding:14px 16px; background:rgba(23,58,54,.035); font-size:14px; color:var(--ink-soft); }
.comment-list { list-style:none; padding:0; margin:22px 0 0; }
.comment-list li { padding:16px 0; box-shadow:0 1px 0 var(--line); }
.comment-list li.pending { opacity:.72; }
.comment-head { display:flex; gap:10px; align-items:baseline; flex-wrap:wrap; font:13px system-ui,sans-serif; color:var(--ink-soft); }
.comment-head strong { color:var(--ink); font-weight:600; }
.comment-pending { color:var(--gold); }
.comment-list p { margin:6px 0 4px; font-size:15px; white-space:pre-line; overflow-wrap:anywhere; }
.comment-tools { display:flex; gap:14px; font-size:13px; }
.sr-only { position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; border:0; }
@media (max-width:860px) { .community-detail { grid-template-columns:1fr; gap:28px; } .community-figure { position:static; } }
</style>
