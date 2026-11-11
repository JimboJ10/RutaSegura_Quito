import { useEffect, useState } from 'react';
import { GeoJSON, Pane, Popup } from 'react-leaflet';
import { api } from '../api';
import { categories } from '../thefts';
import type { Crossings, TheftCell, TheftGrid } from '../thefts';
import { format } from '../types';
import type { RouteId, Routes } from '../types';

export function useTheftGrid(visible: boolean) {
  const [grid, setGrid] = useState<TheftGrid | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!visible || grid) return;
    const controller = new AbortController();
    setError('');
    api.thefts(controller.signal).then(data => {
      if (!controller.signal.aborted) setGrid(data);
    }).catch(() => {
      if (!controller.signal.aborted) setError('La capa local de robos históricos no está disponible.');
    });
    return () => controller.abort();
  }, [visible, grid]);
  return { grid, error };
}

function CellDetails({ cell }: { cell: TheftCell }) {
  return <div className="theft-details"><strong>{cell.celda_id} · {cell.periodo}</strong>
    <div>Registros: {cell.numero_registros ?? cell.rango_registros}</div>
    <div>Superficie: {format(cell.area_km2, 3)} km²</div>
    <div>Densidad: {cell.densidad_registros_periodo_km2 === null ? 'Sin valor publicado' :
      format(cell.densidad_registros_periodo_km2) + ' registros/km²'}</div></div>;
}

export function TheftLayer({ grid, picking }: { grid: TheftGrid; picking: boolean }) {
  return <Pane name="theft-grid" style={{ zIndex: 365, pointerEvents: picking ? 'none' : undefined }}>
    {grid.features.map(f => <GeoJSON key={f.properties.celda_id + String(picking)} data={f}
      pane="theft-grid" interactive={!picking} style={{ color: '#813939', weight: 1, opacity: 0.55,
        fillColor: categories[f.properties.nivel][1], fillOpacity: 0.46 }}>
      {!picking && <Popup><CellDetails cell={f.properties} /></Popup>}
    </GeoJSON>)}</Pane>;
}

export function CellSelector({ grid }: {grid: TheftGrid}) {
  const [id, setId] = useState('');
  const cell = grid.features.find(f => f.properties.celda_id === id)?.properties;
  return <><label htmlFor="theft-cell">Consultar cuadrícula</label>
    <select id="theft-cell" value={id} onChange={e => setId(e.target.value)}>
      <option value="">Elegir cuadrícula</option>
      {grid.features.map(f => <option key={f.properties.celda_id}>{f.properties.celda_id}</option>)}
    </select>{cell && <CellDetails cell={cell} />}</>;
}

export function TheftLegend({ grid }: {grid: TheftGrid}) {
  return <div className="theft-legend"><strong>Robos · registros/km² · 2019–2022</strong><div>
    {Object.entries(categories).filter(([key]) => grid.features.some(f => f.properties.nivel === key))
      .map(([key,[label,color]]) => <span key={key}><i style={{background: color}}/>{label}</span>)}
  </div></div>;
}

export function useCrossings(routes: Routes | null) {
  const [result, setResult] = useState<{ routes: Routes; data: Crossings | null } | null>(null);
  useEffect(() => {
    if (!routes) return;
    const controller = new AbortController();
    api.theftCrossings(routes, controller.signal).then(data => {
      for (const {properties} of routes.features) {
        const entry = data[properties.id];
        if (!Array.isArray(entry?.zonas) || !Array.isArray(entry.tramos)) throw new Error('Detalle no disponible');
      }
      if (!controller.signal.aborted) setResult({routes, data});
    }).catch(() => { if (!controller.signal.aborted) setResult({routes, data: null}); });
    return () => controller.abort();
  }, [routes]);
  return result && result.routes === routes ? result.data : undefined;
}

export function TheftCrossings({ info, selected, highlight, toggle, onZoom }: {
  info: Crossings | null | undefined; selected: RouteId; highlight: boolean; toggle: () => void; onZoom: () => void;
}) {
  const zones = info?.[selected].zonas ?? [];
  const shared = info && Object.entries(info).some(([id, other]) =>
    id !== selected && other.zonas.some(z => zones.includes(z)));
  return <section className="theft-summary" aria-labelledby="history-title">
    <span className="history-period">Robos a personas · 2019–2022</span>
    <h3 id="history-title">Información histórica de tu recorrido</h3>
    <p role="status">{info === null ? 'Consulta histórica no disponible para este recorrido.' :
      !info ? 'Consultando el trazado…' : zones.length === 0 ?
      'Este recorrido no atraviesa zonas de mayor concentración histórica de robos.' :
      <>Atraviesa <b>{zones.length === 1 ? 'una zona' : zones.length + ' zonas'}</b> de mayor concentración histórica de robos.
        {shared && ' Otras modalidades también pasan por alguna de estas zonas.'}</>}</p>
    {zones.length > 0 && <label className="history-toggle"><input type="checkbox" checked={highlight} onChange={toggle} />
      Resaltar tramos en el mapa</label>}
    {zones.length > 0 && highlight && <button type="button" className="history-zoom" onClick={onZoom}>Acercar a los tramos</button>}
    <small>Son registros agrupados por zona. El contorno no indica el lugar exacto de un delito ni un peligro actual.</small>
  </section>;
}
