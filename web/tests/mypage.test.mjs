import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { gardenPoints } from '../src/data/garden-points.js'

// 与 garden-map.test.mjs 相同的约定：组件里内联纯函数块（带标记），
// 测试直接抽取真实实现求值，避免再复制一份逻辑。
const myPageSource = await readFile(new URL('../src/components/MyPage.vue', import.meta.url), 'utf8')
const pureBlock = myPageSource.match(/\/\* PURE_HELPERS_START[\s\S]*?\*\/([\s\S]*?)\/\* PURE_HELPERS_END \*\//)
assert.ok(pureBlock, 'MyPage.vue 缺少 PURE_HELPERS 标记，纯函数无法被测试')
const pureExports = [
  'isWorkRecord', 'normalizeWorkId', 'sanitizeWorkList', 'collectWorkPointCounts',
  'pointTotal', 'pointRowsWithCounts', 'pointCountObject', 'dedupeLocalWorks'
]
const pureModule = await import(`data:text/javascript;base64,${Buffer.from(`${pureBlock[1]}\nexport { ${pureExports.join(', ')} }`).toString('base64')}`)
const {
  sanitizeWorkList, collectWorkPointCounts, pointTotal,
  pointRowsWithCounts, pointCountObject, dedupeLocalWorks
} = pureModule

const pointIds = new Set(gardenPoints.map(point => point.id))
const [water, bridge] = gardenPoints
const round3dSource = await readFile(new URL('../src/components/RoundWindow3D.vue', import.meta.url), 'utf8')
const mascotSource = await readFile(new URL('../src/components/MascotGuide.vue', import.meta.url), 'utf8')

test('本机作品列表对脏数据只过滤、不抛异常', () => {
  assert.deepEqual(sanitizeWorkList(undefined), [])
  assert.deepEqual(sanitizeWorkList(null), [])
  assert.deepEqual(sanitizeWorkList({}), [], 'localStorage 损坏成对象时不能当数组用')
  assert.deepEqual(sanitizeWorkList('[]'), [])
  assert.deepEqual(sanitizeWorkList([null, undefined, 'x', 3, { id: 'a' }, [{ id: 'nested' }]]), [{ id: 'a' }])
  // 超大 payload 也不应抛异常
  const huge = Array.from({ length: 20000 }, (_, index) => ({ id: `work-${index}`, pointId: index % 2 ? water.id : 'not-a-point' }))
  assert.equal(sanitizeWorkList(huge).length, 20000)
})

test('作品点位计数：同一作品只算一次，合法点位优先，缺 id 也不崩', () => {
  const counts = collectWorkPointCounts({
    works: [
      { id: 'w1', pointId: water.id },
      { id: 'w1', pointId: '' }, // 云端旧副本没有标注
      { id: 'w2', pointId: bridge.id },
      { id: 'w3' }, // 旧作品没有 pointId
      { pointId: water.id }, // 缺 id 的脏数据仍可计数
      { id: null, pointId: bridge.id },
      null,
      undefined
    ],
    cloudWorks: [
      { id: 'w1' }, // 本机已有标注，云端副本不能覆盖成空
      { id: 'w4', pointId: 'illegal-point' }, // 白名单外
      { id: 'w5', pointId: water.id }
    ],
    validPointIds: pointIds
  })
  assert.equal(counts.get(water.id), 3) // w1 + 缺 id 一条 + w5
  assert.equal(counts.get(bridge.id), 2) // w2 + id:null 一条
  assert.equal(counts.size, 2)
  assert.equal(pointTotal(counts), 5)
})

test('点位地图对 undefined / 非法参数返回空结构而不是抛异常', () => {
  assert.deepEqual(collectWorkPointCounts(), new Map())
  assert.deepEqual(collectWorkPointCounts({ works: undefined, cloudWorks: undefined, validPointIds: undefined }), new Map())
  assert.deepEqual(collectWorkPointCounts({ works: 'bad', cloudWorks: {}, validPointIds: 'bad' }), new Map())
  assert.equal(pointTotal(undefined), 0)
  assert.equal(pointTotal(null), 0)
  assert.deepEqual(pointRowsWithCounts(undefined, undefined), [])
  assert.deepEqual(pointRowsWithCounts(gardenPoints, null), [])
  assert.deepEqual(pointCountObject(undefined), {})
})
test('点位地图与 GardenMap 的 pointCounts 结构对齐', () => {
  const counts = new Map([[water.id, 3]])
  const rows = pointRowsWithCounts(gardenPoints, counts)
  assert.equal(rows.length, 1)
  assert.equal(rows[0].id, water.id)
  assert.equal(rows[0].count, 3)
  assert.ok(rows[0].lat !== undefined, '地图点位需要保留经纬度')
  assert.deepEqual(pointCountObject(counts), { [water.id]: 3 })
  // 点位数据异常时跳过，不污染地图
  assert.deepEqual(pointRowsWithCounts([null, undefined, { id: water.id }], counts), [{ id: water.id, count: 3 }])
})

test('待导入作品去重：云端 null/undefined 项不会让 some(cloud.id) 抛错', () => {
  const local = [{ id: 'a', title: '本机 A' }, { id: 'b', title: '本机 B' }, null, { title: '没有 id 的旧作品' }]
  const cloud = [{ id: 'a' }, null, undefined, {}]
  const pending = dedupeLocalWorks(local, cloud)
  assert.deepEqual(pending.map(work => work.title), ['本机 B', '没有 id 的旧作品'])
  assert.deepEqual(dedupeLocalWorks(undefined, undefined), [])
  assert.deepEqual(dedupeLocalWorks(local, 'bad'), local.filter(Boolean))
})

test('云端 /profile/works 失败只提示，不阻断本机作品列表', async () => {
  // loadCloud 必须有 try/finally，任何分支都把 cloudLoading 落回 false。
  const loadCloud = myPageSource.match(/async function loadCloud\(\) \{[\s\S]*?\n\}/)
  assert.ok(loadCloud, 'MyPage.vue 缺少 loadCloud')
  assert.match(loadCloud[0], /try \{/)
  assert.match(loadCloud[0], /finally \{/)
  assert.match(loadCloud[0], /cloudLoading\.value = false/)
  assert.match(loadCloud[0], /catch \(error\) \{[\s\S]*?handleError\(error\)/)
  // 云端数据先过 sanitize，null/非数组都不会写入渲染列表。
  assert.match(loadCloud[0], /cloudWorks\.value = sanitizeWorkList\(data\)/)
  // 本机作品列表用安全后的数组独立渲染，不依赖 user / cloudError。
  assert.match(myPageSource, /:works="safeWorks"/)
  assert.match(myPageSource, /data-cloud-state="cloudState"/)
  assert.match(myPageSource, /:works="safeWorks"/)
  assert.match(myPageSource, /v-if="cloudError"[^]*?重新加载/)
})

test('401 只触发 session-expired，本机 works 不能被清空', () => {
  const handleError = myPageSource.match(/function handleError\(error\) \{[\s\S]*?\n\}/)
  assert.ok(handleError, 'MyPage.vue 缺少 handleError')
  assert.match(handleError[0], /error\?\.status === 401/)
  assert.match(handleError[0], /emit\('session-expired'\)/)
  // 本机作品来源只有 props.works，401 路径不能写 works / localStorage。
  assert.doesNotMatch(handleError[0], /works\s*=/)
  assert.doesNotMatch(myPageSource, /removeItem\(|clearSession\(/)
})

test('进入我的页会预加载钱钱模型，3D 失败自动重试一次', () => {
  assert.match(myPageSource, /import \{ preloadCharacter \} from '\.\/RoundWindow3D\.vue'/)
  assert.match(myPageSource, /preloadCharacter\('coin'\)/)
  assert.match(myPageSource, /requestIdleCallback\(warm/)
  assert.match(round3dSource, /export function preloadCharacter\(character = 'coin'\)/)
  assert.match(round3dSource, /MASCOT_RETRY_LIMIT/)
  assert.match(round3dSource, /MASCOT_RETRY_DELAY/)
  assert.match(round3dSource, /attemptState\.canRetry/)
  assert.match(round3dSource, /:data-status="status"/)
  assert.match(round3dSource, /:data-attempts="attempts"/)
  assert.match(round3dSource, /defineExpose\(\{ retry \}\)/)
  // 预加载和挂载共用同一份缓存，不会重复下载；模型交给组件后从缓存移除。
  assert.match(round3dSource, /takeCharacterModel/)
  assert.match(round3dSource, /warmModels\.delete\(file\)/)
})

test('吉祥物暴露 data-reveal 状态，失败时提供手动重试', () => {
  assert.match(mascotSource, /:data-reveal="revealState"/)
  assert.match(mascotSource, /:data-model="mascot\.model \|\| 'none'"/)
  assert.match(mascotSource, /revealState === 'failed'/)
  assert.match(mascotSource, /重试动态形象/)
  assert.match(mascotSource, /reveal\?\.retry\(\)/)
  assert.match(mascotSource, /stage\.value\?\.retry\(\)/)
})
