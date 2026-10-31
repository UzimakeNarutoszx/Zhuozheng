<script setup>
import { assetUrl } from '../utils/assets.js'
import { onBeforeUnmount, ref } from 'vue'
import { apiRequest } from '../utils/api.js'
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
</script>

<template>
  <section class="page login-page">
    <div class="login-story"><span class="eyebrow">让梅梅陪你看景</span><h1>推开一扇窗，<br>接着聊园林。</h1><p>登录后向梅梅提问，了解拙政园的造景手法，把自己的作品留在账号里。</p><img :src="assetUrl('/assets/mascots/window-round-cutout.png')" alt="梅梅站在窗前等你"><button type="button" class="text-link" @click="emit('navigate', 'home')">先继续游园</button></div>
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
.login-story img { display:block; width:220px; height:240px; object-fit:contain; margin:20px 0; }
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
@media (max-width:700px) { .login-page { grid-template-columns:1fr; gap:28px; padding-top:38px; } .login-story img { width:115px; height:130px; float:right; margin:-100px 0 0; opacity:.7; } .login-story p { max-width:calc(100% - 125px); font-size:13px; } .login-panel { padding:26px 22px; } }
</style>
