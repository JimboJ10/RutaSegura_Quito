// Render offline de la fuente OSM conservada y los GeoJSON de la auditoría.
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from '@playwright/test';
const root = path.resolve('..');
const out = path.join(root, 'backend/evidencias/acceso/capturas');
fs.mkdirSync(out, { recursive: true });
const source = JSON.parse(fs.readFileSync(path.join(root, 'resultados/ampliacion/cache_osmnx/e275a3de6ac9e0fbd4a90530b29956a6a15357c6.json'), 'utf8'));
const nodes = new Map(source.elements.filter(e => e.type === 'node').map(n => [n.id, [n.lon, n.lat]]));
const roads = source.elements.filter(e => e.type === 'way' && e.tags.highway).map(w => ({ id: w.id, kind: w.tags.highway, cs: w.nodes.map(n => nodes.get(n)) }));
const rutas = JSON.parse(fs.readFileSync(path.join(root, 'backend/evidencias/acceso/rutas.geojson'), 'utf8')).features;
const retiradas = JSON.parse(fs.readFileSync(path.join(root, 'backend/evidencias/acceso/ampliada-retiradas.geojson'), 'utf8')).features;
const browser = await chromium.launch();
try {
  for (const caso of ['piloto', 'norte_sur', 'suroeste_noreste', 'centro_este', 'humboldt']) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 700 }, deviceScaleFactor: 1 });
    await page.setContent('<html lang="es"><meta charset="utf-8"><style>*{box-sizing:border-box}body{font:16px system-ui;margin:20px;color:#223b35;background:#fffdf7}h1{font-size:23px;margin:0 0 8px}p{margin:6px 0 12px}main{display:grid;grid-template-columns:1fr 1fr;gap:14px}figure{margin:0}h2{font-size:17px;margin:0 0 6px}.map{height:490px;background:#f8f5ed!important;border:1px solid #aaa}small{display:block;margin-top:10px}</style><h1></h1><p></p><main></main><small>© OpenStreetMap contributors · ODbL · extracto local 2026-11-04 05:06:56 UTC. Norte arriba. Sin verificación física.</small></html>');
    await page.addStyleTag({ path: path.resolve('node_modules/leaflet/dist/leaflet.css') });
    await page.addScriptTag({ path: path.resolve('node_modules/leaflet/dist/leaflet.js') });
    await page.evaluate(({ roads, rutas, retiradas, caso }) => {
      const ll = p => [p[1], p[0]];
      const esSendero = caso === 'humboldt';
      const puntos = [[-78.5308236, -.203156], [-78.533058, -.1966033]];
      const rutasCaso = rutas.filter(f => f.properties.cobertura === 'ampliada' && f.properties.caso === caso);
      document.querySelector('h1').textContent = esSendero ? 'Sendero de Humboldt · arista recta de 766,47 m' : `Auditoría peatonal · ${caso.replaceAll('_', ' ')}`;
      document.querySelector('p').textContent = esSendero ? 'OSM conserva dos nodos consecutivos. Permiso no explícito, sin prohibición documentada. Trazado físico pendiente.' : 'Veto en rojo; incertidumbre en ocre discontinuo. Rutas corta verde, histórica azul y LightGBM violeta discontinuo.';
      for (const fase of ['antes', 'despues']) {
        const fig = document.createElement('figure'); fig.innerHTML = '<h2></h2><div class="map"></div>'; document.querySelector('main').append(fig);
        fig.firstChild.textContent = esSendero ? (fase === 'antes' ? 'Fuente OSM original' : 'Arista conservada, pendiente de campo') : (fase === 'antes' ? 'Grafo original' : caso === 'centro_este' ? 'Candidato · HTTP 422, ajuste 333,8 m' : 'Copia filtrada');
        const map = L.map(fig.lastChild, { preferCanvas: true, zoomSnap: .25, zoomControl: false, attributionControl: false, zoomAnimation: false, fadeAnimation: false });
        const cs = esSendero ? puntos : rutasCaso.flatMap(f => f.geometry.coordinates.flat());
        map.fitBounds(L.latLngBounds(cs.map(ll)), { padding: [30, 30], maxZoom: 18 });
        L.control.scale({ imperial: false }).addTo(map);
        const box = map.getBounds().pad(.05);
        const visibles = roads.filter(r => box.intersects(L.latLngBounds(r.cs.map(ll))));
        L.polyline(visibles.map(r => r.cs.map(ll)), { color: '#a3aaa3', weight: 1.3, opacity: .9, interactive: false }).addTo(map);
        if (!esSendero) {
          for (const estado of ['restringida', 'revision']) {
            const lines = retiradas.filter(f => f.properties.estado === estado && box.intersects(L.latLngBounds(f.geometry.coordinates.flat().map(ll))));
            L.polyline(lines.flatMap(f => f.geometry.coordinates.map(l => l.map(ll))), { color: estado === 'restringida' ? '#d52424' : '#ad8824', weight: 3.3, opacity: .85, dashArray: estado === 'revision' ? '3 5' : null }).addTo(map);
          }
          for (const f of rutasCaso.filter(f => f.properties.fase === fase)) {
            const id = f.properties.id;
            L.polyline(f.geometry.coordinates.map(l => l.map(ll)), { color: { corta: '#007859', historica: '#0066cb', lightgbm: '#8f2fba' }[id], weight: id === 'historica' ? 4.2 : 3, opacity: 1, dashArray: id === 'lightgbm' ? '6 6' : null }).addTo(map);
          }
          if (caso === 'centro_este') L.circleMarker([-.199, -78.516], { color: '#111', fillColor: '#fff', fillOpacity: 1, radius: 6 }).bindTooltip('Origen solicitado', { permanent: true }).addTo(map);
        } else if (fase === 'despues') {
          L.polyline(puntos.map(ll), { color: '#007859', weight: 5 }).addTo(map);
          puntos.forEach((p, i) => L.circleMarker(ll(p), { color: '#111', radius: 5, fillColor: '#fff', fillOpacity: 1 }).bindTooltip(String([4615266609, 4615266656][i]), { permanent: true }).addTo(map));
        }
      }
    }, { roads, rutas, retiradas, caso });
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    await page.screenshot({ path: path.join(out, `osm-${caso}.png`), fullPage: true });
    await page.close();
  }
} finally { await browser.close(); }
