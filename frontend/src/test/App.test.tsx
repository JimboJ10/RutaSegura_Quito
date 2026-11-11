import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
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
  vi.spyOn(api, 'alternative').mockResolvedValue({estado:'sin_alternativa'});
});
afterEach(cleanup);
it('descarta la respuesta experimental si se cambia el recorrido durante la consulta', async () => {
  let terminar!: () => void;
  vi.mocked(api.alternative).mockImplementationOnce(() => new Promise(resolve => {
    terminar = () => resolve({estado:'coincidente', modalidad:'historica'});
  }));
  render(<App />);
  fireEvent.click(await screen.findByRole('button', {name:'Probar recorrido de ejemplo'}));
  fireEvent.click(screen.getByRole('button', {name:'Comparar recorridos'}));
  await waitFor(() => expect(api.alternative).toHaveBeenCalledOnce());
  const signal = vi.mocked(api.alternative).mock.calls[0][2];
  fireEvent.click(screen.getByRole('button', {name:'Restablecer'}));
  expect(signal.aborted).toBe(true);
  await act(async () => terminar());
  expect(screen.queryByText(/ya cumple el criterio/)).toBeNull();
});
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
  await screen.findByRole('heading', { name: 'Tres modalidades de comparación' });
  expect(api.routes).toHaveBeenCalledWith(request.origen, request.destino, expect.any(AbortSignal));
  const historical = screen.getByRole('button', { name: /Menor concentración histórica de siniestros/ });
  fireEvent.click(historical);
  expect(historical.getAttribute('aria-pressed')).toBe('true');
  expect(screen.getByText('104,7 m')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Restablecer' }));
  expect(screen.queryByRole('heading', { name: 'Tres modalidades de comparación' })).toBeNull();
});
it('los errores de rutas son visibles y no se presentan resultados inventados', async () => {
  vi.mocked(api.routes).mockRejectedValueOnce(new Error('Origen o destino demasiado lejos de la red con predicciones.'));
  render(<App />);
  fireEvent.click(await screen.findByRole('button', { name: 'Probar recorrido de ejemplo' }));
  fireEvent.click(screen.getByRole('button', { name: 'Comparar recorridos' }));
  expect(await screen.findByRole('alert')).toHaveProperty('textContent', expect.stringContaining('demasiado lejos'));
  expect(screen.queryByRole('heading', { name: 'Tres modalidades de comparación' })).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Intentar nuevamente' }));
  await screen.findByRole('heading', { name: 'Tres modalidades de comparación' });
});
it('describe modalidades aunque las tres geometrías coincidan', async () => {
  const coincidentes = structuredClone(routes);
  coincidentes.features.forEach(feature => {
    feature.geometry = structuredClone(coincidentes.features[0].geometry);
  });
  vi.mocked(api.routes).mockResolvedValueOnce(coincidentes);
  render(<App />);
  fireEvent.click(await screen.findByRole('button', { name: 'Probar recorrido de ejemplo' }));
  fireEvent.click(screen.getByRole('button', { name: 'Comparar recorridos' }));
  await screen.findByRole('heading', { name: 'Tres modalidades de comparación' });
  expect(screen.getByText('Las modalidades pueden compartir el mismo recorrido.')).toBeTruthy();
  expect(screen.getAllByRole('button', { name: /Más corta|Menor concentración histórica de siniestros|Con estimación de IA/ })).toHaveLength(3);
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
  await screen.findByRole('heading', { name: 'Tres modalidades de comparación' });
  expect(api.routes).toHaveBeenCalledWith(request.origen, request.destino, expect.any(AbortSignal));
});
