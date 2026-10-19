<template>
  <div ref="rootRef" class="markdown-rich">
    <template v-for="(seg, i) in segments" :key="i">
      <div v-if="seg.t === 'md'" class="md-chunk" v-html="renderMd(seg.raw)" />
      <div v-else class="mermaid-wrap">
        <div class="mermaid" :ref="(el) => setMermaidContent(el, seg.code)" />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.use({ gfm: true, breaks: true })

const props = defineProps({
  content: { type: String, default: '' },
})

const rootRef = ref(null)
let mermaidModule = null
let mermaidThemeKey = ''

function splitSegments(text) {
  if (text == null || String(text).trim() === '') return []
  const s = String(text)
  const re = /```mermaid\s*\n([\s\S]*?)```/gi
  const out = []
  let last = 0
  let m
  while ((m = re.exec(s)) !== null) {
    if (m.index > last) out.push({ t: 'md', raw: s.slice(last, m.index) })
    out.push({ t: 'mermaid', code: (m[1] || '').trim() })
    last = m.index + m[0].length
  }
  if (last < s.length) out.push({ t: 'md', raw: s.slice(last) })
  return out
}

const segments = computed(() => splitSegments(props.content))
const hasMermaid = computed(() => segments.value.some((s) => s.t === 'mermaid'))

