<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { assetUrl } from '../utils/assets.js'

const props = defineProps({ speaking: Boolean, compact: Boolean, preview: { type: Boolean, default: true }, character: { type: String, default: 'round' } })
const emit = defineEmits(['ready', 'error'])
const characters = {
  round: { name: '梅梅', file: 'round-window' },
  coin: { name: '钱钱', file: 'coin-window' },
  ice: { name: '冰冰', file: 'ice-window' }
}
const character = computed(() => characters[props.character] || characters.round)
const host = ref(null), ready = ref(false), greeting = ref(false), unavailable = ref(false)
let cleanup = () => {}, greet = () => {}, stopGreeting = () => {}, fallbackTimer
function sayHello() {
  clearTimeout(fallbackTimer)
  greeting.value = false
  requestAnimationFrame(() => {
    greeting.value = true
    greet()
    fallbackTimer = setTimeout(() => { greeting.value = false }, 2600)
  })
}
watch(() => props.speaking, speaking => { if (speaking) stopGreeting() })

// 不阻塞首屏：等浏览器画出第一帧再开始下载 Three.js（动态 import）和模型。
// compact 是右下角导览吉祥物，首屏就要准备 3D，所以只等两帧；大图角色继续等空闲。
function waitBeforeLoading(compact) {
  if (compact) return new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))
  return new Promise(resolve => {
    let done = false
    const finish = () => { if (!done) { done = true; resolve() } }
    const timer = setTimeout(finish, 500)
    if (window.requestIdleCallback) requestIdleCallback(() => { clearTimeout(timer); finish() }, { timeout: 800 })
  })
}

onMounted(async () => {
  const conn = navigator.connection || {}
  if (conn.saveData || /(^|-)(2g|3g)/.test(conn.effectiveType || '')) { emit('error'); return }
  await waitBeforeLoading(props.compact)
  let disposed = false
  let renderer, resize, observer, mixer, frame = 0, model
  const resources = new Set()
  const disposeModel = object => object?.traverse(node => {
    if (node.geometry) resources.add(node.geometry)
    for (const material of [].concat(node.material || [])) {
      resources.add(material)
      for (const value of Object.values(material)) if (value?.isTexture) resources.add(value)
    }
  })
  cleanup = () => {
    disposed = true
    cancelAnimationFrame(frame)
    resize?.disconnect(); observer?.disconnect(); mixer?.stopAllAction()
    disposeModel(model)
    for (const resource of resources) resource.dispose()
    renderer?.dispose(); renderer?.domElement.remove()
    greet = () => {}; stopGreeting = () => {}
  }
  try {
    const [THREE, { GLTFLoader }] = await Promise.all([import('three'), import('three/addons/loaders/GLTFLoader.js')])
    if (disposed) return
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(34, 1, .1, 100)
    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: 'low-power' })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.setClearColor(0xffffff, 0)
    renderer.domElement.setAttribute('aria-hidden', 'true')
    host.value.appendChild(renderer.domElement)
    scene.add(new THREE.HemisphereLight(0xffffff, 0xaaaaaa, 2.5))
    const key = new THREE.DirectionalLight(0xffffff, 3); key.position.set(-3, 4, 5); scene.add(key)
    const fill = new THREE.DirectionalLight(0xffffff, 1.4); fill.position.set(4, 2, 2); scene.add(fill)
    const group = new THREE.Group(); scene.add(group)
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)')
    let visible = true, hoverX = 0, last = performance.now(), elapsed = 0, helloStart = -10
    let hand, handRest = 0, eyes = [], width = 1, height = 1, size, greetingAction
    const fit = () => {
      if (!host.value) return
      const rect = host.value.getBoundingClientRect()
      width = Math.max(1, rect.width); height = Math.max(1, rect.height)
      renderer.setSize(width, height)
      camera.aspect = width / height
      if (size) {
        const distance = Math.max(size.y, size.x / camera.aspect) / (2 * Math.tan(THREE.MathUtils.degToRad(17))) * 1.19
        camera.position.set(size.x * .045, size.y * .025, distance)
        camera.lookAt(0, 0, 0)
      }
      camera.updateProjectionMatrix()
    }
    resize = new ResizeObserver(fit); resize.observe(host.value); fit()
    observer = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting })
    observer.observe(host.value)
    greet = () => {
      helloStart = elapsed; greeting.value = true
      if (!motion.matches) greetingAction?.reset().play()
    }
    stopGreeting = () => { helloStart = -10; greeting.value = false; greetingAction?.stop() }
    const pointer = event => {
      const rect = host.value.getBoundingClientRect()
      hoverX = THREE.MathUtils.clamp(((event.clientX - rect.left) / rect.width - .5) * .55, -.28, .28)
    }
    host.value.addEventListener('pointermove', pointer)
    host.value.addEventListener('pointerleave', () => { hoverX = 0 })
    host.value.addEventListener('pointerenter', () => { if (!props.speaking && !greeting.value) greet() })
    renderer.domElement.addEventListener('webglcontextlost', event => {
      event.preventDefault(); ready.value = false; unavailable.value = true; emit('error'); cleanup()
    })
    const gltf = await new GLTFLoader().loadAsync(assetUrl(`/assets/models/${character.value.file}.glb`))
    model = gltf.scene
    if (disposed) { disposeModel(model); for (const resource of resources) resource.dispose(); return }
    const box = new THREE.Box3().setFromObject(model)
    size = box.getSize(new THREE.Vector3())
    model.position.sub(box.getCenter(new THREE.Vector3()))
    group.add(model); fit()
    hand = model.getObjectByName('WaveHandPivot'); handRest = hand?.rotation.z || 0
    eyes = ['EyeLeft', 'EyeRight'].map(name => model.getObjectByName(name)).filter(Boolean).map(node => ({ node, height: node.scale.y }))
    if (gltf.animations.length) {
      mixer = new THREE.AnimationMixer(model)
      const clip = gltf.animations.find(clip => clip.name === 'Idle') || gltf.animations[0]
      mixer.clipAction(clip).setLoop(THREE.LoopRepeat, Infinity).play()
      const hello = gltf.animations.find(clip => clip.name === 'Greeting')
      if (hello) greetingAction = mixer.clipAction(hello).setLoop(THREE.LoopOnce, 1)
    }
    renderer.render(scene, camera)
    ready.value = true
    emit('ready')
    greet()
    const tick = now => {
      frame = requestAnimationFrame(tick)
      const delta = Math.min((now - last) / 1000, .05); last = now
      if (!visible || document.hidden) return
      elapsed += delta
      const helloTime = elapsed - helloStart
      const waving = helloTime >= 0 && helloTime < 2.4
      if (!waving && greeting.value) greeting.value = false
      if (!motion.matches) {
        mixer?.update(delta)
        const envelope = waving ? Math.sin(Math.PI * helloTime / 2.4) : 0
        const target = hoverX + Math.sin(elapsed * .65) * .045
        group.rotation.y = THREE.MathUtils.damp(group.rotation.y, target, 10, delta)
        group.rotation.z = Math.sin(elapsed * 1.6) * .012 + envelope * Math.sin(helloTime * 5) * .065
        group.rotation.x = props.speaking ? Math.sin(elapsed * 4) * .045 : 0
        group.position.y = envelope * Math.sin(Math.PI * helloTime / 2.4) * .10
        if (hand && !greetingAction) hand.rotation.z = handRest + envelope * (.18 + Math.sin(helloTime * 14) * .42)
        const blink = elapsed % 4.6 > 4.45
        for (const eye of eyes) eye.node.scale.y = eye.height * (blink ? .12 : 1)
      } else {
        group.rotation.set(0, 0, 0); group.position.y = 0
        if (hand) hand.rotation.z = handRest
        for (const eye of eyes) eye.node.scale.y = eye.height
      }
      renderer.render(scene, camera)
    }
    frame = requestAnimationFrame(tick)
  } catch {
    if (!disposed) { unavailable.value = true; ready.value = false; emit('error'); cleanup() }
  }
})
onBeforeUnmount(() => { clearTimeout(fallbackTimer); cleanup() })
</script>

