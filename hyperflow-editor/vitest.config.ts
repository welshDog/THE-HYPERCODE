import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    setupFiles: ['src/test.setup.ts'],
    exclude: [
      'e2e/**',
      'node_modules/**',
      'playwright/**',
      'playwright-report/**',
      'test-results/**'
    ],
  },
})
