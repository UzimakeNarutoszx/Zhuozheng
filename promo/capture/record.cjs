// 宣传片录屏：每个镜头单独一个浏览器上下文录制手机竖屏 webm，并记录内容就绪时间点
// 用法: node promo/capture/record.cjs [镜头名...]（镜头名取 clip 文件名，如 home methods）
// 依赖本机已启动的 4173 网站、8011 后端；PLAYWRIGHT_PATH 指向本机 playwright 包
// 画面用 CDP screencast 逐帧取 JPEG（带真实时间戳），再用系统 ffmpeg 编码成 780x1688 的 webm
const fs = require('fs')
const path = require('path')
const { execFileSync } = require('child_process')
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright')

const ROOT = path.resolve(__dirname, '../..')
const OUT = path.join(ROOT, 'output/promo-video/capture')
const TIMELINE = JSON.parse(fs.readFileSync(path.join(ROOT, 'promo/timeline.json'), 'utf8'))
const BASE = TIMELINE.url
const PHOTO = path.join(ROOT, 'web/public/assets/garden/garden-001.jpg')
const MOBILE = { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 }
const VIDEO = { width: 780, height: 1688 }
const EXTRA = 2.0 // 镜头时长之外多录的余量，供后期取用
// 只在录制页内生效：隐藏滚动条与鼠标指针，隐藏梅梅导览浮层（左下角挡住地图与卡片）
const HIDE = 'html{scroll-behavior:auto!important}' +
  '::-webkit-scrollbar{width:0!important;height:0!important;display:none!important}' +
  '*{scrollbar-width:none!important;cursor:none!important}' +
  '.mascot-guide{display:none!important}'

const sleep = ms => new Promise(r => setTimeout(r, ms))

// 平滑滚动：总距离 px，在 ms 内匀速完成；scroll-behavior 已在页面内改成 auto，这里逐帧推进
async function glide(page, px, ms, selector) {
  const steps = Math.max(1, Math.round(ms / 16))
  for (let i = 0; i < steps; i++) {
    await page.evaluate(([dy, sel]) => {
      const el = sel && document.querySelector(sel)
      if (el) el.scrollTop += dy
      else document.scrollingElement.scrollTop += dy
    }, [px / steps, selector])
    await sleep(16)
  }
}

// 首屏内的图片是否都解码完成（页面底部的图是 loading=lazy，不能一并等）
const VISIBLE_IMAGES = () => [...document.images].filter(img => {
  const r = img.getBoundingClientRect()
  return r.bottom > -200 && r.top < innerHeight + 400 && r.width > 0
}).every(img => img.complete)

// 内容就绪：关键元素可见 + 首屏图片解码完成 + 字体就绪 + 网络空闲
async function ready(page, selector) {
  await page.waitForSelector(selector, { state: 'visible', timeout: 20000 })
  await page.waitForFunction(VISIBLE_IMAGES, null, { timeout: 12000 }).catch(() => {})
  await page.evaluate(() => document.fonts.ready).catch(() => {})
  await page.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {})
  await sleep(400)
}

const frameReady = (page, selector) =>
  page.waitForFunction(sel => [...document.querySelectorAll(sel)].every(img => img.complete), selector, { timeout: 12000 }).catch(() => {})

// 每个镜头：before() 等页面就绪，action() 是就绪之后录进成片的动作
const SHOTS = {
  // 首页：标题与主图，再慢速下滚约 1.2 屏，露出真实地图这一节
  home: {
    before: page => ready(page, '.hero h1'),
    async action(page) {
      await sleep(500)
      await glide(page, 1010, 2800)
      await sleep(200)
    }
  },
  // 手法页：下滚经过五张手法卡片
  methods: {
    before: page => ready(page, '.methods-list .method-card'),
    async action(page) {
      await sleep(400)
      await glide(page, 1500, 3200)
      await sleep(200)
    }
  },
  // 详情页：从现场照片滚到「构景解析」与图解
  detail: {
    before: page => ready(page, '.detail-reference img'),
    async action(page) {
      await sleep(400)
      await glide(page, 1040, 2900)
      await sleep(200)
    }
  },
  // 游园页：地图出现后悬停观察点看提示气泡（成片窗口内保持气泡），窗口之后再点一下这个观察点，
  // 站点里点击是跳转到对应手法详情（没有页内弹窗），跳转结果留在余量里供剪辑取用
  explore: {
    before: page => ready(page, '.garden-map .garden-pin'),
    extra: 3.4,
    async action(page) {
      await sleep(200)
      await glide(page, 150, 600)
      const pin = page.locator('.garden-pin:not(.main-pin)').nth(3) // 廊桥 → 障景
      await pin.hover({ force: true })
      await sleep(3600)
      await pin.click({ force: true })
      await page.waitForSelector('.detail-hero h1', { state: 'visible', timeout: 8000 }).catch(() => {})
    }
  },
  // 创作页：上传园中照片，再依次切换三个窗型
  studio: {
    before: async page => {
      await ready(page, '.frame-grid button')
      await frameReady(page, '.frame-thumb img')
    },
    async action(page) {
      await sleep(200)
      await glide(page, 470, 600)
      await page.locator('input[type=file]').first().setInputFiles(PHOTO)
      await page.waitForFunction(() => !document.querySelector('.canvas-wrap[aria-busy="true"]'), null, { timeout: 15000 }).catch(() => {})
      await sleep(600)
      const frames = page.locator('.frame-grid button')
      for (const index of [1, 2, 3]) { await frames.nth(index).click({ force: true }); await sleep(600) }
    }
  },
  // 问答页：只录未登录可见状态（介绍、示例问题、登录提示），不下滚过远，也不发送问题
  ask: {
    before: page => ready(page, '.ask-welcome .ask-suggestions button'),
    async action(page) {
      await sleep(400)
      await glide(page, 330, 1600)
      await sleep(200)
    }
  },
  // 社区页：作品流为空时录真实可见的空状态与筛选条
  community: {
    before: page => ready(page, '.community-toolbar'),
    async action(page) {
      await sleep(400)
      await glide(page, 286, 1500)
      await sleep(200)
    }
  }
}

