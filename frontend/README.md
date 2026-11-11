# RutaInformada Quito · frontend

**Decide tu camino con datos.**

Aplicación web experimental que permite comparar rutas peatonales en una zona del centro-norte de Quito utilizando información histórica de siniestros de tránsito e inteligencia artificial.

MVP de comparación de recorridos peatonales con React, TypeScript, Vite, Leaflet y React Leaflet. Interfaz en español, panel inferior expandible en celulares y panel lateral contraíble desde 768 px. La identidad pública también se refleja en `/health`, `/config` y Swagger; el contrato, los datos y el algoritmo se conservan.

Para conectar el frontend a la demo peatonal filtrada sin modificar `.env.local`, consulta el [ensayo aislado de integración](../backend/INTEGRACION_DEMO_FILTRADA.md). Usa `main:app` en `127.0.0.1:8802` y el servidor de pruebas Vite en `127.0.0.1:5185`; el proxy `/api` mantiene las solicitudes locales. El panel presenta tres modalidades, que pueden compartir el mismo recorrido.

**Demostración retrospectiva con datos de junio de 2026. Los indicadores no representan probabilidades individuales de accidente ni garantizan la seguridad de los recorridos.**

El nombre público es **RutaInformada Quito**. Se conservan los identificadores técnicos `RutaSegura_Quito`, `rutasegura-quito`, `useRutaSegura.ts` y `RUTASEGURA_CORS_ORIGINS` para mantener compatibilidad. Las capturas y el informe de la auditoría anterior documentan la identidad usada entonces; la verificación del cambio está en [IDENTIDAD.md](IDENTIDAD.md).

El backend inicia ahora con la **demo filtrada predeterminada**. No es necesario establecer variables de cobertura/red. Consulta [MVP_FILTRADO.md](../backend/MVP_FILTRADO.md) para obtener los dos datos obligatorios, verificar su integridad y ejecutar ambos servicios. Las capturas y cifras anteriores siguen siendo evidencia histórica; no se han vuelto a ejecutar por este cambio de selección.

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
7. En «Capas», muestra las cuadrículas de la zona activa y cambia entre histórico y LightGBM. La demo tiene 25 celdas y el ensayo ampliado tiene 99. La escala usa el mínimo y máximo del campo seleccionado. Las unidades son conteos mensuales estimados por celda original de 1 km².
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
├── playwright.config.ts
├── README.md
├── VERIFICACION.md
├── IDENTIDAD.md
├── e2e/
│   ├── audit-helpers.mjs
│   ├── identity.spec.ts
│   └── responsive.spec.ts
├── scripts/
│   ├── run-playwright.mjs
│   └── audit-visual.mjs
├── evidencias/auditoria-responsive/
│   ├── INFORME.md
│   ├── index.html
│   ├── pruebas-playwright.json
│   ├── antes/
│   └── despues/
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
- `MapView`: OpenStreetMap, marcadores, geometrías, cuadrículas, leyendas y encuadre. ResizeObserver actualiza el tamaño y conserva el encuadre al cambiar el espacio del mapa. Las cuadrículas se dibujan debajo de las rutas en un pane independiente.
- `RouteResults`: métricas, selección accesible y ajustes a la red.
- `Icon` y `styles.css`: iconos SVG locales y presentación Mobile First.

No se usan router, biblioteca de estado global, geocodificación ni GPS.

## Dependencias

Ejecución: React/React DOM 19.3.1, Leaflet 1.9.4 y React Leaflet 5.0.0.

Desarrollo: Vite 8.3.5, plugin React 6.2.1, TypeScript 5.9.3, tipos de React/Leaflet/GeoJSON, Vitest 5.1.0, jsdom 27.4.0, Testing Library React 16.3.3 y Playwright Test 1.64.1. Se usa `npm ci` para reproducir el lock.

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

### Navegador real y capturas automáticas

Con FastAPI en `127.0.0.1:8000` y Vite en `127.0.0.1:5173`, desde `frontend`:

```powershell
npm run browser:install
npm run test:e2e
npm run audit:visual
```

La instalación descarga Chromium en `.playwright-browsers/`, excluido de Git. Se puede omitir si ya está instalado; `PLAYWRIGHT_BROWSERS_PATH` permite usar otra ubicación existente. Las pruebas necesitan acceso a las teselas de OpenStreetMap y a la API local. No abren puertos, no arrancan servidores ni modifican el backend.

