import test from 'node:test'
import assert from 'node:assert/strict'
import { canUseStorage, getSourceImage, readWorks, removeWork, writeWork } from '../src/utils/local-work.js'

function createStorage({ fail = false } = {}) {
  const data = new Map()
  return {
    getItem: key => data.get(key) || null,
    setItem: (key, value) => { if (fail) throw new Error('quota'); data.set(key, value) },
    removeItem: key => data.delete(key)
  }
}

test('works preserve newest-first ordering and replace by id', () => {
  globalThis.localStorage = createStorage()
  writeWork({ id: 'one', title: '旧' })
  writeWork({ id: 'two', title: '新' })
  writeWork({ id: 'one', title: '更新' })
  assert.deepEqual(readWorks().map(work => work.id), ['one', 'two'])
  assert.equal(readWorks()[0].title, '更新')
})

test('storage failures are reported to the caller', () => {
  globalThis.localStorage = createStorage({ fail: true })
  assert.equal(canUseStorage(), false)
  assert.throws(() => writeWork({ id: 'one' }), error => error.code === 'STORAGE_WRITE_FAILED')
  assert.throws(() => removeWork('one'), error => error.code === 'STORAGE_WRITE_FAILED')
})

test('old works fall back to the composed image while new works use the source image', () => {
  assert.equal(getSourceImage({ imageDataUrl: 'composed' }), 'composed')
  assert.equal(getSourceImage({ sourceImageDataUrl: 'source', imageDataUrl: 'composed' }), 'source')
})
