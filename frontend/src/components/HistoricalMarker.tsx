import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Marker } from 'react-leaflet';
import L from 'leaflet';
import type { MultiLineString } from 'geojson';

// Un solo símbolo, en el punto medio de la sección recta más larga del recorte.
export function historicalAnchor(lines?: MultiLineString['coordinates']): L.LatLngTuple | null {
  let longest = 0;
  let anchor: L.LatLngTuple | null = null;
  for (const line of lines ?? []) {
    for (let i = 1; i < line.length; i++) {
      const [x, y] = line[i - 1], [u, v] = line[i];
      if (![x,y,u,v].every(Number.isFinite)) continue;
      const length = L.latLng(y,x).distanceTo([v,u]);
      if (length > longest) {
        longest = length;
        anchor = [(y+v)/2,(x+u)/2];
      }
    }
  }
  return anchor;
}

const label = 'Consultar información histórica del tramo';
const icon = L.divIcon({
  className:'historical-pin', iconSize:[44,44], iconAnchor:[2,22],
  html:'<span aria-hidden="true">⚠︎</span>',
});

export function HistoricalMarker({segments}: {segments?: MultiLineString['coordinates']}) {
  const anchor = historicalAnchor(segments);
  const available = !!anchor;
  const announced = useRef(false);
  const marker = useRef<L.Marker>(null);
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
  const slot = document.getElementById('historical-notice-slot');
  if (!anchor) return null;
  return <>
    <Marker position={anchor} ref={marker} icon={icon} title={label} zIndexOffset={600} autoPanOnFocus={false}
      eventHandlers={{click:() => setOpening(n => n+1), add:e => {
        const el = e.target.getElement();
        el.setAttribute('aria-label',label);
        el.onkeydown = (event: KeyboardEvent) => {
          if (event.key === ' ' || event.key === 'Enter') {
            event.preventDefault(); event.stopPropagation(); setOpening(n => n+1);
          }
        };
      }}}/>
    {slot && opening > 0 && createPortal(<div className={'historical-notice' + (details ? ' notice-expanded' : '')}>
      <strong className="notice-summary" role="status">Zona con más registros de robos · 2019–2022</strong>
      <button className="notice-details" aria-expanded={details} aria-controls="historical-full" onClick={() => setDetails(!details)}>{details ? 'Ver menos' : 'Ver detalles'}</button>
      <div role="status" id="historical-full"><strong>Información histórica: este recorrido atraviesa una zona con mayor concentración de robos registrados entre 2019 y 2022.</strong>
      <small>No representa peligro actual ni identifica el lugar exacto de un delito</small></div>
      <button aria-label="Cerrar información histórica" onClick={() => {
        setDetails(false); setOpening(0); marker.current?.getElement()?.focus({preventScroll:true});
      }}>×</button>
    </div>,slot)}
  </>;
}
