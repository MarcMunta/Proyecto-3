<#
Descarga los datos raw del proyecto (Release "datos-raw-2026-11-09" de GitHub) y los
descomprime en data/raw/. Comprueba la huella SHA-256 antes de descomprimir.

Uso, desde la raíz del repositorio:
    powershell -ExecutionPolicy Bypass -File scripts\descargar_datos_raw.ps1

Alternativa: volver a descargar cada fuente con los scripts de src/ingesta/ (ver README).
#>
$ErrorActionPreference = 'Stop'

$Raiz = Split-Path -Parent $PSScriptRoot
$Url = 'https://github.com/MarcMunta/Proyecto-3/releases/download/datos-raw-2026-11-09/P3_datos_raw_2026-11-09.zip'
$ShaEsperado = 'B225710FF1D8425D9E743808D14A2AAF6DCC41CA17BDE561CE44AD7EDD465ACC'
$Zip = Join-Path $env:TEMP 'P3_datos_raw_2026-11-09.zip'

Write-Host "Descargando datos raw (unos 100 MB) desde:`n  $Url"
Invoke-WebRequest -Uri $Url -OutFile $Zip -UseBasicParsing

$Sha = (Get-FileHash -LiteralPath $Zip -Algorithm SHA256).Hash
if ($Sha -ne $ShaEsperado) {
    throw "La huella SHA-256 no coincide ($Sha). La descarga puede estar corrupta; vuelve a intentarlo."
}

# El zip contiene rutas data/raw/..., así que se descomprime en la raíz del repositorio.
Expand-Archive -LiteralPath $Zip -DestinationPath $Raiz -Force
Remove-Item -LiteralPath $Zip
Write-Host "Listo: datos descomprimidos en $Raiz\data\raw"
