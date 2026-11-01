import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile, access } from 'node:fs/promises'
import { assetUrl, imageSrcset } from '../src/utils/assets.js'
import { createLatestImageRequest, loadImage } from '../src/utils/image-loader.js'
import { imageVariants } from '../src/data/image-variants.js'

test('asset URLs support subpath hosting and preserve uploaded/remote sources', () => {
  assert.equal(assetUrl('/assets/garden/a.jpg', '/garden/'), '/garden/assets/garden/a.jpg')
  assert.equal(assetUrl('/api/v1/media/thumb/abc.webp', '/garden/'), '/garden/api/v1/media/thumb/abc.webp')
  assert.equal(assetUrl('data:image/png;base64,abc', '/garden/'), 'data:image/png;base64,abc')
  assert.equal(assetUrl('https://example.com/photo.jpg', '/garden/'), 'https://example.com/photo.jpg')
  assert.ok(imageSrcset('/assets/garden/garden-001.jpg').includes('480w'))
})

test('responsive image manifest only references existing files and excludes private research documents', async () => {
  for (const [original, variants] of Object.entries(imageVariants)) {
    await access(new URL(`../public${original}`, import.meta.url))
    for (const variant of variants) {
      const bytes = await readFile(new URL(`../public${variant.src}`, import.meta.url))
      assert.equal(bytes.toString('ascii', 8, 12), 'WEBP')
      assert.ok(bytes.length > 0)
    }
  }
  await assert.rejects(access(new URL('../public/materials/jiangnan-research-report.docx', import.meta.url)))
  await assert.rejects(access(new URL('../public/materials/paper-writing-method.docx', import.meta.url)))
})

test('out-of-order frame or uploaded image responses cannot replace the latest selection', async () => {
  const pending = new Map()
  const request = createLatestImageRequest(src => new Promise((resolve, reject) => pending.set(src, { resolve, reject })))
  const round = request.load('round'), square = request.load('square')
  pending.get('square').resolve({ src: 'square' })
  assert.deepEqual(await square, { src: 'square' })
  pending.get('round').resolve({ src: 'round' })
  assert.equal(await round, null)
  const photo = request.load('photo')
  request.cancel()
  pending.get('photo').reject(new Error('old upload failed'))
  assert.equal(await photo, null)
})

test('failed cached image loads can be retried and successful frame loads are shared', async () => {
  const previous = globalThis.Image
  const images = []
  globalThis.Image = class { constructor() { images.push(this) } }
  try {
    const first = loadImage('/test-frame.png', { cached: true })
    assert.equal(loadImage('/test-frame.png', { cached: true }), first)
    images[0].onerror()
    await assert.rejects(first, /图片加载失败/)
    const retry = loadImage('/test-frame.png', { cached: true })
    assert.equal(images.length, 2)
    images[1].onload()
    assert.equal(await retry, images[1])
    assert.equal(await loadImage('/test-frame.png', { cached: true }), images[1])
  } finally { globalThis.Image = previous }
})
