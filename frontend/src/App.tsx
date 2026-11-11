import { useEffect, useRef, useState } from 'react';
import { Icon } from './components/Icon';
import { TheftCrossings, useCrossings } from './components/TheftHistory';
import { SavedLibrary, SaveTripButton } from './components/SavedLibrary';
import { MapView } from './components/MapView';
import { HistoricalSafetyStats } from './components/HistoricalSafetyStats';
import { Planner } from './components/Planner';
import { RouteResults } from './components/RouteResults';
import { useDemo, useRoutePlanner } from './useRutaSegura';
import { useExperimentalRoute } from './useExperimentalRoute';
import { periodLabel, ROUTE_META } from './types';
import type { Endpoint, Point, RouteId } from './types';

const WARNING = 'Demostración retrospectiva con datos de junio de 2026. Los indicadores no representan probabilidades individuales de accidente ni garantizan la seguridad de los recorridos.';
const DESCRIPTION = 'Aplicación web experimental que permite comparar rutas peatonales en una zona del centro-norte de Quito utilizando información histórica de siniestros de tránsito e inteligencia artificial.';

export default function App() {
  const demo = useDemo();
  const planner = useRoutePlanner();
  const [target, setTarget] = useState<Endpoint | null>('origen');
  const [expanded, setExpanded] = useState(() => window.innerWidth >= 768);
  const [selected, setSelected] = useState<RouteId>('corta');
  const { routes, message } = useExperimentalRoute(planner.routes, planner.points);
  const history = useCrossings(routes);
  const [highlight, setHighlight] = useState(true);
  const [focus, setFocus] = useState<{ kind: 'zone' | 'route' | 'segments'; serial: number }>({ kind: 'zone', serial: 0 });
  const [library, setLibrary] = useState(false);
  const [offline, setOffline] = useState(!navigator.onLine);
  const dialog = useRef<HTMLDialogElement>(null);
  const resultsStart = useRef<HTMLDivElement>(null);
  const openInfo = () => {
    const info = dialog.current;
    if (!info) return;
    info.showModal();
    info.querySelector<HTMLElement>('#data-title')?.focus({ preventScroll: true });
    info.scrollTop = 0;
  };
  const center = (kind: 'zone' | 'route' | 'segments') => setFocus(previous => ({ kind, serial: previous.serial + 1 }));
  useEffect(() => {
    const online = () => setOffline(false);
    const offline = () => setOffline(true);
    window.addEventListener('online', online); window.addEventListener('offline', offline);
    return () => { window.removeEventListener('online', online); window.removeEventListener('offline', offline); };
  }, []);
  useEffect(() => {
    if (!planner.routes) return;
    setTarget(null); setExpanded(true); setHighlight(true); center('route');
    const frame = requestAnimationFrame(() => {
      const start = resultsStart.current;
      if (start?.parentElement) start.parentElement.scrollTop = start.offsetTop - start.parentElement.offsetTop;
    });
    return () => cancelAnimationFrame(frame);
  }, [planner.routes]);
  const choosePoint = (endpoint: Endpoint, point: Point) => {
    planner.setPoint(endpoint, point);
    setTarget(endpoint === 'origen' && !planner.points.destino ? 'destino' : null);
  };
  return <div className="app-shell">
    <a className="skip-link" href="#journey-panel">Ir al panel de recorridos</a>
    <header className="app-header">
      <a className="brand" href="./" aria-label="RutaInformada Quito, inicio"><span className="brand-symbol"><Icon name="route" /></span><span>RutaInformada<span className="brand-city">QUITO</span></span></a>
      <div className="header-right"><span className="experimental-tag">Explorador peatonal</span><span className={`connection ${demo.error || offline ? 'unavailable' : ''}`} role="status"><span className="live-dot" />{offline ? 'Sin conexión' : demo.loading ? 'Conectando…' : demo.error ? 'API no disponible' : 'Demo conectada'}</span></div>
    </header>
    {offline && <div className="offline-banner" role="alert">Sin conexión a la red. Puedes consultar tus recorridos guardados.</div>}
    {library || offline || demo.error ? <main className="library-page">
      {demo.error && !offline && <div><p role="alert">{demo.error}</p><button className="secondary" onClick={demo.retry}>Intentar nuevamente</button></div>}
      {routes && (offline || demo.error) && <div><p>Última consulta de esta sesión</p><SaveTripButton points={planner.points} routes={routes}/></div>}
      <SavedLibrary />
      {library && !offline && !demo.error && <button className="secondary" onClick={() => setLibrary(false)}>Volver al planificador</button>}
    </main> : !demo.config ? <main className="startup-state">
      <span className="large-symbol"><Icon name="route" /></span><p className="eyebrow">Decide tu camino con datos.</p>
      <h1>{demo.loading ? 'Preparando tu mapa…' : 'No pudimos conectar'}</h1>
      {demo.loading ? <p role="status">Cargando la zona disponible y la red peatonal.</p> : <><p role="alert">{demo.error}</p><button className="primary" onClick={demo.retry}>Intentar nuevamente<Icon name="reset" /></button></>}
    </main> : <main className={`workspace ${expanded ? 'panel-expanded' : ''}`}>
      <aside id="journey-panel" className="journey-panel" aria-label="Planificación y resultados" tabIndex={-1}>
        <button className="panel-toggle" aria-label={expanded ? 'Contraer panel de rutas' : 'Expandir panel de rutas'} aria-expanded={expanded} aria-controls="panel-content" onClick={() => setExpanded(v => !v)}>
          <span className="drawer-handle" /><span><strong>{planner.routes ? ROUTE_META[selected].name : 'Planea tu recorrido'}</strong><small>{planner.routes ? 'Modalidad seleccionada' : 'Selecciona origen y destino en el mapa'}</small></span><Icon name="chevron" />
        </button>
        <div id="panel-content" className="panel-content">
          <Planner config={demo.config} points={planner.points} target={target}
            onTarget={endpoint => { setTarget(endpoint); if (window.innerWidth < 768) setExpanded(false); }}
            onPoint={choosePoint} onSwap={() => { planner.swap(); setTarget(null); }}
            onReset={() => { planner.reset(); setTarget('origen'); center('zone'); }}
            onCalculate={() => { setSelected('corta'); setTarget(null); void planner.calculate(); }}
            onExample={() => {
              planner.setPoint('origen', { lat: -0.201, lon: -78.504 });
              planner.setPoint('destino', { lat: -0.184, lon: -78.486 });
              setTarget(null); center('zone');
            }} loading={planner.loading} error={planner.error} />
          {routes ? <div ref={resultsStart}><p className="sr-only" role="status">{routes.features.length} modalidades disponibles. Selecciona una para comparar sus indicadores.</p><RouteResults routes={routes} selected={selected} onSelect={setSelected} onFocus={() => { center('route'); setExpanded(false); }}>
            {message && <p role="status" className="fine-print">{message}</p>}
            <TheftCrossings selected={selected} info={history} highlight={highlight} toggle={() => setHighlight(v => !v)} onZoom={() => { center('segments'); if (window.innerWidth < 768) setExpanded(false); }} />
          </RouteResults><SaveTripButton key={routes.features.length} routes={routes} points={planner.points} /></div> :
            <div className="empty-state"><span className="empty-icon"><Icon name="walk" /></span><strong>Decide tu camino con datos.</strong><p>{DESCRIPTION}</p></div>}
          <p className="panel-footnote"><Icon name="info" />Ajuste máximo a la red: {demo.config.distancia_maxima_ajuste_m} m. Sin cálculo de accesos peatonales.</p>
        </div>
      </aside>
      <MapView config={demo.config} points={planner.points} target={target} onPoint={choosePoint} routes={routes}
        selected={selected} segments={highlight ? history?.[selected].tramos : undefined} onSelect={setSelected} focus={focus} onCenter={() => center('zone')}
        predictions={demo.predictions} predictionLoading={demo.predictionLoading} predictionError={demo.predictionError} onRetryPredictions={demo.retryPredictions} />
    </main>}
    <p className="theft-note">Datos históricos de robos a personas registrados entre 2019 y 2022. No representan condiciones actuales de seguridad.</p>
    <footer className="app-footer"><span><span className="demo-label">DEMO</span>Retrospectiva · {demo.config ? periodLabel(demo.config.periodo) : 'junio de 2026'}</span><button disabled={offline || !!demo.error} onClick={() => setLibrary(v => !v)} aria-pressed={library || offline || !!demo.error}>{library && !offline && !demo.error ? 'Planificador' : 'Guardados'}</button><button onClick={openInfo}><Icon name="info" /><span>Sobre los datos</span></button></footer>
    <dialog ref={dialog} className="data-dialog" aria-labelledby="data-title">
      <p className="eyebrow">RutaInformada Quito · Experimental</p><h2 id="data-title" tabIndex={-1}>Cómo leer este mapa</h2><p className="main-warning">{WARNING}</p>
      <p>{DESCRIPTION}</p>
      <ul>{demo.config?.advertencias.map(text => <li key={text}>{text}</li>)}</ul>
      <p>Las rutas parten y terminan en nodos ajustados. La distancia al nodo no es un itinerario de acceso. El límite del 15 % se aplica entre esos nodos.</p>
      <HistoricalSafetyStats />
      <form method="dialog"><button className="primary full-width">Entendido, volver al mapa</button></form>
    </dialog>
  </div>;
}
