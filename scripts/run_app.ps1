# Activa el entorno virtual .venv y lanza la aplicación Streamlit.
# Uso (desde cualquier carpeta):  powershell -ExecutionPolicy Bypass -File scripts\run_app.ps1
# Puerto opcional: powershell -ExecutionPolicy Bypass -File scripts\run_app.ps1 -Puerto 8765

param(
    [int]$Puerto = 8501
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

$activar = Join-Path $raiz ".venv\Scripts\Activate.ps1"
if (-not (Test-Path $activar)) {
    Write-Error "No existe el entorno .venv. Créalo con: python -m venv .venv ; .venv\Scripts\python -m pip install -r requirements.txt"
    exit 1
}

. $activar
streamlit run (Join-Path $raiz "app\streamlit_app.py") --server.port $Puerto
