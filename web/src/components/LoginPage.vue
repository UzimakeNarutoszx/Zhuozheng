<script setup>
import { assetUrl } from '../utils/assets.js'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { apiRequest } from '../utils/api.js'
import RoundWindow3D from './RoundWindow3D.vue'
import { createMascotReveal } from '../data/mascots.js'
import { LOGIN_MASCOT_STILL, loginMascotLayers } from '../utils/login-mascot.js'
const emit = defineEmits(['authenticated', 'navigate'])
const mode = ref('login'), phone = ref(''), password = ref(''), nickname = ref(''), smsCode = ref(''), busy = ref(false), error = ref(''), smsBusy = ref(false), smsMessage = ref('')
const cooldown = ref(0)
let cooldownTimer
async function submit() {
  if (busy.value) return
  error.value = ''; busy.value = true
  try {
    if (mode.value === 'forgot-password') { await apiRequest('/auth/forgot-password', { body: { phone: phone.value.trim(), new_password: password.value, sms_code: smsCode.value.trim() } }); mode.value = 'login'; password.value = ''; smsCode.value = ''; smsMessage.value = '密码已重置，请使用新密码登录。' }
    else { const session = await apiRequest(`/auth/${mode.value}`, { body: { phone: phone.value.trim(), password: password.value, ...(mode.value === 'register' ? { nickname: nickname.value.trim(), sms_code: smsCode.value.trim() } : {}) } }); emit('authenticated', session) }
  } catch (failure) { error.value = failure.message } finally { busy.value = false }
}
function switchMode(next) { mode.value = next; error.value = ''; smsMessage.value = ''; smsCode.value = '' }
async function sendCode() {
  if (smsBusy.value || cooldown.value) return
  if (!/^1[3-9]\d{9}$/.test(phone.value.trim())) { error.value = '请先输入有效的 11 位手机号码。'; return }
  smsBusy.value = true; error.value = ''; smsMessage.value = ''
  try { const data = await apiRequest('/auth/send-sms', { body: { phone: phone.value.trim(), scene: mode.value === 'register' ? 'register' : 'reset_password' } }); smsMessage.value = data.message || '验证码已发送，请查看手机。'; cooldown.value = data.retry_after || 60; clearInterval(cooldownTimer); cooldownTimer = setInterval(() => { if (--cooldown.value <= 0) clearInterval(cooldownTimer) }, 1000) } catch (failure) { error.value = failure.message } finally { smsBusy.value = false }
}
onBeforeUnmount(() => clearInterval(cooldownTimer))

// 左栏梅梅：静态剪影先出现（首屏不空白），3D ready 后 200ms 淡入；
// 失败/2.5s 超时保留静态图（复用吉祥物通用的 reveal 状态机，不碰 3D 组件内部）。
const mascotScene = ref('placeholder')
const mascotLayers = computed(() => loginMascotLayers(mascotScene.value))
let mascotReveal = null
let mascotEarlyReady = false
let mascotEarlyError = false
function onMascotReady() { if (mascotReveal) mascotReveal.ready(); else mascotEarlyReady = true }
function onMascotError() { if (mascotReveal) mascotReveal.fail(); else mascotEarlyError = true }
onMounted(() => {
  mascotReveal = createMascotReveal({ onChange: state => { mascotScene.value = state } })
  mascotReveal.start()
  // 子组件的 mounted 可能先于父组件，ready/error 先记下来，状态机建好后补发。
  if (mascotEarlyError) mascotReveal.fail()
  else if (mascotEarlyReady) mascotReveal.ready()
})
onBeforeUnmount(() => { mascotReveal?.dispose(); mascotReveal = null })
</script>

