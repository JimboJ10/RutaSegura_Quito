import { test, expect } from '@playwright/test';
import { expandPanel, collapsePanel } from './audit-helpers.mjs';

const label = 'Mostrar robos históricos (2019–2022)';
test('consulta histórica local y piloto con las tres modalidades', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Capas', exact: true }).click();
  const toggle = page.getByRole('checkbox', { name: label });
  await expect(toggle).not.toBeChecked();
  const loaded = page.waitForResponse(r => r.url().endsWith('/robos-historicos'));
  await toggle.check();
  const response = await loaded;
  test.skip(response.status() === 503, 'Requiere la capa local autorizada');
  expect(response.status()).toBe(200);
  const cells = (await response.json()).features;
  await expect(page.locator('.leaflet-theft-grid-pane path')).toHaveCount(25);
  const masked = cells.find((c: {properties:{numero_registros:number|null}}) => c.properties.numero_registros === null);
  await page.getByLabel('Consultar cuadrícula').selectOption(masked.properties.celda_id);
  await expect(page.locator('.theft-details')).toContainText('Registros: 1-4');
  await expect(page.locator('.theft-details')).toContainText('Sin valor publicado');
  await page.getByRole('button', { name: 'Cerrar opciones de capas' }).click();
  await expect(page.locator('.theft-legend')).toBeVisible();
  await expect(page.locator('.theft-note')).toBeInViewport();
  await page.locator('.map-canvas').click({position:{x:85,y:160}});
  await expect(page.locator('.marker-pin.origen')).toHaveCount(1);
  await expandPanel(page);
  await page.getByRole('button', {name:'Probar recorrido de ejemplo'}).click();
  await page.getByRole('button', {name:'Comparar recorridos'}).click();
  await expect(page.locator('.theft-summary h3')).toHaveText('Información histórica de tu recorrido');
  await expect(page.locator('.theft-summary')).toContainText('Otras modalidades');
  await expect(page.locator('.route-line:not(.route-robos)')).toHaveCount(3);
  await collapsePanel(page);
  const hit = await page.locator('.map-canvas').evaluate(map => {
    const bounds = map.getBoundingClientRect();
    for (let y = bounds.top + 10; y < bounds.bottom - 10; y += 5) {
      for (let x = bounds.left + 10; x < bounds.right - 10; x += 5) {
        if (document.elementFromPoint(x,y)?.matches('.leaflet-theft-grid-pane path')) return {x,y};
      }
    }
    throw new Error('Ninguna cuadrícula seleccionable en el mapa');
  });
  await page.mouse.click(hit.x, hit.y);
  await expect(page.locator('.leaflet-popup')).toContainText('Superficie');
  await page.getByRole('button', { name: 'Capas', exact: true }).click();
  await toggle.uncheck();
  await expect(page.locator('.leaflet-theft-grid-pane path')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('capa ausente permite comparar y conserva el aviso permanente', async ({page}) => {
  await page.route('**/robos-historicos*', r => r.fulfill({status:503,json:{detail:'No disponible'}}));
  await page.route('**/robos-historicos/cruces*', r => r.fulfill({status:503,json:{detail:'No disponible'}}));
  await page.route('**/robos-historicos/alternativa', r => r.fulfill({status:503,json:{detail:'No disponible'}}));
  await page.goto('/');
  await page.getByRole('button',{name:'Capas',exact:true}).click();
  await page.getByRole('checkbox',{name:label}).check();
  await expect(page.locator('#layer-settings')).toContainText('no está disponible');
  await page.getByRole('button',{name:'Cerrar opciones de capas'}).click();
  await expandPanel(page);
  await page.getByRole('button',{name:'Probar recorrido de ejemplo'}).click();
  await page.getByRole('button',{name:'Comparar recorridos'}).click();
  await expect(page.locator('.route-card')).toHaveCount(3);
  await expect(page.locator('.theft-summary')).toContainText('Consulta histórica no disponible');
  await expect(page.locator('.theft-note')).toBeInViewport();
});
test('leyendas simultáneas dejan libres el mapa y sus controles', async ({page}, testInfo) => {
  await page.goto('/');
  await expect(page.locator('.panel-toggle')).toBeVisible();
  await expandPanel(page);
  await page.getByRole('button',{name:'Probar recorrido de ejemplo'}).click();
  await page.getByRole('button',{name:'Comparar recorridos'}).click();
  await expect(page.locator('.route-line:not(.route-robos)')).toHaveCount(3);
  await page.getByRole('button',{name:'Capas',exact:true}).click();
  await page.getByLabel('Mostrar 25 cuadrículas').check();
  const loaded = page.waitForResponse(r => r.url().endsWith('/robos-historicos'));
  await page.getByLabel(label).check();
  test.skip((await loaded).status() === 503, 'Requiere la capa local autorizada');
  await page.getByRole('button',{name:'Cerrar opciones de capas'}).click();
  for (const selector of ['.theft-legend','.prediction-legend','.layer-button','.leaflet-control-attribution']) {
    await expect(page.locator(selector)).toBeInViewport();
  }
  const legend = await page.locator('.theft-legend').boundingBox();
  const center = await page.locator('.map-center').boundingBox();
  expect(legend!.y).toBeGreaterThanOrEqual(center!.y + center!.height);
  await page.screenshot({path:testInfo.outputPath('capas-locales.png')});
});