function renderMd(raw) {
  try {
    const html = marked.parse(raw || '', { async: false })
    return DOMPurify.sanitize(html, { ADD_ATTR: ['target', 'rel'] })
  } catch {
    const esc = (raw || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
    return `<p>${esc}</p>`
  }
}

function setMermaidContent(el, code) {
  if (el) el.textContent = code || ''
}

function isDarkScheme() {
  return typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
}

async function ensureMermaidConfigured() {
  const dark = isDarkScheme()
  const key = dark ? 'dark' : 'light'
  if (!mermaidModule || mermaidThemeKey !== key) {
    mermaidModule = (await import('mermaid')).default
    mermaidThemeKey = key
    mermaidModule.initialize({
      startOnLoad: false,
      securityLevel: 'strict',
      theme: dark ? 'dark' : 'neutral',
      fontFamily: 'ui-sans-serif, system-ui, -apple-system, sans-serif',
      themeVariables: dark
        ? {
            primaryColor: '#334155',
            primaryTextColor: '#e2e8f0',
            primaryBorderColor: '#475569',
            lineColor: '#64748b',
            secondaryColor: '#1e293b',
            tertiaryColor: '#0f172a',
            edgeLabelBackground: '#1e293b',
            clusterBkg: '#1e293b',
            clusterBorder: '#475569',
          }
        : {
            primaryColor: '#e8edf7',
            primaryTextColor: '#334155',
            primaryBorderColor: '#cbd5e1',
            lineColor: '#94a3b8',
            secondaryColor: '#f1f5f9',
            tertiaryColor: '#f8fafc',
            edgeLabelBackground: '#f8fafc',
            clusterBkg: '#f1f5f9',
            clusterBorder: '#e2e8f0',
          },
    })
  }
  return mermaidModule
}

async function runMermaid() {
  await nextTick()
  const root = rootRef.value
  if (!root || !hasMermaid.value) return
  const nodes = root.querySelectorAll('.mermaid')
  if (!nodes.length) return
  try {
    const mermaid = await ensureMermaidConfigured()
    await mermaid.run({ nodes: [...nodes] })
  } catch (e) {
    console.warn('[MarkdownRich] mermaid', e)
  }
}

function onColorSchemeChange() {
  mermaidThemeKey = ''
  mermaidModule = null
  runMermaid()
}

watch(() => props.content, runMermaid, { flush: 'post' })

onMounted(() => {
  runMermaid()
  if (typeof window !== 'undefined' && window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', onColorSchemeChange)
  }
})

onUnmounted(() => {
  if (typeof window !== 'undefined' && window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').removeEventListener('change', onColorSchemeChange)
  }
})
</script>

<style scoped>
.markdown-rich {
  --mr-text: #475569;
  --mr-heading: #0f172a;
  --mr-muted: #64748b;
  --mr-code-bg: #f1f5f9;
  --mr-code-border: #e2e8f0;
  --mr-pre-bg: #1e293b;
  --mr-pre-fg: #e2e8f0;
  --mr-border: #e2e8f0;
  --mr-quote-bg: rgba(241, 245, 249, 0.85);
  --mr-quote-border: #94a3b8;
  --mr-thead: #f1f5f9;
  --mr-stripe: rgba(248, 250, 252, 0.95);
  --mr-link: #2563eb;
  --mr-hr: #e2e8f0;
  --mr-wrap-bg: linear-gradient(180deg, #fafbfc 0%, #f4f6f9 100%);
  --mr-wrap-border: #e2e8f0;

  font-size: 14px;
  line-height: 1.7;
  color: var(--mr-text);
  word-break: break-word;
  letter-spacing: 0.01em;
}

@media (prefers-color-scheme: dark) {
  .markdown-rich {
    --mr-text: #cbd5e1;
    --mr-heading: #f1f5f9;
    --mr-muted: #94a3b8;
    --mr-code-bg: rgba(30, 41, 59, 0.85);
    --mr-code-border: #475569;
    --mr-pre-bg: #0f172a;
    --mr-pre-fg: #e2e8f0;
    --mr-border: #334155;
    --mr-quote-bg: rgba(30, 41, 59, 0.65);
    --mr-quote-border: #64748b;
    --mr-thead: rgba(30, 41, 59, 0.9);
    --mr-stripe: rgba(15, 23, 42, 0.45);
    --mr-link: #93c5fd;
    --mr-hr: #475569;
    --mr-wrap-bg: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
    --mr-wrap-border: #334155;
  }
}

.md-chunk :deep(h1),
.md-chunk :deep(h2),
.md-chunk :deep(h3),
.md-chunk :deep(h4) {
  margin: 1.15em 0 0.5em;
  font-weight: 700;
  color: var(--mr-heading);
  line-height: 1.35;
  letter-spacing: -0.02em;
}
.md-chunk :deep(h1) {
  font-size: 1.35rem;
  padding-bottom: 0.35em;
  border-bottom: 1px solid var(--mr-border);
}
.md-chunk :deep(h2) {
  font-size: 1.2rem;
  border-bottom: 1px solid var(--mr-border);
  padding-bottom: 0.35em;
}
.md-chunk :deep(h3) {
  font-size: 1.08rem;
}
.md-chunk :deep(h4) {
  font-size: 1rem;
  font-weight: 650;
}

.md-chunk :deep(p) {
  margin: 0.6em 0;
}

.md-chunk :deep(strong) {
  font-weight: 700;
  color: var(--mr-heading);
}
.md-chunk :deep(em) {
  font-style: italic;
  color: var(--mr-muted);
}

.md-chunk :deep(ul),
.md-chunk :deep(ol) {
  margin: 0.55em 0;
  padding-left: 1.4em;
}
.md-chunk :deep(li) {
  margin: 0.3em 0;
}
.md-chunk :deep(li::marker) {
  color: var(--mr-muted);
}

.md-chunk :deep(blockquote) {
  margin: 0.85em 0;
  padding: 0.65em 1em;
  border-left: 4px solid var(--mr-quote-border);
  background: var(--mr-quote-bg);
  color: var(--mr-text);
  border-radius: 0 10px 10px 0;
}
.md-chunk :deep(blockquote p) {
  margin: 0.35em 0;
}

.md-chunk :deep(hr) {
  border: none;
  height: 1px;
  margin: 1.25em 0;
  background: linear-gradient(90deg, transparent, var(--mr-hr), transparent);
}

.md-chunk :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.88em;
  background: var(--mr-code-bg);
  border: 1px solid var(--mr-code-border);
  padding: 0.15em 0.45em;
  border-radius: 6px;
}
.md-chunk :deep(pre) {
  background: var(--mr-pre-bg);
  color: var(--mr-pre-fg);
  padding: 14px 16px;
  border-radius: 12px;
  overflow-x: auto;
  margin: 0.9em 0;
  border: 1px solid var(--mr-border);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
}
.md-chunk :deep(pre code) {
  background: transparent;
  border: none;
  padding: 0;
  color: inherit;
  font-size: 0.86em;
  line-height: 1.55;
}

.md-chunk :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 14px 0;
  font-size: 13px;
  display: block;
  overflow-x: auto;
  max-width: 100%;
  border-radius: 12px;
  border: 1px solid var(--mr-border);
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}
.md-chunk :deep(thead) {
  background: var(--mr-thead);
}
.md-chunk :deep(th),
.md-chunk :deep(td) {
  border: 1px solid var(--mr-border);
  padding: 10px 14px;
  text-align: left;
}
.md-chunk :deep(th) {
  font-weight: 650;
  color: var(--mr-heading);
  white-space: nowrap;
}
.md-chunk :deep(tbody tr:nth-child(even)) {
  background: var(--mr-stripe);
}

.md-chunk :deep(a) {
  color: var(--mr-link);
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color 0.2s ease, color 0.2s ease;
}
.md-chunk :deep(a:hover) {
  border-bottom-color: currentColor;
}

.mermaid-wrap {
  margin: 18px 0;
  padding: 16px;
  background: var(--mr-wrap-bg);
  border: 1px solid var(--mr-wrap-border);
  border-radius: 14px;
  overflow-x: auto;
  text-align: center;
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.06);
}
@media (prefers-color-scheme: dark) {
  .mermaid-wrap {
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35);
  }
}
</style>
