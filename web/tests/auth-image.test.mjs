import test from 'node:test'
import assert from 'node:assert/strict'
import { imageCacheSize, loadAuthImage, revokeAll } from '../src/utils/auth-image.js'

const thumb = '/api/v1/media/thumb/' + 'a'.repeat(32) + '.webp'
const full = '/api/v1/media/full/' + 'b'.repeat(32) + '.webp'

function stubObjectUrls() {
  const created = [], revoked = []
  const original = { create: URL.createObjectURL, revoke: URL.revokeObjectURL }
  URL.createObjectURL = blob => { const url = `blob:test/${created.length + 1}`; created.push({ url, blob }); return url }
  URL.revokeObjectURL = url => { revoked.push(url) }
  return { created, revoked, restore() { URL.createObjectURL = original.create; URL.revokeObjectURL = original.revoke } }
}

function stubFetch(handler) {
  const original = globalThis.fetch
  const calls = []
  globalThis.fetch = async (url, init) => { calls.push({ url, init }); return handler(url, init, calls.length) }
  return { calls, restore() { if (original) globalThis.fetch = original; else delete globalThis.fetch } }
}

function imageResponse(bytes = 'webp') {
  return new Response(new Blob([bytes], { type: 'image/webp' }), { status: 200 })
}

test('loads protected images with a bearer header and reuses the cached blob URL', async () => {
  revokeAll()
  const urls = stubObjectUrls()
  const fetched = stubFetch(() => imageResponse())
  try {
    const first = await loadAuthImage(thumb, 'secret-token')
    assert.equal(first, 'blob:test/1')
    assert.equal(urls.created.length, 1)
    assert.equal(fetched.calls.length, 1)
    assert.equal(fetched.calls[0].url, thumb)
    assert.deepEqual(fetched.calls[0].init.headers, { Authorization: 'Bearer secret-token' })
    assert.ok(!fetched.calls[0].url.includes('secret-token'), 'the token never goes into the URL')
    const second = await loadAuthImage(thumb, 'secret-token')
    assert.equal(second, first)
    assert.equal(fetched.calls.length, 1, 'the same URL is served from the cache')
    assert.equal(imageCacheSize(), 1)
  } finally {
    revokeAll()
    fetched.restore()
    urls.restore()
  }
})

test('anonymous requests omit the Authorization header', async () => {
  revokeAll()
  const urls = stubObjectUrls()
  const fetched = stubFetch(() => imageResponse())
  try {
    await loadAuthImage(thumb)
    assert.deepEqual(fetched.calls[0].init.headers, {})
    assert.equal(imageCacheSize(), 1)
  } finally {
    revokeAll()
    fetched.restore()
    urls.restore()
  }
})

test('concurrent requests for one URL share a single fetch and blob URL', async () => {
  revokeAll()
  const urls = stubObjectUrls()
  let release
  const fetched = stubFetch(() => new Promise(resolve => { release = resolve }))
  try {
    const pending = [loadAuthImage(thumb, 'token'), loadAuthImage(thumb, 'token')]
    assert.equal(fetched.calls.length, 1)
    release(imageResponse())
    const [a, b] = await Promise.all(pending)
    assert.equal(a, b)
    assert.equal(fetched.calls.length, 1)
    assert.equal(urls.created.length, 1)
  } finally {
    revokeAll()
    fetched.restore()
    urls.restore()
  }
})

test('a rejected response creates no blob URL and a retry fetches again', async () => {
  revokeAll()
  const urls = stubObjectUrls()
  const fetched = stubFetch((url, init, count) => count === 1 ? new Response('denied', { status: 403 }) : imageResponse())
  try {
    await assert.rejects(loadAuthImage(thumb, 'token'), /没有查看权限/)
    assert.equal(urls.created.length, 0)
    assert.equal(imageCacheSize(), 0)
    const retry = await loadAuthImage(thumb, 'token')
    assert.equal(retry, 'blob:test/1')
    assert.equal(fetched.calls.length, 2)
  } finally {
    revokeAll()
    fetched.restore()
    urls.restore()
  }
})

test('network and empty-body failures reject without caching', async () => {
  revokeAll()
  const urls = stubObjectUrls()
  const offline = stubFetch(() => { throw new TypeError('Failed to fetch') })
  try {
    await assert.rejects(loadAuthImage(thumb, 'token'), /网络异常/)
    assert.equal(imageCacheSize(), 0)
  } finally {
    revokeAll()
    offline.restore()
  }
  const empty = stubFetch(() => new Response(new Blob([]), { status: 200 }))
  try {
    await assert.rejects(loadAuthImage(full, 'token'), /图片加载失败/)
    assert.equal(imageCacheSize(), 0)
    assert.equal(urls.created.length, 0)
  } finally {
    revokeAll()
    empty.restore()
    urls.restore()
  }
})

test('revokeAll releases every cached blob URL and clears reuse', async () => {
  revokeAll()
  const urls = stubObjectUrls()
  const fetched = stubFetch(() => imageResponse())
  try {
    await loadAuthImage(thumb, 'token')
    await loadAuthImage(full, 'token')
    assert.deepEqual(urls.created.map(entry => entry.url), ['blob:test/1', 'blob:test/2'])
    revokeAll()
    assert.deepEqual(urls.revoked, ['blob:test/1', 'blob:test/2'])
    assert.equal(imageCacheSize(), 0)
    await loadAuthImage(thumb, 'token')
    assert.equal(fetched.calls.length, 3, 'released URLs are fetched again')
    assert.equal(urls.created.at(-1).url, 'blob:test/3')
  } finally {
    revokeAll()
    fetched.restore()
    urls.restore()
  }
})

test('revoking while a fetch is in flight never leaks the object URL', async () => {
  revokeAll()
  const urls = stubObjectUrls()
  let release
  const fetched = stubFetch(() => new Promise(resolve => { release = resolve }))
  try {
    const pending = loadAuthImage(thumb, 'token')
    revokeAll()
    release(imageResponse())
    await assert.rejects(pending, /图片已释放/)
    assert.equal(urls.created.length, 1)
    assert.deepEqual(urls.revoked, urls.created.map(entry => entry.url))
    assert.equal(imageCacheSize(), 0)
  } finally {
    revokeAll()
    fetched.restore()
    urls.restore()
  }
})
