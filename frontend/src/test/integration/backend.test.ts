import { expect, it } from 'vitest';
import { createApi } from '../../api';

// Integración real, explícita: requiere Uvicorn iniciado. Nunca sustituye la API.
const base = import.meta.env.VITE_API_BASE_URL;
const client = createApi(base);
const signal = () => new AbortController().signal;
const request = { origen: { lat: -0.201, lon: -78.504 }, destino: { lat: -0.184, lon: -78.486 } };

it('el backend real tiene su grafo disponible', async () => {
  expect(await client.health(signal())).toMatchObject({ estado: 'ok', periodo: '2026-06' });
});
it('publica el contrato esperado para la demostración', async () => {
  expect(await client.config(signal())).toMatchObject({
    metodos: ['corta', 'historica', 'lightgbm'], periodo: '2026-06',
    crs: 'EPSG:4326', desvio_maximo_pct: 15, distancia_maxima_ajuste_m: 300,
  });
});
it('el cliente interpreta las 25 cuadrículas reales, en longitud-latitud', async () => {
  const data = await client.predictions(signal());
  expect(data.features).toHaveLength(25);
  for (const feature of data.features) {
    expect(feature.properties.anio).toBe(2026);
    expect(feature.properties.mes).toBe(6);
    for (const ring of feature.geometry.coordinates) {
      expect(ring[0]).toEqual(ring.at(-1));
      for (const [lon, lat] of ring) {
        expect(lon).toBeGreaterThan(-79); expect(lon).toBeLessThan(-78);
        expect(lat).toBeGreaterThan(-1); expect(lat).toBeLessThan(0);
      }
    }
  }
});
it('mantiene las tres distancias, indicadores, continuidad y límite del 15 %', async () => {
  const data = await client.routes(request.origen, request.destino, signal());
  const filtered = (process.env.RUTAINFORMADA_RED ?? 'peatonal_filtrada') === 'peatonal_filtrada';
  expect((await client.health(signal())).aristas).toBe(filtered ? 43248 : 44672);
  const references = filtered
    ? { corta: 3.255669, historica: 3.346387, lightgbm: 3.293076 }
    : { corta: 3.255669, historica: 3.306152, lightgbm: 3.297791 };
  for (const route of data.features) {
    const p = route.properties;
    expect(Math.abs(p.distancia_km - references[p.id])).toBeLessThanOrEqual(0.001);
    expect(p.desvio_pct).toBeLessThanOrEqual(15);
    expect(p.indice_historico).toBeGreaterThanOrEqual(0);
    expect(p.indice_lightgbm).toBeGreaterThanOrEqual(0);
    const lines = route.geometry.coordinates;
    for (let i = 1; i < lines.length; i++) expect(lines[i - 1].at(-1)).toEqual(lines[i][0]);
    console.log(`${p.id}: ${p.distancia_km} km`);
  }
  expect(data.metadata.origen_ajustado.distancia_ajuste_m).toBe(104.7);
  expect(data.metadata.destino_ajustado.distancia_ajuste_m).toBe(76.2);
});
it('presenta el error real de puntos fuera de cobertura', async () => {
  await expect(client.routes({ lat: 0, lon: 0 }, request.destino, signal())).rejects.toThrow('demasiado lejos');
});
it('interpreta la lista real de errores de validación', async () => {
  await expect(client.routes({ lat: 100, lon: -78 }, request.destino, signal())).rejects.toThrow('origen.lat');
});
it('el preflight real permite React local y Content-Type', async () => {
  const response = await fetch(`${base}/rutas`, { method: 'OPTIONS', headers: {
    Origin: 'http://127.0.0.1:5173', 'Access-Control-Request-Method': 'POST',
    'Access-Control-Request-Headers': 'Content-Type',
  } });
  expect(response.status).toBe(200);
  expect(response.headers.get('access-control-allow-origin')).toBe('http://127.0.0.1:5173');
});
