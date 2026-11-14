import test from 'node:test'
import assert from 'node:assert/strict'
import { access } from 'node:fs/promises'
import {
  mascots, mascotCoin, mascotEasterEgg,
  MASCOT_REVEAL_DELAY, MASCOT_REVEAL_TIMEOUT, createMascotReveal,
  MASCOT_RETRY_LIMIT, MASCOT_RETRY_DELAY, createMascotAttemptState
} from '../src/data/mascots.js'

// 可注入的假计时器：让状态机测试不依赖真实时间。
function createClock() {
  let now = 0
  let seq = 0
  const timers = new Map()
  return {
    get now() { return now },
    schedule(fn, ms) {
      const id = ++seq
      timers.set(id, { at: now + ms, fn })
      return id
    },
    cancel(id) { timers.delete(id) },
    advance(ms) {
      const target = now + ms
      for (;;) {
        const due = [...timers.entries()]
          .filter(([, timer]) => timer.at <= target)
          .sort((a, b) => a[1].at - b[1].at || a[0] - b[0])[0]
        if (!due) break
        const [id, timer] = due
        timers.delete(id)
        now = timer.at
        timer.fn()
      }
      now = target
    },
    get pending() { return timers.size }
  }
}

function createTrackedReveal(options = {}) {
  const clock = createClock()
  const states = []
  const reveal = createMascotReveal({
    schedule: clock.schedule,
    cancel: clock.cancel,
    onChange: state => states.push(state),
    ...options
  })
  return { clock, states, reveal }
}

test('吉祥物数据都有可用的静态图和 3D 模型映射', async () => {
  const modelIds = new Set(['round', 'coin', 'ice'])
  for (const [key, mascot] of Object.entries({ ...mascots, coin: mascotCoin })) {
    assert.equal(mascot.id, key, `${key} 的 id 应与其键一致`)
    assert.ok(modelIds.has(mascot.model), `${mascot.name} 的 model 应为 round/coin/ice，实际是 ${mascot.model}`)
    assert.ok(mascot.asset.startsWith('/assets/mascots/'), `${mascot.name} 的静态图路径异常`)
    assert.ok(mascot.alt && mascot.alt.trim(), `${mascot.name} 缺少 alt`)
    assert.ok(mascot.messages.length >= 2, `${mascot.name} 提示语不足`)
    await access(new URL(`../public${mascot.asset}`, import.meta.url))
  }
  // 彩蛋沿用钱钱的静态图与 3D 模型，只是换文案
  assert.equal(mascotEasterEgg.model, mascots.flower.model)
  assert.equal(mascotEasterEgg.asset, mascots.flower.asset)
  assert.equal(mascotEasterEgg.name, '钱钱')
})

test('首屏先展示静态图；3D ready 后延迟 150-250ms 才淡入', () => {
  assert.ok(MASCOT_REVEAL_DELAY >= 150 && MASCOT_REVEAL_DELAY <= 250, `淡入延迟 ${MASCOT_REVEAL_DELAY}ms 不在 150-250ms 内`)
  const { clock, states, reveal } = createTrackedReveal()
  reveal.start()
  assert.equal(reveal.state, 'placeholder')
  clock.advance(500)
  reveal.ready()
  assert.equal(reveal.state, 'placeholder', 'ready 后不能立刻切 3D')
  clock.advance(MASCOT_REVEAL_DELAY - 1)
  assert.equal(reveal.state, 'placeholder')
  clock.advance(1)
  assert.equal(reveal.state, 'revealed')
  assert.deepEqual(states, ['revealed'])
  // 淡入后看门狗必须已取消，不会再改成 fallback
  clock.advance(MASCOT_REVEAL_TIMEOUT * 2)
  assert.equal(reveal.state, 'revealed')
})

test('2.5s 超时保留静态图，迟到的 3D 仍可平滑升级', () => {
  assert.equal(MASCOT_REVEAL_TIMEOUT, 2500)
  const { clock, states, reveal } = createTrackedReveal()
  reveal.start()
  clock.advance(MASCOT_REVEAL_TIMEOUT - 1)
  assert.equal(reveal.state, 'placeholder')
  clock.advance(1)
  assert.equal(reveal.state, 'fallback', '超时后应回退到静态图状态')
  assert.deepEqual(states, ['fallback'])
  // 慢网络下模型迟到：仍然允许淡入，而不是永久卡在静态图
  reveal.ready()
  clock.advance(MASCOT_REVEAL_DELAY)
  assert.equal(reveal.state, 'revealed')
  assert.deepEqual(states, ['fallback', 'revealed'])
})

