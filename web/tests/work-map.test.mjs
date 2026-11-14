import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { gardenPoints } from '../src/data/garden-points.js'

const pointIds = gardenPoints.map(point => point.id)

test('作品地图使用的园内点位完整且唯一', () => {
  assert.equal(gardenPoints.length, 5)
  assert.deepEqual(new Set(pointIds).size, 5)
  for (const point of gardenPoints) {
    assert.ok(point.id && point.name && point.methodId, point.id)
    assert.ok(Number.isFinite(point.lat) && Number.isFinite(point.lng), point.id)
    assert.ok(point.id.length <= 64, `${point.id} 超出后端 pointId 长度限制`)
  }
})

test('后端点位白名单与 garden-points.js 保持一致', async () => {
  const schema = await readFile(new URL('../../backend/app/schemas.py', import.meta.url), 'utf8')
  const whitelist = schema.match(/GARDEN_POINT_IDS\s*=\s*frozenset\(\{([^}]*)\}\)/)
  assert.ok(whitelist, 'schemas.py 缺少 GARDEN_POINT_IDS 常量')
  const backendIds = [...whitelist[1].matchAll(/'([^']+)'/g)].map(match => match[1]).sort()
  assert.deepEqual(backendIds, [...pointIds].sort())
  assert.match(schema, /pointId: str = Field\(default='', max_length=64\)/)
})

test('创作、云端同步与“我的”页面都保留点位标注', async () => {
  const creation = await readFile(new URL('../src/components/CreationCanvas.vue', import.meta.url), 'utf8')
  assert.match(creation, /import \{ gardenPoints \} from '\.\.\/data\/garden-points\.js'/)
  assert.match(creation, /v-model="pointId"/)
  assert.match(creation, /pointId: pointId\.value \|\| ''/)

  // 云端同步是显式字段白名单，漏掉 pointId 会让换设备后地图丢标注。
  const cloud = await readFile(new URL('../src/utils/cloud-work.js', import.meta.url), 'utf8')
  assert.match(cloud, /pointId: work\.pointId \|\| ''/)

  const map = await readFile(new URL('../src/components/GardenMap.vue', import.meta.url), 'utf8')
  assert.match(map, /pointCounts:/)
  assert.match(map, /watch\(\(\) => props\.pointCounts, refreshMarkers/)

  const myPage = await readFile(new URL('../src/components/MyPage.vue', import.meta.url), 'utf8')
  assert.match(myPage, /:point-counts="pointCountMap"/)
  // 旧作品没有 pointId 时只跳过地图，不隐藏作品本身。
  assert.match(myPage, /validIds\.has\(work\.pointId\)/)
  // 脏数据（缺 id / null / 非数组）不能让作品地图 computed 抛异常整块消失。
  assert.match(myPage, /function sanitizeWorkList\(value\)/)
  assert.match(myPage, /try \{ return collectWorkPointCounts/)
})
