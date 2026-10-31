import MarkdownIt from 'markdown-it'

// Raw HTML is text, and markdown-it rejects javascript: links before rendering.
const markdown = new MarkdownIt({ html: false, linkify: true, breaks: true })

// Same paragraph boundaries as the Jianwen website, including blank lines in fences.
export function streamBlocks(text) {
  const blocks = []
  for (const chunk of String(text).replace(/\r\n?/g, '\n').split(/\n{2,}/)) {
    if (blocks.length && (blocks.at(-1).match(/^\s*```/gm) || []).length % 2) blocks[blocks.length - 1] += `\n\n${chunk}`
    else blocks.push(chunk)
  }
  return blocks
}

export function markdownNodes(text) {
  function nodes(tokens) {
    const result = [], stack = [result]
    for (const [index, token] of tokens.entries()) {
      const children = stack.at(-1)
      if (token.nesting === -1) { stack.pop(); continue }
      const node = { key: index, tag: token.tag, attrs: Object.fromEntries(token.attrs || []), children: [] }
      if (token.type === 'inline') { children.push(...nodes(token.children || [])); continue }
      if (token.type === 'text') { children.push({ key: index, text: token.content }); continue }
      if (token.type === 'softbreak' || token.type === 'hardbreak') node.tag = 'br'
      if (token.type === 'code_inline') node.children = [{ key: 0, text: token.content }]
      if (token.type === 'fence' || token.type === 'code_block') {
        node.tag = 'pre'
        const language = token.info.trim().split(/\s+/)[0]
        node.children = [{ key: 0, tag: 'code', attrs: language ? { class: `language-${language}` } : {}, children: [{ key: 0, text: token.content }] }]
      }
      if (token.type === 'image') node.attrs.alt = token.content
      if (node.tag === 'a') { node.attrs.target = '_blank'; node.attrs.rel = 'noopener noreferrer' }
      children.push(node)
      if (token.nesting === 1) stack.push(node.children)
    }
    return result
  }
  return nodes(markdown.parse(String(text || ''), {}))
}
