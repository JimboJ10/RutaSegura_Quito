import { expect, it } from 'vitest';
import { historicalAnchor } from '../components/HistoricalMarker';

it('elige un punto interior de una sola sección, sin unir fragmentos', () => {
  expect(historicalAnchor([[[0,0],[0,2],[1,2]],[[4,3],[5,3]]])).toEqual([1,0]);
});
it('omite cruces vacíos, puntuales y degenerados', () => {
  expect(historicalAnchor([[],[[0,0]],[[1,1],[1,1]]])).toBeNull();
  expect(historicalAnchor(undefined)).toBeNull();
});
