import { apiRequest } from './api.js'

export const methodFilters = [{ id: '', label: '全部' }, { id: 'frame', label: '框景' }, { id: 'borrow', label: '借景' }, { id: 'opposition', label: '对景' }, { id: 'leak', label: '漏景' }, { id: 'screen', label: '障景' }]
export function methodLabel(id) { return methodFilters.find(item => item.id === id && id)?.label || '造景' }

const statusText = { pending: '审核中', approved: '已公开', rejected: '未通过', private: '' }
export function reviewLabel(status) { return statusText[status] ?? '' }

export function formatDate(value, now = Date.now()) {
  const time = Date.parse(value || '')
  if (!Number.isFinite(time)) return ''
  const minutes = Math.floor((now - time) / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  if (minutes < 1440) return `${Math.floor(minutes / 60)} 小时前`
  if (minutes < 10080) return `${Math.floor(minutes / 1440)} 天前`
  const date = new Date(time)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

export function shareUrl(id, location = globalThis.location) {
  return `${location.origin}${location.pathname}#community/${encodeURIComponent(id)}`
}

export function feedQuery({ method = '', sort = 'latest', cursor = '' } = {}) {
  const params = new URLSearchParams({ sort, limit: '20' })
  if (method) params.set('method', method)
  if (cursor) params.set('cursor', cursor)
  return `/community/works?${params}`
}

// Samples a damped spring (mass 1) into a CSS linear() easing, so no ease curve is layered on top.
export function springEasing(stiffness, damping, samples = 48) {
  const w0 = Math.sqrt(stiffness), zeta = damping / (2 * w0)
  const settle = Math.min(1.2, 4.6 / (zeta * w0))
  const wd = w0 * Math.sqrt(Math.max(1e-6, 1 - zeta * zeta))
  const points = []
  for (let i = 0; i <= samples; i++) {
    const t = settle * i / samples
    const value = zeta < 1 ? 1 - Math.exp(-zeta * w0 * t) * (Math.cos(wd * t) + zeta * w0 / wd * Math.sin(wd * t)) : 1 - Math.exp(-w0 * t) * (1 + w0 * t)
    points.push(i === samples ? 1 : Number(value.toFixed(4)))
  }
  return { easing: `linear(${points.join(', ')})`, duration: Math.round(settle * 1000) }
}

export function likePop(element) {
  if (!element?.animate || globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
  const { easing, duration } = springEasing(380, 18)
  try { element.animate([{ transform: 'scale(.82)' }, { transform: 'scale(1)' }], { duration, easing }) } catch { /* Browsers without linear() skip the flourish. */ }
}

export const community = {
  feed: (options, token) => apiRequest(feedQuery(options), { token }),
  detail: (id, token) => apiRequest(`/community/works/${encodeURIComponent(id)}`, { token }),
  like: (id, liked, token) => apiRequest(`/community/works/${encodeURIComponent(id)}/like`, { token, method: liked ? 'POST' : 'DELETE' }),
  favorite: (id, saved, token) => apiRequest(`/community/works/${encodeURIComponent(id)}/favorite`, { token, method: saved ? 'POST' : 'DELETE' }),
  favorites: (cursor, token) => apiRequest(`/profile/favorites${cursor ? `?cursor=${cursor}` : ''}`, { token }),
  comments: (id, cursor, token) => apiRequest(`/community/works/${encodeURIComponent(id)}/comments${cursor ? `?cursor=${cursor}` : ''}`, { token }),
  comment: (id, content, token) => apiRequest(`/community/works/${encodeURIComponent(id)}/comments`, { token, body: { content } }),
  removeComment: (cid, token) => apiRequest(`/community/comments/${cid}`, { token, method: 'DELETE' }),
  report: (targetType, targetId, reason, token) => apiRequest('/community/reports', { token, body: { targetType, targetId: String(targetId), reason } }),
  publish: (workId, token) => apiRequest(`/profile/works/${encodeURIComponent(workId)}/publish`, { token, method: 'POST' }),
  unpublish: (workId, token) => apiRequest(`/profile/works/${encodeURIComponent(workId)}/unpublish`, { token, method: 'POST' }),
  queue: (type, token) => apiRequest(`/admin/queue?type=${type}`, { token }),
  reviewWork: (id, action, reason, token) => apiRequest(`/admin/works/${encodeURIComponent(id)}/review`, { token, body: { action, reason } }),
  reviewComment: (cid, action, token) => apiRequest(`/admin/comments/${cid}/review`, { token, body: { action } }),
  resolveReport: (rid, action, token) => apiRequest(`/admin/reports/${rid}/resolve`, { token, body: { action } })
}
