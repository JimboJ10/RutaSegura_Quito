import type { ApiConfig, Predictions, Routes } from '../types';

// Datos sintéticos para pruebas unitarias; nunca se utilizan como resultados de la aplicación.
export const request = { origen: { lat: -0.201, lon: -78.504 }, destino: { lat: -0.184, lon: -78.486 } };
export const config: ApiConfig = {
  proyecto: 'RutaInformada Quito', version_api: '0.1.0', zona_demo: 'Zona de demostración de Quito',
  bbox: [-78.515, -0.215, -78.478, -0.173], periodo: '2026-06', tipo: 'demostracion_retrospectiva',
  metodos: ['corta', 'historica', 'lightgbm'], desvio_maximo_pct: 15,
  distancia_maxima_ajuste_m: 300, crs: 'EPSG:4326', advertencias: ['Las distancias excluyen el acceso.'],
};
export const predictions: Predictions = { type: 'FeatureCollection', features: [{
  type: 'Feature', properties: { anio: 2026, mes: 6, cx: 1, cy: 2, pred_historico: 1, pred_lightgbm_v2: 2 },
  geometry: { type: 'Polygon', coordinates: [[[-78.51, -0.21], [-78.50, -0.21], [-78.50, -0.20], [-78.51, -0.21]]] },
}] };
export const routes: Routes = {
  type: 'FeatureCollection',
  features: (['corta', 'historica', 'lightgbm'] as const).map((id, i) => ({
    type: 'Feature', properties: { id, distancia_km: [3.2557, 3.3062, 3.2978][i], desvio_pct: [0, 1.551, 1.294][i], indice_historico: 9.7, indice_lightgbm: 8.5 },
    geometry: { type: 'MultiLineString', coordinates: [[[-78.503, -0.2008], [-78.4854, -0.1844]]] },
  })),
  metadata: {
    periodo: '2026-06', tipo: 'demostracion_retrospectiva', desvio_maximo_pct: 15,
    origen_ajustado: { lat: -0.2008, lon: -78.503, distancia_ajuste_m: 104.7 },
    destino_ajustado: { lat: -0.1844, lon: -78.4854, distancia_ajuste_m: 76.2 },
    advertencia: 'Distancias calculadas entre nodos ajustados. No incluyen el acceso.',
  },
};
