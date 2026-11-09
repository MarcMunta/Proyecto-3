"""
01 - Base de municipios.

Es la tabla "columna vertebral" del proyecto: todos los demás datos
(población, clima, energía...) se unirán a ella por el CÓDIGO INE
del municipio (5 dígitos: 2 de provincia + 3 de municipio).

Fuentes:
  - INE: Relación de municipios y sus códigos (lista oficial).
  - Eurostat GISCO: límites municipales (LAU) con superficie y polígonos,
    que usaremos para sacar las coordenadas (centroide) de cada municipio.
"""
from utils import RAW, descargar

DESTINO = RAW / "municipios"

# 1) Lista oficial de municipios del INE (año 2026)
descargar(
    url="https://www.ine.es/daco/daco42/codmun/diccionario26.xlsx",
    destino=DESTINO / "ine_diccionario_municipios_2026.xlsx",
    fuente="INE",
    descripcion="Relación de municipios y sus códigos por provincias (2026)",
)

# 2) Límites municipales de Europa (Eurostat GISCO, LAU 2024, WGS84)
#    Viene toda Europa; el filtrado a España se hace en la fase de transformación.
GISCO = "https://gisco-services.ec.europa.eu/distribution/v2/lau"
descargar(
    url=f"{GISCO}/shp/LAU_RG_01M_2024_4326.shp.zip",
    destino=DESTINO / "gisco_lau_2024_4326.shp.zip",
    fuente="Eurostat GISCO",
    descripcion="Límites municipales LAU 2024 (polígonos, EPSG:4326)",
)
descargar(
    url=f"{GISCO}/csv/LAU_RG_01M_2024_4326.csv",
    destino=DESTINO / "gisco_lau_2024_atributos.csv",
    fuente="Eurostat GISCO",
    descripcion="Atributos LAU 2024: población, densidad, superficie km2",
)
