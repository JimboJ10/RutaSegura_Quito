import type { Feature, FeatureCollection, MultiLineString, Polygon } from 'geojson';

export type RouteId = 'corta' | 'historica' | 'lightgbm';
export type Point = { lat: number; lon: number };
export type Endpoint = 'origen' | 'destino';
export type Points = Record<Endpoint, Point | null>;
export type BBox = [number, number, number, number];
export type ApiConfig = {
  proyecto: string; version_api: string; zona_demo: string; bbox: BBox;
  periodo: string; tipo: string; metodos: RouteId[];
  desvio_maximo_pct: number; distancia_maxima_ajuste_m: number;
  crs: string; advertencias: string[];
};
export type Health = { estado: string; nodos: number; aristas: number; periodo: string };
export type PredictionProperties = {
  anio: number; mes: number; cx: number; cy: number;
  pred_historico: number; pred_lightgbm_v2: number;
};
export type Predictions = FeatureCollection<Polygon, PredictionProperties>;
export type PredictionField = 'pred_historico' | 'pred_lightgbm_v2';
export type RouteProperties = {
  id: RouteId; distancia_km: number; desvio_pct: number;
  indice_historico: number; indice_lightgbm: number;
};
export type RouteFeature = Feature<MultiLineString, RouteProperties>;
export type AdjustedPoint = Point & { distancia_ajuste_m: number };
export type Routes = FeatureCollection<MultiLineString, RouteProperties> & {
  metadata: {
    periodo: string; tipo: string; desvio_maximo_pct: number;
    origen_ajustado: AdjustedPoint; destino_ajustado: AdjustedPoint; advertencia: string;
  };
};
export const ROUTE_META: Record<RouteId, { name: string; short: string; color: string; symbol: string; dash?: string }> = {
  corta: { name: 'Ruta más corta', short: 'Más corta', color: '#175b4b', symbol: '01' },
  historica: { name: 'Ruta histórica', short: 'Histórica', color: '#955018', symbol: '02', dash: '10 5' },
  lightgbm: { name: 'Ruta LightGBM', short: 'LightGBM', color: '#6554ac', symbol: '03', dash: '3 6' },
};
export const format = (value: number, digits = 2) => new Intl.NumberFormat('es-EC', {
  minimumFractionDigits: digits, maximumFractionDigits: digits,
}).format(value);
export function periodLabel(period: string) {
  const [year, month] = period.split('-').map(Number);
  return new Intl.DateTimeFormat('es', { month: 'long', year: 'numeric', timeZone: 'UTC' })
    .format(new Date(Date.UTC(year, month - 1, 1)));
}
export function pointError(points: Points): string | null {
  if (!points.origen || !points.destino) return 'Selecciona un origen y un destino.';
  for (const point of [points.origen, points.destino]) {
    if (!Number.isFinite(point.lat) || !Number.isFinite(point.lon) ||
      Math.abs(point.lat) > 90 || Math.abs(point.lon) > 180)
      return 'Introduce latitudes entre −90 y 90 y longitudes entre −180 y 180.';
  }
  if (points.origen.lat === points.destino.lat && points.origen.lon === points.destino.lon)
    return 'El origen y el destino coinciden. Elige dos puntos diferentes.';
  return null;
}
