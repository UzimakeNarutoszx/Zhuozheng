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
