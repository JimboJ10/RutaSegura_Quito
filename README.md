# RutaInformada Quito

Demo de STEMergent Hacks 2026 para comparar recorridos peatonales en una zona piloto de 19,13 km² del centro-norte de Quito. El recorrido de ejemplo permite comparar distancia, concentración histórica de siniestros, estimación vial LightGBM y, con el recurso local autorizado, concentración histórica de robos a personas. Consulta la revisión `hackathon-final-2026-11-14` para reproducir la entrega.

## Preparar Windows

Desde la raíz de una copia limpia del repositorio, con PowerShell, Python 3.14 x64 y Node.js 22.12 o posterior:

```powershell
Expand-Archive -LiteralPath .\entregas\demo-peatonal-v1-2026-11-04.zip -DestinationPath . -Force
py -3.14 -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-lock.txt
npm.cmd --prefix frontend ci
.\backend\.venv\Scripts\python.exe scripts\distribuir_mvp.py verificar
```

Si ya dispones del entorno y los datos validados, utiliza directamente el arranque. El ZIP incluye el grafo peatonal filtrado y las 25 cuadrículas de predicciones de junio de 2026. El manifiesto verifica tamaños y SHA-256. Las estimaciones e indicadores utilizados por la API ya están calculados. Ejecutar la demo no requiere entrenar ni cargar otro modelo.

## Demo completa del equipo

La cuarta modalidad, los contornos rojos y los triángulos necesitan este archivo local validado:

```text
resultados/delincuencia_exploratoria/robos_historicos_2019_2022_cuadriculas.geojson
SHA-256 fab7a8a2de13f0718863caf28581e9a81e988f1834f7296129779b04df15e6a1
```

Su redistribución está pendiente de autorización. El repositorio y el ZIP base permiten reproducir las tres modalidades viales. Para reproducir la demo completa, un tercero necesita también acceso legítimo al archivo anterior. Las advertencias pueden aparecer en cualquiera de las modalidades cuando el trazado corta un tramo histórico válido. La cuarta tarjeta aparece solo si el backend encuentra una alternativa distinta que supera sus criterios de mejora.

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

1. Pulsa **Probar recorrido de ejemplo** y **Comparar recorridos**. Los límites son 300 m de ajuste y 15 % de desvío entre nodos. Las distancias excluyen el acceso desde los puntos solicitados.
2. Con los datos completos, selecciona una modalidad y activa **Resaltar tramos en el mapa**. Toca el triángulo y **Ver detalles**. La marca se refiere a registros agregados de 2019–2022. No señala un delito individual ni permite inferir peligro actual.
3. Pulsa **Guardar recorrido** y abre **Guardados**. Una vez preparada la aplicación para uso sin conexión, puedes cerrar y volver a abrirla en ese navegador, consultar cada modalidad guardada y utilizar las calles vectoriales de referencia. El cálculo de nuevos recorridos requiere FastAPI. Las teselas públicas de OpenStreetMap se consultan en línea.
4. Tras cambiar de versión, abre el mismo origen con conexión y recarga tras la activación de la actualización. Una ventana ya abierta conserva su interfaz hasta la siguiente navegación. Borrar los datos del sitio también borra los recorridos guardados.

Consulta el [backend](backend/README.md), el [contrato de integración](backend/FRONTEND_API.md) y la [guía del frontend](frontend/README.md) para las pruebas y los detalles técnicos.
