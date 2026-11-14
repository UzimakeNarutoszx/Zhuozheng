// 登录页左侧梅梅：首屏静态剪影立即显示，3D 就绪后淡入。
// 把静态图路径与“两层怎么切换”拆成纯数据 / 纯函数，便于 node:test 直接验证，不用挂载 Vue。
export const LOGIN_MASCOT_STILL = '/assets/mascots/window-round-frame.png'
export const LOGIN_MASCOT_MODEL = 'round'

// placeholder / fallback / failed → 静态图继续遮挡；只有 revealed 才让静态图淡出、3D 舞台淡入。
// 3D 失败或超时永远停在静态图，不会出现空白。
export function loginMascotLayers(state) {
  const revealed = state === 'revealed'
  return { stillHidden: revealed, stageVisible: revealed }
}
