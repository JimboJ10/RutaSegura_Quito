import { expect, test, type Page } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { expandPanel } from './audit-helpers.mjs';

async function checkControls(page: Page, mobile: boolean) {
  const center = page.getByRole('button', {name:'Centrar zona'});
  const zoom = page.locator('.map-canvas .leaflet-control-zoom');
  const c = (await center.boundingBox())!, z = (await zoom.boundingBox())!;
  expect(c.width).toBeGreaterThanOrEqual(44);
  expect(c.height).toBeGreaterThanOrEqual(44);
  if (mobile) {
    const dx = Math.max(0, z.x-c.x-c.width, c.x-z.x-z.width);
    const dy = Math.max(0, z.y-c.y-c.height, c.y-z.y-z.height);
    expect(Math.hypot(dx,dy)).toBeCloseTo(12, 0);
  }
  for (const selector of ['.map-center', '.leaflet-control-zoom a', '.layer-button', '.expand-map',
    '.map-canvas .leaflet-control-attribution a', '.map-region .route-legend']) {
    for (const el of await page.locator(selector).all()) {
      if (!await el.isVisible()) continue;
      expect(await el.evaluate(node => {
        const r = node.getBoundingClientRect();
        if (node.classList.contains('route-legend')) {
          const buttons = document.querySelectorAll('.map-center,.leaflet-control-zoom,.map-topbar button');
          return [...buttons].every(button => {
            const b = button.getBoundingClientRect();
            return b.right <= r.left || r.right <= b.left || b.bottom <= r.top || r.bottom <= b.top;
          });
        }
        return node.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));
      }), selector).toBe(true);
    }
  }
}

test('dos grupos reales tienen avisos consultables y dejan libres los controles', async ({page,isMobile,browserName}) => {
  // muestra_002 de la validación de cobertura. Datos consultados en la API local.
  await page.goto('/');
  await expect(page.locator('.map-center')).toBeVisible();
  await expandPanel(page);
  await page.getByText('Introducir coordenadas',{exact:true}).click();
  for (const [name,value] of Object.entries({
    'Origen: latitud':-.17735033710019216, 'Origen: longitud':-78.486595648251,
    'Destino: latitud':-.21132433547373866, 'Destino: longitud':-78.51264638087993,
  })) await page.getByRole('spinbutton',{name}).fill(String(value));
  await page.getByRole('button',{name:'Aplicar coordenadas'}).click();
  await page.getByRole('button',{name:'Comparar recorridos',exact:true}).click();
  const pins = page.locator('.historical-pin');
  await expect(pins).toHaveCount(2, {timeout:30000});
  await expect(page.getByText('Evaluando la alternativa de robos históricos…')).toHaveCount(0, {timeout:30000});
  await expect(pins).toHaveCount(2);
  const dir = resolve('../resultados/aviso-compacto', browserName);
  await mkdir(dir,{recursive:true});
  for (const view of ['normal','ampliado']) {
    if (view === 'ampliado') await page.getByRole('button',{name:'Ampliar mapa'}).click();
    await checkControls(page, isMobile);
    const map = page.locator('.map-canvas');
    const frame = await map.boundingBox();
    const center = await page.locator('.map-center').boundingBox();
    await pins.last().click();
    await expect(page.locator('.historical-notice')).toHaveCount(1);
    await expect(page.locator('.historical-notice')).toContainText('2019');
    await expect.poll(() => page.locator('img.leaflet-tile').evaluateAll(tiles => tiles.length > 0 &&
      tiles.every(t => (t as HTMLImageElement).complete && Number(getComputedStyle(t).opacity) === 1))).toBe(true);
    await page.screenshot({path:resolve(dir, page.viewportSize()!.width+'-'+view+'.png')});
    await page.getByRole('button',{name:'Cerrar información histórica'}).click();
    await expect(pins.last()).toBeFocused();
    expect(await map.boundingBox()).toEqual(frame);
    expect(await page.locator('.map-center').boundingBox()).toEqual(center);
    await pins.last().click();
    expect(await map.boundingBox()).toEqual(frame);
    if (isMobile) {
      await page.getByRole('button',{name:'Ver detalles'}).click();
      await expect(page.locator('#historical-full')).toContainText('por km²');
      expect(await map.boundingBox()).toEqual(frame);
      await checkControls(page, true);
    }
    await page.getByRole('button',{name:'Cerrar información histórica'}).click();
    if (view === 'normal' && isMobile) {
      const info = page.getByRole('button',{name:'Información de cobertura'});
      await info.click();
      await checkControls(page, true);
      await info.click();
    }
  }
  await pins.first().press('Enter');
  await expect(page.locator('.historical-notice')).toBeVisible();
});
