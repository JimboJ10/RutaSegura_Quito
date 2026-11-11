import { useEffect, useState } from 'react';
import { api } from './api';
import { ROUTE_META } from './types';
import type { Points, Routes } from './types';

export function useExperimentalRoute(base: Routes | null, points: Points) {
  const [result, setResult] = useState<{ base: Routes; routes: Routes; message: string } | null>(null);
  useEffect(() => {
    if (!base || !points.origen || !points.destino) return;
    const controller = new AbortController();
    const finish = (routes: Routes, message = '') => {
      if (!controller.signal.aborted) setResult({base, routes, message});
    };
    api.alternative(points.origen, points.destino, controller.signal).then(data => {
      if (data.estado === 'disponible') finish({...base, features: [...base.features, data.feature]});
      else if (data.estado === 'coincidente')
        finish(base, 'La modalidad «' + ROUTE_META[data.modalidad].name + '» ya cumple el criterio experimental de robos históricos.');
      else finish(base, 'Ninguna alternativa evaluada cumple los criterios de mejora histórica y desvío.');
    }).catch(() => finish(base, 'Comparación experimental de robos históricos no disponible.'));
    return () => controller.abort();
  }, [base, points]);
  return result && result.base === base ? result : {routes: base, message: 'Evaluando la alternativa de robos históricos…'};
}
