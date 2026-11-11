import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

// Para el ensayo en teléfono se usan certificados ya confiables en ese dispositivo.
const cert = process.env.PWA_TLS_CERT;
const key = process.env.PWA_TLS_KEY;
if (Boolean(cert) !== Boolean(key)) throw new Error('Indica PWA_TLS_CERT y PWA_TLS_KEY juntos.');

export default defineConfig({
  preview: {
    host: '127.0.0.1', port: 4173, strictPort: true,
    https: cert && key ? {cert: readFileSync(cert), key: readFileSync(key)} : undefined,
    proxy: { '/api': {target: 'http://127.0.0.1:8000', rewrite: path => path.replace(/^\/api/, '')} },
  },
  plugins: [react(), {
    name: 'ruta-shell', apply: 'build', enforce: 'post',
    generateBundle(_, bundle) {
      const publicFiles = ['manifest.webmanifest', 'favicon.svg', 'icon-192.png', 'icon-512.png', 'icon-maskable.png'];
      const files = ['index.html', ...Object.keys(bundle).filter(name => /^assets\/[^/]+\.(js|css)$/.test(name)), ...publicFiles];
      const template = readFileSync(new URL('./scripts/service-worker.template.js', import.meta.url), 'utf8');
      const hash = createHash('sha256').update(template);
      for (const name of files) {
        const asset = bundle[name];
        hash.update(name).update(asset ? (asset.type === 'chunk' ? asset.code : asset.source) :
          readFileSync(new URL('./public/' + name, import.meta.url)));
      }
      this.emitFile({type: 'asset', fileName: 'sw.js', source: template
        .replace('__REVISION__', JSON.stringify(hash.digest('hex').slice(0, 20)))
        .replace('__SHELL_FILES__', JSON.stringify(files.map(name => '/' + name)))});
    },
  }],
  build: { target: ['es2022', 'safari16.4'] },
  test: {
    include: ['src/test/*.test.{ts,tsx}'],
    environment: 'jsdom', restoreMocks: true, clearMocks: true,
  },
});
