import { Icon } from './Icon';
import { format, ROUTE_META } from '../types';
import type { Routes, RouteId } from '../types';

export function RouteResults({ routes, selected, onSelect, onFocus }: {
  routes: Routes; selected: RouteId; onSelect: (id: RouteId) => void; onFocus: () => void;
}) {
  return <section className="results" aria-labelledby="results-title">
    <div className="section-heading"><div><p className="eyebrow">COMPARA Y ELIGE</p><h2 id="results-title">Tres modalidades de comparación</h2></div><span className="count-badge">3</span></div>
    <p className="muted fine-print">Las modalidades pueden compartir el mismo recorrido.</p>
    <div className="route-options" aria-label="Alternativas de recorrido">
      {routes.features.map(({ properties: route }) => {
        const meta = ROUTE_META[route.id];
        return <button type="button" className={`route-card ${selected === route.id ? 'selected' : ''}`} key={route.id}
          aria-pressed={selected === route.id} onClick={() => onSelect(route.id)} style={{ '--route-color': meta.color } as React.CSSProperties}>
          <span className="route-card-heading"><span className="route-symbol">{meta.symbol}</span><strong>{meta.name}</strong><span className="selection-mark">{selected === route.id && <Icon name="check" />}</span></span>
          <span className="route-distance">{format(route.distancia_km, 3)} <small>km</small><span className="detour">{route.desvio_pct === 0 ? 'Referencia' : `+${format(route.desvio_pct, 2)} % de desvío`}</span></span>
          <span className="route-indices"><span>Ind. histórico <b>{format(route.indice_historico, 4)}</b></span><span>Ind. LightGBM <b>{format(route.indice_lightgbm, 4)}</b></span></span>
        </button>;
      })}
    </div>
    <button className="secondary full-width" onClick={onFocus}><Icon name="target" />Ver recorrido seleccionado</button>
    <div className="adjustment-note">
      <strong>Ajuste a la red peatonal</strong>
      <dl><div><dt>Origen</dt><dd>{format(routes.metadata.origen_ajustado.distancia_ajuste_m, 1)} m</dd></div><div><dt>Destino</dt><dd>{format(routes.metadata.destino_ajustado.distancia_ajuste_m, 1)} m</dd></div></dl>
      <p>Las distancias excluyen el acceso desde tus puntos hasta los nodos ajustados. Los círculos pequeños en el mapa indican esos nodos.</p>
    </div>
    <p className="muted fine-print">Indicadores: concentración estimada ponderada por longitud (puntuación × km), no probabilidad de accidente. Las alternativas pueden coincidir.</p>
  </section>;
}
