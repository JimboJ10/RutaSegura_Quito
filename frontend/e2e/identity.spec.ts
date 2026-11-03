import { test, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { expandPanel, measure } from './audit-helpers.mjs';

const description = 'Aplicación web experimental que permite comparar rutas peatonales en una zona del centro-norte de Quito utilizando información histórica de siniestros de tránsito e inteligencia artificial.';
const warning = 'Demostración retrospectiva con datos de junio de 2026. Los indicadores no representan probabilidades individuales de accidente ni garantizan la seguridad de los recorridos.';

test('identidad pública: nombre, presentación científica y cabecera responsive', async ({ page, isMobile }, testInfo) => {
  const health = page.waitForResponse(r => r.url().endsWith('/health') && r.status() === 200);
  const config = page.waitForResponse(r => r.url().endsWith('/config') && r.status() === 200);
  await page.goto('/');
  for (const response of await Promise.all([health, config])) {
    expect((await response.json()).proyecto).toBe('RutaInformada Quito');
  }
  await expect(page.getByText('Demo conectada', { exact: true })).toBeVisible();
  await expect(page).toHaveTitle('RutaInformada Quito · Decide tu camino con datos.');
  await expect(page.locator('meta[name="description"]')).toHaveAttribute('content', description);
  await expect(page.getByRole('link', { name: 'RutaInformada Quito, inicio' })).toBeVisible();
  await expect(page.locator('body')).not.toContainText('RutaSegura');
  await page.evaluate(() => document.fonts.ready);
  const header = await page.evaluate(() => {
    const brand = document.querySelector('.brand')!.getBoundingClientRect();
    const status = document.querySelector('.header-right')!.getBoundingClientRect();
    return { brandRight: brand.right, statusLeft: status.left, statusRight: status.right, width: innerWidth };
  });
  expect(header.brandRight + 8).toBeLessThanOrEqual(header.statusLeft);
  expect(header.statusRight).toBeLessThanOrEqual(header.width);
  expect((await measure(page)).horizontalOverflow).toBe(false);

  const output = resolve('evidencias/identidad-publica', testInfo.project.name);
  await mkdir(output, { recursive: true });
  const capture = async (name: string) => {
    await page.waitForFunction(() => {
      const map = document.querySelector('.map-canvas')!.getBoundingClientRect();
      const tiles = [...document.querySelectorAll<HTMLImageElement>('.leaflet-tile')].filter(img => {
        const r = img.getBoundingClientRect();
        return r.bottom > map.top && r.top < map.bottom && r.right > map.left && r.left < map.right;
      });
      return tiles.length > 0 && tiles.every(img => img.complete && img.naturalWidth > 0 && Number(getComputedStyle(img).opacity) >= 1);
    });
    await page.screenshot({ path: resolve(output, name + '.png'), fullPage: true, animations: 'disabled' });
  };
  await capture('01-inicio');
  await expandPanel(page);
  const slogan = page.locator(isMobile ? '.empty-state strong' : '.planner-intro h1');
  await slogan.scrollIntoViewIfNeeded();
  await expect(slogan).toHaveText('Decide tu camino con datos.');
  await expect(slogan).toBeInViewport();
  expect((await measure(page)).horizontalOverflow).toBe(false);
  await capture('02-presentacion');

  await page.getByRole('button', { name: 'Sobre los datos' }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('heading')).toBeFocused();
  await expect(dialog.getByRole('heading')).toBeInViewport({ ratio: 1 });
  await expect(dialog.locator('.main-warning')).toBeInViewport({ ratio: 1 });
  await expect(dialog).toContainText('RutaInformada Quito');
  await expect(dialog).toContainText(description);
  await expect(dialog).toContainText(warning);
  await expect(dialog).toContainText('excluyen el acceso desde las coordenadas solicitadas');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await capture('03-advertencias');
  await page.getByRole('button', { name: 'Entendido, volver al mapa' }).click();
  await expect(dialog).not.toBeVisible();
});
