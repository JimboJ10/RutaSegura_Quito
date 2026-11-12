import { test, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { expandPanel } from './audit-helpers.mjs';

const dir = resolve('../resultados/viabilidad_modalidad_robos/capturas-cobertura');
test.use({serviceWorkers:'block'});

test('zona publicada y aviso del piloto',async ({page,isMobile}, info) => {
  await mkdir(dir,{recursive:true});
  await page.goto('/');
  await expect(page.getByText('Zona piloto: centro-norte de Quito',{exact:true})).toBeVisible();
  await expect(page.getByText(/Actualmente puedes consultar/)).toBeVisible();
  await expect(page.locator('.panel-toggle')).toBeVisible();
  await page.screenshot({path:resolve(dir,info.project.name+'-inicio.png')});
  await page.getByRole('button',{name:'Ver zona disponible'}).click();
  await expect(page.locator('.coverage-boundary')).toHaveAttribute('d',/L/);
  await expect(page.getByText(/una conexión peatonal entre ellos/)).toBeVisible();
  await page.screenshot({path:resolve(dir,info.project.name+'-zona.png')});
  await page.getByRole('button',{name:'Ocultar límite'}).click();
  await expect(page.locator('.coverage-boundary')).toHaveCount(0);
  await expandPanel(page);
  await page.getByRole('button',{name:'Probar recorrido de ejemplo'}).click();
  await page.getByRole('button',{name:'Comparar recorridos'}).click();
  await expect(page.locator('.route-card')).toHaveCount(4,{timeout:30000});
  await page.locator('[data-modalidad="historica"]').click();
  await expect(page.locator('.historical-pin')).toBeVisible();
  await expect(page.locator('.historical-notice')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:resolve(dir,info.project.name+'-aviso.png')});
  if(isMobile) {
    expect((await page.locator('.historical-notice').boundingBox())!.height).toBeLessThan(85);
    await page.getByRole('button',{name:'Ver detalles'}).click();
  }
  await expect(page.getByText('No representa peligro actual ni identifica el lugar exacto de un delito')).toBeVisible();
});

test('distingue las tres causas con respuestas reales',async ({page})=>{
  await page.goto('/');
  await expect(page.locator('.panel-toggle')).toBeVisible();
  await expandPanel(page);
  await page.getByText('Introducir coordenadas',{exact:true}).click();
  for(const [lat,lon,endLat,endLon,message] of [
    [0,0,-.184,-78.486,'Fuera de la zona habilitada'],
    [-.21499,-78.47801,-.184,-78.486,'supera el ajuste máximo de 300 m'],
    [-.1865032,-78.4855812,-.1859903,-78.4854491,'sus nodos no tienen una conexión peatonal válida'],
  ] as const) {
    for (const [label,n] of [['Origen: latitud',lat],['Origen: longitud',lon],['Destino: latitud',endLat],['Destino: longitud',endLon]] as const)
      await page.getByRole('spinbutton',{name:label}).fill(String(n));
    await page.getByRole('button',{name:'Aplicar coordenadas'}).click();
    await page.getByRole('button',{name:'Comparar recorridos'}).click();
    await expect(page.locator('.error-box')).toContainText(message);
  }
});
