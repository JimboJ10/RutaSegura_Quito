import { test, expect } from '@playwright/test';
import { expandPanel } from './audit-helpers.mjs';

test('React usa la cobertura activa para el mapa, las cuadrículas y las tres rutas', async ({ page }, testInfo) => {
  const configResponse = page.waitForResponse(r => r.url().endsWith('/config') && r.ok());
  const layerResponse = page.waitForResponse(r => r.url().endsWith('/predicciones') && r.ok());
  await page.goto('/');
  const config = await (await configResponse).json();
  const layer = await (await layerResponse).json();
  expect(['Zona de demostración de Quito', 'Zona ampliada · Quito']).toContain(config.zona_demo);
  const ampliada = config.zona_demo === 'Zona ampliada · Quito';
  const cantidad = ampliada ? 99 : 25;
  expect(layer.features).toHaveLength(cantidad);
  await expect(page.locator('.map-place')).toHaveText(ampliada ? config.zona_demo : 'Zona demo · Quito');
  await page.getByRole('button', { name: 'Capas', exact: true }).click();
  await page.getByRole('checkbox', { name: `Mostrar ${cantidad} cuadrículas` }).check();
  await page.getByRole('button', { name: 'Cerrar opciones de capas' }).click();
  await expect(page.locator('.leaflet-prediction-grid-pane path')).toHaveCount(cantidad);
  await expandPanel(page);
  if (ampliada) {
    await page.getByText('Introducir coordenadas', { exact: true }).click();
    for (const [campo, valor] of Object.entries({
      'Origen: latitud': '-0.150', 'Origen: longitud': '-78.498',
      'Destino: latitud': '-0.218', 'Destino: longitud': '-78.505',
    })) await page.getByRole('spinbutton', { name: campo }).fill(valor);
    await page.getByRole('button', { name: 'Aplicar coordenadas' }).click();
  } else {
    await page.getByRole('button', { name: 'Probar recorrido de ejemplo' }).click();
  }
  const routeResponse = page.waitForResponse(r => r.url().endsWith('/rutas') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Comparar recorridos' }).click();
  const response = await routeResponse;
  expect(response.status()).toBe(200);
  const rutas = await response.json();
  const distancias = ampliada ? [8.837156, 9.538431, 9.538431] : process.env.RUTAINFORMADA_RED === 'original' ? [3.255669, 3.306152, 3.297791] : [3.255669, 3.346387, 3.293076];
  expect(rutas.features).toHaveLength(3);
  for (let i = 0; i < 3; i++) {
    expect(Math.abs(rutas.features[i].properties.distancia_km - distancias[i])).toBeLessThanOrEqual(.001);
  }
  await expect(page.locator('.route-card')).toHaveCount(3);
  await page.getByRole('button', { name: /Con estimación de IA/ }).click();
  await expect(page.locator('.route-lightgbm')).toHaveAttribute('stroke-width', '7');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await testInfo.attach('mapa', { body: await page.screenshot(), contentType: 'image/png' });
});
