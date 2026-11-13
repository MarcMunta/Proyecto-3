<#
Construye el almacén DuckDB (data/almacen/p3_cpd.duckdb) con todas las tablas curadas y abre
la interfaz web de DuckDB en el navegador (http://localhost:4213) para verlas, ordenarlas y consultarlas con SQL.

Uso, desde la raíz del repositorio:
    powershell -ExecutionPolicy Bypass -File scripts\abrir_datos.ps1            # reconstruye y abre
    powershell -ExecutionPolicy Bypass -File scripts\abrir_datos.ps1 -Actualizar # antes refresca los datos por API

Para cerrar la interfaz, pulsa Enter en esta ventana.
#>
param([switch]$Actualizar)
$ErrorActionPreference = 'Stop'

$Raiz = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Raiz '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    throw "No se encuentra el entorno .venv. Créalo primero siguiendo el README."
}

Push-Location $Raiz
try {
    if ($Actualizar) {
        Write-Host "Refrescando los datos por API..."
        & $Python -m cpd.fuentes.actualizar
    }
    & $Python -m cpd.almacen --ui
}
finally {
    Pop-Location
}
