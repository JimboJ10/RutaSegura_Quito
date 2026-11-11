import type { ReactNode } from 'react';
import { Icon } from './Icon';
import { format, ROUTE_META } from '../types';
import type { Routes, RouteId } from '../types';

export function RouteResults({ routes, selected, onSelect, onFocus, children }: {
  children: ReactNode; routes: Routes; selected: RouteId; onSelect: (id: RouteId) => void; onFocus: () => void;
}) {
  const current = routes.features.find(f => f.properties.id === selected)!.properties;
  const description = {
    corta: 'Minimiza la distancia entre los nodos de la red.',
    historica: 'Compara los recorridos por su indicador histórico de siniestros de tránsito.',
    lightgbm: 'Compara los recorridos con la estimación de siniestros de LightGBM.',
  };
  return <section className="results" aria-labelledby="results-title">
    <h2 id="results-title">Tres modalidades de comparación</h2>
    <div className="mode-picker" role="group" aria-label="Elegir modalidad">
      {routes.features.map(({ properties: r }) => {
        const meta = ROUTE_META[r.id];
        return <button type="button" className={`route-card mode-button ${selected === r.id ? 'selected' : ''}`}
          key={r.id} aria-pressed={selected === r.id} aria-label={`${meta.name}, ${format(r.distancia_km, 3)} km`}
          style={{ '--route-color': meta.color } as React.CSSProperties} onClick={() => onSelect(r.id)}>
          <span className="mode-label">{meta.short}</span>
          <strong>{format(r.distancia_km, 3)} km</strong>
          <small>{r.id === 'corta' ? 'Referencia' : `+${format(r.desvio_pct)} %`}</small>
        </button>;
      })}
    </div>
    <div className="chosen-mode"><h3>{ROUTE_META[selected].name}</h3>
      <p>{description[selected]}</p></div>
    {children}
    <div className="route-indices"><span>Índice histórico <b>{format(current.indice_historico, 4)}</b></span>
      <span>Índice LightGBM <b>{format(current.indice_lightgbm, 4)}</b></span></div>
    <p className="muted fine-print">Las modalidades pueden compartir el mismo recorrido.</p>
    <button className="secondary full-width" onClick={onFocus}><Icon name="target" />Ver recorrido seleccionado</button>
    <div className="adjustment-note">
      <strong>Ajuste a la red peatonal</strong>
      <dl><div><dt>Origen</dt><dd>{format(routes.metadata.origen_ajustado.distancia_ajuste_m, 1)} m</dd></div><div><dt>Destino</dt><dd>{format(routes.metadata.destino_ajustado.distancia_ajuste_m, 1)} m</dd></div></dl>
      <p>Las distancias excluyen el acceso desde tus puntos hasta los nodos ajustados. Los círculos pequeños en el mapa indican esos nodos.</p>
    </div>
    <p className="muted fine-print">Indicadores: concentración estimada ponderada por longitud (puntuación × km), no probabilidad de accidente. Las alternativas pueden coincidir.</p>
  </section>;
}
