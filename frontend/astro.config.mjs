import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

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
    server: {
      hmr: {
        overlay: true,
      },
    },
  },
});
