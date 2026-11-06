import { defineConfig } from 'astro/config';
import { loadEnv } from 'vite';
import react from '@astrojs/react';
import { visualizer } from 'rollup-plugin-visualizer';

const isAnalyze = process.env.ANALYZE === 'true';

// Origins the browser may call: the backend API and Supabase Storage (presigned
// PDF uploads go straight from the browser to storage).
const env = loadEnv(process.env.NODE_ENV ?? 'production', process.cwd(), 'PUBLIC_');
function originOf(url, fallback) {
  try {
    return new URL(url).origin;
  } catch {
    return fallback;
  }
}
const apiOrigin = originOf(env.PUBLIC_API_BASE_URL ?? process.env.PUBLIC_API_BASE_URL, 'http://localhost:8000');
const storageOrigin = env.PUBLIC_STORAGE_ORIGIN || process.env.PUBLIC_STORAGE_ORIGIN || 'https://*.supabase.co';

export default defineConfig({
  output: 'static',
  compressHTML: true,
  prefetch: {
    prefetchAll: false,
    defaultStrategy: 'hover',
  },
  integrations: [react()],
  // Content-Security-Policy <meta> on every page: Astro hashes each script and
  // style it emits, so injected markup cannot run script. frame-ancestors and
  // other header-only directives are set in vercel.json.
  security: {
    csp: {
      directives: [
        "default-src 'self'",
        `connect-src 'self' ${apiOrigin} ${storageOrigin}`,
        "img-src 'self' data: blob:",
        "font-src 'self' data:",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-src 'none'",
        "worker-src 'self'",
      ],
    },
  },
  server: {
    host: true,
  },
  vite: {
    plugins: [
      isAnalyze && visualizer({
        filename: 'dist/stats/bundle-visualizer.html',
        open: false,
        gzipSize: true,
        brotliSize: true,
      }),
    ].filter(Boolean),
    server: {
      hmr: {
        overlay: true,
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('node_modules/react-dom')) return 'vendor-react';
            if (id.includes('node_modules/react')) return 'vendor-react';
            if (id.includes('node_modules/dompurify')) return 'vendor-sanitize';
            if (id.includes('node_modules/marked')) return 'vendor-markdown';
            if (id.includes('node_modules/@fontsource')) return 'vendor-fonts';
          },
        },
      },
    },
  },
});