const shots = TIMELINE.shots
  .filter(shot => (shot.clip || '').startsWith('capture/'))
  .map(shot => ({ key: path.basename(shot.clip, '.webm'), route: shot.route, duration: +(shot.end - shot.start).toFixed(2) }))

// 逐帧 JPEG + 真实时间戳 → 恒定 30fps 的 webm（每帧按真实间隔拉长，最后用 -t 截到真实总时长）
function encode(frames, tmp, dest, endTs) {
  const last = frames[frames.length - 1]
  const list = frames.map((f, i) => {
    const next = frames[i + 1] ? frames[i + 1].ts : endTs
    return `file '${f.file}'\nduration ${Math.max(0.01, next - f.ts).toFixed(4)}`
  }).join('\n')
  // concat 需要重复末帧才会承认它的 duration，多出的那一点由 -t 截掉
  fs.writeFileSync(path.join(tmp, 'list.txt'), `${list}\nfile '${last.file}'\n`)
  const span = Math.max(0.1, endTs - frames[0].ts)
  execFileSync('ffmpeg', ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', path.join(tmp, 'list.txt'),
    '-vf', `fps=30,scale=${VIDEO.width}:${VIDEO.height}:flags=lanczos,format=yuv420p`,
    '-c:v', 'libvpx-vp9', '-crf', '24', '-b:v', '0', '-row-mt', '1', '-t', span.toFixed(3), dest])
  return span
}

;(async () => {
  fs.mkdirSync(OUT, { recursive: true })
  const names = process.argv.slice(2).length ? process.argv.slice(2) : shots.map(s => s.key)
  const readyPath = path.join(OUT, 'ready.json')
  const marks = fs.existsSync(readyPath) ? JSON.parse(fs.readFileSync(readyPath, 'utf8')) : {}
  const browser = await chromium.launch({ channel: 'chrome' })
  for (const name of names) {
    const shot = shots.find(s => s.key === name)
    if (!shot || !SHOTS[name]) throw new Error(`未定义的镜头：${name}`)
    const tmp = path.join(OUT, `.tmp-${name}`)
    fs.rmSync(tmp, { recursive: true, force: true }); fs.mkdirSync(tmp, { recursive: true })
    const ctx = await browser.newContext(MOBILE)
    const page = await ctx.newPage()
    const errors = []
    page.on('pageerror', e => errors.push(e.message))
    const cdp = await ctx.newCDPSession(page)
    const frames = []
    cdp.on('Page.screencastFrame', frame => {
      const file = path.join(tmp, `${String(frames.length).padStart(5, '0')}.jpg`)
      fs.writeFileSync(file, Buffer.from(frame.data, 'base64'))
      frames.push({ file, ts: frame.metadata.timestamp })
      cdp.send('Page.screencastFrameAck', { sessionId: frame.sessionId }).catch(() => {})
    })
    await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 92, maxWidth: VIDEO.width, maxHeight: VIDEO.height, everyNthFrame: 1 })
    const t0 = Date.now() / 1000
    await page.goto(BASE + shot.route, { waitUntil: 'domcontentloaded' })
    await page.addStyleTag({ content: HIDE })
    await SHOTS[name].before(page)
    const readyAt = Date.now() / 1000 - t0
    await SHOTS[name].action(page)
    // 补足「镜头时长 + 余量」，动作结束后的停留也属于成片画面
    const need = shot.duration + (SHOTS[name].extra || EXTRA)
    while (Date.now() / 1000 - t0 < need) await sleep(120)
    const end = Date.now() / 1000 - t0
    const screenText = await page.evaluate(() => document.body.innerText.replace(/\s+/g, ' ').slice(0, 240)).catch(() => '')
    const scrollTop = await page.evaluate(() => Math.round(document.scrollingElement.scrollTop)).catch(() => null)
    await cdp.send('Page.stopScreencast').catch(() => {})
    await ctx.close()
    if (!frames.length) throw new Error(`${name} 没有录到任何画面`)
    // 第一帧之前的时间不计入成片，就绪点相应左移；末帧按录制结束时刻补齐
    const lead = Math.max(0, frames[0].ts - t0)
    const dest = path.join(OUT, `${name}.webm`)
    const span = encode(frames, tmp, dest, t0 + end)
    fs.rmSync(tmp, { recursive: true, force: true })
    const ready = +Math.max(0, readyAt - lead).toFixed(2)
    marks[name] = ready
    fs.writeFileSync(readyPath, JSON.stringify(marks, null, 2))
    console.log(`${name}: ${dest} 帧数=${frames.length} 就绪=${ready}s 录制=${span.toFixed(2)}s 需要=${need}s 滚动=${scrollTop}${errors.length ? ' errors=' + errors.join('; ') : ''}`)
    console.log(`  画面文字: ${screenText}`)
  }
  await browser.close()
})().catch(e => { console.error(e); process.exit(1) })
