import { test, expect, type Page } from '@playwright/test';
import { expandPanel, collapsePanel, measure } from './audit-helpers.mjs';
import { mkdir, readFile } from 'node:fs/promises';
import path from 'node:path';

const evidence = path.resolve(process.env.RUTAINFORMADA_EVIDENCIAS || '../backend/evidencias/integracion-demo-filtrada');
type Pair = { id: string; origen: [number, number]; destino: [number, number] };

async function coordinates(page: Page, pair: Pair) {
  await expandPanel(page);
  if (await page.locator('.manual-entry').getAttribute('open') === null) {
    await page.getByText('Introducir coordenadas', { exact: true }).click();
  }
  for (const [label, point] of [['Origen', pair.origen], ['Destino', pair.destino]] as const) {
    await page.getByRole('spinbutton', { name: `${label}: latitud` }).fill(String(point[1]));
    await page.getByRole('spinbutton', { name: `${label}: longitud` }).fill(String(point[0]));
  }
  await page.getByRole('button', { name: 'Aplicar coordenadas' }).click();
}

async function calculate(page: Page) {
  const response = page.waitForResponse(r => r.url().endsWith('/rutas') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Comparar recorridos', exact: true }).click();
  return response;
}

async function capture(page: Page, name: string) {
  await expect.poll(() => page.evaluate(() => {
    const tiles = [...document.querySelectorAll<HTMLImageElement>('img.leaflet-tile')];
    return tiles.length > 0 && tiles.every(t => t.complete && t.naturalWidth > 0 && Number(getComputedStyle(t).opacity) === 1);
  }), { timeout: 25000 }).toBe(true);
  await mkdir(path.join(evidence, 'capturas'), { recursive: true });
  await page.screenshot({ path: path.join(evidence, 'capturas', `${name}.png`) });
}

test('main:app filtrada: endpoints reales, indicadores y capturas responsive', async ({ page }, testInfo) => {
  const configResponse = page.waitForResponse(r => r.url().endsWith('/config') && r.ok());
  const predictionsResponse = page.waitForResponse(r => r.url().endsWith('/predicciones') && r.ok());
  await page.goto('/');
  const config = await (await configResponse).json();
  expect(config.zona_demo).toBe('Zona de demostración de Quito');
  expect(config.advertencias.join(' ')).toContain('demo peatonal filtrada');
  expect(config.desvio_maximo_pct).toBe(15);
  expect(config.distancia_maxima_ajuste_m).toBe(300);
  expect((await (await predictionsResponse).json()).features).toHaveLength(25);
  expect(await (await page.request.get('/api/health')).json()).toMatchObject({ nodos: 14686, aristas: 43248 });
  await capture(page, `${testInfo.project.name}-01-inicial`);
  await expandPanel(page);
  await page.getByRole('button', { name: 'Probar recorrido de ejemplo' }).click();
  const response = await calculate(page);
  expect(response.status()).toBe(200);
  const data = await response.json();
  for (const f of data.features) {
    expect(f.properties.indice_historico).toBeGreaterThanOrEqual(0);
    expect(f.properties.indice_lightgbm).toBeGreaterThanOrEqual(0);
    const lines = f.geometry.coordinates;
    for (let i = 1; i < lines.length; i++) expect(lines[i - 1].at(-1)).toEqual(lines[i][0]);
  }
  await expect(page.locator('.route-card')).toHaveCount(3);
  await expect(page.getByRole('heading', { name: 'Tres modalidades de comparación' })).toBeVisible();
  await expect(page.getByText('Las modalidades pueden compartir el mismo recorrido.')).toBeVisible();
  await capture(page, `${testInfo.project.name}-02-resultados`);
  await collapsePanel(page);
  await page.getByRole('button', { name: 'Capas', exact: true }).click();
  await page.getByRole('checkbox', { name: 'Mostrar 25 cuadrículas' }).check();
  await page.getByRole('button', { name: 'Cerrar opciones de capas' }).click();
  await expect(page.locator('.leaflet-prediction-grid-pane path')).toHaveCount(25);
  const metrics = await measure(page);
  expect(metrics.horizontalOverflow).toBe(false);
  expect(metrics.attribution.unobstructed).toBe(true);
  expect(metrics.predictionLegendVisible).toBe(true);
  await capture(page, `${testInfo.project.name}-03-cuadriculas`);
  await coordinates(page, { id: 'centro_este', origen: [-78.516, -.199], destino: [-78.483, -.180] });
  expect((await calculate(page)).status()).toBe(422);
  await expect(page.getByRole('alert')).toContainText('demasiado lejos');
  await expect(page.locator('.route-line')).toHaveCount(0);
  await capture(page, `${testInfo.project.name}-04-cobertura-422`);
});

test('isla desconectada y modalidades coincidentes no simulan tres caminos distintos', async ({ page }, testInfo) => {
  const pairs: Pair[] = JSON.parse(await readFile('../backend/evidencias/validacion-cobertura/demo-pares.json', 'utf8'));
  const records = (await readFile('../backend/evidencias/validacion-cobertura/demo-peticiones.jsonl', 'utf8'))
    .trim().split('\n').map(line => JSON.parse(line));
  const identical = records.find(r => r.grupo === 'muestra' && r.version === 'filtrado' && r.geometrias_distintas === 1);
  await page.goto('/');
  await expect(page.locator('.map-canvas')).toBeVisible();
  await coordinates(page, pairs.find(p => p.id === 'isla_01')!);
  expect((await calculate(page)).status()).toBe(422);
  await expect(page.getByRole('alert')).toContainText('No existe una ruta conectada.');
  await expect(page.locator('.route-card')).toHaveCount(0);
  await capture(page, `${testInfo.project.name}-05-desconexion-422`);
  await coordinates(page, pairs.find(p => p.id === identical.id)!);
  const response = await calculate(page);
  expect(response.status()).toBe(200);
  const data = await response.json();
  expect(data.features).toHaveLength(3);
  expect(data.features[1].geometry).toEqual(data.features[0].geometry);
  expect(data.features[2].geometry).toEqual(data.features[0].geometry);
  await expect(page.getByText('Las modalidades pueden compartir el mismo recorrido.')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Tres modalidades de comparación' })).toBeVisible();
  await capture(page, `${testInfo.project.name}-06-coincidentes`);
});
