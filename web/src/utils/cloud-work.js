import { loadImage } from './image-loader.js'
import { compressPhoto } from './image-export.js'

async function compressedImage(source) {
  if (!source) return ''
  const image = await loadImage(source)
  return compressPhoto(image)
}

export async function prepareCloudWork(work) {
  const imageDataUrl = await compressedImage(work.imageDataUrl)
  const sourceImageDataUrl = work.sourceImageDataUrl ? await compressedImage(work.sourceImageDataUrl) : ''
  return { id: work.id, title: work.title || '未命名取景', note: work.note || '', methodId: work.methodId || 'frame', frameId: work.frameId || 'round', keepCanvasBorder: work.keepCanvasBorder ?? true, scale: work.scale || 1, offset: work.offset || { x: 0, y: 0 }, createdAt: work.createdAt || Date.now(), pointId: work.pointId || '', imageDataUrl, sourceImageDataUrl }
}
