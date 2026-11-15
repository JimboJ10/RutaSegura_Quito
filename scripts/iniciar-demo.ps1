param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('backend', 'frontend')]
    [string]$Servicio
)
$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
Push-Location $raiz
try {
    if ($Servicio -eq 'backend') {
        $env:RUTAINFORMADA_COBERTURA = 'demo'
        $env:RUTAINFORMADA_RED = 'peatonal_filtrada'
        $env:RUTASEGURA_CORS_ORIGINS = 'http://127.0.0.1:4173,http://127.0.0.1:5173,http://localhost:5173'
        $python = Join-Path $raiz 'backend/.venv/Scripts/python.exe'
        if (!(Test-Path -LiteralPath $python)) { throw 'Falta backend/.venv. Instale las dependencias indicadas en README.md.' }
        & $python scripts/distribuir_mvp.py verificar
        if ($LASTEXITCODE) { throw 'Revise los datos del paquete base del MVP.' }
        $capa = 'resultados/delincuencia_exploratoria/robos_historicos_2019_2022_cuadriculas.geojson'
        if (!(Test-Path -LiteralPath $capa -PathType Leaf)) { throw "Falta $capa. Consulte el paso de generacion local de ArcGIS en README.md." }
        & $python scripts/generar_capa_robos_historicos_quito.py --verificar
        if ($LASTEXITCODE) { throw 'La capa historica no coincide con los datos validados de la demo.' }
        Set-Location backend
        & $python -m uvicorn main:app --host 127.0.0.1 --port 8000
    } else {
        Set-Location frontend
        $env:VITE_API_BASE_URL = '/api'
        Remove-Item Env:PWA_TLS_CERT, Env:PWA_TLS_KEY -ErrorAction SilentlyContinue
        & npm.cmd run build
        if ($LASTEXITCODE) { throw 'Fallo la compilacion. Preview no se ha iniciado.' }
        & node ./node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 4173 --strictPort
    }
    if ($LASTEXITCODE) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}
