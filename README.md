# RutaInformada Quito

**English** · [Español](README.es.md)

RutaInformada Quito is a STEMergent Hacks 2026 demo for comparing walking routes within a 19.13 km² pilot area in north-central Quito, Ecuador. The example trip offers four ways to compare the journey: shortest distance, historical traffic crash concentration, a LightGBM estimate of traffic crashes, and historical concentration of reported robberies against people (experimental). To reproduce all four from GitHub, use this revision of `main` and generate the optional historical layer locally. The tag `hackathon-final-2026-11-14` preserves the previous startup procedure.

## Architecture and data

The React and TypeScript frontend is built with Vite. Leaflet draws routes returned by FastAPI. The Python backend uses OSMnx and NetworkX with a pedestrian-access-filtered street graph derived from © OpenStreetMap contributors. LightGBM supplies precomputed, retrospective traffic crash estimates for June 2026. The API serves the three base routes through `POST /rutas` and evaluates the optional robbery comparison separately through `POST /robos-historicos/alternativa`. These indicators describe historical concentrations. They cannot establish an individual's likelihood of a crash or guarantee a safe journey.

## Set up on Windows

Start in a new directory with Git, PowerShell, 64-bit Python 3.14 and Node.js 22.12 or later installed.

```powershell
git clone https://github.com/JimboJ10/RutaSegura_Quito.git
cd RutaSegura_Quito
Expand-Archive -LiteralPath .\entregas\demo-peatonal-v1-2026-11-04.zip -DestinationPath . -Force
py -3.14 -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-lock.txt
npm.cmd --prefix frontend ci
.\backend\.venv\Scripts\python.exe scripts\distribuir_mvp.py verificar
```

If your environment and data have already been validated, skip to startup. The ZIP contains the filtered pedestrian graph and the 25 prediction grid cells for June 2026. The verifier checks file sizes and SHA-256 hashes against the manifest. The API uses precomputed estimates and indicators, so running the demo requires no model training or additional model loading.

<a id="generar-la-capa-histórica-en-el-equipo-del-juez"></a>

## Generate the historical layer on your computer

After extracting the ZIP and installing dependencies, review the source terms below. For a local evaluation consistent with those terms, run these commands from the repository root.

```powershell
.\backend\.venv\Scripts\python.exe scripts\generar_capa_robos_historicos_quito.py
.\backend\.venv\Scripts\python.exe scripts\generar_capa_robos_historicos_quito.py --verificar
```

The first command requires internet access. It requests ArcGIS metadata, a control count for the pilot rectangle and one count for each of the 25 polygons. It clips the bundled grid to the pilot rectangle and counts events dated January 1, 2019 through December 31, 2022 inclusive. The sum must match the control count. Counts of one to four per cell are suppressed. The generator writes a GeoJSON file and an audit report to `resultados/delincuencia_exploratoria/`, outside Git. It never requests individual incidents.

The second command verifies `robos_historicos_2019_2022_cuadriculas.geojson` offline. If you already have the layer, this step is sufficient. The Windows reference file has SHA-256 `fab7a8a2de13f0718863caf28581e9a81e988f1834f7296129779b04df15e6a1`. Startup checks normalized JSON content, allowing differences in indentation, line endings, UTF-8 BOM, key order and cell order. It checks the period, source and cell identities. The fingerprint also covers coordinates, counts, densities, classifications and metadata. If the source changes or a query fails, generation stops before replacing the layer. If the service is unavailable and you lack a legitimate local copy, use the three-mode startup below.

### Provenance and reuse · reviewed November 15, 2026

