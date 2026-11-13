import { expect, test } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { expandPanel } from './audit-helpers.mjs';

test('el aviso sigue las cuatro modalidades y permite consultar de nuevo el tramo', async ({page},info) => {
  await page.goto('/');
  await expect(page.locator('.panel-toggle')).toBeVisible();
  await expandPanel(page);
  await page.getByRole('button',{name:'Probar recorrido de ejemplo'}).click();
  await page.getByRole('button',{name:'Comparar recorridos'}).click();
  await expect(page.locator('.route-card')).toHaveCount(4,{timeout:30000});
  const pin = page.getByRole('button',{name:'Consultar información histórica del tramo'});
  const notice = page.locator('.historical-notice');
  for (const id of ['historica','lightgbm','robos','corta']) {
    await page.locator('[data-modalidad="'+id+'"]').click();
    await expect(pin).toHaveCount(1);
    await expect(notice).toBeVisible();
  }
  await page.getByRole('button',{name:'Cerrar información histórica'}).click();
  await expect(notice).toHaveCount(0);
  await pin.focus();
  await pin.press('Enter');
  await expect(notice).toBeVisible();
  const dir = resolve('../resultados/viabilidad_modalidad_robos/capturas-aviso');
  await mkdir(dir,{recursive:true});
  await page.screenshot({path:resolve(dir,info.project.name+'.png')});
  const box = await notice.boundingBox();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x+box!.width).toBeLessThanOrEqual(page.viewportSize()!.width);
  await expect(notice).toHaveCount(0,{timeout:7000});
  await pin.click();
  await expect(notice).toBeVisible();
});

for (const scenario of ['uno','varios','ninguno','ausente']) {
  test('intersecciones: '+scenario, async ({page}) => {
    await page.route('**/robos-historicos/alternativa',r=>r.fulfill({json:{estado:'sin_alternativa'}}));
    const lines = [[[-78.5,-.196],[-78.498,-.194]]];
    if (scenario==='varios') lines.push([[-78.5,-.195],[-78.498,-.193]]);
    await page.route('**/robos-historicos/cruces?*',r=>r.fulfill(scenario==='ausente' ? {status:503,json:{detail:'Sin datos'}} :
      {json:Object.fromEntries(['corta','historica','lightgbm'].map(id=>[id,{zonas:scenario==='ninguno'?[]:['zona'],tramos:scenario==='ninguno'?[]:lines}]))}));
    await page.goto('/');
    await expect(page.locator('.panel-toggle')).toBeVisible();
    await expandPanel(page);
    await page.getByRole('button',{name:'Probar recorrido de ejemplo'}).click();
    await page.getByRole('button',{name:'Comparar recorridos'}).click();
    const eligible = ['uno','varios'].includes(scenario);
    await expect(page.locator('.theft-summary')).toContainText(eligible?'Atraviesa':scenario==='ausente'?'no disponible':'no atraviesa');
    await expect(page.locator('.historical-pin')).toHaveCount(eligible?1:0);
    await expect(page.locator('.historical-notice')).toHaveCount(eligible?1:0);
    if (scenario === 'varios') {
      await expect(page.locator('.historical-pin')).toHaveAccessibleName(/2 grupos en esta vista/);
      await page.getByRole('button',{name:'Acercar a los tramos'}).click();
      await expect(page.locator('.historical-pin')).toHaveCount(2);
      await page.getByRole('button',{name:'Centrar zona'}).click();
      await expect(page.locator('.historical-pin')).toHaveCount(1);
      await expect(page.locator('.historical-pin')).toHaveAccessibleName(/2 grupos en esta vista/);
    }
  });
}
