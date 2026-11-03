import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import L from 'leaflet';
import { MapView } from '../components/MapView';
import { config, predictions, request, routes } from './fixtures';

// Leaflet real en jsdom; se habilita SVG y ResizeObserver ausentes en este DOM.
// Esto no simula píxeles, gestos táctiles ni solicitudes de teselas.
const originalSvg = Object.getOwnPropertyDescriptor(L.Browser, 'svg')!;
beforeEach(() => {
  Object.defineProperty(L.Browser, 'svg', { ...originalSvg, value: true });
  vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} });
});
afterEach(() => { cleanup(); Object.defineProperty(L.Browser, 'svg', originalSvg); vi.unstubAllGlobals(); });
function props() {
  return {
    config, points: request, target: 'origen' as const, onPoint: vi.fn(), routes,
    selected: 'corta' as const, onSelect: vi.fn(), focus: { kind: 'zone' as const, serial: 0 },
    onCenter: vi.fn(), predictions, predictionLoading: false, predictionError: '', onRetryPredictions: vi.fn(),
  };
}
it('monta Leaflet con rutas, marcadores y controles sin seleccionar un punto al centrar', () => {
  const input = props(); render(<MapView {...input} />);
  fireEvent.click(screen.getByRole('button', { name: 'Centrar zona' }));
  expect(input.onCenter).toHaveBeenCalledOnce();
  expect(input.onPoint).not.toHaveBeenCalled();
  expect(screen.getByTitle('A · Origen solicitado')).toBeTruthy();
  expect(screen.getByRole('region', { name: /Mapa de Quito/ })).toBeTruthy();
});
it('permite activar polígonos GeoJSON y cambiar el indicador de la leyenda', () => {
  render(<MapView {...props()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Capas' }));
  fireEvent.click(screen.getByRole('checkbox', { name: 'Mostrar 1 cuadrículas' }));
  expect(screen.getByText('LightGBM · siniestros estimados / mes')).toBeTruthy();
  fireEvent.change(screen.getByLabelText('Indicador'), { target: { value: 'pred_historico' } });
  expect(screen.getByText('Histórico · siniestros estimados / mes')).toBeTruthy();
  fireEvent.click(screen.getByRole('checkbox', { name: 'Mostrar 1 cuadrículas' }));
  expect(screen.queryByText('Histórico · siniestros estimados / mes')).toBeNull();
});
it('ofrece un reintento de capa sin sustituir predicciones por ceros', () => {
  const input = props();
  render(<MapView {...input} predictions={null} predictionError="Las predicciones no están disponibles." />);
  fireEvent.click(screen.getByRole('button', { name: 'Capas' }));
  expect(screen.getByRole('alert').textContent).toContain('no están disponibles');
  expect(screen.queryByRole('checkbox')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Reintentar capa' }));
  expect(input.onRetryPredictions).toHaveBeenCalledOnce();
});
