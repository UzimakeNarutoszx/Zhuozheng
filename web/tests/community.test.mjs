import test from 'node:test'
import assert from 'node:assert/strict'
import { feedQuery, formatDate, methodLabel, reviewLabel, shareUrl, springEasing } from '../src/utils/community.js'
import { formatHash, parseHash } from '../src/utils/navigation.js'

const id = 'a'.repeat(32)

test('community hashes route the feed and a single work', () => {
  assert.deepEqual(parseHash('#community'), { page: 'community', methodId: null, communityId: null })
  assert.deepEqual(parseHash(formatHash('community', id)), { page: 'community', methodId: null, communityId: id })
  assert.equal(parseHash('#community/not-an-id').communityId, null)
  assert.deepEqual(parseHash('#mine/review'), { page: 'mine', methodId: null, mineTab: 'review' })
})

test('feed query only sends filters that are set', () => {
  assert.equal(feedQuery(), '/community/works?sort=latest&limit=20')
  assert.equal(feedQuery({ method: 'borrow', sort: 'popular', cursor: '3.9' }), '/community/works?sort=popular&limit=20&method=borrow&cursor=3.9')
})

test('labels and relative dates', () => {
  assert.equal(methodLabel('screen'), '障景')
  assert.equal(methodLabel(''), '造景')
  assert.equal(reviewLabel('pending'), '审核中')
  assert.equal(reviewLabel('private'), '')
  const now = Date.parse('2026-11-01T12:00:00Z')
  assert.equal(formatDate('2026-11-01T11:59:40Z', now), '刚刚')
  assert.equal(formatDate('2026-11-01T11:00:00Z', now), '1 小时前')
  assert.equal(formatDate('2026-10-29T12:00:00Z', now), '3 天前')
  assert.equal(formatDate('bad', now), '')
})

test('share links point at the work hash', () => {
  assert.equal(shareUrl(id, { origin: 'http://127.0.0.1:4173', pathname: '/' }), `http://127.0.0.1:4173/#community/${id}`)
})

test('like spring overshoots once and settles at 1', () => {
  const { easing, duration } = springEasing(380, 18)
  const points = easing.slice(7, -1).split(', ').map(Number)
  assert.equal(points[0], 0)
  assert.equal(points.at(-1), 1)
  assert.ok(Math.max(...points) > 1 && Math.max(...points) < 1.2)
  assert.ok(duration > 200 && duration <= 1200)
})
