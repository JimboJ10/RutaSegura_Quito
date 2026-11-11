import { useCallback, useEffect, useRef, useState } from 'react';
import { api, errorMessage } from './api';
import { pointError } from './types';
import type { ApiConfig, Endpoint, Point, Points, Predictions, Routes } from './types';

export function useDemo() {
  const [config, setConfig] = useState<ApiConfig | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const [predictions, setPredictions] = useState<Predictions | null>(null);
  const [predictionError, setPredictionError] = useState('');
  const [predictionLoading, setPredictionLoading] = useState(false);
  const [predictionAttempt, setPredictionAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let running = false;
    let configured = false;
    async function check() {
      if (running || !navigator.onLine) return;
      running = true;
      try {
        const health = await api.health(controller.signal);
        if (health.estado !== 'ok') throw new Error('La red de rutas no está disponible.');
        if (!configured) {
          const settings = await api.config(controller.signal);
          if (controller.signal.aborted) return;
          setConfig(settings);
          configured = true;
        }
        if (!controller.signal.aborted) setError('');
      } catch (cause) {
        if (!controller.signal.aborted) setError(errorMessage(cause));
      } finally {
        running = false;
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    setLoading(true); setError('');
    void check();
    const timer = window.setInterval(check, 15000);
    window.addEventListener('online', check);
    window.addEventListener('focus', check);
    return () => {
      controller.abort(); clearInterval(timer);
      window.removeEventListener('online', check);
      window.removeEventListener('focus', check);
    };
  }, [attempt]);
  useEffect(() => {
    if (!config) return;
    const controller = new AbortController();
    setPredictionLoading(true); setPredictionError('');
    api.predictions(controller.signal).then(data => {
      if (!controller.signal.aborted) setPredictions(data);
    }).catch(error => { if (!controller.signal.aborted) setPredictionError(errorMessage(error)); })
      .finally(() => { if (!controller.signal.aborted) setPredictionLoading(false); });
    return () => controller.abort();
  }, [config, predictionAttempt]);
  return { config, error, loading, predictions, predictionError, predictionLoading,
    retry: () => setAttempt(v => v + 1), retryPredictions: () => setPredictionAttempt(v => v + 1) };
}

export function useRoutePlanner() {
  const [points, setPoints] = useState<Points>({ origen: null, destino: null });
  const [routes, setRoutes] = useState<Routes | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const pending = useRef<AbortController | null>(null);
  const sequence = useRef(0);
  const invalidate = useCallback(() => {
    sequence.current += 1; pending.current?.abort();
    setRoutes(null); setError(''); setLoading(false);
  }, []);
  useEffect(() => () => { sequence.current += 1; pending.current?.abort(); }, []);
  const setPoint = useCallback((endpoint: Endpoint, point: Point) => {
    invalidate(); setPoints(previous => ({ ...previous, [endpoint]: point }));
  }, [invalidate]);
  const reset = () => { invalidate(); setPoints({ origen: null, destino: null }); };
  const swap = () => { invalidate(); setPoints(previous => ({ origen: previous.destino, destino: previous.origen })); };
  const calculate = async () => {
    invalidate();
    const validation = pointError(points);
    if (validation) { setError(validation); return; }
    const id = sequence.current;
    const controller = new AbortController();
    pending.current = controller;
    setLoading(true);
    try {
      const result = await api.routes(points.origen!, points.destino!, controller.signal);
      if (id === sequence.current && !controller.signal.aborted) setRoutes(result);
    } catch (error) {
      if (id === sequence.current && !controller.signal.aborted) setError(errorMessage(error));
    } finally {
      if (id === sequence.current) setLoading(false);
    }
  };
  return { points, routes, loading, error, setPoint, reset, swap, calculate };
}