The public **Robo_personas view** item lists `jquinteros_esriecdemos` as its publisher. The item credits, item-specific terms and layer copyright fields are blank. The service reports its last data edit in June 2023. The spatial query selects the Quito rectangle. The item also carries the tag “cuenca” and identifies neither the original producer nor the rights holder. It gives no positional accuracy for the points. [Original item](https://www.arcgis.com/home/item.html?id=f406a38db5f7465b9be1eadec882f769) · [Item metadata](https://www.arcgis.com/sharing/rest/content/items/f406a38db5f7465b9be1eadec882f769?f=pjson) · [Layer service and metadata](https://services1.arcgis.com/UOl0yzPDLol8nS3m/ArcGIS/rest/services/Robo_personas_view/FeatureServer/0)

Esri describes permission to use, reproduce, create derivatives of and distribute publicly shared content, subject to provider restrictions. Its service terms also refer users to the owner's terms and metadata. The item supports public queries. We have been unable to verify that its publisher holds sufficient rights to authorize redistribution of this derivative on GitHub. Aggregation reduces disclosure of individual data but does not resolve ownership. The repository therefore includes the generation procedure and excludes its outputs. [ArcGIS Online terms](https://doc.arcgis.com/en/arcgis-online/reference/terms-of-use.htm) · [Esri service terms](https://www.esri.com/en-us/legal/terms/web-site-service)

Quito's Municipal Code provides for access to municipal public information in reusable formats. Applying those provisions here would require evidence linking this item to an official municipal publication and establishing the chain of rights. Confirmation from the rights holder covering the aggregates and their republication would allow us to revisit distribution. [Quito Municipal Code](https://www.quito-turismo.gob.ec/descargas/LOTAIP_2024/marzo/CODIGO_MUNICIPAL.pdf)

## Start the demo

Open **two terminals at the repository root**. In the first, start FastAPI.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\iniciar-demo.ps1 backend
```

Once Uvicorn reports that it is ready, start the frontend in the second terminal.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\iniciar-demo.ps1 frontend
```

Open **http://127.0.0.1:4173**. The backend command verifies the full demo resources and starts `main:app` with coverage `demo` and network `peatonal_filtrada`. The frontend command rebuilds the app before serving Vite Preview and sets `VITE_API_BASE_URL=/api`. Check connectivity at http://127.0.0.1:4173/api/health. The API listens on port 8000. Press Ctrl+C in each terminal to stop its process. Use the same browser and origin each time to access saved trips.

**With only the public ZIP**, start the backend as follows and use the same frontend command above.

```powershell
$env:RUTAINFORMADA_COBERTURA = 'demo'
$env:RUTAINFORMADA_RED = 'peatonal_filtrada'
Push-Location backend
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
Pop-Location
```

## Try the example and test offline access

The interface is in Spanish. The labels below match the controls on screen.

1. Click **Probar recorrido de ejemplo** (load the example trip), then **Comparar recorridos** (compare routes). With the validated layer, you will see four distinct routes from A (−0.201, −78.504) to B (−0.184, −78.486), in latitude–longitude order. For other endpoints, the fourth card appears only for a distinct alternative that reduces distance inside higher-concentration zones by at least **10 m and 2%**, and the density-weighted indicator by at least **2%**, relative to the shortest route. It must also avoid increasing exposure in areas with missing or suppressed density data. Endpoints must snap to the network within 300 m. Routes may be at most 15% longer than the shortest path between snapped nodes. Reported distances exclude the walk from the requested points to those nodes.
2. Select a route and enable **Resaltar tramos en el mapa** (highlight segments on the map). Tap a yellow triangle on a highlighted segment, then **Ver detalles** (view details). The marker refers to aggregated 2019–2022 records. It identifies neither an individual crime location nor a present danger.
3. Click **Guardar recorrido** (save trip), then **Guardados** (saved trips). Once the progressive web app is ready for offline use, you can close and reopen it in the same browser, switch between saved routes and view local vector reference streets. New calculations require FastAPI. Public OpenStreetMap tiles are fetched online. The service worker caches the app shell and reference streets, and IndexedDB stores the trips you choose to save.
4. After a version change, open the same origin online and reload once the update activates. An open window keeps its current interface until the next navigation. Clearing site data also deletes saved trips.

See the [backend guide](backend/README.md), [integration contract](backend/FRONTEND_API.md) and [frontend guide](frontend/README.md) for tests and technical details (in Spanish).

To repeat the HTTP integration checks, keep FastAPI running and open another terminal at the repository root.

```powershell
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8000'
npm.cmd --prefix frontend run test:integration
```

To check the route cards, interactive triangle and saved trip, keep Preview running and use the same terminal.

```powershell
npm.cmd --prefix frontend run browser:install
$env:PLAYWRIGHT_TEST_BASE_URL = 'http://127.0.0.1:4173'
npm.cmd --prefix frontend run test:e2e -- alternativa-robos.spec.ts --project=390x844 --project=1280x800
```
