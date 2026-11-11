import { test, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { expandPanel } from './audit-helpers.mjs';

test('el contorno y la tarjeta siguen la modalidad activa', async ({page}, info) => {
  await page.goto('/');
  await expect(page.locator('.panel-toggle')).toBeVisible();
  await expandPanel(page);
  await page.getByRole('button',{name:'Probar recorrido de ejemplo'}).click();
  const pending = page.waitForResponse(r=>r.url().includes('/robos-historicos/cruces?detalle=true'));
  await page.getByRole('button',{name:'Comparar recorridos'}).click();
  const response = await pending;
  test.skip(response.status() === 503, 'Requiere la capa local');
  expect(response.status()).toBe(200);
  const detail = await response.json();
  const card = page.locator('.theft-summary');
  const paths = page.locator('.leaflet-historical-segments-pane path');
  for (const [id,name] of [['corta','Más corta'],['historica','Menor concentración histórica de siniestros'],['lightgbm','Con estimación de IA']]) {
    const button = page.getByRole('button',{name:new RegExp('^'+name+',')});
    await button.click();
    await expect(button).toHaveAttribute('aria-pressed','true');
    await expect(page.locator('.chosen-mode h3')).toHaveText(name);
    await expect(page.locator('.route-'+id)).toHaveAttribute('stroke-opacity','1');
    const count = detail[id].zonas.length;
    await expect(card).toContainText(count===1 ? 'una zona' : count+' zonas');
    await expect(card).not.toContainText('celda-');
    await expect(paths).toHaveCount(1);
    await expect(page.locator('.leaflet-theft-grid-pane path')).toHaveCount(0);
    await page.getByLabel('Resaltar tramos en el mapa').uncheck();
    await expect(paths).toHaveCount(0);
    await page.getByLabel('Resaltar tramos en el mapa').check();
    await expect(paths).toHaveCount(1);
  }
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  if(process.env.CAPTURAS_RECORRIDO) {
    const folder=path.resolve(process.env.CAPTURAS_RECORRIDO);
    await mkdir(folder,{recursive:true});
    await expect.poll(()=>page.locator('img.leaflet-tile').evaluateAll(imgs=>imgs.length>0 && imgs.every(el=>{
      const img=el as HTMLImageElement; return img.complete && img.naturalWidth>0 && Number(getComputedStyle(img).opacity)===1;
    })),{timeout:25000}).toBe(true);
    await page.locator('#results-title').evaluate(el=>el.scrollIntoView({block:'start'}));
    await page.screenshot({path:path.join(folder,info.project.name+'-comparacion.png')});
    await card.scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(folder,info.project.name+'-historia.png')});
    await page.getByRole('button',{name:'Acercar a los tramos'}).click();
    await expect.poll(()=>page.locator('img.leaflet-tile').evaluateAll(imgs=>imgs.length>0 && imgs.every(el=>{
      const img=el as HTMLImageElement; return img.complete && img.naturalWidth>0 && Number(getComputedStyle(img).opacity)===1;
    })),{timeout:25000}).toBe(true);
    await page.screenshot({path:path.join(folder,info.project.name+'-tramo.png')});
  }
});

test('modalidad sin intersección no dibuja contornos', async ({page})=>{
  await page.route('**/robos-historicos/cruces?*',r=>r.fulfill({json:Object.fromEntries(
    ['corta','historica','lightgbm'].map(id=>[id,{zonas:[],tramos:[]}]))}));
  await page.goto('/');
  await expect(page.locator('.panel-toggle')).toBeVisible();
  await expandPanel(page);
  await page.getByRole('button',{name:'Probar recorrido de ejemplo'}).click();
  await page.getByRole('button',{name:'Comparar recorridos'}).click();
  await expect(page.locator('.theft-summary')).toContainText('no atraviesa zonas');
  await expect(page.getByLabel('Resaltar tramos en el mapa')).toHaveCount(0);
  await expect(page.locator('.leaflet-historical-segments-pane path')).toHaveCount(0);
  await expect(page.locator('.route-line')).toHaveCount(3);
});
