# RutaInformada Quito

Demo de STEMergent Hacks 2026 para comparar recorridos peatonales en una zona piloto de 19,13 km² del centro-norte de Quito. El recorrido de ejemplo permite comparar distancia, concentración histórica de siniestros, estimación vial LightGBM y concentración histórica de robos a personas. Para reproducir las cuatro modalidades desde GitHub, usa esta revisión de `main` y genera la capa opcional en tu equipo. El tag `hackathon-final-2026-11-14` conserva el arranque anterior.

## Preparar Windows

En una carpeta nueva, con Git, PowerShell, Python 3.14 x64 y Node.js 22.12 o posterior:

```powershell
git clone https://github.com/JimboJ10/RutaSegura_Quito.git
cd RutaSegura_Quito
Expand-Archive -LiteralPath .\entregas\demo-peatonal-v1-2026-11-04.zip -DestinationPath . -Force
py -3.14 -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-lock.txt
npm.cmd --prefix frontend ci
.\backend\.venv\Scripts\python.exe scripts\distribuir_mvp.py verificar
```

Si ya dispones del entorno y los datos validados, utiliza directamente el arranque. El ZIP incluye el grafo peatonal filtrado y las 25 cuadrículas de predicciones de junio de 2026. El manifiesto verifica tamaños y SHA-256. Las estimaciones e indicadores utilizados por la API ya están calculados. Ejecutar la demo no requiere entrenar ni cargar otro modelo.

## Generar la capa histórica en el equipo del juez

Tras extraer el ZIP e instalar las dependencias, revisa las condiciones de la fuente que se detallan abajo. Para una evaluación local compatible con esas condiciones, ejecuta desde la raíz:

```powershell
.\backend\.venv\Scripts\python.exe scripts\generar_capa_robos_historicos_quito.py
.\backend\.venv\Scripts\python.exe scripts\generar_capa_robos_historicos_quito.py --verificar
```

El primer comando requiere internet y consulta los metadatos, un conteo de control y 25 conteos por polígono en ArcGIS. Usa la fecha del hecho desde el 1 de enero de 2019 hasta antes del 1 de enero de 2023 y recorta las cuadrículas del ZIP al rectángulo piloto. Exige que la suma coincida con el control y oculta los conteos de 1 a 4 por celda. Escribe el GeoJSON y un informe de auditoría en `resultados/delincuencia_exploratoria/`, fuera de Git. Ninguna consulta solicita incidentes individuales.

El segundo comando verifica sin internet `robos_historicos_2019_2022_cuadriculas.geojson`. Si ya tienes la capa, basta con este paso. El SHA-256 del archivo de referencia en Windows es `fab7a8a2de13f0718863caf28581e9a81e988f1834f7296129779b04df15e6a1`. El arranque ahora verifica el contenido JSON normalizado. Acepta diferencias de sangrado, finales de línea, BOM UTF-8 y orden de las claves o de las 25 celdas. Comprueba el periodo, la fuente y la identidad de cada celda, y la huella abarca también coordenadas, conteos, densidades, clasificación y metadatos. Si la fuente cambia o falla, la generación se detiene antes de sustituir la capa. Si no puedes acceder al servicio ni dispones de una copia legítima, usa el arranque de tres modalidades descrito más abajo.

### Procedencia y reutilización · revisión del 15 de noviembre de 2026

