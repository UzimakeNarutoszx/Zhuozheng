const KEY = 'garden-observation-works-v1'
export function readWorks() { try { return JSON.parse(localStorage.getItem(KEY) || '[]') } catch { return [] } }
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
