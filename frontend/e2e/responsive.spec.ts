import { test, expect, type Page } from '@playwright/test';
import { expandPanel, collapsePanel, measure } from './audit-helpers.mjs';

const payload = { origen: { lat: -0.201, lon: -78.504 }, destino: { lat: -0.184, lon: -78.486 } };
async function open(page: Page) {
  const configResponse = page.waitForResponse(r => r.url().endsWith('/config') && r.ok());
  await page.goto('/');
  await expect(page.locator('.map-canvas')).toBeVisible();
  await expect(page.getByText('Demo conectada', { exact: true })).toBeVisible();
  if ((process.env.RUTAINFORMADA_RED ?? 'peatonal_filtrada') === 'peatonal_filtrada') {
    const health = await page.request.get(new URL('health', (await configResponse).url()).href);
    expect((await health.json()).aristas).toBe(43248);
  }
  await page.evaluate(() => document.fonts.ready);
}
async function layout(page: Page, legend = false) {
  const state = await measure(page);
  expect(state.horizontalOverflow).toBe(false);
  expect(state.panelHorizontalOverflow).toBe(false);
  expect(state.map.width).toBeGreaterThanOrEqual(300);
  expect(state.map.height).toBeGreaterThanOrEqual(210);
  expect(state.attribution.visible).toBe(true);
  expect(state.attribution.unobstructed).toBe(true);
  expect(state.smallControls).toEqual([]);
  expect(state.blockedControls).toEqual([]);
  expect(state.overlaps).toEqual([]);
  if (legend) {
    expect(state.predictionLegendVisible).toBe(true);
    const legendBox = await page.locator('.prediction-legend').boundingBox();
    expect(legendBox!.y + legendBox!.height).toBeLessThanOrEqual(state.map.bottom);
  }
}
async function selectExample(page: Page) {
  await expandPanel(page);
  await page.getByRole('button', { name: 'Probar recorrido de ejemplo' }).click();
}
async function calculate(page: Page) {
  const responsePromise = page.waitForResponse(r => r.url().endsWith('/rutas') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Comparar recorridos' }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  expect(response.request().postDataJSON()).toEqual(payload);
  const data = await response.json();
  const refs = (process.env.RUTAINFORMADA_RED ?? 'peatonal_filtrada') === 'peatonal_filtrada'
    ? { corta: 3.255669, historica: 3.346387, lightgbm: 3.293076 }
    : { corta: 3.255669, historica: 3.306152, lightgbm: 3.297791 };
  expect(data.features).toHaveLength(3);
  for (const feature of data.features) {
    expect(Math.abs(feature.properties.distancia_km - refs[feature.properties.id as keyof typeof refs])).toBeLessThanOrEqual(.001);
    expect(feature.properties.desvio_pct).toBeLessThanOrEqual(15);
  }
  await expect(page.getByRole('heading', { name: /modalidades de comparación/ })).toBeVisible();
}
async function markerVisibility(page: Page) {
  // Se inspeccionan los marcadores y sus puntos de impacto; no solo el DOM presente.
  await expect.poll(async () => page.locator('.point-marker').evaluateAll(elements => {
    const map = document.querySelector('.map-canvas')!.getBoundingClientRect();
    return elements.length === 2 && elements.every(el => {
      const r = el.getBoundingClientRect();
      const top = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
      return r.x >= map.x && r.right <= map.right && r.y >= map.y && r.bottom <= map.bottom &&
        !!top && (el === top || el.contains(top));
    });
  })).toBe(true);
}
test('flujo real: mapa, puntos, tres rutas, resaltado, capas y panel', async ({ page, isMobile }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await open(page);
  await expect.poll(() => page.locator('.leaflet-tile').evaluateAll(images =>
    images.filter(img => (img as HTMLImageElement).complete && (img as HTMLImageElement).naturalWidth > 0).length)).toBeGreaterThan(0);
  await layout(page);
  const map = await page.locator('.map-canvas').boundingBox();
  for (const [x, y] of [[.4, .42], [.57, .55]]) {
    if (isMobile) await page.touchscreen.tap(map!.x + map!.width * x, map!.y + map!.height * y);
    else await page.mouse.click(map!.x + map!.width * x, map!.y + map!.height * y);
  }
  expect(await page.locator('.point-marker').count()).toBe(2);
  await selectExample(page);
  await calculate(page);
  for (const [id, name] of [['corta', 'Más corta'], ['historica', 'Menor concentración histórica de siniestros'], ['lightgbm', 'Con estimación de IA']]) {
    const card = page.getByRole('button', { name: new RegExp(name) });
    await card.click();
    await expect(card).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator(`.route-${id}`)).toHaveAttribute('stroke-width', '7');
    await expect(page.locator(`.route-${id}`)).toHaveAttribute('stroke-opacity', '1');
  }
  await page.getByRole('button', { name: 'Ver recorrido seleccionado' }).click();
  await markerVisibility(page);
  await page.getByRole('button', { name: 'Capas', exact: true }).click();
  await page.getByRole('checkbox', { name: 'Mostrar 25 cuadrículas' }).check();
  await page.getByRole('button', { name: 'Cerrar opciones de capas' }).click();
  await expect(page.locator('.leaflet-prediction-grid-pane path')).toHaveCount(25);
  const panes = await page.evaluate(() => ({
    predictions: Number(getComputedStyle(document.querySelector('.leaflet-prediction-grid-pane')!).zIndex),
    routes: Number(getComputedStyle(document.querySelector('.leaflet-route-lines-pane')!).zIndex),
  }));
  expect(panes.predictions).toBeLessThan(panes.routes);
  await expandPanel(page);
  await layout(page, true);
  await markerVisibility(page);
  await collapsePanel(page);
  await layout(page, true);
  await markerVisibility(page);
  await page.getByRole('button', { name: 'Capas', exact: true }).click();
  await page.getByLabel('Indicador', { exact: true }).selectOption('pred_historico');
  await expect(page.getByText('Histórico · siniestros estimados / mes')).toBeVisible();
  await page.getByRole('checkbox', { name: 'Mostrar 25 cuadrículas' }).uncheck();
  await expect(page.locator('.leaflet-prediction-grid-pane path')).toHaveCount(0);
  await page.getByRole('button', { name: 'Cerrar opciones de capas' }).click();
  await expandPanel(page);
  await page.getByRole('button', { name: 'Intercambiar origen y destino' }).click();
  await expect(page.locator('.point-button').filter({ hasText: 'Origen' })).toContainText('-0.18400, -78.48600');
  await expect(page.locator('.route-line')).toHaveCount(0);
  await page.getByRole('button', { name: 'Restablecer', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Comparar recorridos' })).toBeDisabled();
  await expect(page.locator('.point-marker')).toHaveCount(0);
  expect(errors).toEqual([]);
});

test('carga y errores: respuesta real demorada, cobertura 422 y pérdida de red simulada', async ({ page }) => {
  await open(page);
  await selectExample(page);
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/rutas', async route => {
    const real = await route.fetch();
    await gate; // Solo se demora el transporte; se conserva la respuesta real de FastAPI.
    await route.fulfill({ response: real });
  });
  await page.getByRole('button', { name: 'Comparar recorridos' }).click();
  await expect(page.getByRole('button', { name: 'Calculando recorridos…' })).toBeDisabled();
  release();
  await expect(page.getByRole('heading', { name: /modalidades de comparación/ })).toBeVisible();
  await page.unroute('**/rutas');
  await page.getByText('Introducir coordenadas', { exact: true }).click();
  await page.getByRole('spinbutton', { name: 'Origen: latitud' }).fill('0');
  await page.getByRole('spinbutton', { name: 'Origen: longitud' }).fill('0');
  await page.getByRole('button', { name: 'Aplicar coordenadas' }).click();
  const invalid = page.waitForResponse(r => r.url().endsWith('/rutas') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Comparar recorridos' }).click();
  expect((await invalid).status()).toBe(422);
  await expect(page.getByRole('alert')).toContainText('demasiado lejos');
  await expect(page.locator('.route-line')).toHaveCount(0);
  await layout(page);
  await selectExample(page);
  await page.route('**/rutas', route => route.abort('failed'));
  await page.getByRole('button', { name: 'Comparar recorridos' }).click();
  await expect(page.getByRole('alert')).toContainText('No se pudo conectar');
  await page.unroute('**/rutas');
  await page.getByRole('button', { name: 'Intentar nuevamente', exact: true }).click();
  await expect(page.getByRole('heading', { name: /modalidades de comparación/ })).toBeVisible();
});

test('redimensionado conserva mapa y extremos; diálogo accesible por teclado', async ({ page }) => {
  await open(page); await selectExample(page); await calculate(page);
  const original = page.viewportSize()!;
  await page.setViewportSize({ width: original.width < 768 ? 1280 : 390, height: 844 });
  await collapsePanel(page);
  await layout(page);
  await markerVisibility(page);
  await page.setViewportSize(original);
  await expandPanel(page);
  await layout(page);
  await markerVisibility(page);
  const info = page.getByRole('button', { name: 'Sobre los datos' });
  await info.focus(); await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('dialog')).toContainText('no representan probabilidades individuales de accidente');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(info).toBeFocused();
  await info.click();
  await page.getByRole('button', { name: 'Entendido, volver al mapa' }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
});

test('indisponibilidad inicial simulada permite reconectar al backend real', async ({ page }) => {
  await page.route('**/health', route => route.abort('failed'));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Recorridos guardados' })).toBeVisible();
  await expect(page.getByRole('alert')).toContainText('No se pudo conectar');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.unroute('**/health');
  await page.getByRole('button', { name: 'Intentar nuevamente', exact: true }).click();
  await expect(page.locator('.map-canvas')).toBeVisible();
});
