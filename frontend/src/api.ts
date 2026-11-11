import type { ApiConfig, BaseRouteId, Health, Point, Predictions, RouteFeature, Routes } from './types';

import type { TheftGrid, Crossings } from './thefts';

type Alternative = { estado: 'disponible'; feature: RouteFeature }
  | { estado: 'coincidente'; modalidad: BaseRouteId } | { estado: 'sin_alternativa' };
const baseIds = ['corta', 'historica', 'lightgbm'];

export class ApiError extends Error {
  constructor(message: string, public status?: number) { super(message); this.name = 'ApiError'; }
}
export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'No se pudo completar la operación. Intenta nuevamente.';
}
function detailMessage(body: unknown, status: number) {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((item: { loc?: unknown[]; msg?: string }) =>
    [item.loc?.filter(part => part !== 'body').join('.'), item.msg].filter(Boolean).join(': ')).join('; ');
  return status === 503 ? 'Los datos de la demostración no están disponibles. Intenta nuevamente.'
    : status >= 500 ? 'El servidor no pudo procesar la solicitud. Intenta nuevamente.'
    : `No se pudo completar la solicitud (HTTP ${status}).`;
}
export function createApi(baseUrl: string | undefined) {
  async function request<T>(path: string, signal: AbortSignal, body?: unknown): Promise<T> {
    if (!baseUrl?.trim()) throw new ApiError('Falta configurar la URL de conexión con la API.');
    const controller = new AbortController();
    let timedOut = false;
    const relay = () => controller.abort();
    if (signal.aborted) controller.abort();
    signal.addEventListener('abort', relay, { once: true });
    const timer = setTimeout(() => { timedOut = true; controller.abort(); }, 30000);
    try {
      const response = await fetch(`${baseUrl.trim().replace(/\/+$/, '')}${path}`, {
        method: body === undefined ? 'GET' : 'POST',
        cache: 'no-store', credentials: 'omit', signal: controller.signal,
        headers: { Accept: 'application/json, application/geo+json', ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
      const data: unknown = await response.json().catch(() => null);
      if (!response.ok) throw new ApiError(detailMessage(data, response.status), response.status);
      if (!data) throw new ApiError('La API devolvió una respuesta no válida. Intenta nuevamente.');
      return data as T;
    } catch (error) {
      if (signal.aborted) throw new DOMException('Solicitud cancelada', 'AbortError');
      if (timedOut) throw new ApiError('La respuesta está tardando demasiado. Revisa la conexión e intenta nuevamente.');
      if (error instanceof ApiError) throw error;
      throw new ApiError('No se pudo conectar con el backend. Comprueba que esté iniciado y revisa la conexión y CORS.');
    } finally {
      clearTimeout(timer);
      signal.removeEventListener('abort', relay);
    }
  }
  return {
    alternative: async (origen: Point, destino: Point, signal: AbortSignal) => {
      const data = await request<Alternative>('/robos-historicos/alternativa', signal, { origen, destino });
      if (data.estado === 'sin_alternativa' || (data.estado === 'coincidente' && baseIds.includes(data.modalidad)) ||
          (data.estado === 'disponible' && validFeature(data.feature) && validAlternative(data.feature))) return data;
      throw new ApiError('Respuesta experimental inválida.');
    },
    thefts: (signal: AbortSignal) => request<TheftGrid>('/robos-historicos', signal),
    theftCrossings: (routes: Routes, signal: AbortSignal) => request<Crossings>('/robos-historicos/cruces?detalle=true', signal,
      Object.fromEntries(routes.features.map(f => [f.properties.id, f.geometry.coordinates]))),
    health: (signal: AbortSignal) => request<Health>('/health', signal),
    config: async (signal: AbortSignal) => {
      const data = await request<ApiConfig>('/config', signal);
      if (data.crs !== 'EPSG:4326' || !Array.isArray(data.bbox) || data.bbox.length !== 4 ||
          !data.bbox.every(Number.isFinite) || data.bbox[0] >= data.bbox[2] || data.bbox[1] >= data.bbox[3] ||
          !/^\d{4}-(0[1-9]|1[0-2])$/.test(data.periodo) || !Array.isArray(data.advertencias) ||
          !Array.isArray(data.metodos) || !(['corta', 'historica', 'lightgbm'] as const).every(id => data.metodos.includes(id)))
        throw new ApiError('La configuración de la demostración no es válida.');
      return data;
    },
    predictions: async (signal: AbortSignal) => {
      const data = await request<Predictions>('/predicciones', signal);
      if (data.type !== 'FeatureCollection' || !Array.isArray(data.features) || !data.features.length ||
          !data.features.every(f => f.geometry?.type === 'Polygon' &&
            validPositions(f.geometry.coordinates, 2) &&
            [f.properties?.pred_historico, f.properties?.pred_lightgbm_v2].every(nonnegative)))
        throw new ApiError('La capa de predicciones no contiene un GeoJSON válido.');
      return data;
    },
    routes: async (origen: Point, destino: Point, signal: AbortSignal) => {
      const data = await request<Routes>('/rutas', signal, { origen, destino });
      if (!validRoutes(data))
        throw new ApiError('La API no devolvió las tres rutas con geometrías e indicadores válidos.');
      return data;
    },
  };
}
function validAlternative(f: RouteFeature) {
  const p = f.properties.comparacion_robos;
  return f.properties.id === 'robos' && f.properties.desvio_pct <= 15 && p?.periodo === '2019-2022' &&
    [p.altas_m, p.altas_corta_m, p.ponderado, p.ponderado_corta].every(nonnegative) &&
    p.altas_m < p.altas_corta_m && p.ponderado < p.ponderado_corta;
}
function validFeature(f: RouteFeature) {
  return f?.type === 'Feature' && !!f.properties && f.geometry?.type === 'MultiLineString' &&
    validPositions(f.geometry.coordinates, 2) &&
    [f.properties.distancia_km, f.properties.desvio_pct, f.properties.indice_historico, f.properties.indice_lightgbm].every(nonnegative);
}
export function validRoutes(value: unknown, allowAlternative = false): value is Routes {
  const data = value as Routes;
  if (!data || data.type !== 'FeatureCollection' || !Array.isArray(data.features) ||
      !(data.features.length === 3 || (allowAlternative && data.features.length === 4)))
    return false;
  if (!data.features.every(f => validFeature(f) && (baseIds.includes(f.properties.id) ||
      (allowAlternative && validAlternative(f))))) return false;
  const ids = new Set<string>(data.features.map(f => f.properties.id));
  if (ids.size !== data.features.length || !baseIds.every(id => ids.has(id))) return false;
  const meta = data.metadata;
  return !!meta && typeof meta.periodo === 'string' && /^\d{4}-(0[1-9]|1[0-2])$/.test(meta.periodo)
    && typeof meta.tipo === 'string' && typeof meta.advertencia === 'string' && nonnegative(meta.desvio_maximo_pct)
    && [meta.origen_ajustado, meta.destino_ajustado].every(p =>
      p && validPositions([p.lon, p.lat], 0) && nonnegative(p.distancia_ajuste_m));
}
const nonnegative = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v) && v >= 0;
function validPositions(value: unknown, depth: number): boolean {
  if (!Array.isArray(value) || value.length === 0) return false;
  if (depth) return (depth !== 1 || value.length >= 2) && value.every(v => validPositions(v, depth - 1));
  return value.length === 2 && value.every(v => typeof v === 'number' && Number.isFinite(v)) &&
    Math.abs(value[0]) <= 180 && Math.abs(value[1]) <= 90;
}
export const api = createApi(import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.PROD ? '/api' : undefined));
