import test from 'node:test'
import assert from 'node:assert/strict'
import { access, readFile } from 'node:fs/promises'
import { LOGIN_MASCOT_MODEL, LOGIN_MASCOT_STILL, loginMascotLayers } from '../src/utils/login-mascot.js'

const LOGIN_PAGE = new URL('../src/components/LoginPage.vue', import.meta.url)

test('登录页梅梅的静态图与 3D 模型都存在', async () => {
  assert.equal(LOGIN_MASCOT_MODEL, 'round', '登录页梅梅应复用 round 角色')
  assert.match(LOGIN_MASCOT_STILL, /^\/assets\/mascots\/[\w-]+\.png$/)
  await access(new URL(`../public${LOGIN_MASCOT_STILL}`, import.meta.url))
  await access(new URL(`../public/assets/models/${LOGIN_MASCOT_MODEL}-window.glb`, import.meta.url))
})

test('静态图立即显示，只有 3D ready 后才把两层切过去', () => {
  // 首屏与失败/超时：静态图继续遮挡，3D 舞台透明；不会出现空白。
  for (const state of ['placeholder', 'fallback', 'failed', undefined, '', 'READY']) {
    assert.deepEqual(loginMascotLayers(state), { stillHidden: false, stageVisible: false }, `状态 ${state} 不应切到 3D`)
  }
  // 3D ready（延迟 200ms 后）：静态图淡出、3D 淡入。
  assert.deepEqual(loginMascotLayers('revealed'), { stillHidden: true, stageVisible: true })
})

test('登录页按约定挂载 RoundWindow3D，静态层先渲染，3D 失败/超时回退静态图', async () => {
  const source = await readFile(LOGIN_PAGE, 'utf8')
  // 220x240 区域：round 角色、非 compact、非 preview，并接 ready/error
  assert.match(source, /<RoundWindow3D\b/, '缺少 RoundWindow3D')
  assert.match(source, /character="round"/)
  assert.match(source, /:compact="false"/)
  assert.match(source, /:preview="false"/)
  assert.match(source, /@ready="onMascotReady"/)
  assert.match(source, /@error="onMascotError"/)
  // 静态 layer 用常量路径，且排在 3D 之前（立即显示层）
  assert.match(source, /assetUrl\(LOGIN_MASCOT_STILL\)/)
  assert.ok(source.indexOf('login-mascot__still') < source.indexOf('<RoundWindow3D'), '静态图必须先渲染')
  // 状态机：复用吉祥物通用 reveal（200ms 淡入、超时/失败保留静态图），并在卸载时清理
  assert.match(source, /createMascotReveal/)
  assert.match(source, /mascotReveal\.start\(\)/)
  assert.match(source, /mascotReveal\?\.dispose\(\)/)
  assert.match(source, /loginMascotLayers\(mascotScene\.value\)/)
})

test('登录页表单与登录逻辑保持原样，移动端沿用 115x130 缩小规则', async () => {
  const source = await readFile(LOGIN_PAGE, 'utf8')
  assert.match(source, /<form @submit\.prevent="submit">/)
  assert.match(source, /name="phone"/)
  assert.match(source, /name="password"/)
  assert.ok(source.includes('apiRequest(`/auth/${mode.value}`, {'), '登录请求逻辑不应被改动')
  assert.ok(source.includes('width:115px; height:130px'), '移动端梅梅应保持 115x130')
  assert.ok(source.includes('.login-mascot :deep(.character-stage)'), '3D 舞台尺寸应由外层 CSS 收敛到容器')
})
