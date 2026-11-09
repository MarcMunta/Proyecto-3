"""
02 - Demografía y socioeconomía.

Variables del enunciado que cubre:
  población, densidad (con la superficie del bloque 01), evolución demográfica,
  envejecimiento, desempleo, nivel educativo, renta.

Fuentes:
  - INE Padrón (tabla 29005): población por municipio y sexo, 1996-hoy.
  - INE Atlas de Distribución de Renta de los Hogares (ADRH):
      tabla 30824 = renta media y mediana
      tabla 30832 = indicadores demográficos (edad media, % mayores de 65...)
  - INE Censo 2021: nivel de estudios por municipio (tablas 66620 y 66623).
  - SEPE: paro registrado por municipio y mes.
"""
import re

from utils import RAW, descargar, descargar_filtrado

DESTINO = RAW / "demografia"
INE_CSV = "https://www.ine.es/jaxiT3/files/t/es/csv_bdsc"  # CSV separado por ';'

# --- Padrón municipal: serie completa ---
descargar(f"{INE_CSV}/29005.csv", DESTINO / "ine_padron_municipios_29005.csv",
          "INE", "Cifras oficiales del padrón por municipio y sexo (1996-actualidad)")

# --- Atlas de Renta (ADRH) ---
# Una fila es de nivel municipio cuando las columnas Distritos y Secciones
# van vacías, es decir: "01001 Alegría-Dulantzi;;;..."
es_municipio = re.compile(r"^\d{5} [^;]*;;;").match

descargar_filtrado(f"{INE_CSV}/30824.csv", DESTINO / "ine_adrh_renta_30824.csv",
                   "INE", "ADRH: indicadores de renta media y mediana", es_municipio)
descargar_filtrado(f"{INE_CSV}/30832.csv", DESTINO / "ine_adrh_demograficos_30832.csv",
                   "INE", "ADRH: indicadores demográficos (edad media, % >65, tamaño hogar...)", es_municipio)

# --- Censo 2021: nivel de estudios ---
descargar(f"{INE_CSV}/66620.csv", DESTINO / "ine_censo2021_estudios_mun500mas_66620.csv",
          "INE", "Censo 2021: nivel de estudios, municipios de 500 o más habitantes")
descargar(f"{INE_CSV}/66623.csv", DESTINO / "ine_censo2021_estudios_mun50a500_66623.csv",
          "INE", "Censo 2021: nivel de estudios, municipios de 50 a 500 habitantes")

# --- SEPE: paro registrado por municipio (un fichero por año, datos mensuales) ---
SEPE = "https://sede.sepe.gob.es/es/portaltrabaja/resources/sede/datos_abiertos/datos"
for anio in [2023, 2024, 2025, 2026]:
    descargar(f"{SEPE}/Paro_por_municipios_{anio}_csv.csv", DESTINO / f"sepe_paro_municipios_{anio}.csv",
              "SEPE", f"Paro registrado por municipios, {anio} (mensual)")

print("FIN 02_demografia")
