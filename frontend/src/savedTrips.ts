import { validRoutes } from './api';
import { pointError } from './types';
import type { Point, Routes } from './types';

export type SavedTrip = {
  version: 1; id: string; savedAt: string;
  points: { origen: Point; destino: Point }; routes: Routes;
};
export function isSavedTrip(value: unknown): value is SavedTrip {
  const row = value as SavedTrip | null;
  return !!row && row.version === 1 && typeof row.id === 'string' && !!row.id &&
    typeof row.savedAt === 'string' && Number.isFinite(Date.parse(row.savedAt)) &&
    !!row.points && !pointError(row.points) && validRoutes(row.routes);
}

async function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const op = indexedDB.open('rutainformada-recorridos', 1);
    let blocked = false;
    op.onupgradeneeded = () => op.result.createObjectStore('recorridos', {keyPath: 'id'});
    op.onblocked = () => { blocked = true; reject(new Error('Cierra las otras pestañas de la aplicación y vuelve a intentar.')); };
    op.onerror = () => reject(op.error);
    op.onsuccess = () => {
      const db = op.result;
      db.onversionchange = () => db.close();
      if (blocked) db.close(); else resolve(db);
    };
  });
}

async function withStore<T>(mode: IDBTransactionMode, action: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await openDB();
  try {
    return await new Promise<T>((resolve, reject) => {
      const tx = db.transaction('recorridos', mode);
      const request = action(tx.objectStore('recorridos'));
      tx.oncomplete = () => resolve(request.result);
      tx.onabort = () => reject(tx.error || request.error || new Error('Operación cancelada.'));
    });
  } finally { db.close(); }
}
export async function listSaved() {
  const rows: unknown[] = await withStore('readonly', s => s.getAll());
  const trips = rows.filter(isSavedTrip).sort((a,b) => b.savedAt.localeCompare(a.savedAt));
  return { trips, invalid: rows.length - trips.length };
}
export async function saveTrip(row: SavedTrip) {
  if (!isSavedTrip(row)) throw new Error('El recorrido no tiene el formato esperado.');
  await withStore('readwrite', s => s.put(row));
}
export async function deleteTrip(id: string) {
  await withStore('readwrite', s => s.delete(id));
}
export function storageMessage(error: unknown) {
  if (error instanceof DOMException && error.name === 'QuotaExceededError')
    return 'Almacenamiento lleno. Elimina un recorrido guardado o libera espacio y vuelve a intentar.';
  return 'No se pudo acceder a los recorridos guardados. Revisa el almacenamiento del navegador y vuelve a intentar.';
}
