import test from 'node:test'
import assert from 'node:assert/strict'
import { methods } from '../src/data/methods.js'
import { cases } from '../src/data/cases.js'
import { sources } from '../src/data/sources.js'

test('five methods are complete and unique', () => {
  assert.equal(methods.length, 5)
  assert.deepEqual(new Set(methods.map(item => item.id)).size, 5)
  for (const item of methods) assert.ok(item.name && item.summary && item.detail && item.observe && item.image)
})
test('cases and image sources are linked', () => {
  assert.ok(cases.length >= 3)
  for (const item of cases) assert.ok(sources.some(source => source.id === item.sourceId))
})
