# Frontend — perf & build notes

## Lighthouse targets (desktop)

| Category    | Target |
|-------------|--------|
| Performance | ≥ 90   |
| A11y        | ≥ 95   |
| Best Practices | ≥ 95   |

## Bundle size (build output)

**Total dist:** 1.3 MB

### JS chunks

| Chunk | Size |
|---|---|
| `vendor-react.js` (React 18 + React DOM) | 140 KB |
| `vendor-markdown.js` (marked) | 44 KB |
| `vendor-sanitize.js` (DOMPurify) | 28 KB |
| `dashboard.*.js` | 24 KB |
| `DetailedSummarizer.*.js` | 8 KB |
| All other page JS chunks | ~4 KB each |

### CSS

| File | Size |
|---|---|
| `BaseLayout.*.css` (global styles) | 40 KB |
| `summarizer.*.css` | 8 KB |

### HTML pages

| Page | Size |
|---|---|
| `/dashboard` | ~14.8 KB |
| `/register` | ~13.0 KB |
| `/login` | ~12.5 KB |
| `/summarizer` | ~11.4 KB |
| `/profile` | ~9.7 KB |
| `/admin` | ~5.5 KB |
| `/admin/chat-messages` | ~4.4 KB |
| `/admin/user-chats` | ~4.4 KB |
| `/` | ~4.2 KB |

## Manual chunk splitting (Vite)

Applied in `astro.config.mjs` via `vite.build.rollupOptions.output.manualChunks`:

- `vendor-react` — `react`, `react-dom`
- `vendor-sanitize` — `dompurify`
- `vendor-markdown` — `marked`
- `vendor-fonts` — `@fontsource/*` (CSS only, no JS)

## Font preloading

Four critical latin woff2 fonts are preloaded in `BaseLayout.astro`:

| Font | Weight | File size (woff2) |
|---|---|---|
| Fraunces | 600 (normal) | 18 KB |
| Fraunces | 700 (normal) | 18 KB |
| IBM Plex Sans | 400 (normal) | 23 KB |
| IBM Plex Sans | 500 (normal) | 24 KB |

Preloaded via `<link rel="preload" as="font" type="font/woff2" crossorigin>` using
Vite `?url` imports from `@fontsource` packages.

Fonts are declared in `global.css` via `@import "@fontsource/*"`.

## Bundle analysis

- Tool: `rollup-plugin-visualizer` (configured in `astro.config.mjs`)
- Run: `npm run build:analyze` (sets `ANALYZE=true`)
- Output: `dist/stats/bundle-visualizer.html` (176 KB interactive treemap)

## Build config

- `output: 'static'` (SSG)
- `compressHTML: true`
- Prefetch on hover (not prefetchAll)
