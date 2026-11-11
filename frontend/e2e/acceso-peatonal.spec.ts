import { test, expect } from '@playwright/test';
import { expandPanel, collapsePanel, measure } from './audit-helpers.mjs';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';

test('Candidato peatonal: rutas reales, capa, selección móvil y rechazo de ajuste', async ({ page }, testInfo) => {
  test.skip(!process.env.RUTAINFORMADA_ENSAYO, 'Requiere el servidor aislado de copias filtradas');
  const ampliada = process.env.RUTAINFORMADA_ENSAYO === 'ampliada';
  const configPromise = page.waitForResponse(r => r.url().endsWith('/config') && r.ok());
  const capaPromise = page.waitForResponse(r => r.url().endsWith('/predicciones') && r.ok());
  await page.goto('/');
  const config = await (await configPromise).json();
  expect(config.zona_demo).toBe(ampliada ? 'Zona ampliada · Quito' : 'Zona de demostración de Quito');
  expect(config.distancia_maxima_ajuste_m).toBe(300);
  expect((await (await capaPromise).json()).features).toHaveLength(ampliada ? 99 : 25);
  const health = await (await page.request.get('/api/health')).json();
  expect(health.aristas).toBe(ampliada ? 88704 : 43248);
  await expandPanel(page);
  await page.getByRole('button', { name: 'Probar recorrido de ejemplo' }).click();
  const respuesta = page.waitForResponse(r => r.url().endsWith('/rutas') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Comparar recorridos' }).click();
  const response = await respuesta;
  expect(response.status()).toBe(200);
  const rutas = await response.json();
  const referencias = [3.255669, 3.346387, 3.293076];
  for (let i = 0; i < 3; i++) {
    const feature = rutas.features[i];
    expect(Math.abs(feature.properties.distancia_km - referencias[i])).toBeLessThanOrEqual(.001);
    expect(feature.properties.desvio_pct).toBeLessThanOrEqual(15);
    const lineas = feature.geometry.coordinates;
    for (let j = 1; j < lineas.length; j++) expect(lineas[j - 1].at(-1)).toEqual(lineas[j][0]);
  }
  await expect(page.locator('.route-card:not([data-modalidad="robos"])')).toHaveCount(3);
  for (const [id, label] of [['corta', /Más corta/], ['historica', /Menor concentración histórica de siniestros/], ['lightgbm', /Con estimación de IA/]] as const) {
    await page.getByRole('button', { name: label }).click();
    await expect(page.locator(`.route-${id}`)).toHaveAttribute('stroke-width', '7');
  }
  await collapsePanel(page);
  await page.getByRole('button', { name: 'Capas', exact: true }).click();
  await page.getByRole('checkbox', { name: `Mostrar ${ampliada ? 99 : 25} cuadrículas` }).check();
  await page.getByRole('button', { name: 'Cerrar opciones de capas' }).click();
  await expect(page.locator('.leaflet-prediction-grid-pane path')).toHaveCount(ampliada ? 99 : 25);
  // Espera explícita a teselas y opacidad tras la transición de Leaflet.
  await expect.poll(() => page.evaluate(() => {
    const tiles = [...document.querySelectorAll<HTMLImageElement>('.leaflet-tile-container img')];
    return tiles.length > 0 && tiles.every(t => t.complete && t.naturalWidth > 0 && Number(getComputedStyle(t).opacity) === 1);
  }), { timeout: 25000 }).toBe(true);
  const medicion = await measure(page);
  expect(medicion.horizontalOverflow).toBe(false);
  expect(medicion.attribution.visible).toBe(true);
  const folder = path.resolve('..', 'backend/evidencias/acceso/capturas');
  await mkdir(folder, { recursive: true });
  await page.screenshot({ path: path.join(folder, `${process.env.RUTAINFORMADA_ENSAYO}-${testInfo.project.name}.png`) });
  await expandPanel(page);
  await page.getByText('Introducir coordenadas', { exact: true }).click();
  for (const [campo, valor] of Object.entries({
    'Origen: latitud': '-0.199', 'Origen: longitud': '-78.516',
    'Destino: latitud': '-0.180', 'Destino: longitud': '-78.483',
  })) await page.getByRole('spinbutton', { name: campo }).fill(valor);
  await page.getByRole('button', { name: 'Aplicar coordenadas' }).click();
  const errorPromise = page.waitForResponse(r => r.url().endsWith('/rutas') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Comparar recorridos' }).click();
  expect((await errorPromise).status()).toBe(422);
  await expect(page.getByText(/demasiado lejos/i)).toBeVisible();
});
