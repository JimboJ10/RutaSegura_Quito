import { useEffect, useRef, useState } from 'react';
import { Icon } from './components/Icon';
import { MapView } from './components/MapView';
import { Planner } from './components/Planner';
import { RouteResults } from './components/RouteResults';
import { useDemo, useRoutePlanner } from './useRutaSegura';
import { periodLabel } from './types';
import type { Endpoint, Point, RouteId } from './types';

const WARNING = 'Demostración retrospectiva con datos de junio de 2026. Los indicadores no representan probabilidades individuales de accidente ni garantizan la seguridad de los recorridos.';

export default function App() {
  const demo = useDemo();
  const planner = useRoutePlanner();
  const [target, setTarget] = useState<Endpoint | null>('origen');
  const [expanded, setExpanded] = useState(false);
  const [selected, setSelected] = useState<RouteId>('corta');
  const [focus, setFocus] = useState<{ kind: 'zone' | 'route'; serial: number }>({ kind: 'zone', serial: 0 });
  const [offline, setOffline] = useState(!navigator.onLine);
  const dialog = useRef<HTMLDialogElement>(null);
  const resultsStart = useRef<HTMLDivElement>(null);
  const center = (kind: 'zone' | 'route') => setFocus(previous => ({ kind, serial: previous.serial + 1 }));
  useEffect(() => {
    const online = () => setOffline(false);
    const offline = () => setOffline(true);
    window.addEventListener('online', online); window.addEventListener('offline', offline);
    return () => { window.removeEventListener('online', online); window.removeEventListener('offline', offline); };
  }, []);
  useEffect(() => {
    if (!planner.routes) return;
    setTarget(null); setExpanded(true); center('route');
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
      <a className="brand" href="./" aria-label="RutaSegura Quito, inicio"><span className="brand-symbol"><Icon name="route" /></span><span>RutaSegura<span className="brand-city">QUITO</span></span></a>
      <div className="header-right"><span className="experimental-tag">Explorador peatonal</span><span className={`connection ${demo.error || offline ? 'unavailable' : ''}`} role="status"><span className="live-dot" />{offline ? 'Sin conexión' : demo.loading ? 'Conectando…' : demo.error ? 'API no disponible' : 'Demo conectada'}</span></div>
    </header>
    {offline && <div className="offline-banner" role="alert">Sin conexión a la red. Revisa tu Wi-Fi y vuelve a intentar la operación.</div>}
    {!demo.config ? <main className="startup-state">
      <span className="large-symbol"><Icon name="route" /></span><p className="eyebrow">EXPLORA QUITO CON MÁS INFORMACIÓN</p>
      <h1>{demo.loading ? 'Preparando tu mapa…' : 'No pudimos conectar'}</h1>
      {demo.loading ? <p role="status">Cargando la zona disponible y la red peatonal.</p> : <><p role="alert">{demo.error}</p><button className="primary" onClick={demo.retry}>Intentar nuevamente<Icon name="reset" /></button></>}
    </main> : <main className={`workspace ${expanded ? 'panel-expanded' : ''}`}>
      <aside id="journey-panel" className="journey-panel" aria-label="Planificación y resultados" tabIndex={-1}>
        <button className="panel-toggle" aria-expanded={expanded} aria-controls="panel-content" onClick={() => setExpanded(v => !v)}>
          <span className="drawer-handle" /><span><strong>{planner.routes ? 'Tus tres alternativas' : 'Planea tu recorrido'}</strong><small>{planner.routes ? 'Compara distancias e indicadores' : 'Selecciona origen y destino en el mapa'}</small></span><Icon name="chevron" />
        </button>
        <div id="panel-content" className="panel-content">
          <Planner config={demo.config} points={planner.points} target={target}
            onTarget={endpoint => { setTarget(endpoint); setExpanded(false); }}
            onPoint={choosePoint} onSwap={() => { planner.swap(); setTarget(null); }}
            onReset={() => { planner.reset(); setTarget('origen'); center('zone'); }}
            onCalculate={() => { setSelected('corta'); setTarget(null); void planner.calculate(); }}
            onExample={() => {
              planner.setPoint('origen', { lat: -0.201, lon: -78.504 });
              planner.setPoint('destino', { lat: -0.184, lon: -78.486 });
              setTarget(null); center('zone');
            }} loading={planner.loading} error={planner.error} />
          {planner.routes ? <div ref={resultsStart}><p className="sr-only" role="status">Tres alternativas disponibles. Selecciona una para comparar sus indicadores.</p><RouteResults routes={planner.routes} selected={selected} onSelect={setSelected} onFocus={() => { center('route'); setExpanded(false); }} /></div> :
            <div className="empty-state"><span className="empty-icon"><Icon name="walk" /></span><strong>Una ciudad. Distintos caminos.</strong><p>Compara la ruta más corta con alternativas basadas en datos históricos y LightGBM.</p></div>}
          <p className="panel-footnote"><Icon name="info" />Ajuste máximo a la red: {demo.config.distancia_maxima_ajuste_m} m. Sin cálculo de accesos peatonales.</p>
        </div>
      </aside>
      <MapView config={demo.config} points={planner.points} target={target} onPoint={choosePoint} routes={planner.routes}
        selected={selected} onSelect={setSelected} focus={focus} onCenter={() => center('zone')}
        predictions={demo.predictions} predictionLoading={demo.predictionLoading} predictionError={demo.predictionError} onRetryPredictions={demo.retryPredictions} />
    </main>}
    <footer className="app-footer"><span><span className="demo-label">DEMO</span>Retrospectiva · {demo.config ? periodLabel(demo.config.periodo) : 'junio de 2026'}</span><button onClick={() => dialog.current?.showModal()}><Icon name="info" /><span>Sobre los datos</span></button></footer>
    <dialog ref={dialog} className="data-dialog" aria-labelledby="data-title">
      <p className="eyebrow">UNA DEMOSTRACIÓN, CON CONTEXTO</p><h2 id="data-title">Cómo leer este mapa</h2><p className="main-warning">{WARNING}</p>
      <ul>{demo.config?.advertencias.map(text => <li key={text}>{text}</li>)}</ul>
      <p>Las rutas parten y terminan en nodos ajustados. La distancia al nodo no es un itinerario de acceso. El límite del 15 % se aplica entre esos nodos.</p>
      <form method="dialog"><button className="primary full-width">Entendido, volver al mapa</button></form>
    </dialog>
  </div>;
}
