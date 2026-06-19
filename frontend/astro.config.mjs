import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import { visualizer } from 'rollup-plugin-visualizer';

const isAnalyze = process.env.ANALYZE === 'true';

export default defineConfig({
  output: 'static',
  compressHTML: true,
  prefetch: {
    prefetchAll: false,
    defaultStrategy: 'hover',
  },
  integrations: [react()],
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
