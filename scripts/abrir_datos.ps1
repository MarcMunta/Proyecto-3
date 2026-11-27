<#
Abre el DuckDB de la publicación activa para consultar sus datos con SQL.
Sin publicación activa, reconstruye el almacén auxiliar desde data/curated.

Uso, desde la raíz del repositorio:
    powershell -ExecutionPolicy Bypass -File scripts\abrir_datos.ps1            # abre el almacén
    powershell -ExecutionPolicy Bypass -File scripts\abrir_datos.ps1 -Actualizar # refresca, entrena y publica

Para cerrar la interfaz, pulsa Enter en esta ventana.
#>
param([switch]$Actualizar, [switch]$PermitirDemandaIncompleta)
$ErrorActionPreference = 'Stop'

$Raiz = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Raiz '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    throw "No se encuentra el entorno .venv. Créalo primero siguiendo el README."
}

Push-Location $Raiz
try {
    if ($Actualizar) {
        $opciones = @('--actualizar')
        if ($PermitirDemandaIncompleta) { $opciones += '--permitir-demanda-incompleta' }
        & $Python -m cpd.publicar @opciones
        if ($LASTEXITCODE -ne 0) { throw "La actualización se rechazó. Se conserva la versión activa." }
    }
    if (Test-Path -LiteralPath (Join-Path $Raiz 'frontend\public\data\publicacion.json')) {
        & $Python -m cpd.almacen --publicado --ui
    }
    else {
        & $Python -m cpd.almacen --ui
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}
