# Despliegue público de RutaInformada Quito

[Abrir la aplicación pública](https://rutainformada-quito.vercel.app)

El 15 de noviembre de 2026, dos clientes Chromium sin sesión de Vercel probaron el dominio de producción a 390 × 844 y 1280 × 800. Ambos cargaron teselas reales, calcularon el piloto y reabrieron las tres geometrías guardadas sin conexión. Dos consultas públicas posteriores al piloto tardaron 3,43 y 1,80 s desde el cliente de prueba.

La salida estática local ocupa 1.689.636 bytes. El ZIP público ocupa aproximadamente 2,63 MB y el GraphML extraído 24,94 MB. En Windows, un proceso nuevo con el mismo paquete de datos tardó 8,74 s en importar la API y preparar el grafo, con un máximo de 602 MB de memoria residente durante el ensayo. Estas dos medidas son locales. El build remoto instaló las ruedas binarias Linux y publicó la imagen en Vercel Container Registry.

La rama `deploy/vercel` sirve React/Vite y FastAPI desde el mismo origen HTTPS. Vercel evalúa primero la regla para `/api/*` y envía el resto al servicio estático. El adaptador monta FastAPI bajo `/api` y ejecuta su ciclo de vida para cargar el grafo una vez por proceso. El comando local habitual sigue usando `main:app`.

## Configuración del proyecto

- Usa Vercel Services con el repositorio en la raíz (`.`). Para una integración con Git, selecciona `deploy/vercel` como rama de producción antes de promover el despliegue. La entrega para Devpost sigue en su propia revisión.
- Conserva los ajustes de compilación de cada servicio en `vercel.json`. El servicio `web` usa Vite en `frontend/` y produce `dist/`. El servicio `api` se construye desde `Dockerfile.vercel` en la raíz y sirve HTTP en el puerto 80 por defecto.
- Variables obligatorias: ninguna. La compilación de producción usa `/api` por defecto. Si defines `VITE_API_BASE_URL`, usa exactamente `/api`. Los valores por defecto son `RUTAINFORMADA_COBERTURA=demo` y `RUTAINFORMADA_RED=peatonal_filtrada`. Evita heredar direcciones de localhost, certificados de desarrollo o ajustes de otra cobertura.
- Para repetir el despliegue por CLI, usa un clon limpio de esta rama. Ejecuta `npx vercel link`, selecciona el proyecto del equipo y ejecuta `npx vercel deploy --prod`. El dominio de producción debe permitir acceso anónimo.

## Datos, recursos y PWA

El build extrae únicamente el grafo y las predicciones del ZIP público versionado y valida sus tamaños y SHA-256 contra el manifiesto del código. La imagen Linux usa Python 3.14, OSMnx, NetworkX y las dependencias geoespaciales binarias. LightGBM ya calculó los indicadores. Una instancia nueva debe cargar 14.686 nodos y 43.248 aristas antes de atender la primera solicitud.

Esta rama incluye en deploy-data únicamente la capa agregada de 25 polígonos de 2019–2022. La auditoría original concilió 1.102 registros con el control del rectángulo piloto. Los conteos de 1 a 4 aparecen como intervalo. El build verifica la huella de la copia validada y la carga con el lector de FastAPI. La cuarta tarjeta se ofrece sólo para alternativas distintas que cumplen los criterios históricos y de desvío. Los datos no describen el peligro actual.

El manifest y el service worker conservan el alcance `/`. Una primera carga HTTPS prepara la interfaz y las calles vectoriales. Guarda el recorrido antes de desconectar el dispositivo. La PWA consulta IndexedDB al reabrirse en el mismo origen. Los recorridos nuevos requieren FastAPI y las teselas de OpenStreetMap se solicitan en línea.

## Verificación del dominio

Comprueba `/api/health` y `/api/predicciones`, abre el ejemplo y compara los recorridos. Las distancias de referencia son 3,2557, 3,3464, 3,2931 y 3,3318 km. Para comprobar en Chromium el mapa, los guardados y la reapertura offline a 390 × 844 y 1280 × 800:

```powershell
cd frontend
npm.cmd ci
npm.cmd run browser:install
$env:PLAYWRIGHT_BROWSERS_PATH = (Resolve-Path .playwright-browsers).Path
node scripts/test-vercel.mjs https://DOMINIO-DE-PRODUCCION
```

[Vercel Services y reglas de enrutamiento](https://vercel.com/kb/guide/vercel-services) · [Contenedores HTTP en Vercel](https://vercel.com/kb/guide/docker)

La cuenta jquinteros_esriecdemos publica la [ficha ArcGIS](https://www.arcgis.com/home/item.html?id=f406a38db5f7465b9be1eadec882f769). Sus campos de licencia y créditos están vacíos. Esri describe permisos generales para contenido compartido, sujetos a restricciones del proveedor. La publicación del agregado por decisión del equipo no acredita la cadena de derechos del productor ni concede una licencia adicional a terceros. [Condiciones de ArcGIS Online](https://doc.esri.com/en/arcgis-online/latest/reference/terms-of-use.html)
