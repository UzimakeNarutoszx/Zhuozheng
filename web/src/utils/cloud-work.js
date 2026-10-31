import { loadImage } from './image-loader.js'

async function compressedImage(source) {
  if (!source) return ''
  const image = await loadImage(source)
  const ratio = Math.min(1, 1600 / Math.max(image.naturalWidth, image.naturalHeight))
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(1, Math.round(image.naturalWidth * ratio))
  canvas.height = Math.max(1, Math.round(image.naturalHeight * ratio))
  canvas.getContext('2d').drawImage(image, 0, 0, canvas.width, canvas.height)
  const result = canvas.toDataURL('image/webp', .82)
  if (result.length > 4_000_000) throw new Error('这幅作品压缩后仍然过大，请先导出并缩小图片。')
  return result
}

export async function prepareCloudWork(work) {
  const imageDataUrl = await compressedImage(work.imageDataUrl)
  const sourceImageDataUrl = work.sourceImageDataUrl ? await compressedImage(work.sourceImageDataUrl) : ''
  return { id: work.id, title: work.title || '未命名取景', note: work.note || '', methodId: work.methodId || 'frame', frameId: work.frameId || 'round', keepCanvasBorder: work.keepCanvasBorder ?? true, scale: work.scale || 1, offset: work.offset || { x: 0, y: 0 }, createdAt: work.createdAt || Date.now(), imageDataUrl, sourceImageDataUrl }
}
