import { act, cleanup, renderHook } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { api } from '../api';
import { useRoutePlanner } from '../useRutaSegura';
import { request, routes } from './fixtures';
import type { Routes } from '../types';
afterEach(cleanup);
function setup() {
  const hook = renderHook(useRoutePlanner);
  act(() => { hook.result.current.setPoint('origen', request.origen); hook.result.current.setPoint('destino', request.destino); });
  return hook;
}
it('impide solicitudes sin coordenadas', async () => {
  const call = vi.spyOn(api, 'routes');
  const { result } = renderHook(useRoutePlanner);
  await act(() => result.current.calculate());
  expect(call).not.toHaveBeenCalled();
  expect(result.current.error).toContain('Selecciona');
});
it('descarta respuestas antiguas incluso si el transporte ignora abort', async () => {
  let resolve!: (data: Routes) => void;
  const call = vi.spyOn(api, 'routes').mockImplementation(() => new Promise(done => { resolve = done; }));
  const { result } = setup();
  let pending!: Promise<void>;
  act(() => { pending = result.current.calculate(); });
  const signal = call.mock.calls[0][2];
  act(() => result.current.setPoint('destino', { lat: -0.19, lon: -78.49 }));
  expect(signal.aborted).toBe(true);
  await act(async () => { resolve(routes); await pending; });
  expect(result.current.routes).toBeNull();
  expect(result.current.loading).toBe(false);
});
it('solo conserva la respuesta de la solicitud más reciente', async () => {
  const resolvers: ((data: Routes) => void)[] = [];
  vi.spyOn(api, 'routes').mockImplementation(() => new Promise(done => resolvers.push(done)));
  const { result } = setup();
  let first!: Promise<void>; let second!: Promise<void>;
  act(() => { first = result.current.calculate(); });
  act(() => { second = result.current.calculate(); });
  await act(async () => { resolvers[1](routes); await second; });
  const old = structuredClone(routes); old.metadata.advertencia = 'respuesta antigua';
  await act(async () => { resolvers[0](old); await first; });
  expect(result.current.routes?.metadata.advertencia).toBe(routes.metadata.advertencia);
});
it('limpia rutas al intercambiar o restablecer los puntos', async () => {
  vi.spyOn(api, 'routes').mockResolvedValue(routes);
  const { result } = setup();
  await act(() => result.current.calculate());
  expect(result.current.routes).not.toBeNull();
  act(() => result.current.swap());
  expect(result.current.points.origen).toEqual(request.destino);
  expect(result.current.routes).toBeNull();
  act(() => result.current.reset());
  expect(result.current.points).toEqual({ origen: null, destino: null });
});
it('muestra el error real y permite reintentar', async () => {
  vi.spyOn(api, 'routes').mockRejectedValueOnce(new Error('No existe una ruta conectada.')).mockResolvedValueOnce(routes);
  const { result } = setup();
  await act(() => result.current.calculate());
  expect(result.current.error).toContain('No existe una ruta');
  expect(result.current.routes).toBeNull();
  await act(() => result.current.calculate());
  expect(result.current.routes).toEqual(routes);
  expect(result.current.error).toBe('');
});
it('cancela una solicitud al desmontar el panel', () => {
  const call = vi.spyOn(api, 'routes').mockImplementation(() => new Promise(() => {}));
  const { result, unmount } = setup();
  act(() => { void result.current.calculate(); });
  const signal = call.mock.calls[0][2];
  unmount(); expect(signal.aborted).toBe(true);
});
