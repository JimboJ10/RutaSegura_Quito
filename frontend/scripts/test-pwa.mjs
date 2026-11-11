// Ejecutar desde frontend. Servidores y perfil exclusivos de esta prueba.
import { build, preview } from 'vite';
import { chromium, expect } from '@playwright/test';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { resolve, sep } from 'node:path';
import { mkdir, mkdtemp, rm, realpath, writeFile } from 'node:fs/promises';
import assert from 'node:assert/strict';


const origin = 'http://127.0.0.1:4193', backend = 'http://127.0.0.1:8893';
const dir = resolve('test-results/pwa');
await mkdir(dir, {recursive:true});
const profile = await mkdtemp(resolve(dir,'perfil-'));
let apiProcess, apiExit, server, context, installed = false;
const stopFile = resolve(profile,'stop-test-api');
const python = process.env.PWA_TEST_PYTHON || resolve('../backend/.venv/Scripts/python.exe');
async function startApi() {
  assert.equal(await fetch(backend+'/health').then(()=>true,()=>false),false,'Puerto de pruebas ocupado');
  await rm(stopFile,{force:true});
  apiProcess = spawn(python,['-c',[
    'import sys, threading, time, pathlib, uvicorn',
    'server = uvicorn.Server(uvicorn.Config("main:app", host="127.0.0.1", port=8893, log_level="info"))',
    'def stop():',
    '    while not pathlib.Path(sys.argv[1]).is_file(): time.sleep(0.2)',
    '    server.should_exit = True',
    'threading.Thread(target=stop, daemon=True).start()',
    'server.run()',
  ].join('\n'), stopFile], {cwd:resolve('../backend'), windowsHide:true, stdio:['pipe','ignore','inherit'],
    env:{...process.env,RUTAINFORMADA_RED:'peatonal_filtrada',RUTAINFORMADA_COBERTURA:'demo'}});
  apiExit = once(apiProcess,'exit');
  await expect.poll(async()=> (await fetch(backend+'/health').catch(()=>null))?.status,{timeout:60000}).toBe(200);
}
async function stopApi() {
  if (!apiProcess) return;
  await writeFile(stopFile,'stop'); await apiExit; apiProcess = null;
}
async function startWeb() {
  server = await preview({configFile:false,build:{outDir:resolve(dir,'build')},preview:{
    host:'127.0.0.1',port:4193,strictPort:true,proxy:{'/api':{target:backend,rewrite:p=>p.replace(/^\/api/,'')}}}});
}
async function launch(offline=false) {
  context = await chromium.launchPersistentContext(profile,{channel:'chromium',headless:true,
    offline,viewport:{width:390,height:844},hasTouch:true,isMobile:true});
  // La prueba funciona sin depender de internet para las teselas.
  await context.route('https://tile.openstreetmap.org/**',r=>r.abort());
  return context.pages()[0] || await context.newPage();
}
async function calculate(page) {
  const toggle = page.locator('.panel-toggle');
  await expect(toggle).toBeVisible();
  if (await toggle.getAttribute('aria-expanded')==='false') await toggle.click();
  await page.getByRole('button',{name:'Probar recorrido de ejemplo'}).click();
  const res = page.waitForResponse(r=>r.url().endsWith('/rutas') && r.request().method()==='POST');
  await page.getByRole('button',{name:'Comparar recorridos'}).click();
  const response=await res; assert.equal(response.status(),200);
  await expect(page.locator('.route-card')).toHaveCount(3);
  return response.json();
}
async function stored(page) {
  return page.evaluate(async()=> {
    const db = await new Promise((yes,no)=>{const r=indexedDB.open('rutainformada-recorridos');r.onsuccess=()=>yes(r.result);r.onerror=()=>no(r.error)});
    return new Promise((yes,no)=>{const r=db.transaction('recorridos').objectStore('recorridos').getAll();
      r.onsuccess=()=>{db.close();yes(r.result)};r.onerror=()=>no(r.error)});
  });
}
try {
  process.env.VITE_API_BASE_URL='/api';
  await build({build:{outDir:resolve(dir,'build')}});
  await startApi(); await startWeb();
  let page=await launch(); await page.goto(origin);
  await page.waitForFunction(()=>!!navigator.serviceWorker.controller);
  let cdp=await context.newCDPSession(page);
  assert.deepEqual((await cdp.send('Page.getInstallabilityErrors')).installabilityErrors,[]);
  await cdp.send('PWA.install',{manifestId:origin+'/',installUrlOrBundleUrl:origin+'/'});
  installed=true;
  await cdp.send('PWA.changeAppUserSettings',{manifestId:origin+'/',displayMode:'standalone'});
  await cdp.send('PWA.getOsAppState',{manifestId:origin+'/'});
  console.log('PWA instalada en perfil temporal');
  const original=await calculate(page);
  const save=page.getByRole('button',{name:'Guardar recorrido',exact:true});
  await page.evaluate(()=>{window.realPut=IDBObjectStore.prototype.put;IDBObjectStore.prototype.put=()=>{throw new DOMException('quota','QuotaExceededError')}});
  await save.click(); await expect(page.getByText(/Almacenamiento lleno/)).toBeVisible();
  await page.evaluate(()=>{IDBObjectStore.prototype.put=window.realPut;delete window.realPut});
  assert.equal((await stored(page)).length,0);
  await save.click(); await expect(page.getByText('Recorrido guardado en este dispositivo')).toBeVisible();
  const [row]=await stored(page); assert.deepEqual(row.routes,original);
  assert.deepEqual(row.points,{origen:{lat:-.201,lon:-78.504},destino:{lat:-.184,lon:-78.486}});
  const layerStatus = await page.evaluate(async()=> (await fetch('/api/robos-historicos',{cache:'no-store'})).status);
  assert.ok([200,503].includes(layerStatus));
  const stats=await page.evaluate(async()=>{
    const names=await caches.keys(); const cache=await caches.open(names[0]);const requests=await cache.keys();
    const urls=requests.map(r=>new URL(r.url));
    if(names.length!==1 || urls.some(u=>u.origin!==location.origin || !/^\/(index\.html|manifest\.webmanifest|favicon\.svg|icon-(192|512|maskable)\.png|assets\/[^/]+\.(js|css))$/.test(u.pathname))) throw Error('Contenido inesperado en precaché');
    let bytes=0;for(const r of requests) bytes+=(await (await cache.match(r)).arrayBuffer()).byteLength;
    return {recursos:requests.length,bytes};
  });
  console.log('Tamaño de precaché y copia JSON',stats,Buffer.byteLength(JSON.stringify(row)));
  await stopApi();
  await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
  await expect(page.getByRole('heading',{name:'Recorridos guardados'})).toBeVisible();
  const blank=await context.newPage();
  for (const tab of context.pages()) if (tab !== blank) await tab.close();
  await context.close(); context=null; await server.close(); server=null;
  page=await launch(true);
  cdp=await context.newCDPSession(page);
  const opened=context.waitForEvent('page');
  const launched=await cdp.send('PWA.launch',{manifestId:origin+'/'});
  page=await opened;
  await expect(page.getByRole('heading',{name:'Recorridos guardados'})).toBeVisible();
  const {targetInfo}=await cdp.send('Target.getTargetInfo',{targetId:launched.targetId});
  assert.equal(new URL(page.url()).origin,origin);
  console.log('Lanzamiento instalado',targetInfo.type,targetInfo.url,
    'display-mode standalone:',await page.evaluate(()=>matchMedia('(display-mode: standalone)').matches));
  assert.equal(await page.evaluate(()=>navigator.onLine),false);
  await page.locator('.saved-library li button').first().click();
  for(const id of ['corta','historica','lightgbm']) {
    const i=original.features.findIndex(f=>f.properties.id===id);
    await page.locator('.saved-options button').nth(i).click();
    await expect(page.locator('.saved-map path')).toHaveCount(1);
    await expect(page.locator('.saved-map path')).toHaveAttribute('d',/L/);
  }
  assert.deepEqual((await stored(page))[0],row);
  assert.equal(await page.locator('.saved-map .leaflet-tile').count(),0);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await page.screenshot({path:resolve(dir,'guardado-390.png')});
  await startApi(); await startWeb(); await context.setOffline(false);
  await expect(page.locator('.panel-toggle')).toBeVisible({timeout:25000});
  assert.deepEqual((await calculate(page)).features,original.features);
  await page.getByRole('button',{name:'Guardados',exact:true}).click();
  await page.getByRole('button',{name:'Eliminar',exact:true}).click();
  await expect(page.getByText('Aún no tienes recorridos guardados.')).toBeVisible();
  assert.deepEqual(await stored(page),[]);
  console.log('Guardado, cuota, caída de FastAPI, cierre de Chromium, reapertura sin servidores, tres geometrías, recuperación y eliminación: OK');
} finally {
  if(installed && context) {
    const p=context.pages()[0] || await context.newPage();
    await (await context.newCDPSession(p)).send('PWA.uninstall',{manifestId:origin+'/'});
  }
  if(context) await context.close();
  if(server) await server.close();
  await stopApi();
  if((await realpath(profile)).startsWith((await realpath(dir))+sep+'perfil-'))
    await rm(profile,{recursive:true,force:true});
}
