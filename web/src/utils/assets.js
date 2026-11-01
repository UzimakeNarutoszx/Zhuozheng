import { imageVariants } from '../data/image-variants.js'

export function assetUrl(path, base = import.meta.env?.BASE_URL || '/') {
  if (!path || /^(?:[a-z][a-z\d+.-]*:|\/\/|#)/i.test(path)) return path
  return `${base.replace(/\/$/, '')}/${path.replace(/^\//, '')}`
}

export function imageSrcset(path) {
  return (imageVariants[path] || []).map(item => `${assetUrl(item.src)} ${item.width}w`).join(', ')
}