La suite Playwright del MVP ejecuta seis escenarios en siete tamaños, 42 pruebas en total. Comprueba selección de puntos, respuestas reales, resaltado de alternativas, capas, panel, desbordamiento, controles, redimensionado, advertencias, carga, errores, recuperación, identidad y cobertura. Los tamaños son **360×800, 390×844, 430×932, 768×1024, 1024×768, 1280×800 y 1920×1080**. Las distancias y el error de cobertura HTTP 422 proceden de FastAPI real. Con el backend ampliado, ejecuta el escenario específico mediante `npm run test:e2e -- e2e/cobertura.spec.ts`. Para apuntar Playwright a otro servidor local de pruebas, utiliza `PLAYWRIGHT_TEST_BASE_URL`. [Modos y resultados](../backend/COBERTURAS.md)

`npm run audit:visual` guarda 49 PNG y mediciones DOM en `evidencias/auditoria-responsive/despues/`, esperando las fuentes y el fundido de las teselas. **Sobrescribe esa carpeta de evidencias** al repetirlo. La línea base `antes/` corresponde al código previo a las correcciones y debe conservarse. Las capturas requieren inspección visual; el script no interpreta su contenido.

Si solo cambia el medidor de pruebas y la aplicación sigue igual, `npm run audit:visual -- --solo-mediciones` actualiza el JSON recorriendo los mismos estados sin volver a generar los PNG.

Abre la [galería antes/después](evidencias/auditoria-responsive/index.html) como archivo local. El [informe visual](evidencias/auditoria-responsive/INFORME.md) registra defectos y límites, y [VERIFICACION.md](VERIFICACION.md) resume aquella auditoría. El reporte predeterminado de Playwright queda en `evidencias/auditoria-responsive/pruebas-playwright.json`; las trazas de fallos quedan en `test-results/`, excluido de Git. La verificación de identidad guarda sus capturas y reportes en `evidencias/identidad-publica/`, según [IDENTIDAD.md](IDENTIDAD.md).

`npm run preview` sirve el build en el puerto 5173. Detén primero el servidor de desarrollo si usa ese puerto.

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
- Auditoría visual completada en Chromium en los siete tamaños indicados, con capturas inspeccionadas y sin desbordamiento horizontal en los estados revisados. Es emulación móvil, no una prueba en teléfonos físicos. Quedan pendientes Safari/WebKit, teclado virtual, barras dinámicas, áreas seguras y gestos en Android/iPhone reales.
- El contrato completo sigue en [FRONTEND_API.md](../backend/FRONTEND_API.md). No se modificó ningún archivo del backend.

## Robos históricos en el mapa

En **Capas**, activa **Mostrar robos históricos (2019–2022)**. El color compara registros por km² en el periodo completo. Entre celdas comparables, el generador utiliza la mediana y el percentil 75 para distinguir los tres niveles de concentración. El selector «Consultar cuadrícula» permite leer los datos mientras se eligen puntos. Una vez elegidos los puntos, también se puede pulsar un polígono. Las celdas con 1–4 registros conservan el rango publicado y la densidad suprimida.

Al calcular un recorrido, el panel consulta qué tramos pasan por el interior de cuadrículas de mayor concentración y señala las compartidas entre modalidades. La selección de rutas sigue basada en siniestros de tránsito. Los cruces se consultan aunque la capa visual esté apagada.

FastAPI lee el GeoJSON agregado directamente desde `resultados/delincuencia_exploratoria/robos_historicos_2019_2022_cuadriculas.geojson` cuando se solicita `GET /robos-historicos` o `POST /robos-historicos/cruces`. Con el archivo ausente, ambos endpoints responden 503 y la planificación de rutas sigue disponible. El uso es local mientras se verifican los permisos de redistribución. Mantener el GeoJSON, su auditoría y las capturas que los muestren fuera de Git, del directorio público y del paquete de entrega.

## PWA y recorridos guardados

Para preparar la aplicación en esta computadora, inicia FastAPI en el puerto 8000 como en la demo habitual. En otra consola, desde `frontend`:

```powershell
$env:VITE_API_BASE_URL = '/api'
npm.cmd run build
npm.cmd run preview
```

