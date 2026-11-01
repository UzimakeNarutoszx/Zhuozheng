import test from 'node:test'
import assert from 'node:assert/strict'
import { formatHash, parseHash } from '../src/utils/navigation.js'

test('navigation hashes round-trip page and method state', () => {
  assert.deepEqual(parseHash(formatHash('method-detail', 'borrow')), { page: 'method-detail', methodId: 'borrow' })
  assert.deepEqual(parseHash('#gallery'), { page: 'mine', methodId: null, mineTab: 'works' })
})

test('invalid navigation hashes fall back to home', () => {
  assert.deepEqual(parseHash('#unknown'), { page: 'home', methodId: null })
  assert.deepEqual(parseHash('#method-detail'), { page: 'home', methodId: null })
  assert.deepEqual(parseHash('#method-detail/%E0%A4%A'), { page: 'home', methodId: null })
})

test('mine combines works and about while preserving old links', () => {
  assert.deepEqual(parseHash('#mine'), { page: 'mine', methodId: null, mineTab: 'works' })
  assert.deepEqual(parseHash('#mine/about'), { page: 'mine', methodId: null, mineTab: 'about' })
  assert.deepEqual(parseHash(formatHash('mine', 'records')), { page: 'mine', methodId: null, mineTab: 'records' })
  assert.deepEqual(parseHash('#about'), { page: 'mine', methodId: null, mineTab: 'about' })
  assert.equal(formatHash('about'), '#mine/about')
  assert.equal(formatHash('mine', 'works'), '#mine/works')
  assert.equal(parseHash('#chat').page, 'ask')
  assert.equal(parseHash('#ask').page, 'ask')
  assert.equal(parseHash('#login').page, 'login')
})
