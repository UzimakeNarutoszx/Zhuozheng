const KEY = 'garden-observation-works-v1'
export function readWorks() { try { return JSON.parse(localStorage.getItem(KEY) || '[]') } catch { return [] } }
export function makeThumbFromCanvas(canvas, max = 480) {
  try {
    const ratio = Math.min(1, max / Math.max(canvas.width, canvas.height || 1))
    const thumb = document.createElement('canvas')
    thumb.width = Math.max(1, Math.round(canvas.width * ratio))
    thumb.height = Math.max(1, Math.round(canvas.height * ratio))
    thumb.getContext('2d').drawImage(canvas, 0, 0, thumb.width, thumb.height)
    return thumb.toDataURL('image/jpeg', 0.68)
  } catch (error) { return '' }
}

export function getSourceImage(work) { return work?.sourceImageDataUrl || work?.imageDataUrl || '' }
export function writeWork(work) {
  const list = readWorks().filter(item => item.id !== work.id)
  const next = [work, ...list].slice(0, 24)
  try { localStorage.setItem(KEY, JSON.stringify(next)); return next } catch { const error = new Error('Unable to save work'); error.code = 'STORAGE_WRITE_FAILED'; throw error }
}
export function removeWork(id) {
  const list = readWorks().filter(item => item.id !== id)
  try { localStorage.setItem(KEY, JSON.stringify(list)); return list } catch { const error = new Error('Unable to remove work'); error.code = 'STORAGE_WRITE_FAILED'; throw error }
}
export function canUseStorage() { try { const key = '__garden_test'; localStorage.setItem(key, '1'); localStorage.removeItem(key); return true } catch { return false } }
