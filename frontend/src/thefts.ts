import type { FeatureCollection, MultiLineString, Polygon } from 'geojson';
import type { RouteId } from './types';

export const categories = {
  menor_concentracion_historica_relativa: ['Menor', '#f4aaa9'],
  concentracion_historica_intermedia: ['Intermedia', '#db5858'],
  mayor_concentracion_historica_relativa: ['Mayor', '#a30922'],
  uno_a_cuatro_registros: ['1–4 registros', '#a596a3'],
  sin_registros_en_esta_fuente: ['Sin registros', '#e0e0dc'],
  celda_parcial_no_comparable: ['Área parcial', '#909493'],
} as const;
export type TheftCell = {
  celda_id: string; periodo: string; numero_registros: number | null; rango_registros: string | null;
  area_km2: number; densidad_registros_periodo_km2: number | null; nivel: keyof typeof categories;
};
export type TheftGrid = FeatureCollection<Polygon, TheftCell>;
export type Crossings = Record<RouteId, { zonas: string[]; tramos: MultiLineString['coordinates'] }>;
