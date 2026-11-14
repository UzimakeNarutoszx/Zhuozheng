import test from 'node:test'
import assert from 'node:assert/strict'
import { gardenRoutes, isRoutesHash } from '../src/data/routes.js'
import { gardenPoints } from '../src/data/garden-points.js'
import { methods } from '../src/data/methods.js'

const pointIds = new Set(gardenPoints.map(point => point.id))
const methodIds = new Set(methods.map(method => method.id))
const pointsById = new Map(gardenPoints.map(point => [point.id, point]))

test('三条路线结构完整，每条 5-7 站且 pointId 都存在于 garden-points', () => {
  assert.equal(gardenRoutes.length, 3)
  assert.deepEqual(new Set(gardenRoutes.map(route => route.id)).size, 3)
  const titles = gardenRoutes.map(route => route.title)
  assert.ok(titles.includes('1 小时精华') && titles.includes('半日深度') && titles.includes('摄影机位'), titles.join(' / '))
  for (const route of gardenRoutes) {
    assert.ok(route.id && route.title && route.subtitle && route.duration, route.id)
    assert.ok(route.stops.length >= 5 && route.stops.length <= 7, `${route.title} 有 ${route.stops.length} 站`)
    for (const stop of route.stops) {
      assert.ok(pointIds.has(stop.pointId), `${route.title} 的 ${stop.pointId} 不在 garden-points 中`)
      assert.ok(stop.name && stop.name.trim(), `${route.title} 缺少站名`)
      assert.ok(stop.note && stop.note.trim().length >= 12, `${route.title} 的「${stop.name}」缺少一句话说明`)
    }
  }
})

test('路线覆盖全部点位，并与现有手法数据保持一致', () => {
  const used = new Set(gardenRoutes.flatMap(route => route.stops.map(stop => stop.pointId)))
  assert.deepEqual([...used].sort(), [...pointIds].sort())
  for (const route of gardenRoutes) {
    for (const stop of route.stops) {
      const methodId = pointsById.get(stop.pointId).methodId
      assert.ok(methodIds.has(methodId), `${stop.pointId} 的手法 ${methodId} 不存在`)
    }
  }
})

test('#routes 是园内路线页的哈希标识，且不影响其它页面哈希', () => {
  assert.equal(isRoutesHash('#routes'), true)
  assert.equal(isRoutesHash('routes'), true)
  assert.equal(isRoutesHash('#routes/'), false)
  for (const hash of ['', '#home', '#methods', '#explore', '#community', '#method-detail/borrow']) {
    assert.equal(isRoutesHash(hash), false, hash)
  }
})
