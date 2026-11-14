export function jpegData(canvas, limit = 3_000_000) {
  for (const quality of [.88, .8, .7, .6, .5, .4]) {
    const data = canvas.toDataURL('image/jpeg', quality)
    if (data.length <= limit) return data
  }
  throw new Error('图片压缩后仍然过大，请选择较小的照片。')
}
export function compressPhoto(image) {
  const canvas = document.createElement('canvas')
  canvas.width = image.naturalWidth || image.width
  canvas.height = image.naturalHeight || image.height
  const ctx = canvas.getContext('2d')
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  ctx.drawImage(image, 0, 0)
  return jpegData(canvas)
}
export function downloadCanvas(canvas, filename = '我的园林取景.jpg') { const link = document.createElement('a'); link.download = filename; link.href = jpegData(canvas); link.click() }
export function fitImage(image, canvasWidth, canvasHeight) { const scale = Math.max(canvasWidth / image.width, canvasHeight / image.height); return { scale, width: image.width * scale, height: image.height * scale } }
