import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { mkdir, writeFile } from 'node:fs/promises';
import { sizes, expandPanel, collapsePanel, measure } from '../e2e/audit-helpers.mjs';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
process.env.PLAYWRIGHT_BROWSERS_PATH ||= resolve(root, '.playwright-browsers');
const { chromium } = await import('@playwright/test');
const phase = process.argv[2] || 'despues';
const measurementsOnly = process.argv.includes('--solo-mediciones');
if (!['antes', 'despues'].includes(phase)) throw new Error('Fase admitida: antes o despues');
const output = resolve(root, 'evidencias/auditoria-responsive', phase);
await mkdir(output, { recursive: true });
const browser = await chromium.launch();
const report = { phase, browser: browser.version(), measuredAt: new Date().toISOString(), capturesUpdated: !measurementsOnly, results: [] };
try {
  for (const viewport of sizes) {
    const context = await browser.newContext({ viewport, isMobile: viewport.width < 768, hasTouch: viewport.width < 1024, deviceScaleFactor: 1, locale: 'es-EC', reducedMotion: 'reduce' });
    const page = await context.newPage();
    page.setDefaultTimeout(10000);
    const result = { viewport, steps: {}, errors: [], consoleErrors: [], networkErrors: [] };
    page.on('pageerror', error => result.consoleErrors.push(error.message));
    page.on('requestfailed', request => result.networkErrors.push({ url: request.url(), reason: request.failure()?.errorText }));
    const dir = resolve(output, String(viewport.width));
    await mkdir(dir, { recursive: true });
    const capture = async name => {
      await page.evaluate(() => document.fonts.ready);
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      await page.waitForFunction(() => {
        const map = document.querySelector('.map-canvas')?.getBoundingClientRect();
        const tiles = [...document.querySelectorAll('img.leaflet-tile')].filter(img => {
          const r = img.getBoundingClientRect();
          return map && r.bottom > map.top && r.top < map.bottom && r.right > map.left && r.left < map.right;
        });
        return tiles.length > 0 && tiles.every(img => img.complete && img.naturalWidth > 0 && Number(getComputedStyle(img).opacity) >= 1);
      }, undefined, { timeout: 15000 }).catch(() => result.errors.push('Teselas pendientes en ' + name));
      if (!measurementsOnly) await page.screenshot({ path: resolve(dir, name + '.png'), fullPage: true, animations: 'disabled' });
      result.steps[name] = await measure(page);
    };
    try {
      await page.goto('http://127.0.0.1:5173');
      await page.locator('.map-canvas').waitFor();
      await page.waitForFunction(() => [...document.querySelectorAll('img.leaflet-tile')].some(img => img.complete && img.naturalWidth > 0), undefined, { timeout: 15000 }).catch(() => result.errors.push('Teselas no cargadas durante la espera inicial'));
      await capture('01-inicio');
      const box = await page.locator('.map-canvas').boundingBox();
      await page.mouse.click(box.x + box.width * .40, box.y + box.height * .42);
      await page.mouse.click(box.x + box.width * .57, box.y + box.height * .55);
      result.mapSelection = await page.locator('.point-button').allTextContents();
      await expandPanel(page);
      await capture('02-panel-expandido');
      await page.getByRole('button', { name: 'Probar recorrido de ejemplo' }).click();
      const responsePromise = page.waitForResponse(r => r.url().endsWith('/rutas') && r.request().method() === 'POST');
      await page.getByRole('button', { name: 'Comparar recorridos' }).click();
      const response = await responsePromise;
      result.routeStatus = response.status();
      result.routePayload = response.request().postDataJSON();
      const data = await response.json();
      result.routeDistances = data.features?.map(f => f.properties);
      await page.getByRole('heading', { name: 'Tres modalidades de comparación' }).waitFor();
      for (const name of ['Más corta', 'Menor concentración histórica de siniestros', 'Con estimación de IA']) {
        await page.getByRole('button', { name: new RegExp(name) }).click();
        result.steps['seleccion-' + name] = await measure(page);
      }
      await page.getByRole('button', { name: /Más corta/ }).click();
      await capture('03-tres-rutas');
      await page.getByRole('button', { name: 'Ver recorrido seleccionado' }).click();
      await capture('04-rutas-en-mapa');
      await page.getByRole('button', { name: 'Capas', exact: true }).click();
      await page.getByRole('checkbox', { name: 'Mostrar 25 cuadrículas' }).check();
      await page.getByRole('button', { name: 'Cerrar opciones de capas' }).click();
      await capture('05-predicciones');
      await expandPanel(page);
      await capture('06-predicciones-panel');
      await page.getByRole('button', { name: 'Sobre los datos' }).click();
      await capture('07-advertencias');
      await page.getByRole('button', { name: 'Entendido, volver al mapa' }).click();
      await page.getByRole('button', { name: 'Intercambiar origen y destino' }).click();
      result.swappedPoints = await page.locator('.point-button').allTextContents();
      await page.getByRole('button', { name: 'Restablecer', exact: true }).click();
      result.resetDisabled = await page.getByRole('button', { name: 'Comparar recorridos' }).isDisabled();
    } catch (error) {
      result.errors.push(error.message);
      await capture('99-interrupcion').catch(() => {});
    }
    report.results.push(result);
    await context.close();
    console.log(JSON.stringify({ width: viewport.width, captured: Object.keys(result.steps).length, errors: result.errors }));
    await writeFile(resolve(output, 'mediciones.json'), JSON.stringify(report, null, 2));
  }
} finally { await browser.close(); }
if (report.results.some(result => result.errors.length)) process.exitCode = 1;
