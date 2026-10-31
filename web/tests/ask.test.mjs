import test from 'node:test'
import assert from 'node:assert/strict'
import { markdownNodes, streamBlocks } from '../src/utils/markdown.js'
import { chatHistory, streamChat } from '../src/utils/api.js'
import { createTextReveal } from '../src/utils/text-reveal.js'

function flatten(nodes) { return nodes.flatMap(node => [node, ...flatten(node.children || [])]) }

test('website streaming formats completed paragraphs and keeps fenced blank lines in the live block', () => {
  assert.deepEqual(streamBlocks('## 标题\n\n**还在增长**'), ['## 标题', '**还在增长**'])
  assert.deepEqual(streamBlocks('## 标题\n\n```js\nconst a = 1\n\nconst b = 2'), ['## 标题', '```js\nconst a = 1\n\nconst b = 2'])
  assert.deepEqual(streamBlocks('```js\nconst a = 1\n\nconst b = 2\n```\n\n下一个段落'), ['```js\nconst a = 1\n\nconst b = 2\n```', '下一个段落'])
})

test('retry excludes interrupted turns from model history without losing completed turns', () => {
  const complete = [{ role: 'user', content: '框景是什么' }, { role: 'assistant', content: '框景组织边界' }]
  assert.deepEqual(chatHistory([...complete, { role: 'user', content: '再讲一讲' }, { role: 'assistant', content: '部分内容', failed: true }]), complete)
  assert.deepEqual(chatHistory([{ role: 'user', content: '第一次失败' }, { role: 'assistant', content: '', failed: true }]), [])
})

test('Markdown preserves headings, nested lists, links, tables and unfinished code fences', () => {
  const nodes = flatten(markdownNodes('## 园林\n\n**框景**与`窗`\n\n- 近景\n  - 水面\n\n> 留意视线\n\n[来源](https://whc.unesco.org/)\n\n| 手法 | 观察 |\n| --- | --- |\n| 框景 | 边界 |\n\n```js\nconst 窗 = "🌿"\n'))
  for (const tag of ['h2', 'strong', 'ul', 'li', 'blockquote', 'a', 'table', 'th', 'pre', 'code']) assert.ok(nodes.some(node => node.tag === tag), tag)
  assert.equal(nodes.find(node => node.tag === 'a').attrs.rel, 'noopener noreferrer')
  assert.ok(nodes.some(node => node.text === 'const 窗 = "🌿"\n'))
})

test('Markdown renders raw HTML as text and rejects active URL schemes', () => {
  const nodes = flatten(markdownNodes('<img src=x onerror=alert(1)>\n\n<script>alert(1)</script>\n\n[危险](javascript:alert(1))\n\n![危险](javascript:alert(1))'))
  assert.ok(!nodes.some(node => ['script', 'img', 'a'].includes(node.tag)))
  assert.ok(nodes.some(node => node.text?.includes('<img src=x onerror=alert(1)>')))
})

test('text reveal emits progressive Unicode batches and flushes all received text on stop', async () => {
  const frames = new Map(), values = []
  let id = 0
  const reveal = createTextReveal(text => values.push(text), { schedule: callback => { frames.set(++id, callback); return id }, cancel: handle => frames.delete(handle) })
  const step = () => { const [handle, callback] = frames.entries().next().value; frames.delete(handle); callback() }
  reveal.push('框景🌿你好')
  assert.deepEqual(values, [])
  step()
  assert.deepEqual(values, ['框景'])
  step()
  assert.equal(values.at(-1), '框景🌿你')
  const finished = reveal.finish()
  step(); await finished
  assert.equal(values.at(-1), '框景🌿你好')
  reveal.push('，继续')
  reveal.flush()
  assert.equal(values.at(-1), '框景🌿你好，继续')
  assert.equal(frames.size, 0)
})

test('streamChat emits UTF-8 text before the response finishes', async () => {
  const original = globalThis.fetch
  let writer, observed, ended = false, answer = ''
  const seen = new Promise(resolve => { observed = resolve })
  globalThis.fetch = async () => new Response(new ReadableStream({ start(controller) { writer = controller } }), { headers: { 'Content-Type': 'text/plain; charset=utf-8' } })
  try {
    const running = streamChat('问题', [], { token: 'test', onDelta: delta => { answer += delta; if (answer === '框景🌿') observed() } }).then(() => { ended = true })
    for (const byte of new TextEncoder().encode('框景🌿')) writer.enqueue(new Uint8Array([byte]))
    await seen
    assert.equal(ended, false)
    writer.enqueue(new TextEncoder().encode('\n\n**边界**')); writer.close()
    await running
    assert.equal(answer, '框景🌿\n\n**边界**')
  } finally { globalThis.fetch = original }
})

test('SSE handles CRLF and JSON split across single bytes and preserves errors', async () => {
  const original = globalThis.fetch
  function response(text) { return new Response(new ReadableStream({ start(controller) { for (const byte of new TextEncoder().encode(text)) controller.enqueue(new Uint8Array([byte])); controller.close() } }), { headers: { 'Content-Type': 'text/event-stream' } }) }
  try {
    globalThis.fetch = async () => response('data: {"delta":"框景🌿"}\r\n\r\ndata: {"choices":[{"delta":{"content":"很好"}}]}\r\n\r\ndata: [DONE]\r\n\r\n')
    let answer = ''
    await streamChat('问题', [], { token: 'test', onDelta: delta => { answer += delta } })
    assert.equal(answer, '框景🌿很好')
    globalThis.fetch = async () => response('data: {"delta":"部分回答"}\n\ndata: {"error":"服务中断"}\n\n')
    answer = ''
    await assert.rejects(streamChat('问题', [], { token: 'test', onDelta: delta => { answer += delta } }), /服务中断/)
    assert.equal(answer, '部分回答')
  } finally { globalThis.fetch = original }
})

test('streamChat exposes 401 and honours stopping before a queued chunk', async () => {
  const original = globalThis.fetch
  try {
    globalThis.fetch = async () => new Response('{"detail":"请重新登录"}', { status: 401 })
    await assert.rejects(streamChat('问题', [], { token: 'expired', onDelta() {} }), error => error.status === 401 && /重新登录/.test(error.message))
    const controller = new AbortController(); controller.abort()
    globalThis.fetch = async () => new Response('不会显示')
    await assert.rejects(streamChat('问题', [], { token: 'test', signal: controller.signal, onDelta() { assert.fail('aborted text must not appear') } }), { name: 'AbortError' })
  } finally { globalThis.fetch = original }
})
