const TOKEN_KEY = 'garden-auth-token-v1'
const USER_KEY = 'garden-auth-user-v1'

export function readSession() {
  try { return { token: localStorage.getItem(TOKEN_KEY) || '', user: JSON.parse(localStorage.getItem(USER_KEY) || 'null') } } catch { return { token: '', user: null } }
}
export function saveSession(session) {
  try { localStorage.setItem(TOKEN_KEY, session.token); localStorage.setItem(USER_KEY, JSON.stringify(session.user)) } catch { /* The current tab can still use its in-memory session. */ }
}
export function clearSession() {
  try { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USER_KEY) } catch { /* Storage may be disabled. */ }
}

export function chatHistory(messages) {
  const pairs = messages.flatMap((message, index) => {
    const reply = messages[index + 1]
    return message.role === 'user' && reply?.role === 'assistant' && reply.content && !reply.failed ? [message, reply] : []
  })
  return pairs.slice(-20).map(({ role, content }) => ({ role, content: Array.from(content).slice(0, 4000).join('') }))
}

export async function apiRequest(path, { token, body, signal, method = body ? 'POST' : 'GET' } = {}) {
  let response
  try { response = await fetch(`/api/v1${path}`, { method, signal, headers: { ...(body ? { 'Content-Type': 'application/json' } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) }, ...(body ? { body: JSON.stringify(body) } : {}) }) } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new Error('暂时连接不上服务，请检查网络后重试。')
  }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) { const detail = data.error || data.detail || data.message; const error = new Error(typeof detail === 'string' ? detail : '请求未完成，请稍后重试。'); error.status = response.status; throw error }
  return data
}

export async function streamChat(question, history, { token, signal, onDelta }) {
  let response
  try { response = await fetch('/api/v1/content/ask/stream', { method: 'POST', signal, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify({ question, history }) }) } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new Error('暂时连接不上梅梅，请检查网络后重试。')
  }
  if (!response.ok) { const data = await response.json().catch(() => ({})); const error = new Error(data.detail || data.error || data.message || '梅梅暂时没有回应，请稍后重试。'); error.status = response.status; throw error }
  const eventStream = response.headers.get('content-type')?.includes('text/event-stream')
  if (response.headers.get('content-type')?.includes('application/json')) { const data = await response.json(); onDelta(data.answer || data.reply || data.message || data.content || ''); return }
  if (!response.body) throw new Error('浏览器无法读取流式回答，请更新浏览器后重试。')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let pending = '', length = 0
  function emit(delta) {
    if (!delta) return
    length += delta.length
    if (length > 250000) throw new Error('回答过长，已停止接收。请缩小问题范围。')
    onDelta(delta)
  }
  function consume(frame) {
    const raw = frame.split('\n').filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n').trim()
    if (!raw || raw === '[DONE]') return
    let data
    try { data = JSON.parse(raw) } catch { throw new Error('回答数据中断，请重试。') }
    if (data.error) throw new Error(typeof data.error === 'string' ? data.error : data.error.message || '回答中断，请重试。')
    emit(data.delta ?? data.content ?? data.choices?.[0]?.delta?.content ?? '')
  }
  try {
    while (true) {
      if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
      const { done, value } = await reader.read()
      if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
      pending += decoder.decode(value || new Uint8Array(), { stream: !done })
      if (!eventStream) { emit(pending); pending = '' }
      else { pending = pending.replace(/\r\n/g, '\n'); const frames = pending.split('\n\n'); pending = frames.pop(); frames.forEach(consume) }
      if (done) { if (pending.trim()) consume(pending); break }
    }
  } finally { await reader.cancel().catch(() => {}); reader.releaseLock() }
}