test('3D 加载失败是终态：永久保留静态图，迟到的 ready 被忽略', () => {
  const { clock, states, reveal } = createTrackedReveal()
  reveal.start()
  reveal.fail()
  assert.equal(reveal.state, 'failed')
  clock.advance(MASCOT_REVEAL_TIMEOUT * 3)
  assert.equal(reveal.state, 'failed')
  reveal.ready()
  clock.advance(MASCOT_REVEAL_DELAY * 3)
  assert.equal(reveal.state, 'failed', '失败后不应再切 3D')
  assert.deepEqual(states, ['failed'])
})

test('超时后失败、已淡入后失败都会退回静态图', () => {
  const timedOut = createTrackedReveal()
  timedOut.reveal.start()
  timedOut.clock.advance(MASCOT_REVEAL_TIMEOUT)
  timedOut.reveal.fail()
  assert.equal(timedOut.reveal.state, 'failed')

  const revealed = createTrackedReveal()
  revealed.reveal.start()
  revealed.reveal.ready()
  revealed.clock.advance(MASCOT_REVEAL_DELAY)
  assert.equal(revealed.reveal.state, 'revealed')
  revealed.reveal.fail() // 例如 WebGL context lost
  assert.equal(revealed.reveal.state, 'failed')
})

test('dispose 会取消未触发的计时器，不再回调', () => {
  const { clock, states, reveal } = createTrackedReveal()
  reveal.start()
  reveal.ready()
  reveal.dispose()
  assert.equal(clock.pending, 0)
  clock.advance(MASCOT_REVEAL_TIMEOUT * 2)
  assert.equal(reveal.state, 'placeholder')
  assert.deepEqual(states, [])
})

test('重复 start / ready 不会产生重复计时器或重复状态回调', () => {
  const { clock, states, reveal } = createTrackedReveal()
  reveal.start()
  reveal.start()
  assert.equal(clock.pending, 1, 'start 应只登记一个超时计时器')
  reveal.ready()
  reveal.ready()
  assert.equal(clock.pending, 1, 'ready 应只登记一个淡入计时器')
  clock.advance(MASCOT_REVEAL_DELAY)
  assert.deepEqual(states, ['revealed'])
})

test('3D 加载失败自动重试一次，第二次失败才进入终态', () => {
  assert.equal(MASCOT_RETRY_LIMIT, 1, '只自动重试一次，不能无限重试')
  assert.ok(MASCOT_RETRY_DELAY >= 400 && MASCOT_RETRY_DELAY <= 1500, `重试间隔 ${MASCOT_RETRY_DELAY}ms 应给慢网一点喘息`)
  const state = createMascotAttemptState()
  assert.equal(state.status, 'idle')
  assert.ok(state.start())
  assert.equal(state.status, 'loading')
  assert.equal(state.attempts, 1)
  assert.ok(state.failed())
  assert.equal(state.status, 'failed')
  assert.equal(state.canRetry, true, '第一次失败后应允许自动重试')
  assert.ok(state.retry())
  assert.equal(state.status, 'loading')
  assert.equal(state.attempts, 2)
  assert.ok(state.failed())
  assert.equal(state.canRetry, false, '第二次失败后不再自动重试')
  assert.equal(state.retry(), false)
  assert.equal(state.attempts, 2)
  assert.ok(state.loaded() === false, '终态后 ready 不能再改变状态')
})

test('成功后不再允许重试；手动重试不受自动重试次数限制', () => {
  const ok = createMascotAttemptState()
  ok.start(); ok.loaded()
  assert.equal(ok.status, 'ready')
  assert.equal(ok.canRetry, false)
  assert.equal(ok.failed(), false, 'ready 后失败事件应被忽略')

  const manual = createMascotAttemptState()
  manual.start(); manual.failed(); manual.retry(); manual.failed()
  assert.equal(manual.canRetry, false)
  // 用户点“重试动态形象”：手动重试永远允许，但每次只进行一次新尝试。
  assert.ok(manual.retry({ manual: true }))
  assert.equal(manual.status, 'loading')
  assert.equal(manual.attempts, 3)
  assert.equal(manual.retry(), false, '正在 loading 时重复重试应被忽略')
})

test('reveal.retry 让失败终态回到静态图占位，并重新武装超时看门狗', () => {
  const { clock, states, reveal } = createTrackedReveal()
  reveal.start()
  reveal.fail()
  assert.equal(reveal.state, 'failed')
  assert.equal(reveal.retry(), true)
  assert.equal(reveal.state, 'placeholder')
  // 手动重试后看门狗重新计时：超时仍回到 fallback，静态图一直在。
  clock.advance(MASCOT_REVEAL_TIMEOUT)
  assert.equal(reveal.state, 'fallback')
  reveal.ready()
  clock.advance(MASCOT_REVEAL_DELAY)
  assert.equal(reveal.state, 'revealed', '手动重试成功后仍可升级成 3D')
  assert.deepEqual(states, ['failed', 'placeholder', 'fallback', 'revealed'])
  // 非失败态调用 retry 不产生噪音
  assert.equal(reveal.retry(), false)
})
