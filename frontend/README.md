# RutaSegura Quito · frontend

MVP de comparación de recorridos peatonales con React, TypeScript, Vite, Leaflet y React Leaflet. Interfaz en español, panel inferior expandible en celulares y panel lateral desde 768 px. El backend y sus datos se conservan intactos.

**Demostración retrospectiva con datos de junio de 2026. Los indicadores no representan probabilidades individuales de accidente ni garantizan la seguridad de los recorridos.**

## Requisitos e instalación

Entorno comprobado: Windows, Node 22.23.1 y npm 10.9.8. El proyecto requiere Node 22.12 o posterior compatible con Vite. Las versiones resueltas quedan en `package-lock.json`.

Desde la raíz del repositorio, en PowerShell:

```powershell
Set-Location .\frontend
npm ci
if (-not (Test-Path -LiteralPath '.env.local')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env.local'
}
npm run dev
```

No sobrescribas un `.env.local` existente. Su valor inicial es:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Abre [http://127.0.0.1:5173](http://127.0.0.1:5173). El puerto es fijo para coincidir con CORS; si está ocupado, Vite falla en vez de cambiarlo silenciosamente.

En otra terminal, desde la raíz:

```powershell
Set-Location .\backend
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

La preparación del GraphML y GeoJSON está en el [README del backend](../backend/README.md). El frontend no copia, descarga ni regenera esos archivos.

Si el lanzador `npm` de Windows apunta a una instalación global defectuosa, se puede usar la copia incluida con Node sin modificar la instalación global:

```powershell
& 'C:\Program Files\nodejs\node.exe' 'C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js' run dev
```

Aplica el mismo prefijo a `ci`, `test` o `run build` si fuera necesario. Ajusta la ruta si Node está instalado en otro lugar.

## Uso

1. El inicio consulta `/health` y `/config`; el bbox real determina la vista inicial.
2. Toca el mapa para elegir A (origen) y B (destino). Sus botones permiten cambiarlos. También puedes introducir coordenadas por teclado, intercambiarlas o restablecerlas.
3. «Probar recorrido de ejemplo» coloca los puntos conocidos; todavía no solicita rutas.
4. «Comparar recorridos» envía exclusivamente `{ origen: { lat, lon }, destino: { lat, lon } }` a `POST /rutas`.
5. Elige una de las tres tarjetas. El mapa conserva las otras alternativas atenuadas; etiquetas 01/02/03 y trazos diferentes complementan los colores.
6. «Ver recorrido seleccionado» encuadra la geometría. «Centrar zona» recupera el bbox disponible.
7. En «Capas», muestra las 25 cuadrículas y cambia entre histórico y LightGBM. La escala usa el mínimo y máximo del campo seleccionado; las unidades son conteos mensuales estimados por celda original de 1 km². Los valores no se convierten a probabilidades.
8. «Sobre los datos», siempre accesible en el pie, explica la demostración y sus límites.

La distancia de las rutas se muestra con tres decimales en km, a partir del valor enviado por la API. El acceso desde las coordenadas solicitadas hasta los nodos no está incluido. Se muestran las distancias de ajuste y los nodos ajustados como círculos; no se inventan tramos de acceso.

Las capas y rutas se entregan a Leaflet en GeoJSON con orden **longitud-latitud**. Los marcadores y bounds de Leaflet utilizan **latitud-longitud**. No se altera la geometría recibida.

## Estructura

```text
frontend/
├── .env.example
├── .gitignore
├── index.html
├── package.json
├── package-lock.json
├── tsconfig.json
├── vite.config.ts
├── vitest.integration.config.ts
├── README.md
├── VERIFICACION.md
├── public/
│   └── favicon.svg
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── api.ts
    ├── types.ts
    ├── useRutaSegura.ts
    ├── styles.css
    ├── components/
    │   ├── Icon.tsx
    │   ├── Planner.tsx
    │   ├── MapView.tsx
    │   └── RouteResults.tsx
    └── test/
        ├── fixtures.ts
        ├── api.test.ts
        ├── planner.test.tsx
        ├── App.test.tsx
        ├── MapView.test.tsx
        └── integration/
            └── backend.test.ts
```

- `api.ts`: Fetch, errores HTTP, validación básica de respuestas, timeout de 30 segundos y cancelación.
- `types.ts`: contrato tipado, formato de valores e identidades de las rutas.
- `useRutaSegura.ts`: carga de configuración/capa y estado del recorrido. Cancelación y número de solicitud evitan que respuestas antiguas reemplacen datos nuevos.
- `App.tsx`: composición, estado del panel, selección de alternativa, conexión y diálogo informativo.
- `Planner`: selección, coordenadas manuales, ejemplo, intercambio, reinicio y cálculo.
- `MapView`: OpenStreetMap, marcadores, geometrías, cuadrículas, leyendas y encuadre. ResizeObserver llama a `invalidateSize` cuando cambia el espacio del mapa.
- `RouteResults`: métricas, selección accesible y ajustes a la red.
- `Icon` y `styles.css`: iconos SVG locales y presentación Mobile First.

No se usan router, biblioteca de estado global, geocodificación ni GPS.

## Dependencias

Ejecución: React/React DOM 19.3.1, Leaflet 1.9.4 y React Leaflet 5.0.0.

Desarrollo: Vite 8.3.5, plugin React 6.2.1, TypeScript 5.9.3, tipos de React/Leaflet/GeoJSON, Vitest 5.1.0, jsdom 27.4.0 y Testing Library React 16.3.3. Se usa `npm ci` para reproducir el lock.

Las teselas de OpenStreetMap requieren internet y conservan atribución visible. No hay precarga masiva ni modo offline; se muestra un aviso y reintento ante un fallo del mapa base. Se usan fuentes de Google Fonts con alternativas del sistema si no están disponibles.

Referencias: [React Leaflet](https://react-leaflet.js.org/docs/start-installation/), [Vite](https://vite.dev/guide/), [política de teselas de OpenStreetMap](https://operations.osmfoundation.org/policies/tiles/).

## Pruebas

Desde `frontend`:

```powershell
npm run build
npm test
```

El build comprueba TypeScript y genera `dist/`. Las pruebas unitarias/de componentes usan respuestas sintéticas y no necesitan FastAPI. El mapa está sustituido en las pruebas de App; jsdom no comprueba píxeles ni el comportamiento visual de Leaflet.

Con FastAPI ejecutándose:

```powershell
npm run test:integration
```

Estas pruebas **sí consultan el backend real** mediante el mismo cliente del frontend. Verifican endpoints, 25 cuadrículas, orden de coordenadas, continuidad, indicadores, regresión ±1 metro, errores y preflight CORS. No usan fixtures en lugar de la API. Requieren `VITE_API_BASE_URL` en `.env.local`; sin backend disponible fallarán de forma explícita.

`npm run preview` sirve el build en el puerto 5173. Detén primero el servidor de desarrollo si usa ese puerto. El detalle de verificación y la lista visual pendiente están en [VERIFICACION.md](VERIFICACION.md).

## Celulares en la misma Wi-Fi

El teléfono debe utilizar la IPv4 de la **computadora**, nunca su propio localhost.

1. Identifica la IPv4 de la Wi-Fi con `ipconfig`.
2. Desde `backend`:

```powershell
$ipPc = Read-Host 'IPv4 Wi-Fi de esta computadora'
$env:RUTASEGURA_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173,http://${ipPc}:5173"
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

3. En `frontend/.env.local`, sustituye el marcador por esa IPv4:

```dotenv
VITE_API_BASE_URL=http://<IP_LOCAL_PC>:8000
```

4. Inicia Vite y abre `http://<IP_LOCAL_PC>:5173` desde el teléfono:

```powershell
npm run dev -- --host 0.0.0.0
```

Reinicia Vite tras cambiar la variable. El backend no lee `.env.local` del frontend. CORS debe autorizar el origen del frontend en 5173, no el del teléfono ni el puerto 8000. Las variables `VITE_` se incorporan al cliente: no guardes secretos en ellas.

Utiliza solo una red privada de confianza. El firewall puede bloquear Python/Node; revisa permisos limitados a la red privada y subred local, sin desactivar protecciones. No configures túneles, reenvío de puertos ni exposición pública. Al terminar, detén los procesos con Ctrl+C. No se modificaron reglas del firewall durante esta implementación.

## Límites y siguientes revisiones

- Los datos son retrospectivos de junio de 2026 y cubren únicamente la zona demo.
- Las rutas pueden coincidir cuando no existe una mejora admisible. Ninguna garantiza seguridad.
- Un fallo de API muestra el error y permite reintentar; nunca se sustituyen rutas o puntuaciones por datos ficticios.
- Una capa de predicciones no disponible no bloquea la selección de puntos ni el cálculo de rutas si el arranque ya obtuvo la configuración.
- El cliente hace validaciones básicas; el backend sigue siendo la autoridad para cobertura, ajuste máximo y conectividad.
- El diseño tiene safe areas, altura `dvh`, controles de al menos 44 px, alternativa manual por teclado, focos visibles y movimiento reducido. No equivale a una auditoría completa de accesibilidad.
- **Pendiente:** comprobar visualmente 360, 390, 768 y 1280 px, mapa, panel, teclado virtual y dispositivos Android/iPhone. El acceso al navegador fue rechazado; no se certifica ausencia de desbordamiento con pruebas jsdom.
- El contrato completo sigue en [FRONTEND_API.md](../backend/FRONTEND_API.md). No se modificó ningún archivo del backend.
