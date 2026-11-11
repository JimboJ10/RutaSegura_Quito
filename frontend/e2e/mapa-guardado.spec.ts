import { expect, test } from '@playwright/test';
import { request, routes } from '../src/test/fixtures';

for (const version of [1, 2]) {
  test('mapa guardado v' + version + ' con y sin teselas', async ({page, context}) => {
    await page.route('**/health', r => r.fulfill({status:503,json:{detail:'API apagada'}}));
    const tiles = 'https://tile.openstreetmap.org/**';
    let fail = true;
    let requests = 0;
    await page.route(tiles, r => {
      requests++;
      if (fail) return r.abort();
      return r.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="white"/></svg>'});
    });
    await page.goto('/');
    await expect(page.getByText('Aún no tienes recorridos guardados.')).toBeVisible();
    const collection = structuredClone(routes);
    if (version === 2) {
      const fourth = structuredClone(routes.features[0]);
      fourth.properties.id = 'robos';
      fourth.properties.comparacion_robos = {periodo:'2019-2022',altas_m:10,altas_corta_m:50,ponderado:20,ponderado_corta:30};
      collection.features.push(fourth);
    }
    collection.features.forEach((f,i) => f.geometry.coordinates[0].splice(1,0,[-78.50 + i*.001,-.196]));
    await page.evaluate(async row => {
      const db = await new Promise<IDBDatabase>((resolve,reject) => {
        const op = indexedDB.open('rutainformada-recorridos'); op.onsuccess = () => resolve(op.result); op.onerror = () => reject(op.error);
      });
      await new Promise<void>((resolve,reject) => {
        const tx = db.transaction('recorridos','readwrite');
        tx.objectStore('recorridos').put(row);
        tx.oncomplete = () => resolve(); tx.onabort = () => reject(tx.error);
      });
      db.close();
    }, {version,id:'prueba',savedAt:new Date().toISOString(),points:request,routes:collection});
    await page.reload();
    await page.locator('.saved-library li button').first().click();
    const map = page.locator('.saved-map');
    const aviso = page.getByText('Mapa de calles no disponible sin conexión. Tu recorrido sigue guardado',{exact:false});
    await expect(aviso).toBeVisible();
    await expect(map.locator('.leaflet-overlay-pane path')).toHaveAttribute('d',/L/);
    fail = false;
    await page.getByRole('button',{name:'Reintentar mapa'}).click();
    await expect(map.locator('.leaflet-tile-loaded').first()).toBeVisible();
    await expect(map.getByRole('link',{name:'OpenStreetMap'})).toBeVisible();
    const options = page.locator('.saved-options button');
    await expect(options).toHaveCount(collection.features.length);
    const paths = new Set();
    for (const button of await options.all()) {
      await button.click();
      await expect(button).toHaveAttribute('aria-pressed','true');
      paths.add(await map.locator('.leaflet-overlay-pane path').getAttribute('d'));
      const box = await map.boundingBox();
      for (const key of ['A · Origen solicitado','B · Destino solicitado']) {
        const pin = await map.getByTitle(key).boundingBox();
        expect(pin!.x).toBeGreaterThanOrEqual(box!.x);
        expect(pin!.y).toBeGreaterThanOrEqual(box!.y);
        expect(pin!.x+pin!.width).toBeLessThanOrEqual(box!.x+box!.width);
        expect(pin!.y+pin!.height).toBeLessThanOrEqual(box!.y+box!.height);
      }
    }
    expect(paths.size).toBe(collection.features.length);
    await context.setOffline(true);
    await expect(aviso).toBeVisible();
    await expect(map.locator('.leaflet-tile')).toHaveCount(0);
    const before = requests;
    await options.first().click();
    await expect(map.locator('.leaflet-overlay-pane path')).toHaveAttribute('d',/L/);
    expect(requests).toBe(before);
    await context.setOffline(false);
    await expect(map.locator('.leaflet-tile-loaded').first()).toBeVisible();
    await expect(aviso).toHaveCount(0);
  });
}
