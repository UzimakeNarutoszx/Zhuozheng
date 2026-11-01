const pages = new Set(['home', 'methods', 'method-detail', 'explore', 'studio', 'archive', 'mine', 'login', 'ask', 'community'])
const mineTabs = ['about', 'records', 'review']

export function parseHash(hash = '') {
  const value = hash.replace(/^#/, '').trim()
  if (!value) return { page: 'home', methodId: null }
  let parts
  try { parts = value.split('/').map(decodeURIComponent) } catch { return { page: 'home', methodId: null } }
  let [page, methodId] = parts
  if (page === 'chat') page = 'ask'
  if (page === 'gallery') return { page: 'mine', methodId: null, mineTab: 'works' }
  if (page === 'about') return { page: 'mine', methodId: null, mineTab: 'about' }
  if (!pages.has(page) || (page === 'method-detail' && !methodId)) return { page: 'home', methodId: null }
  if (page === 'mine') return { page, methodId: null, mineTab: mineTabs.includes(methodId) ? methodId : 'works' }
  if (page === 'community') return { page, methodId: null, communityId: /^[a-f0-9]{32}$/.test(methodId || '') ? methodId : null }
  return { page, methodId: page === 'method-detail' ? methodId : null }
}

export function formatHash(page, methodId = null) {
  if (page === 'chat') return '#ask'
  if (page === 'gallery') return '#mine/works'
  if (page === 'about') return '#mine/about'
  if (page === 'mine') return `#mine/${mineTabs.includes(methodId) ? methodId : 'works'}`
  if (page === 'community') return methodId ? `#community/${encodeURIComponent(methodId)}` : '#community'
  if (page === 'method-detail' && methodId) return `#${page}/${encodeURIComponent(methodId)}`
  return `#${page}`
}
