import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApi } from '../api';
import { pointError } from '../types';
import { config, predictions, request, routes } from './fixtures';

const client = createApi('http://api.example/');
const signal = () => new AbortController().signal;
const respond = (body: unknown, status = 200) => vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status })));
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

describe('Contrato HTTP', () => {
  it('envía origen/destino con lat/lon numéricos y conserva el GeoJSON lon/lat', async () => {
    respond(routes);
    const response = await client.routes(request.origen, request.destino, signal());
    expect(fetch).toHaveBeenCalledWith('http://api.example/rutas', expect.objectContaining({
      method: 'POST', credentials: 'omit', body: JSON.stringify(request),
      headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
    }));
    expect(response.features[0].geometry.coordinates[0][0]).toEqual([-78.503, -0.2008]);
  });
  it('acepta polígonos de un anillo y devuelve sus indicadores sin transformarlos', async () => {
    respond(predictions);
    expect(await client.predictions(signal())).toEqual(predictions);
  });
  it('lee los métodos, periodo, CRS y cobertura reales de config', async () => {
    respond(config);
    expect(await client.config(signal())).toEqual(config);
  });
  it.each([['CRS no admitido', { ...config, crs: 'EPSG:3857' }], ['bbox invertido', { ...config, bbox: [-78, 0, -79, -1] }]])('rechaza %s', async (_, value) => {
    respond(value); await expect(client.config(signal())).rejects.toThrow('configuración');
  });
  it.each([
    [422, { detail: 'Origen o destino demasiado lejos de la red con predicciones.' }, 'demasiado lejos'],
    [422, { detail: [{ loc: ['body', 'origen', 'lat'], msg: 'Valor no permitido' }] }, 'origen.lat: Valor no permitido'],
    [503, { detail: 'Predicciones no disponibles' }, 'Predicciones no disponibles'],
    [500, {}, 'servidor no pudo'],
  ])('interpreta el error %s', async (status, body, message) => {
    respond(body, status); await expect(client.routes(request.origen, request.destino, signal())).rejects.toThrow(message);
  });
  it('no convierte una respuesta exitosa inválida en rutas ficticias', async () => {
    respond({ ...routes, features: [] }); await expect(client.routes(request.origen, request.destino, signal())).rejects.toThrow('tres rutas');
  });
  it('no sustituye indicadores ausentes por cero', async () => {
    const invalid = structuredClone(predictions);
    delete (invalid.features[0].properties as Partial<typeof invalid.features[0]['properties']>).pred_historico;
    respond(invalid); await expect(client.predictions(signal())).rejects.toThrow('GeoJSON');
  });
  it('informa pérdidas de conexión', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    await expect(client.health(signal())).rejects.toThrow('No se pudo conectar');
  });
  it('informa falta de URL sin enviar solicitudes', async () => {
    const mocked = vi.fn(); vi.stubGlobal('fetch', mocked);
    await expect(createApi(undefined).health(signal())).rejects.toThrow('Falta configurar');
    expect(mocked).not.toHaveBeenCalled();
  });
  it('propaga cancelación sin mostrarla como fallo de red', async () => {
    vi.stubGlobal('fetch', vi.fn((_, options) => new Promise((_resolve, reject) => {
      options.signal.addEventListener('abort', () => reject(new DOMException('Abort', 'AbortError')));
    })));
    const controller = new AbortController();
    const pending = client.health(controller.signal);
    controller.abort();
    await expect(pending).rejects.toMatchObject({ name: 'AbortError' });
  });
  it('limita solicitudes bloqueadas a 30 segundos', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', vi.fn((_, options) => new Promise((_resolve, reject) => {
      options.signal.addEventListener('abort', () => reject(new DOMException('Abort', 'AbortError')));
    })));
    const pending = expect(client.health(signal())).rejects.toThrow('tardando demasiado');
    await vi.advanceTimersByTimeAsync(30000); await pending;
  });
});
describe('Validación previa', () => {
  it.each([
    { origen: null, destino: request.destino },
    { origen: request.origen, destino: request.origen },
    { origen: { lat: NaN, lon: -78 }, destino: request.destino },
    { origen: { lat: -0.2, lon: 181 }, destino: request.destino },
  ])('rechaza puntos incompletos, coincidentes o inválidos: %o', points => expect(pointError(points)).not.toBeNull());
  it('acepta el caso conocido', () => expect(pointError(request)).toBeNull());
});
