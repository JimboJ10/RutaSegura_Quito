import { useState } from 'react';
import { Icon } from './Icon';
import type { ApiConfig, Endpoint, Point, Points } from '../types';
import { pointError } from '../types';

export function Planner({ config, points, target, onTarget, onPoint, onSwap, onReset, onCalculate, onExample, loading, error }: {
  config: ApiConfig; points: Points; target: Endpoint | null; onTarget: (target: Endpoint) => void;
  onPoint: (endpoint: Endpoint, point: Point) => void; onSwap: () => void; onReset: () => void;
  onCalculate: () => void; onExample: () => void; loading: boolean; error: string;
}) {
  const [manualError, setManualError] = useState('');
  const [west,south,east,north] = config.bbox;
  const outside = Object.entries(points).filter(([,p]) => p && (p.lon < west || p.lon > east || p.lat < south || p.lat > north)).map(([name]) => name);
  let guidance = 'Elige otros puntos dentro de la zona disponible o vuelve a intentarlo.';
  if (error.includes('demasiado lejos')) guidance = outside.length
    ? 'Fuera de la zona habilitada: ' + outside.join(' y ') + '. Consulta «Ver zona disponible».'
    : 'Dentro de la zona, el origen o el destino supera el ajuste máximo de ' + config.distancia_maxima_ajuste_m + ' m al nodo peatonal más cercano.';
  if (error.includes('ruta conectada')) guidance = 'Los dos puntos se ajustaron a la red, pero sus nodos no tienen una conexión peatonal válida.';
  return <section className="planner" aria-label="Planificar recorrido">
    <div className="planner-intro"><p className="eyebrow">QUITO, A PIE</p><h1>Decide tu camino<br /> <span>con datos.</span></h1><p>Compara distancias e indicadores.<br />Elige dos puntos para empezar.</p></div>
    <div className="point-fields">
      {(['origen', 'destino'] as const).map((endpoint, index) => <button key={endpoint} className={`point-button ${target === endpoint ? 'active' : ''}`}
        aria-pressed={target === endpoint} onClick={() => onTarget(endpoint)}>
        <span className={`point-letter ${endpoint}`}>{index === 0 ? 'A' : 'B'}</span>
        <span><strong>{endpoint === 'origen' ? 'Origen' : 'Destino'}</strong><small>{points[endpoint] ? `${points[endpoint].lat.toFixed(5)}, ${points[endpoint].lon.toFixed(5)}` : 'Toca para elegir en el mapa'}</small></span>
        <Icon name={points[endpoint] ? 'check' : 'pin'} />
      </button>)}
      <button className="icon-button swap-button" aria-label="Intercambiar origen y destino" title="Intercambiar origen y destino" disabled={!points.origen && !points.destino} onClick={onSwap}><Icon name="swap" /></button>
    </div>
    <div className="planner-aux"><button className="text-button" onClick={onExample}>Probar recorrido de ejemplo</button><button className="text-button" disabled={!points.origen && !points.destino} onClick={onReset}><Icon name="reset" />Restablecer</button></div>
    <details className="manual-entry">
      <summary>Introducir coordenadas</summary>
      <form key={JSON.stringify(points)} onSubmit={event => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        const draft: Points = { origen: { lat: Number(data.get('origen-lat')), lon: Number(data.get('origen-lon')) },
          destino: { lat: Number(data.get('destino-lat')), lon: Number(data.get('destino-lon')) } };
        const message = pointError(draft);
        setManualError(message ?? '');
        if (!message) { onPoint('origen', draft.origen!); onPoint('destino', draft.destino!); }
      }}>
        {(['origen', 'destino'] as const).map(endpoint => <fieldset key={endpoint}><legend>{endpoint === 'origen' ? 'Origen' : 'Destino'}</legend>
          <div className="coordinate-row">{(['lat', 'lon'] as const).map(axis => <label key={axis}>
            {axis === 'lat' ? 'Latitud' : 'Longitud'}
            <input aria-label={`${endpoint === 'origen' ? 'Origen' : 'Destino'}: ${axis === 'lat' ? 'latitud' : 'longitud'}`}
              name={`${endpoint}-${axis}`} defaultValue={points[endpoint]?.[axis] ?? ''} required type="number" step="any"
              min={axis === 'lat' ? -90 : -180} max={axis === 'lat' ? 90 : 180} placeholder={axis === 'lat' ? '−0.201' : '−78.504'} />
          </label>)}</div></fieldset>)}
        {manualError && <p role="alert" className="error-text">{manualError}</p>}
        <button type="submit" className="secondary full-width">Aplicar coordenadas</button>
      </form>
    </details>
    {!error && outside.length > 0 && <p role="status" className="constraint-note">Fuera del límite de la zona: {outside.join(' y ')}. El cálculo utiliza los nodos ajustados de la red.</p>}
    {error && <div className="error-box" role="alert"><strong>No pudimos calcular el recorrido</strong><p>{guidance}</p><p>{error}</p></div>}
    <button className="primary full-width compare-button" onClick={onCalculate} disabled={!points.origen || !points.destino || loading}>
      {loading ? <><span className="spinner" />Calculando recorridos…</> : <>{error ? 'Intentar nuevamente' : 'Comparar recorridos'}<Icon name="arrow" /></>}
    </button>
    <p className="constraint-note">A pie · Hasta {config.desvio_maximo_pct} % de desvío entre nodos</p>
    <p role="status" className="sr-only">{loading ? 'Calculando las tres alternativas.' : ''}</p>
  </section>;
}
