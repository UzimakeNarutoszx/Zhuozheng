import { assetUrl } from './assets.js'

// Some media (works still under review) is only served to the author or an admin and
// needs an Authorization header. <img src> cannot send one, so fetch the bytes here and
// hand the component a same-origin object URL instead. The token never enters a URL.
const cache = new Map()
let epoch = 0

async function requestImage(src, token, signal) {
  let response
  try {
    response = await fetch(src, { signal, headers: token ? { Authorization: `Bearer ${token}` } : {} })
  } catch (error) {
    if (error?.name === 'AbortError' || signal.aborted) throw error
    throw new Error('网络异常，图片加载失败')
  }
  if (!response.ok) throw new Error(response.status === 403 || response.status === 404 ? '图片不存在或没有查看权限' : '图片加载失败')
  const blob = await response.blob().catch(() => null)
  if (!blob || !blob.size) throw new Error('图片加载失败')
  return URL.createObjectURL(blob)
}

// Resolves to a blob: URL for the image, reusing one fetch per URL. Call revokeAll()
// when the list changes or the owning component unmounts.
export function loadAuthImage(url, token) {
  const src = assetUrl(url)
  if (!src) return Promise.reject(new Error('图片地址为空'))
  const cached = cache.get(src)
  if (cached) return cached.promise
  const startedAt = epoch
  const controller = new AbortController()
  const entry = { objectUrl: '', controller, promise: null }
  entry.promise = requestImage(src, token, controller.signal).then(objectUrl => {
    // revokeAll() ran while the fetch was in flight: never hand out a leaked URL.
    if (startedAt !== epoch) { URL.revokeObjectURL(objectUrl); throw new Error('图片已释放') }
    entry.objectUrl = objectUrl
    return objectUrl
  })
  cache.set(src, entry)
  entry.promise.catch(() => { if (cache.get(src) === entry) cache.delete(src) })
  return entry.promise
}

export function revokeAll() {
  epoch += 1
  for (const entry of cache.values()) {
    entry.controller.abort()
    if (entry.objectUrl) URL.revokeObjectURL(entry.objectUrl)
  }
  cache.clear()
}

export function imageCacheSize() {
  return cache.size
}
