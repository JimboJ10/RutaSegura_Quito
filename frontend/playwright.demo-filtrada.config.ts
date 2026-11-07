import { defineConfig } from '@playwright/test';
import base from './playwright.config';

if ((process.env.RUTAINFORMADA_RED ?? 'peatonal_filtrada') !== 'peatonal_filtrada') {
  throw new Error('Este ensayo requiere RUTAINFORMADA_RED=peatonal_filtrada y main:app con la demo filtrada.');
}
export default defineConfig({
  ...base,
  testMatch: ['**/responsive.spec.ts', '**/demo-filtrada.spec.ts', '**/cobertura.spec.ts'],
  outputDir: './test-results/demo-filtrada',
  reporter: [['list'], ['json', { outputFile: (process.env.RUTAINFORMADA_EVIDENCIAS || '../backend/evidencias/integracion-demo-filtrada') + '/playwright.json' }]],
});
