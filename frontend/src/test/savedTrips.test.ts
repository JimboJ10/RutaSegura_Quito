import { describe, expect, it } from 'vitest';
import { isSavedTrip, storageMessage } from '../savedTrips';
import { request, routes } from './fixtures';

const valid = {version:1, id:'local', savedAt:'2026-11-10T12:00:00Z', points:request, routes};
describe('lectura de copias locales', () => {
  it('acepta las tres modalidades y sus coordenadas', () => expect(isSavedTrip(valid)).toBe(true));
  it.each([null, {...valid,version:2}, {...valid,points:{}}, {...valid,savedAt:'?'}, {...valid,routes:{...routes,features:[null]}},
    {...valid,routes:{...routes,metadata:{...routes.metadata,periodo:'desconocido'}}}])('descarta registros incompatibles', row => {
    expect(isSavedTrip(row)).toBe(false);
  });
  it('explica cómo recuperar espacio', () => expect(storageMessage(new DOMException('', 'QuotaExceededError'))).toContain('libera espacio'));
});
