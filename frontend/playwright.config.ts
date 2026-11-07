import { defineConfig } from '@playwright/test';

const sizes = [
  [360, 800], [390, 844], [430, 932], [768, 1024],
  [1024, 768], [1280, 800], [1920, 1080],
];
export default defineConfig({
  testDir: './e2e', testMatch: '**/*.spec.ts',
  fullyParallel: false, workers: 1, retries: 0, timeout: 45000,
  expect: { timeout: 10000 },
  reporter: [['list'], ['json', { outputFile: 'evidencias/auditoria-responsive/pruebas-playwright.json' }]],
  use: {
    baseURL: process.env.PLAYWRIGHT_TEST_BASE_URL || 'http://127.0.0.1:5173', browserName: 'chromium',
    locale: 'es-EC', deviceScaleFactor: 1, reducedMotion: 'reduce',
    screenshot: 'only-on-failure', trace: 'retain-on-failure',
  },
  projects: sizes.map(([width, height]) => ({
    name: `${width}x${height}`,
    use: { viewport: { width, height }, isMobile: width < 768, hasTouch: width < 1024 },
  })),
});
