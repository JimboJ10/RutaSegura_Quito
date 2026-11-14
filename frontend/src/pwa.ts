export async function prepareShell(): Promise<string> {
  if (!import.meta.env.PROD) return 'La apertura sin conexión se habilita en la versión de producción.';
  if (!window.isSecureContext || !('serviceWorker' in navigator))
    return 'La apertura sin conexión requiere un navegador compatible y una conexión segura.';
  try {
    const registration = await navigator.serviceWorker.register('/sw.js', {updateViaCache: 'none'});
    if (!registration.active && registration.installing) {
      const worker = registration.installing;
      await new Promise<void>((resolve, reject) => {
        function changed() {
          if (worker.state === 'activated' || worker.state === 'redundant') {
            worker.removeEventListener('statechange', changed);
            if (worker.state === 'activated') resolve(); else reject(new Error('Precarga incompleta'));
          }
        }
        worker.addEventListener('statechange', changed);
        changed();
      });
    }
    await navigator.serviceWorker.ready;
    return 'Aplicación lista para abrir sin conexión.';
  } catch {
    return 'La interfaz no se pudo preparar para abrir sin conexión. Reabre la aplicación con conexión.';
  }
}
export const shellStatus = prepareShell();
