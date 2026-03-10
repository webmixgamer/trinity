/**
 * Shared markdown rendering utility with DOMPurify sanitization (H-005).
 *
 * All v-html content in the app should use this utility to prevent XSS
 * from agent responses, dashboard widgets, queue items, etc.
 */
import { marked } from 'marked'
import DOMPurify from 'dompurify'

// Configure marked globally
marked.setOptions({
  breaks: true,
  gfm: true
})

// Custom renderer: open links in new tab
const renderer = new marked.Renderer()
renderer.link = (href, title, text) => {
  const titleAttr = title ? ` title="${title}"` : ''
  return `<a href="${href}"${titleAttr} target="_blank" rel="noopener noreferrer">${text}</a>`
}
marked.use({ renderer })

// Allow target and rel attributes for links (DOMPurify strips them by default)
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank')
    node.setAttribute('rel', 'noopener noreferrer')
  }
})

/**
 * Render markdown to sanitized HTML.
 *
 * @param {string} content - Raw markdown string
 * @returns {string} Sanitized HTML string safe for v-html
 */
export function renderMarkdown(content) {
  if (!content) return ''
  const html = marked(content)
  return DOMPurify.sanitize(html)
}
