import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react';
import { createPortal } from 'react-dom';
import { Marker, useMap } from 'react-leaflet';
import L from 'leaflet';
import type { MultiLineString } from 'geojson';

// Los recortes vienen por cuadrícula y pueden llegar desordenados o invertidos.
// Solo un vértice compartido conecta dos porciones de la geometría publicada.
export function historicalAnchors(lines?: MultiLineString['coordinates']): L.LatLngTuple[] {
  type Vertex = { point: L.LatLng; adjacent: Set<Vertex> };
  const vertices = new Map<string, Vertex>();
  function vertex(x: number, y: number): Vertex {
    const key = x + ',' + y;
    let result = vertices.get(key);
    if (!result) {
      result = { point: L.latLng(y, x), adjacent: new Set() };
      vertices.set(key, result);
    }
    return result;
  }
  for (const line of lines ?? []) {
    for (let i = 1; i < line.length; i++) {
      const [x, y] = line[i - 1], [u, v] = line[i];
      if (![x,y,u,v].every(Number.isFinite) || (x === u && y === v)) continue;
      const a = vertex(x,y), b = vertex(u,v);
      a.adjacent.add(b);
      b.adjacent.add(a);
    }
  }
  const anchors: L.LatLngTuple[] = [];
  const visited = new Set<Vertex>();
  for (const start of vertices.values()) {
    if (visited.has(start)) continue;
    visited.add(start);
    const stack = [start];
    let longest = 0;
    let anchor: L.LatLngTuple | undefined;
    while (stack.length) {
      const current = stack.pop()!;
      for (const next of current.adjacent) {
        if (!visited.has(next)) {
          visited.add(next);
          stack.push(next);
        }
        const a = current.point, b = next.point;
        const length = a.distanceTo(b);
        if (length > longest) {
          longest = length;
          anchor = [(a.lat + b.lat) / 2, (a.lng + b.lng) / 2];
        }
      }
    }
    if (anchor) anchors.push(anchor);
  }
  return anchors;
}

const label = 'Consultar información histórica del tramo';
const touchSize = 44;
// El triángulo ocupa 26 px más su borde visible. El botón conserva 44 px.
const symbolSize = 28;
export function visibleGroups(anchors: L.LatLngTuple[], project: (anchor: L.LatLngTuple) => L.Point) {
  const groups: { anchor: L.LatLngTuple; point: L.Point; count: number }[] = [];
  for (const anchor of anchors) {
    const point = project(anchor);
    const overlap = groups.find(g => Math.abs(point.x-g.point.x) < symbolSize && Math.abs(point.y-g.point.y) < symbolSize);
    if (overlap) overlap.count++;
    else groups.push({ anchor, point, count: 1 });
  }
  return groups;
}

function warningIcon(count: number) {
  return L.divIcon({
    className:'historical-pin', iconSize:[touchSize,touchSize], iconAnchor:[2,22],
    html:'<span aria-hidden="true">⚠︎</span>' + (count > 1 ? '<b aria-hidden="true">' + count + '</b>' : ''),
  });
}

export function HistoricalMarker({segments,expanded}: {segments?: MultiLineString['coordinates']; expanded?:boolean}) {
  const map = useMap();
  const watchZoom = useCallback((update: () => void) => {
    map.on('zoomend', update);
    return () => { map.off('zoomend', update); };
  }, [map]);
  const zoom = useSyncExternalStore(watchZoom, () => map.getZoom());
  const anchors = useMemo(() => historicalAnchors(segments), [segments]);
  const groups = useMemo(() => visibleGroups(anchors, a => map.project(a, zoom)), [anchors, map, zoom]);
  const available = anchors.length > 0;
  const announced = useRef(false);
  const markers = useRef(new Map<string,L.Marker>());
  const trigger = useRef('');
  const [opening, setOpening] = useState(0);
  const [details, setDetails] = useState(false);
  useEffect(() => {
    if (available && !announced.current) {
      announced.current = true;
      setOpening(1);
    }
  }, [available]);
  useEffect(() => {
    if (!opening || details) return;
    const timer = window.setTimeout(() => setOpening(0), 5000);
    return () => clearTimeout(timer);
  }, [opening, details]);
  const slot = document.getElementById(expanded ? 'expanded-history-slot' : 'historical-notice-slot');
  function openFrom(key: string) {
    trigger.current = key;
    setOpening(n => n+1);
  }
  if (!available) return null;
  return <>
    {groups.map(({anchor, count}, i) => {
      const key = anchor.join(',');
      const title = count > 1 ? label + ' · ' + count + ' grupos en esta vista. Acerca el mapa para separarlos.' :
        groups.length > 1 ? label + ' · grupo ' + (i + 1) : label;
      return <Marker key={key + title} position={anchor} ref={marker => {
        if (marker) markers.current.set(key, marker);
        else markers.current.delete(key);
      }}
      icon={warningIcon(count)} title={title} zIndexOffset={600} autoPanOnFocus={false}
      eventHandlers={{click:() => openFrom(key), add:e => {
        const el = e.target.getElement();
        el.setAttribute('aria-label', title);
        el.onkeydown = (event: KeyboardEvent) => {
          if (event.key === ' ' || event.key === 'Enter') {
            event.preventDefault(); event.stopPropagation(); openFrom(key);
          }
        };
      }}}/>;
    })}
    {slot && opening > 0 && createPortal(<div className={'historical-notice' + (details ? ' notice-expanded' : '')}>
      <strong className="notice-summary" role="status">Robos registrados · 2019–2022</strong>
      <button className="notice-details" aria-expanded={details} aria-controls="historical-full" onClick={() => setDetails(!details)}>{details ? 'Ver menos' : 'Ver detalles'}</button>
      <div role="status" id="historical-full"><strong>El recorrido atraviesa una de las cinco zonas con mayor densidad de registros de robos por km² entre 2019 y 2022.</strong>
      <small>No representa peligro actual ni identifica el lugar exacto de un delito</small></div>
      <button aria-label="Cerrar información histórica" onClick={() => {
        setDetails(false); setOpening(0);
        const marker = markers.current.get(trigger.current) ?? markers.current.values().next().value;
        marker?.getElement()?.focus({preventScroll:true});
      }}>×</button>
    </div>,slot)}
  </>;
}
