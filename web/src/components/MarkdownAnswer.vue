<script setup>
import { onMounted, ref, watch } from 'vue'
import { markdownNodes, streamBlocks } from '../utils/markdown.js'

const props = defineProps({ text: { type: String, default: '' }, streaming: Boolean })
const host = ref(null)
let completed = [], growingNodes = [], growingText = '', line = null

function formatted(text) {
  function build(nodes) {
    return nodes.map(node => {
      if (node.text !== undefined) return document.createTextNode(node.text)
      const element = document.createElement(node.tag)
      for (const [name, value] of Object.entries(node.attrs)) element.setAttribute(name, value)
      element.append(...build(node.children))
      return element
    })
  }
  return build(markdownNodes(text))
}
function dropGrowing() {
  growingNodes.forEach(node => node.remove())
  growingNodes = []; growingText = ''; line = null
}
function render() {
  if (!host.value) return
  if (!props.streaming) {
    host.value.replaceChildren(...formatted(props.text))
    completed = []; growingNodes = []; growingText = ''; line = null
    return
  }
  const blocks = streamBlocks(props.text)
  const growing = blocks.pop() || ''
  if (completed.length > blocks.length || completed.some((text, index) => text !== blocks[index])) {
    host.value.replaceChildren(); completed = []; dropGrowing()
  }
  if (completed.length < blocks.length) {
    dropGrowing()
    while (completed.length < blocks.length) {
      const text = blocks[completed.length]
      host.value.append(...formatted(text))
      completed.push(text)
    }
  }
  if (!growing.startsWith(growingText)) dropGrowing()
  let order = 0
  for (const character of Array.from(growing.slice(growingText.length))) {
    if (character === '\n' || !line) {
      line = document.createElement('p')
      line.className = 'markdown-growing'
      host.value.append(line); growingNodes.push(line)
      if (character === '\n') continue
    }
    const span = document.createElement('span')
    span.className = 'markdown-character'
    span.style.setProperty('--i', String(Math.min(order++, 5)))
    span.textContent = character
    line.append(span)
  }
  growingText = growing
}
watch(() => [props.text, props.streaming], render, { flush: 'post' })
onMounted(render)
</script>

<template><div ref="host" class="markdown-answer" :aria-busy="streaming" /></template>

<style scoped>
.markdown-answer { min-width:0; font-size:15px; line-height:1.9; overflow-wrap:anywhere; text-wrap:pretty; }
.markdown-answer :deep(p) { margin:0 0 .8em; white-space:normal; }
.markdown-answer :deep(.markdown-growing) { white-space:pre-wrap; }
.markdown-answer :deep(:last-child) { margin-bottom:0; }
.markdown-answer :deep(h1),.markdown-answer :deep(h2),.markdown-answer :deep(h3),.markdown-answer :deep(h4),.markdown-answer :deep(h5),.markdown-answer :deep(h6) { margin:1em 0 .45em; font-size:1.18em; line-height:1.5; font-weight:600; }
.markdown-answer :deep(:first-child) { margin-top:0; }
.markdown-answer :deep(ul),.markdown-answer :deep(ol) { padding-left:1.5em; margin:.6em 0; }
.markdown-answer :deep(li) { margin:.2em 0; }
.markdown-answer :deep(li > p) { margin:.35em 0; }
.markdown-answer :deep(blockquote) { margin:.8em 0; padding:.25em 1em; box-shadow:inset 3px 0 0 var(--line); color:var(--ink-soft); }
.markdown-answer :deep(code) { padding:.1em .3em; background:rgba(23,58,54,.05); border-radius:3px; font-family:ui-monospace,SFMono-Regular,Consolas,monospace; font-size:.88em; }
.markdown-answer :deep(pre) { max-width:100%; overflow-x:auto; padding:14px; margin:.8em 0; background:rgba(23,58,54,.045); border-radius:4px; white-space:pre; line-height:1.65; }
.markdown-answer :deep(pre code) { padding:0; background:transparent; white-space:pre; }
.markdown-answer :deep(a) { color:var(--ink); text-decoration:underline; text-underline-offset:3px; }
.markdown-answer :deep(img) { max-width:100%; height:auto; }
.markdown-answer :deep(table) { display:block; overflow-x:auto; border-collapse:collapse; max-width:100%; margin:.8em 0; font-size:.92em; }
.markdown-answer :deep(th),.markdown-answer :deep(td) { padding:8px 12px; text-align:left; box-shadow:inset 0 -1px 0 var(--line); }
.markdown-answer :deep(th) { font-weight:600; }
.markdown-answer :deep(hr) { border:0; height:1px; background:var(--line); margin:1em 0; }
.markdown-answer :deep(.markdown-character) { animation:markdown-reveal 120ms both; animation-delay:calc(var(--i) * 30ms); }
@keyframes markdown-reveal { from { filter:blur(6px); opacity:0; } to { filter:blur(0); opacity:1; } }
@media(prefers-reduced-motion:reduce) { .markdown-answer :deep(.markdown-character) { animation:none; } }
</style>