Abre `http://localhost:4173`. La vista previa sirve la compilación de producción y dirige las solicitudes de `/api` a FastAPI en esta computadora. En **Guardados**, espera el mensaje **Aplicación lista para abrir sin conexión**. Puedes instalarla desde el menú de un navegador compatible. El servidor de desarrollo de Vite sigue dedicado a la edición del frontend.

1. Calcula el recorrido con FastAPI. En los resultados, pulsa **Guardar recorrido** y espera la confirmación. Cada copia incluye las tres modalidades, los puntos solicitados y ajustados, sus geometrías, distancias, indicadores y periodo.
2. Abre **Guardados**, elige una copia y pulsa una modalidad para consultar su trazado. La fecha de guardado y el periodo de referencia se muestran por separado. El visor utiliza Leaflet sobre un fondo local. **Eliminar** quita esa copia del dispositivo.
3. Tras la primera carga completa puedes cerrar y reabrir el mismo origen, también desde la aplicación instalada. Con la red desconectada o FastAPI inaccesible, la pantalla ofrece la biblioteca local. El cálculo nuevo, las predicciones y la capa histórica necesitan el backend. Las calles del mapa base en el planificador utilizan teselas de OpenStreetMap.

El indicador de red utiliza el estado que comunica el navegador. La disponibilidad de FastAPI se comprueba con `/health` al inicio, al recuperar red, al volver a la ventana y cada 15 segundos. La conexión a una Wi-Fi por sí sola no confirma acceso a internet. Al volver FastAPI, se puede calcular de nuevo. Si la base local está bloqueada o llena, se muestra el error del guardado. Se confirma una escritura al completar su transacción.

El service worker de producción guarda una lista cerrada con HTML, JavaScript, CSS, manifest e iconos propios. Una nueva compilación tiene su propia revisión y se activa al cerrar las ventanas de la versión anterior. La aplicación conserva las copias voluntarias en IndexedDB, con versión de base y de registro. Teselas, respuestas de FastAPI y datos de robos quedan fuera de la precaché. Las mediciones aproximadas son **0,48 MB** de interfaz y **21 kB** de contenido para la copia del piloto. El espacio físico depende del navegador y de la longitud de las geometrías. El almacenamiento pertenece al perfil y al origen: borrar datos del sitio, cambiar el origen o la expulsión por el navegador puede hacer que las copias dejen de estar disponibles.

### Ensayo en un teléfono

Usa una red privada, la misma URL HTTPS para cargar, guardar y reabrir, y un certificado válido para el nombre o la IP que abrirá el teléfono. El dispositivo debe confiar en la cadena del certificado. Con el certificado y su clave en formato PEM fuera del repositorio y del directorio público, inicia FastAPI en el puerto local 8000. En la consola del frontend:

```powershell
$env:VITE_API_BASE_URL = '/api'
npm.cmd run build
$env:PWA_TLS_CERT = Read-Host 'Ruta del certificado PEM válido para la IP o nombre de la computadora'
$env:PWA_TLS_KEY = Read-Host 'Ruta de la clave PEM'
npm.cmd run preview -- --host 0.0.0.0
```

Abre `https://<IP-o-nombre-del-certificado>:4173`. Si usas un nombre DNS personalizado, autorízalo en Vite mediante `__VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS` antes de iniciar la vista previa. El teléfono accede a la API por el mismo origen HTTPS. Una IP de la LAN servida por HTTP no habilita los service workers. Comprueba **Guardados**, instala desde el navegador, guarda el piloto, activa el modo avión y vuelve a abrir desde el icono. Reconecta y comprueba el cálculo en línea. La emulación de Chromium no sustituye este ensayo en Android o iPhone.

### Comprobación automatizada de la PWA

Desde `frontend`, con el Chromium completo del proyecto, las dependencias y los datos locales del MVP:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = (Resolve-Path .playwright-browsers).Path
node scripts/test-pwa.mjs
```

La prueba usa un perfil temporal y los puertos locales 4193 y 8893. Inicia y detiene sus propios servidores de vista previa y FastAPI. Verifica instalación, persistencia entre sesiones de navegador, cuota, consulta sin servidores, recuperación del piloto, lista de archivos precargados y eliminación. Los archivos de prueba quedan en `test-results/pwa`, excluido de Git.
