import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import App from '../App';
import { api } from '../api';
import { config, predictions, request, routes } from './fixtures';

// La interacción Leaflet se verifica por separado en navegador. Aquí aislamos el panel.
vi.mock('../components/MapView', () => ({ MapView: ({ onPoint }: { onPoint: (name: string, point: unknown) => void }) =>
  <div aria-label="Mapa simulado"><button onClick={() => onPoint('origen', request.origen)}>Elegir origen simulado</button><button onClick={() => onPoint('destino', request.destino)}>Elegir destino simulado</button></div> }));
beforeEach(() => {
  vi.spyOn(api, 'health').mockResolvedValue({ estado: 'ok', nodos: 14934, aristas: 44672, periodo: '2026-06' });
  vi.spyOn(api, 'config').mockResolvedValue(config);
  vi.spyOn(api, 'predictions').mockResolvedValue(predictions);
  vi.spyOn(api, 'routes').mockResolvedValue(routes);
});
afterEach(cleanup);
it('deshabilita comparar antes de tener ambos puntos', async () => {
  render(<App />);
  const button = await screen.findByRole('button', { name: 'Comparar recorridos' });
  expect((button as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByRole('button', { name: 'Elegir origen simulado' }));
  expect((button as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByRole('button', { name: 'Elegir destino simulado' }));
  expect((button as HTMLButtonElement).disabled).toBe(false);
});
it('el ejemplo solicita las tres rutas al backend y permite elegirlas', async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole('button', { name: 'Probar recorrido de ejemplo' }));
  expect(api.routes).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Comparar recorridos' }));
  await screen.findByRole('heading', { name: 'Tres formas de llegar' });
  expect(api.routes).toHaveBeenCalledWith(request.origen, request.destino, expect.any(AbortSignal));
  const historical = screen.getByRole('button', { name: /Ruta histórica/ });
  fireEvent.click(historical);
  expect(historical.getAttribute('aria-pressed')).toBe('true');
  expect(screen.getByText('104,7 m')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Restablecer' }));
  expect(screen.queryByRole('heading', { name: 'Tres formas de llegar' })).toBeNull();
});
it('los errores de rutas son visibles y no se presentan resultados inventados', async () => {
  vi.mocked(api.routes).mockRejectedValueOnce(new Error('Origen o destino demasiado lejos de la red con predicciones.'));
  render(<App />);
  fireEvent.click(await screen.findByRole('button', { name: 'Probar recorrido de ejemplo' }));
  fireEvent.click(screen.getByRole('button', { name: 'Comparar recorridos' }));
  expect(await screen.findByRole('alert')).toHaveProperty('textContent', expect.stringContaining('demasiado lejos'));
  expect(screen.queryByRole('heading', { name: 'Tres formas de llegar' })).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Intentar nuevamente' }));
  await screen.findByRole('heading', { name: 'Tres formas de llegar' });
});
it('muestra indisponibilidad del backend y recupera la conexión con reintento', async () => {
  vi.mocked(api.health).mockRejectedValueOnce(new Error('No se pudo conectar con el backend.'));
  render(<App />);
  expect(await screen.findByRole('alert')).toHaveProperty('textContent', 'No se pudo conectar con el backend.');
  fireEvent.click(screen.getByRole('button', { name: 'Intentar nuevamente' }));
  await screen.findByRole('button', { name: 'Comparar recorridos' });
});
it('los fallos de predicciones no bloquean la planificación', async () => {
  vi.mocked(api.predictions).mockRejectedValue(new Error('Capa no disponible'));
  render(<App />);
  await screen.findByRole('button', { name: 'Comparar recorridos' });
  await waitFor(() => expect(api.predictions).toHaveBeenCalled());
  expect(screen.getByRole('button', { name: 'Probar recorrido de ejemplo' })).toBeTruthy();
});
it('permite introducir latitud y longitud por teclado', async () => {
  render(<App />);
  await screen.findByRole('button', { name: 'Comparar recorridos' });
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Origen: latitud' }), { target: { value: '-0.201' } });
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Origen: longitud' }), { target: { value: '-78.504' } });
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Destino: latitud' }), { target: { value: '-0.184' } });
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Destino: longitud' }), { target: { value: '-78.486' } });
  fireEvent.click(screen.getByRole('button', { name: 'Aplicar coordenadas' }));
  fireEvent.click(screen.getByRole('button', { name: 'Comparar recorridos' }));
  await screen.findByRole('heading', { name: 'Tres formas de llegar' });
  expect(api.routes).toHaveBeenCalledWith(request.origen, request.destino, expect.any(AbortSignal));
});
