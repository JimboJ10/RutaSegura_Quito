import L from 'leaflet';

export const icons = {
  origen: L.divIcon({ className: 'point-marker', html: '<span class="marker-pin origen"><span>A</span></span>', iconSize: [44, 48], iconAnchor: [22, 46] }),
  destino: L.divIcon({ className: 'point-marker', html: '<span class="marker-pin destino"><span>B</span></span>', iconSize: [44, 48], iconAnchor: [22, 46] }),
};
