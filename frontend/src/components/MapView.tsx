import type { MultiLineString } from 'geojson';
import { useEffect, useMemo, useRef, useState } from 'react';
import { CellSelector, TheftLayer, TheftLegend, useTheftGrid } from './TheftHistory';
import L from 'leaflet';
import { MapContainer, TileLayer, GeoJSON, Marker, Popup, CircleMarker, Pane, useMap, useMapEvents, ZoomControl } from 'react-leaflet';
import { Icon } from './Icon';
import { format, ROUTE_META } from '../types';
import type { ApiConfig, Endpoint, Point, Points, PredictionField, Predictions, RouteFeature, RouteId, Routes } from '../types';

import { icons } from './pointIcons';
import { HistoricalMarker } from './HistoricalMarker';
function MapBehavior({ target, onPoint, focus, config, route, segments, predictionsVisible, theftVisible }: {
  target: Endpoint | null; onPoint: (endpoint: Endpoint, point: Point) => void;
  focus: { kind: 'zone' | 'route' | 'segments'; serial: number }; config: ApiConfig; route?: RouteFeature; segments?: MultiLineString['coordinates']; predictionsVisible: boolean; theftVisible: boolean;
}) {
  const map = useMapEvents({ click(event) { if (target) onPoint(target, { lat: event.latlng.lat, lon: event.latlng.lng }); } });
  const framing = useRef<{ bounds: L.LatLngBounds; route: boolean } | null>(null);
  const reserve = useRef(90);
  reserve.current = (predictionsVisible ? 160 : 90) + (theftVisible ? 62 : 0);
  const reframe = () => {
    map.invalidateSize({ pan: false });
    if (!framing.current) return;
    const compactRoute = map.getSize().x < 768 && framing.current.route && reserve.current === 90;
    map.fitBounds(framing.current.bounds, {
      paddingTopLeft: compactRoute ? [28, 78] : [42, 110], paddingBottomRight: compactRoute ? [55, 42] : [66, reserve.current],
      maxZoom: framing.current.route ? 17 : 15, animate: false,
    });
  };
  useEffect(() => {
    let noticeHeight = document.getElementById('historical-notice-slot')?.offsetHeight;
    const observer = new ResizeObserver(() => {
      const height = document.getElementById('historical-notice-slot')?.offsetHeight;
      if (height !== noticeHeight) map.invalidateSize({pan:true,animate:false});
      else reframe();
      noticeHeight = height;
    });
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map]);
  useEffect(() => {
    if (focus.kind === 'segments' && segments?.length) {
      const geometry: MultiLineString = {type: 'MultiLineString', coordinates: segments};
      framing.current = {bounds: L.geoJSON(geometry).getBounds(), route: true};
    } else if (focus.kind !== 'zone' && route) {
      const bounds = L.geoJSON(route).getBounds();
      framing.current = { bounds, route: true };
    } else {
      const [west, south, east, north] = config.bbox;
      framing.current = { bounds: L.latLngBounds([south, west], [north, east]), route: false };
    }
    reframe();
  }, [focus, config, map, route, focus.kind === 'segments' ? segments : undefined, predictionsVisible, theftVisible]);
  return null;
}
function RouteLayer({ route, selected, selectable, onSelect }: { route: RouteFeature; selected: boolean; selectable: boolean; onSelect: (id: RouteId) => void }) {
  const layer = useRef<L.GeoJSON>(null);
  const meta = ROUTE_META[route.properties.id];
  useEffect(() => {
    if (selected) layer.current?.bringToFront();
    else layer.current?.bringToBack();
  }, [selected]);
  const options: L.PolylineOptions = {className: `route-line route-${route.properties.id}`, color: meta.color,
    smoothFactor: 0, weight: selected ? 7 : 4, opacity: selected ? 1 : 0.22, dashArray: meta.dash};
  return <GeoJSON ref={layer} data={route} pane="route-lines" style={options}
    eventHandlers={{ click(event) { if (selectable) { L.DomEvent.stopPropagation(event.originalEvent); onSelect(route.properties.id); } } }} />;
}
function MapAccessibility() {
  const map = useMap();
  useEffect(() => {
    map.getContainer().setAttribute('role', 'region');
    map.getContainer().setAttribute('aria-label', 'Mapa de Quito. Usa las flechas para desplazar y los controles para acercar. También puedes introducir coordenadas en el panel.');
  }, [map]);
  return null;
}
export function MapView({ config, points, target, onPoint, routes, selected, segments, onSelect, focus, onCenter, predictions, predictionLoading, predictionError, onRetryPredictions }: {
  segments?: MultiLineString['coordinates'];
  config: ApiConfig; points: Points; target: Endpoint | null; onPoint: (endpoint: Endpoint, point: Point) => void;
  routes: Routes | null; selected: RouteId; onSelect: (id: RouteId) => void;
  focus: { kind: 'zone' | 'route' | 'segments'; serial: number }; onCenter: () => void;
  predictions: Predictions | null; predictionLoading: boolean; predictionError: string; onRetryPredictions: () => void;
}) {
  const [showThefts, setShowThefts] = useState(false);
  const theft = useTheftGrid(showThefts);
  const [visible, setVisible] = useState(false);
  const [layersOpen, setLayersOpen] = useState(false);
  const [field, setField] = useState<PredictionField>('pred_lightgbm_v2');
  const [tileError, setTileError] = useState(false);
  const [tileAttempt, setTileAttempt] = useState(0);
  const [west, south, east, north] = config.bbox;
  const zona = config.zona_demo === 'Zona de demostración de Quito' ? 'Zona demo · Quito' : config.zona_demo;
  const range = useMemo(() => {
    const values = predictions?.features.map(f => f.properties[field]) ?? [0];
    return { min: Math.min(...values), max: Math.max(...values) };
  }, [predictions, field]);
  const segmentGeometry: MultiLineString | undefined = segments?.length ? {type:'MultiLineString', coordinates:segments} : undefined;
  const outline: L.PolylineOptions = {smoothFactor:0, color:'#a63845', weight:11, opacity:.88, lineCap:'butt'};
  const selectedRoute = routes?.features.find(f => f.properties.id === selected);
  return <section className={`map-region ${target ? 'picking' : ''}`} aria-label="Mapa y capas">
    <MapContainer bounds={[[south, west], [north, east]]} zoomControl={false} className="map-canvas" minZoom={11} maxZoom={19}>
      <TileLayer key={tileAttempt} url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> colaboradores'
        eventHandlers={{ tileerror: () => setTileError(true) }} />
      <ZoomControl position="bottomright" zoomInTitle="Acercar mapa" zoomOutTitle="Alejar mapa" />
      <MapBehavior config={config} target={target} onPoint={onPoint} focus={focus} route={selectedRoute} segments={segments} predictionsVisible={visible} theftVisible={showThefts && !!theft.grid} />
      <Pane name="prediction-grid" style={{ zIndex: 350 }}>
      {visible && predictions && <GeoJSON key={field} data={predictions} pane="prediction-grid" interactive={false} style={feature => {
        const value = feature?.properties[field] ?? range.min;
        const proportion = range.max > range.min ? (value - range.min) / (range.max - range.min) : 0.5;
        return { color: '#94500f', weight: 1, fillColor: '#cf7a27', fillOpacity: 0.12 + proportion * 0.5 };
      }} />}
      </Pane>
      {showThefts && theft.grid && <TheftLayer grid={theft.grid} picking={target !== null} />}
      <Pane name="historical-segments" style={{ zIndex: 415, pointerEvents: 'none' }}>
        {segmentGeometry && <GeoJSON key={selected + JSON.stringify(points)} interactive={false} pane="historical-segments"
          data={segmentGeometry} style={outline} />}
      </Pane>
      <Pane name="route-lines" style={{ zIndex: 420 }}>
      {routes?.features.map(route => <RouteLayer key={route.properties.id + JSON.stringify(points)} route={route} selected={selected === route.properties.id} selectable={target === null} onSelect={onSelect} />)}
      </Pane>
      {(['origen', 'destino'] as const).map(endpoint => points[endpoint] && <Marker key={endpoint} position={[points[endpoint].lat, points[endpoint].lon]} icon={icons[endpoint]} title={endpoint === 'origen' ? 'A · Origen solicitado' : 'B · Destino solicitado'}>
        <Popup>{endpoint === 'origen' ? 'Origen' : 'Destino'} solicitado<br />{points[endpoint].lat.toFixed(5)}, {points[endpoint].lon.toFixed(5)}</Popup>
      </Marker>)}
      {routes && (['origen_ajustado', 'destino_ajustado'] as const).map(key => <CircleMarker key={key} center={[routes.metadata[key].lat, routes.metadata[key].lon]} radius={5} pathOptions={{ color: '#173d34', fillColor: 'white', fillOpacity: 1, weight: 2 }}>
        <Popup>Nodo ajustado: {format(routes.metadata[key].distancia_ajuste_m, 1)} m desde el {key === 'origen_ajustado' ? 'origen' : 'destino'}.</Popup>
      </CircleMarker>)}
      <MapAccessibility />
      {selectedRoute && <HistoricalMarker key={selected + JSON.stringify(points)} segments={segments}/>}
    </MapContainer>
    <button className="map-center" onClick={onCenter}><Icon name="target" /><span>Centrar zona</span></button>
    <div className="map-topbar">{tileError && segmentGeometry ?
      <button className="layer-button" title="No se pudo cargar parte del mapa base" onClick={() => { setTileError(false); setTileAttempt(v => v+1); }}>Reintentar mapa base</button> :
      <span className="map-place"><span className="live-dot" />{zona}</span>}<button className="layer-button" aria-expanded={layersOpen} aria-controls="layer-settings" onClick={() => setLayersOpen(v => !v)}><Icon name="layers" />Capas</button></div>
    {layersOpen && <div id="layer-settings" className="layer-settings">
      <div className="layer-heading"><strong>Indicadores por cuadrícula</strong><button className="text-button" onClick={() => setLayersOpen(false)} aria-label="Cerrar opciones de capas">Cerrar</button></div>
      {predictionLoading ? <p role="status">Cargando cuadrículas…</p> : predictionError ? <div role="alert"><p>{predictionError}</p><button className="secondary" onClick={onRetryPredictions}>Reintentar capa</button></div> : <>
        <label className="switch-label"><input type="checkbox" checked={visible} onChange={event => setVisible(event.target.checked)} disabled={!predictions} /><span>Mostrar {predictions?.features.length ?? 0} cuadrículas</span></label>
        <label className="field-label" htmlFor="prediction-field">Indicador</label><select id="prediction-field" value={field} onChange={event => setField(event.target.value as PredictionField)}>
          <option value="pred_lightgbm_v2">LightGBM</option><option value="pred_historico">Histórico</option>
        </select>
        <p>Conteos mensuales estimados por celda de 1 km². El recorte visual mantiene el conteo original.</p>
      </>}
      <strong className="advanced-label">Exploración avanzada</strong>
      <label className="switch-label"><input type="checkbox" checked={showThefts} onChange={e => setShowThefts(e.target.checked)} />
        <span>Mostrar robos históricos (2019–2022)</span></label>
      {showThefts && (theft.grid ? <CellSelector grid={theft.grid} /> : <p role="status">{theft.error || 'Cargando robos históricos…'}</p>)}
    </div>}
    <div className="map-bottom">
      {tileError && !segmentGeometry && <div className="tile-error" role="status">No se pudo cargar parte del mapa base. <button onClick={() => { setTileError(false); setTileAttempt(v => v + 1); }}>Reintentar mapa</button></div>}
      {showThefts && theft.grid && <TheftLegend grid={theft.grid} />}
      {visible && predictions && <div className="prediction-legend"><strong>{field === 'pred_historico' ? 'Histórico' : 'LightGBM'} · siniestros estimados / mes</strong><div className="legend-gradient" /><div className="legend-range"><span>{format(range.min)}</span><span>{format(range.max)}</span></div><small>Por celda original de 1 km² · No es probabilidad</small></div>}
      {routes && <div className="route-legend" aria-label="Leyenda de rutas"><span><i style={{borderColor: ROUTE_META[selected].color}} />{ROUTE_META[selected].short}</span>
        {!!segments?.length && <span><i style={{borderColor:'#a63845'}} />Zona histórica · 2019–2022</span>}</div>}
      {target && <p className="map-hint" role="status"><span className={`point-letter ${target}`}>{target === 'origen' ? 'A' : 'B'}</span>Toca el mapa para elegir {target === 'origen' ? 'el origen' : 'el destino'}</p>}
    </div>
  </section>;
}
