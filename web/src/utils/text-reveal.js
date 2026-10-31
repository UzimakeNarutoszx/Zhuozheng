// Match Jianwen: two characters per frame while receiving, then catch up quickly.
export function createTextReveal(onText, { schedule = requestAnimationFrame, cancel = cancelAnimationFrame } = {}) {
  const characters = []
  let count = 0, visible = '', frame = null, ended = false, resolve
  function tick() {
    frame = null
    const remaining = characters.length - count
    const size = ended ? Math.max(2, Math.ceil(remaining / 24)) : 2
    visible += characters.slice(count, count + size).join('')
    count = Math.min(characters.length, count + size)
    onText(visible)
    if (count < characters.length) start()
    else { resolve?.(); resolve = null }
  }
  function start() { if (frame === null && count < characters.length) frame = schedule(tick) }
  return {
    push(delta) { for (const character of delta) characters.push(character); start() },
    finish() { ended = true; if (count === characters.length) return Promise.resolve(); start(); return new Promise(done => { resolve = done }) },
    flush() { if (frame !== null) cancel(frame); frame = null; count = characters.length; visible = characters.join(''); onText(visible); resolve?.(); resolve = null },
    cancel() { if (frame !== null) cancel(frame); frame = null; resolve?.(); resolve = null }
  }
}
