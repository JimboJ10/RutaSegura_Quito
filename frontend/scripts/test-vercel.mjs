// Run against the public production alias in a fresh, unauthenticated browser.
import assert from 'node:assert/strict';
import { chromium, expect } from '@playwright/test';

const url = new URL(process.argv[2]);
assert.equal(url.protocol, 'https:');
const browser = await chromium.launch();
try {
  for (const [width, height] of [[390, 844], [1280, 800]]) {
    const context = await browser.newContext({ viewport: { width, height }, hasTouch: width < 768 });
    const page = await context.newPage();
    await page.goto(url.origin);
    await expect(page.getByText('Demo conectada', { exact: true })).toBeVisible({ timeout: 60000 });
    const panel = page.locator('.panel-toggle');
    if (await panel.getAttribute('aria-expanded') === 'false') await panel.click();
    await page.getByRole('button', { name: 'Probar recorrido de ejemplo' }).click();
    const result = page.waitForResponse(r => r.url() === url.origin + '/api/rutas');
    const extra = page.waitForResponse(r => r.url() === url.origin + '/api/robos-historicos/alternativa', {timeout: 60000});
    await page.getByRole('button', { name: 'Comparar recorridos', exact: true }).click();
    const response = await result;
    assert.equal(response.status(), 200);
    const expected = { corta: 3.255669, historica: 3.346387, lightgbm: 3.293076, robos: 3.3318 };
    const { features } = await response.json();
    const alternative = await extra;
    assert.equal(alternative.status(), 200);
    const {estado, feature} = await alternative.json();
    assert.equal(estado, 'disponible');
    features.push(feature);
    assert.equal(new Set(features.map(f => JSON.stringify(f.geometry))).size, 4);
    assert.deepEqual(features.map(f => f.properties.id).sort(), Object.keys(expected).sort());
    for (const { properties: p } of features) {
      assert.ok(Math.abs(p.distancia_km - expected[p.id]) <= 0.001);
    }
    await expect(page.locator('.route-card')).toHaveCount(4);
    await page.locator('[data-modalidad="robos"]').click();
    await expect(page.locator('.route-robos')).toHaveAttribute('stroke-width','7');
    await expect(page.locator('.leaflet-historical-segments-pane path').first()).toHaveAttribute('d',/L/);
    const close = page.getByRole('button',{name:'Cerrar información histórica'});
    if (await close.isVisible()) await close.click();
    const frame = await page.locator('.map-canvas').boundingBox();
    await page.locator('.historical-pin').first().click();
    await page.getByRole('button',{name:'Ver detalles'}).click();
    await expect(page.locator('#historical-full')).toContainText('No representa peligro actual');
    assert.deepEqual(await page.locator('.map-canvas').boundingBox(),frame);
    await close.click();
    await expect(page.locator('.leaflet-tile-loaded').first()).toBeVisible();
    await page.getByRole('button', { name: 'Guardar recorrido', exact: true }).click();
    await expect(page.getByText('Recorrido guardado en este dispositivo')).toBeVisible();
    await page.waitForFunction(() => !!navigator.serviceWorker.controller);
    await context.setOffline(true);
    await page.close();
    const saved = await context.newPage();
    await saved.goto(url.origin);
    await saved.locator('.saved-library li button').first().click();
    const options = saved.locator('.saved-options button');
    await expect(options).toHaveCount(4);
    const paths = new Set();
    for (const button of await options.all()) {
      await button.click();
      await expect(saved.locator('.saved-map .leaflet-overlay-pane path')).toHaveAttribute('d', /L/);
      paths.add(await saved.locator('.saved-map .leaflet-overlay-pane path').getAttribute('d'));
    }
    assert.equal(paths.size,4);
    await expect(saved.locator('.leaflet-saved-streets-pane path')).toHaveAttribute('d', /L/);
    await context.close();
    console.log(width, height, 'OK: public routes, tiles and offline library');
  }
} finally {
  await browser.close();
}