<template>
  <div class="round-window-3d" :data-character="props.character" :class="{ 'is-ready': ready, 'is-greeting': greeting, 'is-compact': compact }">
    <button ref="host" class="character-stage" type="button" :aria-label="`和${character.name}打个招呼`" @click="sayHello">
      <img v-if="!ready && preview" :src="assetUrl(`/assets/models/${character.file}-preview.webp`)" :alt="`按原稿制作的立体${character.name}伙伴`" decoding="async">
    </button>
    <div v-if="!compact" class="character-controls">
      <span class="character-caption" role="status">{{ unavailable ? `${character.name}在这里陪你` : speaking ? '我在认真想你的问题…' : greeting ? '你好呀，一起看看园林吧！' : '点点我，我会和你打招呼' }}</span>
      <button class="character-hello" type="button" @click="sayHello">打个招呼 <span aria-hidden="true">✦</span></button>
    </div>
  </div>
</template>

<style scoped>
.round-window-3d { position:relative; width:100%; }
.character-stage { position:relative; display:block; width:100%; height:320px; padding:0; border:0; background:transparent; cursor:pointer; touch-action:manipulation; -webkit-tap-highlight-color:transparent; border-radius:45%; }
.character-stage :deep(canvas) { display:block; width:100%; height:100%; pointer-events:none; }
.character-stage > img { position:absolute; inset:0; width:100%; height:100%; object-fit:contain; }
.character-stage:focus-visible,.character-hello:focus-visible { outline:none; box-shadow:0 0 0 1px rgba(23,58,54,.12),0 0 0 4px rgba(23,58,54,.06); }
.character-controls { display:flex; flex-direction:column; align-items:center; gap:10px; text-align:center; }
.character-caption { color:var(--ink-soft); font-size:12px; line-height:1.5; min-height:18px; }
.character-hello { padding:8px 15px; border:0; border-radius:20px; background:rgba(23,58,54,.06); color:var(--ink); font-size:12px; min-height:36px; transition:background 150ms; }
.character-hello:hover { background:rgba(23,58,54,.1); }
.character-hello span { display:inline-block; transform:translateY(.125em); color:var(--clay); margin-left:5px; }
.is-compact .character-stage { height:190px; }
.is-greeting:not(.is-ready) .character-stage > img { animation:hello-fallback .6s ease-in-out 4; transform-origin:50% 70%; }
@keyframes hello-fallback { 25% { transform:rotate(-5deg) translateY(-6px); } 75% { transform:rotate(5deg) translateY(-6px); } }
@media(max-width:700px) {
  .round-window-3d { width:145px; }
  .character-stage { height:160px; }
  .character-controls { gap:4px; }
  .character-caption { display:none; }
  .character-hello { padding:6px 12px; font-size:11px; min-height:32px; }
  .is-compact { width:100%; }
  .is-compact .character-stage { height:142px; }
}
@media(prefers-reduced-motion:reduce) { .is-greeting:not(.is-ready) .character-stage > img { animation:none; } }
</style>
