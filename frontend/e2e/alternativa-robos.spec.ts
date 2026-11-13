import { expect, test, type Page } from '@playwright/test';
import { expandPanel } from './audit-helpers.mjs';
import { routes } from '../src/test/fixtures';

const endpoint = '**/robos-historicos/alternativa';
const label = /Menor concentración histórica de robos/;

async function piloto(page: Page) {
  await page.goto('/');
  await expect(page.locator('.panel-toggle')).toBeVisible();
  await expandPanel(page);
  await page.getByRole('button', {name:'Probar recorrido de ejemplo'}).click();
  const ready = page.waitForResponse(r => r.url().endsWith('/robos-historicos/alternativa'));
  await page.getByRole('button', {name:'Comparar recorridos'}).click();
  return ready;
}

test.beforeEach(async ({page}) => {
  await page.route('https://tile.openstreetmap.org/**', r => r.abort());
});

test('piloto real, cuarta modalidad seleccionable y copia local', async ({page}) => {
  const respuesta = await piloto(page);
  expect(respuesta.status()).toBe(200);
  const {estado, feature} = await respuesta.json();
  expect(estado).toBe('disponible');
  expect(feature.properties.desvio_pct).toBeLessThanOrEqual(15);
  const card = page.getByRole('button', {name:label});
  await expect(page.locator('.route-card')).toHaveCount(4);
  await expect(card).toContainText('Experimental');
  await card.click();
  await expect(card).toHaveAttribute('aria-pressed','true');
  await expect(page.locator('.route-robos')).toHaveAttribute('stroke-width','7');
  const comparison = page.getByRole('heading', {name:/Comparación con la más corta/});
  await expect(comparison).toBeVisible();
  await expect(page.getByText(/ni predice delitos futuros/)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole('button',{name:'Guardar recorrido',exact:true}).click();
  await expect(page.getByText('Recorrido guardado en este dispositivo')).toBeVisible();
  await page.getByRole('button',{name:'Guardados',exact:true}).click();
  await page.locator('.saved-library li button').first().click();
  await page.getByRole('button',{name:label}).click();
  await expect(comparison).toBeVisible();
  await expect(page.locator('.saved-map .leaflet-overlay-pane path')).toHaveAttribute('d',/L/);
});

const excesiva = {...routes.features[0], properties:{...routes.features[0].properties, id:'robos',
  desvio_pct:15.1, comparacion_robos:{periodo:'2019-2022', altas_m:10, altas_corta_m:50, ponderado:10, ponderado_corta:20}}};
for (const [caso, status, json, aviso] of [
  ['coincidente',200,{estado:'coincidente', modalidad:'historica'},/ya cumple el criterio experimental/],
  ['inexistente',200,{estado:'sin_alternativa'},/Ninguna alternativa evaluada/],
  ['desvío excesivo',200,{estado:'disponible',feature:excesiva},/Comparación experimental de robos históricos no disponible/],
  ['sin datos',503,{detail:'Archivo ausente'},/Comparación experimental de robos históricos no disponible/],
] as const) {
  test(caso + ' conserva tres modalidades',async ({page}) => {
    await page.route(endpoint, r => r.fulfill({status, json}));
    await piloto(page);
    await expect(page.getByText(aviso)).toBeVisible();
    await expect(page.locator('.route-card')).toHaveCount(3);
    await expect(page.getByRole('button',{name:label})).toHaveCount(0);
    await page.getByRole('button',{name:/Con estimación de IA/}).click();
    await expect(page.locator('.route-lightgbm')).toHaveAttribute('stroke-width','7');
  });
}