La ficha pública **Robo_personas view** identifica como publicador a la cuenta `jquinteros_esriecdemos`. Los campos de créditos y condiciones de uso de la ficha y el copyright de la capa están vacíos. El servicio declara su última edición de datos en junio de 2023. La consulta espacial selecciona el rectángulo de Quito. La ficha incluye la etiqueta «cuenca» y no identifica al productor primario, la institución titular ni la precisión de los puntos. [Ficha original](https://www.arcgis.com/home/item.html?id=f406a38db5f7465b9be1eadec882f769) · [Metadatos de la ficha](https://www.arcgis.com/sharing/rest/content/items/f406a38db5f7465b9be1eadec882f769?f=pjson) · [Servicio y metadatos de la capa](https://services1.arcgis.com/UOl0yzPDLol8nS3m/ArcGIS/rest/services/Robo_personas_view/FeatureServer/0)

Esri describe permisos de uso, reproducción, creación de derivados y distribución del contenido compartido públicamente, sujetos a las restricciones del proveedor. Las condiciones del servicio también remiten a los términos y metadatos del titular. La ficha permite la consulta pública. Sigue sin acreditarse que el publicador tenga derechos suficientes sobre la base original para autorizar la redistribución de este derivado en GitHub. La agregación reduce la exposición de datos individuales y deja abierta la cuestión de titularidad. Por ese motivo el repositorio distribuye el procedimiento, sin adjuntar sus resultados. [Reglas de ArcGIS Online](https://doc.arcgis.com/en/arcgis-online/reference/terms-of-use.htm) · [Condiciones del servicio Esri](https://www.esri.com/en-us/legal/terms/web-site-service)

El Código Municipal contempla la apertura de información pública municipal en formatos reutilizables. Para invocar esas disposiciones aquí falta vincular esta ficha con una publicación municipal oficial y su cadena de derechos. Una confirmación del titular que cubra los agregados y su republicación permitiría revisar la distribución. [Código Municipal de Quito, disposiciones sobre transparencia y oficialidad](https://www.quito-turismo.gob.ec/descargas/LOTAIP_2024/marzo/CODIGO_MUNICIPAL.pdf)

## Iniciar la demo

Abre **dos terminales en la raíz del repositorio**. Primero inicia FastAPI:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\iniciar-demo.ps1 backend
```

Cuando Uvicorn indique que está listo, inicia el frontend en la otra terminal:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\iniciar-demo.ps1 frontend
```

Abre **http://127.0.0.1:4173**. El primer comando comprueba los archivos de la demo completa e inicia `main:app` con cobertura `demo` y red `peatonal_filtrada`. El segundo recompila antes de servir Preview y fija `VITE_API_BASE_URL=/api`. Comprueba la conexión en http://127.0.0.1:4173/api/health. El puerto de la API es 8000. Para detener cada proceso, pulsa Ctrl+C en su terminal. Utiliza siempre el mismo origen para volver a encontrar los recorridos guardados.

**Con el ZIP público solamente**, inicia el backend de esta manera y usa el mismo comando del frontend:

```powershell
$env:RUTAINFORMADA_COBERTURA = 'demo'
$env:RUTAINFORMADA_RED = 'peatonal_filtrada'
Push-Location backend
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
Pop-Location
```

## Comprobar el recorrido y la PWA

1. Pulsa **Probar recorrido de ejemplo** y **Comparar recorridos**. Con la capa validada se obtienen cuatro trazados para A (−0,201; −78,504) y B (−0,184; −78,486), en latitud y longitud. Para otros puntos la cuarta tarjeta requiere un recorrido distinto de los tres existentes, con al menos 10 m y 2 % de reducción en zonas de mayor concentración y 2 % de reducción del indicador ponderado frente a la más corta, sin aumentar el recorrido en sectores sin datos o con densidad oculta. Los límites son 300 m de ajuste y 15 % de desvío entre nodos. Las distancias excluyen el acceso desde los puntos solicitados.
2. Con los datos completos, selecciona una modalidad y activa **Resaltar tramos en el mapa**. Toca el triángulo y **Ver detalles**. La marca se refiere a registros agregados de 2019–2022. No señala un delito individual ni permite inferir peligro actual.
3. Pulsa **Guardar recorrido** y abre **Guardados**. Una vez preparada la aplicación para uso sin conexión, puedes cerrar y volver a abrirla en ese navegador, consultar cada modalidad guardada y utilizar las calles vectoriales de referencia. El cálculo de nuevos recorridos requiere FastAPI. Las teselas públicas de OpenStreetMap se consultan en línea.
4. Tras cambiar de versión, abre el mismo origen con conexión y recarga tras la activación de la actualización. Una ventana ya abierta conserva su interfaz hasta la siguiente navegación. Borrar los datos del sitio también borra los recorridos guardados.

Consulta el [backend](backend/README.md), el [contrato de integración](backend/FRONTEND_API.md) y la [guía del frontend](frontend/README.md) para las pruebas y los detalles técnicos.

Para repetir las comprobaciones HTTP desde otra terminal en la raíz, con FastAPI iniciado:

```powershell
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8000'
npm.cmd --prefix frontend run test:integration
```

Para verificar también las tarjetas, el triángulo interactivo y el guardado, deja Preview abierto e inicia estas pruebas desde esa misma terminal:

```powershell
npm.cmd --prefix frontend run browser:install
$env:PLAYWRIGHT_TEST_BASE_URL = 'http://127.0.0.1:4173'
npm.cmd --prefix frontend run test:e2e -- alternativa-robos.spec.ts --project=390x844 --project=1280x800
```
