import { expect, it } from 'vitest';
import L from 'leaflet';
import { historicalAnchors, visibleGroups } from '../components/HistoricalMarker';

it('elige un punto interior de una sola sección, sin unir fragmentos', () => {
  expect(historicalAnchors([[[0,0],[0,2],[1,2]],[[4,3],[5,3]]])).toEqual([[1,0],[3,4.5]]);
});
it('omite cruces vacíos, puntuales y degenerados', () => {
  expect(historicalAnchors([[],[[0,0]],[[1,1],[1,1]],[[0,0],[NaN,1],[2,2]]])).toEqual([]);
  expect(historicalAnchors(undefined)).toEqual([]);
});

it('reúne recortes invertidos, duplicados y ramales con un vértice interior compartido', () => {
  expect(historicalAnchors([[[2,0],[1,0]],[[0,0],[1,0],[1,3]],[[1,0],[2,0]]])).toEqual([[1.5,1]]);
});

it('mantiene grupos geográficos separados aunque al alejar el zoom compartan símbolo', () => {
  const anchors = historicalAnchors([[[0,0],[1,0]],[[1.00001,0],[2,0]]]);
  expect(anchors).toHaveLength(2);
  const atScale = (scale: number) => visibleGroups(anchors, ([lat, lon]) => L.point(lon * scale, lat * scale));
  expect(atScale(20).map(g => g.count)).toEqual([2]);
  expect(atScale(100).map(g => g.count)).toEqual([1,1]);
  expect(atScale(20)[0].anchor).toEqual(anchors[0]);
});
