import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: { target: ['es2022', 'safari16.4'] },
  test: {
    include: ['src/test/*.test.{ts,tsx}'],
    environment: 'jsdom', restoreMocks: true, clearMocks: true,
  },
});
