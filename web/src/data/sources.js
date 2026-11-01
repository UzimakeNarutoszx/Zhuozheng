export const sources = [
  { id: 'field-frame', title: '江南研学现场照片 · 六边形窗', author: '江南研学小组', license: '小组提供，保留原作者权利', url: '/assets/garden/method-frame-hexagonal.jpg', file: '/assets/garden/method-frame-hexagonal.jpg' },
  { id: 'field-borrow', title: '江南研学现场照片 · 北寺塔借景', author: '江南研学小组', license: '小组提供，保留原作者权利', url: '/assets/garden/method-borrow-beisi.jpg', file: '/assets/garden/method-borrow-beisi.jpg' },
  { id: 'field-opposition', title: '江南研学现场照片 · 隔水亭阁', author: '江南研学小组', license: '小组提供，保留原作者权利', url: '/assets/garden/method-opposition-waterfront.jpg', file: '/assets/garden/method-opposition-waterfront.jpg' },
  { id: 'field-leak', title: '江南研学现场照片 · 花格漏窗', author: '江南研学小组', license: '小组提供，保留原作者权利', url: '/assets/garden/method-leak-lattice.jpg', file: '/assets/garden/method-leak-lattice.jpg' },
  { id: 'field-screen', title: '江南研学现场照片 · 缀云峰', author: '江南研学小组', license: '小组提供，保留原作者权利', url: '/assets/garden/method-screen-zhuiyun.jpg', file: '/assets/garden/method-screen-zhuiyun.jpg' },
  { id: 'commons-001', title: "Humble Administrator's Garden Suzhou November 2017 001", author: 'King of Hearts', license: 'CC BY-SA 4.0', url: 'https://commons.wikimedia.org/wiki/File:Humble_Administrator%27s_Garden_Suzhou_November_2017_001.jpg', file: '/assets/garden/garden-001.jpg' },
  { id: 'commons-002', title: "Humble Administrator's Garden Suzhou November 2017 002", author: 'King of Hearts', license: 'CC BY-SA 4.0', url: 'https://commons.wikimedia.org/wiki/File:Humble_Administrator%27s_Garden_Suzhou_November_2017_002.jpg', file: '/assets/garden/garden-002.jpg' },
  { id: 'commons-003', title: "Humble Administrator's Garden Suzhou November 2017 003", author: 'King of Hearts', license: 'CC BY-SA 4.0', url: 'https://commons.wikimedia.org/wiki/File:Humble_Administrator%27s_Garden_Suzhou_November_2017_003.jpg', file: '/assets/garden/garden-003.jpg' },
  { id: 'unesco', title: 'Classical Gardens of Suzhou', author: 'UNESCO World Heritage Centre', license: 'Reference source', url: 'https://whc.unesco.org/en/list/813/', file: null },
  { id: 'yuan-ye', title: '园冶', author: '计成', license: 'Public domain text reference', url: 'https://zh.wikisource.org/wiki/%E5%9C%92%E5%86%B6', file: null }
]
export const getSource = id => sources.find(item => item.id === id)
