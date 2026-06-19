/// <reference types="vitest" />
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/**/*.{test,spec}.{ts,tsx,js,jsx}'],
    css: false,
  },
  resolve: {
    alias: {
      '@': new URL('./src', import.meta.url).pathname,
    },
  },
});
