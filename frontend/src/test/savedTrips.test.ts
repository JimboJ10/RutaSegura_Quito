import { describe, expect, it } from 'vitest';
import { isSavedTrip, storageMessage } from '../savedTrips';
import { request, routes } from './fixtures';

const valid = {version:1, id:'local', savedAt:'2026-11-10T12:00:00Z', points:request, routes};
describe('lectura de copias locales', () => {
  it('acepta las tres modalidades y sus coordenadas', () => expect(isSavedTrip(valid)).toBe(true));
  it('lee copias v2 con tres o cuatro modalidades y exige las métricas de la cuarta', () => {
    const feature = structuredClone(routes.features[0]);
    feature.properties.id = 'robos';
    feature.properties.comparacion_robos = {periodo:'2019-2022', altas_m:10, altas_corta_m:50, ponderado:20, ponderado_corta:30};
    const cuatro = {...valid, version:2, routes:{...routes, features:[...routes.features, feature]}};
    expect(isSavedTrip({...valid,version:2})).toBe(true);
    expect(isSavedTrip(cuatro)).toBe(true);
    expect(isSavedTrip({...cuatro,version:1})).toBe(false);
    delete feature.properties.comparacion_robos;
    expect(isSavedTrip(cuatro)).toBe(false);
  });
  it.each([null, {...valid,version:3}, {...valid,points:{}}, {...valid,savedAt:'?'}, {...valid,routes:{...routes,features:[null]}},
    {...valid,routes:{...routes,metadata:{...routes.metadata,periodo:'desconocido'}}}])('descarta registros incompatibles', row => {
    expect(isSavedTrip(row)).toBe(false);
  });
  it('explica cómo recuperar espacio', () => expect(storageMessage(new DOMException('', 'QuotaExceededError'))).toContain('libera espacio'));
});