<template>
  <section class="page login-page">
    <div class="login-story"><span class="eyebrow">让梅梅陪你看景</span><h1>推开一扇窗，<br>接着聊园林。</h1><p>登录后向梅梅提问，了解拙政园的造景手法，把自己的作品留在账号里。</p><div class="login-mascot" :data-reveal="mascotScene"><img class="login-mascot__still" :class="{ 'is-hidden': mascotLayers.stillHidden }" :src="assetUrl(LOGIN_MASCOT_STILL)" alt="梅梅站在窗前等你" decoding="async"><RoundWindow3D class="login-mascot__stage" :class="{ 'is-visible': mascotLayers.stageVisible }" :inert="mascotLayers.stageVisible ? undefined : 'true'" character="round" :compact="false" :preview="false" @ready="onMascotReady" @error="onMascotError" /></div><button type="button" class="text-link" @click="emit('navigate', 'home')">先继续游园</button></div>
    <div class="login-panel"><h2>{{ mode === 'login' ? '欢迎回来' : mode === 'register' ? '认识一下' : '找回密码' }}</h2><p>{{ mode === 'login' ? '用手机号码和密码登录。' : mode === 'register' ? '创建账号，与梅梅开始对话。' : '验证手机号码，设置一个新密码。' }}</p>
      <form @submit.prevent="submit"><label>手机号码<input v-model="phone" name="phone" type="tel" autocomplete="tel" inputmode="numeric" pattern="1[3-9][0-9]{9}" required maxlength="11" placeholder="11 位手机号码" :disabled="busy"></label><label v-if="mode === 'register'">怎么称呼你<input v-model="nickname" name="nickname" autocomplete="nickname" maxlength="32" required placeholder="留一个名字" :disabled="busy"></label><label v-if="mode !== 'login'">验证码<div class="sms-field"><input v-model="smsCode" name="sms-code" autocomplete="one-time-code" inputmode="numeric" required minlength="6" maxlength="6" placeholder="手机验证码" :disabled="busy"><button type="button" class="secondary-button" :disabled="smsBusy || busy || cooldown > 0" @click="sendCode">{{ smsBusy ? '发送中…' : cooldown ? `${cooldown} 秒后重发` : '获取验证码' }}</button></div></label><label>{{ mode === 'forgot-password' ? '新密码' : '密码' }}<input v-model="password" name="password" type="password" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" required minlength="6" maxlength="72" placeholder="至少 6 位" :disabled="busy"></label><p v-if="smsMessage" class="sms-message" role="status">{{ smsMessage }}</p><p v-if="error" class="login-error" role="alert">{{ error }}</p><button class="primary-button" type="submit" :disabled="busy">{{ busy ? '正在处理…' : mode === 'login' ? '登录' : mode === 'register' ? '创建账号' : '重置密码' }}</button></form>
      <div class="login-options"><button class="text-link" type="button" :disabled="busy" @click="switchMode(mode === 'login' ? 'register' : 'login')">{{ mode === 'login' ? '还没有账号？注册一个' : '已有账号？去登录' }}</button><button v-if="mode === 'login'" class="text-link" type="button" :disabled="busy" @click="switchMode('forgot-password')">忘记密码</button></div>
    </div>
  </section>
</template>

<style scoped>
.login-page { display:grid; grid-template-columns:1.1fr .9fr; gap:80px; align-items:center; min-height:calc(100vh - 170px); }
.login-story h1 { font-size:clamp(42px,5vw,66px); margin:16px 0 24px; }
.login-story p { max-width:430px; }
/* 梅梅：220x240 固定区域，静态剪影立即显示，3D 就绪后 200ms 淡入（尺寸由外层控制）。 */
.login-mascot { position:relative; display:block; width:220px; height:240px; margin:20px 0; }
.login-mascot__still { position:absolute; inset:0; display:block; width:100%; height:100%; object-fit:contain; pointer-events:none; transition:opacity .2s ease; }
.login-mascot__still.is-hidden { opacity:0; }
.login-mascot__stage { position:absolute; inset:0; display:block; width:100%; height:100%; opacity:0; pointer-events:none; transition:opacity .2s ease; }
.login-mascot__stage.is-visible { opacity:1; pointer-events:auto; }
/* RoundWindow3D 默认 320px 舞台 + 操作条；登录页只在外层收成 220x240，不改组件内部逻辑。 */
.login-mascot :deep(.character-stage) { height:100%; }
.login-mascot :deep(.character-controls) { display:none; }
.login-panel { padding:40px; background:rgba(23,58,54,.035); }
.login-panel h2 { font-size:36px; margin-bottom:14px; }
.login-panel > p { font-size:14px; }
form { display:grid; gap:22px; margin-top:30px; }
form label { display:grid; gap:9px; color:var(--ink-soft); font-size:14px; }
input { border:0; box-shadow:0 1px 0 rgba(23,58,54,.16); padding:13px 14px; }
.login-error { color:#9b4d3d; font-size:13px; margin:0; }
.login-options { display:flex; flex-wrap:wrap; justify-content:space-between; gap:16px; margin-top:24px; }
.sms-field { display:flex; gap:8px; }
.sms-field input { min-width:0; }
.sms-field button { flex-shrink:0; padding:10px; font-size:12px; font-variant-numeric:tabular-nums; }
.sms-message { color:var(--ink-soft); font-size:13px; margin:0; }
button:disabled { cursor:wait; opacity:.65; }
@media (max-width:700px) { .login-page { grid-template-columns:1fr; gap:28px; padding-top:38px; } .login-mascot { width:115px; height:130px; float:right; margin:-100px 0 0; opacity:.7; } .login-story p { max-width:calc(100% - 125px); font-size:13px; } .login-panel { padding:26px 22px; } }
@media (prefers-reduced-motion:reduce) { .login-mascot__still, .login-mascot__stage { transition:none; } }
</style>
