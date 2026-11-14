import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { gardenPoints } from '../src/data/garden-points.js'

// 约束要求只改 GardenMap.vue 和 tests/，因此纯逻辑内联在组件里；
// 这里按标记抽出纯函数块在 Node 中求值，直接测真实实现（不是复制一份）。
const mapSource = await readFile(new URL('../src/components/GardenMap.vue', import.meta.url), 'utf8')
const pureBlock = mapSource.match(/\/\* PURE_HELPERS_START[\s\S]*?\*\/([\s\S]*?)\/\* PURE_HELPERS_END \*\//)
assert.ok(pureBlock, 'GardenMap.vue 缺少 PURE_HELPERS 标记，纯函数无法被测试')
const pureExports = [
  'TILE_SOURCES', 'TILE_PRECONNECT_HOSTS', 'TILE_ERROR_LIMIT', 'TILE_TIMEOUT_MS',
  'GARDEN_CENTER', 'FALLBACK_PADDING', 'createTileState', 'gardenBounds', 'latLngToPercent', 'advanceTileState'
]
const pureModule = await import(`data:text/javascript;base64,${Buffer.from(`${pureBlock[1]}\nexport { ${pureExports.join(', ')} }`).toString('base64')}`)
const {
  TILE_SOURCES, TILE_PRECONNECT_HOSTS, TILE_ERROR_LIMIT, TILE_TIMEOUT_MS,
  GARDEN_CENTER, createTileState, gardenBounds, latLngToPercent, advanceTileState
} = pureModule

function clickErrors(times, state = createTileState()) {
  let next = state
  for (let i = 0; i < times; i += 1) next = advanceTileState(next, { type: 'tileerror' })
  return next
}

test('主备瓦片源均为公开 https 地址且不带 key', () => {
  assert.equal(TILE_SOURCES.length, 2)
  assert.equal(TILE_SOURCES[0].id, 'osm')
  assert.match(TILE_SOURCES[0].url, /^https:\/\/tile\.openstreetmap\.org\/\{z\}\/\{x\}\/\{y\}\.png$/)
  assert.equal(TILE_SOURCES[1].url, 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}')
  for (const source of TILE_SOURCES) {
    assert.match(source.url, /^https:\/\//, `${source.id} 必须走 https`)
    assert.ok(source.attribution, `${source.id} 需要版权署名`)
    assert.ok(!/[?&](?:key|token|apikey)=/i.test(source.url), `${source.id} 不能内置 key`)
  }
  // preconnect 主机与瓦片源一致，避免连到无关域名
  for (const host of TILE_PRECONNECT_HOSTS) {
    assert.ok(TILE_SOURCES.some(source => source.url.startsWith(host)), `${host} 没有对应的瓦片源`)
  }
  assert.equal(TILE_TIMEOUT_MS, 8000)
  assert.ok(TILE_ERROR_LIMIT >= 2 && TILE_ERROR_LIMIT <= 5, '连续瓦片错误阈值应在 2-5 之间')
})

test('经纬度包围盒完整覆盖园内点位并留出边距', () => {
  const bounds = gardenBounds(gardenPoints)
  const lats = gardenPoints.map(point => point.lat)
  const lngs = gardenPoints.map(point => point.lng)
  assert.ok(bounds.latMin < Math.min(...lats))
  assert.ok(bounds.latMax > Math.max(...lats))
  assert.ok(bounds.lngMin < Math.min(...lngs))
  assert.ok(bounds.lngMax > Math.max(...lngs))
  assert.ok(bounds.latMax > bounds.latMin && bounds.lngMax > bounds.lngMin)
  // 空数据也不能算出 NaN 包围盒
  const empty = gardenBounds([])
  assert.ok(Number.isFinite(empty.latMin) && Number.isFinite(empty.lngMax))
})

test('经纬度到百分比是线性映射：东→x 增大、北→y 减小', () => {
  // 用人工包围盒验证精确数值，避免测试和实现共用同一套点位数据自我循环。
  const bounds = { latMin: 0, latMax: 10, lngMin: 100, lngMax: 110 }
  assert.deepEqual(latLngToPercent({ lat: 2.5, lng: 107.5 }, bounds), { x: 75, y: 75 })
  assert.deepEqual(latLngToPercent({ lat: 10, lng: 100 }, bounds), { x: 0, y: 0 })
  assert.deepEqual(latLngToPercent({ lat: 0, lng: 110 }, bounds), { x: 100, y: 100 })

  const gardenBox = gardenBounds(gardenPoints)
  const midLat = (Math.min(...gardenPoints.map(point => point.lat)) + Math.max(...gardenPoints.map(point => point.lat))) / 2
  const midLng = (Math.min(...gardenPoints.map(point => point.lng)) + Math.max(...gardenPoints.map(point => point.lng))) / 2
  const middle = latLngToPercent({ lat: midLat, lng: midLng }, gardenBox)
  assert.ok(Math.abs(middle.x - 50) < 0.001 && Math.abs(middle.y - 50) < 0.001, '包围盒中心应映射到 50% / 50%')

  const west = gardenPoints.reduce((a, b) => (a.lng <= b.lng ? a : b))
  const east = gardenPoints.reduce((a, b) => (a.lng >= b.lng ? a : b))
  const south = gardenPoints.reduce((a, b) => (a.lat <= b.lat ? a : b))
  const north = gardenPoints.reduce((a, b) => (a.lat >= b.lat ? a : b))
  assert.ok(latLngToPercent(east, gardenBox).x > latLngToPercent(west, gardenBox).x)
  assert.ok(latLngToPercent(north, gardenBox).y < latLngToPercent(south, gardenBox).y)

  for (const point of gardenPoints) {
    const percent = latLngToPercent(point, gardenBox)
    assert.ok(Number.isFinite(percent.x) && Number.isFinite(percent.y), `${point.id} 映射出了非数字`)
    assert.ok(percent.x >= 0 && percent.x <= 100 && percent.y >= 0 && percent.y <= 100, `${point.id} 超出容器范围`)
    // 园内点位应落在四周留白之内，不会贴边被裁掉
    assert.ok(percent.x > 5 && percent.x < 95 && percent.y > 5 && percent.y < 95)
  }
})

test('越界经纬度夹到 0-100，避免圆点跑出降级图', () => {
  const bounds = { latMin: 0, latMax: 10, lngMin: 0, lngMax: 10 }
  assert.deepEqual(latLngToPercent({ lat: 99, lng: 99 }, bounds), { x: 100, y: 0 })
  assert.deepEqual(latLngToPercent({ lat: -99, lng: -99 }, bounds), { x: 0, y: 100 })
  assert.deepEqual(latLngToPercent({ lat: NaN, lng: undefined }, bounds), { x: 50, y: 50 })
})

test('状态机：loading → 连续 tileerror → 备用源 → failed → retry → ready', () => {
  let state = createTileState()
  assert.equal(state.status, 'loading')
  assert.equal(state.sourceIndex, 0)
  assert.equal(state.backupTried, false)

  // 未达阈值继续 loading，不打断首屏
  state = clickErrors(1, state)
  assert.equal(state.status, 'loading')
  assert.equal(state.sourceIndex, 0)
  state = clickErrors(TILE_ERROR_LIMIT - 1, state)
  assert.equal(state.status, 'loading')
  assert.equal(state.sourceIndex, 1, '主源连续失败后应自动切备用源')
  assert.equal(state.backupTried, true)

  // 备用源也连续失败才进入 failed（此时显示降级示意图）
  state = clickErrors(TILE_ERROR_LIMIT, state)
  assert.equal(state.status, 'failed')
  assert.equal(state.sourceIndex, 1)

  // 重试重建 layer：回到主源、错误清零、generation 递增以便忽略旧事件
  const generationBefore = state.generation
  state = advanceTileState(state, { type: 'retry' })
  assert.equal(state.status, 'loading')
  assert.equal(state.sourceIndex, 0)
  assert.equal(state.backupTried, false)
  assert.equal(state.errors, 0)
  assert.equal(state.generation, generationBefore + 1)

  // 任一瓦片成功即 ready
  state = advanceTileState(state, { type: 'tileload' })
  assert.equal(state.status, 'ready')
})

test('8s 超时同样先尝试备用源，备用源超时才 failed', () => {
  let state = advanceTileState(createTileState(), { type: 'timeout' })
  assert.equal(state.status, 'loading')
  assert.equal(state.sourceIndex, 1)

  state = advanceTileState(state, { type: 'timeout' })
  assert.equal(state.status, 'failed')

  state = advanceTileState(state, { type: 'tileload' })
  assert.equal(state.status, 'failed', '失败后迟到的瓦片不应悄悄恢复')

  state = advanceTileState(state, { type: 'retry' })
  assert.equal(state.status, 'loading')
  state = advanceTileState(state, { type: 'tileload' })
  assert.equal(state.status, 'ready')
})

test('全部瓦片报错（含 load 事件但零成功）也走备用/失败路径', () => {
  let state = advanceTileState(createTileState(), { type: 'allerror' })
  assert.equal(state.status, 'loading')
  assert.equal(state.sourceIndex, 1)
  state = advanceTileState(state, { type: 'allerror' })
  assert.equal(state.status, 'failed')
})

test('ready 之后忽略迟到的失败事件，但允许手动 retry 重新加载', () => {
  let state = advanceTileState(createTileState(), { type: 'tileload' })
  assert.equal(state.status, 'ready')
  assert.equal(advanceTileState(state, { type: 'tileerror' }), state)
  assert.equal(advanceTileState(state, { type: 'timeout' }), state)
  assert.equal(advanceTileState(state, { type: 'allerror' }), state)

  state = advanceTileState(state, { type: 'retry' })
  assert.equal(state.status, 'loading')
  assert.equal(state.sourceIndex, 0)
})

test('组件在 failed 时渲染不依赖网络的降级图，并在成功时隐藏', () => {
  // 降级层只在 failed 分支渲染，ready 时整层移除 → 不遮挡瓦片
  assert.match(mapSource, /v-else-if="tileState\.status === 'failed'" class="map-fallback"/)
  assert.match(mapSource, /class="map-fallback-art"/)
  assert.match(mapSource, /<svg class="map-fallback-art"[\s\S]*?<\/svg>/)
  // 点位由经纬度线性映射成百分比定位，且不回源加载图片
  assert.match(mapSource, /fallbackPoints = gardenPoints\.map\(point => \(\{ point, \.\.\.latLngToPercent\(point, fallbackBounds\) \}\)\)/)
  assert.match(mapSource, /:style="\{ left: item\.x \+ '%', top: item\.y \+ '%' \}"/)
  assert.doesNotMatch(mapSource.slice(mapSource.indexOf('class="map-fallback"'), mapSource.indexOf('class="map-live')), /<img\b/, '降级图不能依赖图片网络加载')
  // 失败文案与重试按钮、成功后的 aria-live 提示
  assert.match(mapSource, /地图加载失败，点击重试/)
  assert.match(mapSource, /地图已加载/)
  assert.match(mapSource, /aria-live="polite"/)
  // 容器尺寸由既有 .garden-map min-height 决定，降级层绝对定位，不改变布局高度
  assert.match(mapSource, /\.map-fallback \{ position: absolute; inset: 0;/)
  // 主备切换、超时判定与 preconnect
  assert.match(mapSource, /layer\.on\('tileerror'/)
  assert.match(mapSource, /TILE_TIMEOUT_MS\)/)
  assert.match(mapSource, /ensurePreconnect/)
  assert.match(mapSource, /startTileCycle\(next\.sourceIndex\)/)
})

test('状态类加在外层：Vue 不能 patch Leaflet 自己维护的 class', () => {
  // 回归：动态 :class 直接写在 .garden-map 上会在状态切换时覆盖 Leaflet 的
  // leaflet-container 等 class，导致重试后地图瓦片错位/只剩一角。
  assert.match(mapSource, /<div class="garden-map-frame" :class="\{ 'is-degraded': tileState\.status === 'failed' \}">/)
  const mapTag = mapSource.match(/<div ref="mapElement"[^>]*>/)
  assert.ok(mapTag, '找不到地图容器节点')
  assert.match(mapTag[0], /class="garden-map"/)
  assert.doesNotMatch(mapTag[0], /:class=/, '地图容器上不能有 Vue 动态 class 绑定')
  assert.match(mapSource, /\.garden-map-frame\.is-degraded :deep\(\.leaflet-control-container\) \{ display: none; \}/)
})
