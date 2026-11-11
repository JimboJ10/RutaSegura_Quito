import { useEffect, useState } from 'react';
import { GeoJSON, Pane, Popup } from 'react-leaflet';
import { api } from '../api';
import { categories } from '../thefts';
import type { Crossings, TheftCell, TheftGrid } from '../thefts';
import { format, ROUTE_META } from '../types';
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

export function TheftCrossings({ routes }: {routes: Routes}) {
  const [info, setInfo] = useState<Crossings | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    setInfo(null); setError(false);
    api.theftCrossings(routes, controller.signal).then(data => {
      if (!controller.signal.aborted) setInfo(data);
    }).catch(() => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, [routes]);
  const ids = Object.keys(ROUTE_META) as RouteId[];
  const shared = info ? [...new Set(ids.flatMap(id => info[id]))].filter(cell =>
    ids.filter(id => info[id].includes(cell)).length > 1) : [];
  return <section className="theft-summary" aria-label="Cruces históricos" aria-live="polite">
    <strong>Robos registrados en 2019–2022</strong>
    {error ? <p>Consulta histórica no disponible para estos recorridos.</p> : !info ? <p>Consultando cruces…</p> :
      <><p>Cuadrículas de mayor concentración histórica que atraviesa cada modalidad:</p>
        <ul>{ids.map(id => <li key={id}>{ROUTE_META[id].short}: {info[id].join(', ') || 'ninguna'}</li>)}</ul>
        {shared.length > 0 && <p>Cuadrículas compartidas por varias modalidades: {shared.join(', ')}.</p>}
        <small>Comparación por densidad de registros del periodo, sin estimar probabilidades individuales.</small></>}
  </section>;
}
