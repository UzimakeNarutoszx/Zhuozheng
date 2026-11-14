export const mascots = {
  round: {
    id: 'round',
    model: 'round',
    name: '梅梅',
    asset: '/assets/mascots/window-round-cutout.png',
    alt: '梅梅，梅花多边形窗造型的研学吉祥物',
    messages: ['先找一处边界，再看景色怎样被收进来。', '窗框像一只眼睛，帮你把视线停在重要的地方。'],
    target: 'methods',
    actionLabel: '去看五种手法'
  },
  flower: {
    id: 'flower',
    model: 'coin',
    name: '钱钱',
    asset: '/assets/mascots/window-flower-cutout.png',
    alt: '钱钱，双层方框抱着铜钱的研学吉祥物',
    messages: ['地图上的每个点，都是一次停下来观察的邀请。', '点开观察点，看看近景和远景怎样互相回应。'],
    target: 'methods',
    actionLabel: '去看造景手法'
  },
  ice: {
    id: 'ice',
    model: 'ice',
    name: '冰冰',
    asset: '/assets/mascots/window-ice-cutout.png',
    alt: '冰冰，冰裂纹花窗造型的研学吉祥物',
    messages: ['把照片放进一扇窗，景色就有了新的边界。', '拖动画面，让你想留下的细节落进窗心。'],
    target: 'studio',
    actionLabel: '开始创作'
  }
}

export const mascotEasterEgg = {
  ...mascots.flower,
  name: '钱钱',
  messages: ['“一窗一景，步步成画。”', '找到我了，继续慢慢看。'],
  target: null,
  actionLabel: ''
}

export const mascotCoin = {
  ...mascots.flower,
  id: 'coin',
  model: 'coin',
  name: '钱钱',
  messages: ['正方形窗框抱着古代铜钱，寓意财源滚滚来。', '关于这次研学的材料和来源，都藏在这里。'],
  target: 'methods',
  actionLabel: '去看造景手法'
}

// 吉祥物展示状态机：静态图先出现（占位），3D 模型 ready 后延迟 readyDelay 毫秒淡入。
// 2.5s 内没准备好就进入 fallback：静态图继续保留，不会闪空；之后模型若迟到但仍能 ready，
// 仍然可以平滑升级成 3D。只有加载失败 / WebGL 不可用才是终态，永久保留静态图。
// 纯逻辑 + 可注入计时器，便于在 node:test 里测 ready / 超时 / 失败分支。
export const MASCOT_REVEAL_DELAY = 200
export const MASCOT_REVEAL_TIMEOUT = 2500

export function createMascotReveal({
  readyDelay = MASCOT_REVEAL_DELAY,
  timeout = MASCOT_REVEAL_TIMEOUT,
  schedule = (fn, ms) => setTimeout(fn, ms),
  cancel = id => clearTimeout(id),
  onChange = () => {}
} = {}) {
  let state = 'placeholder' // placeholder → revealed | fallback(timeout) → revealed；failed 为终态
  let timeoutId = null
  let revealId = null
  const clear = id => { if (id !== null) cancel(id) }
  const clearTimers = () => { clear(timeoutId); timeoutId = null; clear(revealId); revealId = null }
  const apply = next => {
    state = next
    clearTimers()
    onChange(state)
  }
  return {
    get state() { return state },
    // 组件挂载后启动看门狗：超时仍没 ready 就先标记 fallback，静态图继续展示
    start() {
      if (state !== 'placeholder' || timeoutId !== null) return
      timeoutId = schedule(() => { timeoutId = null; if (state === 'placeholder') apply('fallback') }, timeout)
    },
    // 3D 模型就绪：过关后再等 readyDelay 淡入，避免模型刚 ready 第一帧闪空
    ready() {
      if (state === 'failed' || state === 'revealed' || revealId !== null) return
      clear(timeoutId); timeoutId = null
      revealId = schedule(() => { revealId = null; if (state !== 'failed') apply('revealed') }, readyDelay)
    },
    // 加载失败 / WebGL 不可用：终态回退静态图（若已淡入过 3D 也会退回静态图）
    fail() { if (state !== 'failed') apply('failed') },
    dispose() {
      clearTimers()
      onChange = () => {}
    }
  }
}
