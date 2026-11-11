import { useEffect, useState } from 'react';
import { GeoJSON, MapContainer } from 'react-leaflet';
import { shellStatus } from '../pwa';
import L from 'leaflet';
import { deleteTrip, listSaved, saveTrip, storageMessage } from '../savedTrips';
import type { SavedTrip } from '../savedTrips';
import { format, periodLabel, ROUTE_META } from '../types';
import type { Points, RouteId, Routes } from '../types';

export function SaveTripButton({ points, routes }: { points: Points; routes: Routes }) {
  const [state, setState] = useState<'idle' | 'saving' | 'done'>('idle');
  const [error, setError] = useState('');
  useEffect(() => { setState('idle'); setError(''); }, [routes]);
  async function save() {
    if (!points.origen || !points.destino) return;
    setState('saving'); setError('');
    try {
      const id = globalThis.crypto?.randomUUID?.() ?? Array.from(crypto.getRandomValues(new Uint32Array(4))).join('-');
      await saveTrip({version: 1, id, savedAt: new Date().toISOString(),
        points: {origen: points.origen, destino: points.destino}, routes});
      setState('done');
    } catch (e) { setError(storageMessage(e)); setState('idle'); }
  }
  return <div><button className="secondary full-width" disabled={state !== 'idle'} onClick={save}>
    {state === 'done' ? 'Recorrido guardado en este dispositivo' : state === 'saving' ? 'Guardando…' : 'Guardar recorrido'}
  </button>{error && <p role="alert">{error}</p>}</div>;
}

function SavedDetail({trip}: {trip: SavedTrip}) {
  const [selected, select] = useState<RouteId>('corta');
  const f = trip.routes.features.find(f => f.properties.id === selected)!;
  return <article className="saved-detail"><h2>Copia guardada</h2>
    <p>Guardado el {new Date(trip.savedAt).toLocaleString('es-EC')} · Datos de {periodLabel(trip.routes.metadata.periodo)}</p>
    <p>Origen {trip.points.origen.lat}, {trip.points.origen.lon} · Destino {trip.points.destino.lat}, {trip.points.destino.lon}</p>
    <div className="saved-options">{trip.routes.features.map(({properties:r}) =>
      <button className="secondary" key={r.id} aria-pressed={selected === r.id} onClick={() => select(r.id)}>
        {ROUTE_META[r.id].name} · {format(r.distancia_km,3)} km</button>)}</div>
    <MapContainer bounds={L.geoJSON(trip.routes).getBounds().pad(.12)} className="saved-map" attributionControl={false}
      scrollWheelZoom={false} aria-label="Geometría guardada">
      <GeoJSON key={selected} data={f} style={{color: ROUTE_META[selected].color, weight:5, dashArray: ROUTE_META[selected].dash}}/>
    </MapContainer>
    <p>Trazado guardado entre nodos ajustados · {ROUTE_META[selected].name}</p>
    <p>Desvío {format(f.properties.desvio_pct)} % · Índice histórico {format(f.properties.indice_historico,4)} · Índice LightGBM {format(f.properties.indice_lightgbm,4)}</p>
    <p>Los índices miden concentración estimada ponderada por longitud. Las modalidades pueden compartir el mismo trazado.</p>
    <p>{trip.routes.metadata.advertencia}</p></article>;
}

export function SavedLibrary() {
  const [shell, setShell] = useState('Preparando la interfaz para uso sin conexión…');
  useEffect(() => { let active = true; shellStatus.then(s => { if (active) setShell(s); }); return () => { active = false; }; }, []);
  const [rows, setRows] = useState<SavedTrip[]>([]);
  const [selected, select] = useState<string | null>(null);
  const [revision, refresh] = useState(0);
  const [error, setError] = useState('');
  const [invalid, setInvalid] = useState(0);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    setLoading(true); setError('');
    listSaved().then(({trips,invalid}) => {
      if (active) { setRows(trips); setInvalid(invalid); }
    }).catch(e => { if (active) setError(storageMessage(e)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [revision]);
  const trip = rows.find(r => r.id === selected);
  return <section className="saved-library"><h1>Recorridos guardados</h1>
    <p role="status">{shell}</p>
    <p>Copias en este dispositivo. Cada recorrido conserva los datos del momento en que lo guardaste.</p>
    {loading && <p role="status">Leyendo recorridos…</p>}
    {error && <p role="status">{error} <button onClick={() => refresh(n=>n+1)}>Reintentar lectura</button></p>}
    {invalid > 0 && <p role="status">Hay {invalid} copias con formato incompatible.</p>}
    {!loading && !error && !rows.length && <p>Aún no tienes recorridos guardados.</p>}
    <ul>{rows.map(row => <li key={row.id}>
      <button className="secondary" onClick={() => select(row.id)}>{new Date(row.savedAt).toLocaleString('es-EC')} · {format(row.routes.features.find(f=>f.properties.id==='corta')!.properties.distancia_km,3)} km</button>
      <button className="text-button" onClick={async () => {
        try { await deleteTrip(row.id); setRows(prev=>prev.filter(r=>r.id!==row.id)); setError(''); }
        catch (e) { setError(storageMessage(e)); }
      }}>Eliminar</button></li>)}</ul>
    {trip && <SavedDetail key={trip.id} trip={trip} />}</section>;
}
