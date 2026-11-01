const cache = new Map()

export function loadImage(src, { cached = false } = {}) {
  if (cached && cache.has(src)) return cache.get(src)
  const promise = new Promise((resolve, reject) => {
    const image = new Image()
    const timer = setTimeout(() => finish(new Error('图片加载超时，请重试')), 20000)
    function finish(error) {
      clearTimeout(timer)
      image.onload = null
      image.onerror = null
      if (error) reject(error)
      else resolve(image)
    }
    image.onload = () => finish()
    image.onerror = () => finish(new Error('图片加载失败，请重试'))
    image.src = src
  })
  if (cached) {
    cache.set(src, promise)
    promise.catch(() => { if (cache.get(src) === promise) cache.delete(src) })
  }
  return promise
}

export function createLatestImageRequest(loader = loadImage) {
  let sequence = 0
  return {
    cancel() { sequence += 1 },
    async load(src, options) {
      const request = ++sequence
      try {
        const image = await loader(src, options)
        return request === sequence ? image : null
      } catch (error) {
        if (request !== sequence) return null
        throw error
      }
    }
  }
}
