"""
04 - Agua.

Variables del enunciado que cubre:
  embalses cercanos, disponibilidad hídrica, sequías históricas (serie de reservas),
  estrés hídrico.

Fuentes:
  - MITECO, Boletín Hidrológico: base de datos histórica de embalses peninsulares
    mayores de 5 hm3, con capacidad y reserva semanal desde 1988.
  - WRI Aqueduct 4.0: indicador de estrés hídrico por subcuenca (estándar
    internacional, lo usan las propias tecnológicas para elegir dónde poner CPD).
"""
from utils import RAW, descargar

DESTINO = RAW / "agua"

descargar(
    "https://www.miteco.gob.es/content/dam/miteco/es/agua/temas/evaluacion-de-los-recursos-hidricos/"
    "boletin-hidrologico/Historico-de-embalses/BD-Embalses.zip",
    DESTINO / "miteco_bd_embalses_1988_hoy.zip",
    "MITECO", "Reserva semanal de embalses peninsulares >5 hm3 desde 1988 (Boletín Hidrológico)",
)

# Estrés hídrico (WRI Aqueduct 4.0): rankings por país y por PROVINCIA,
# situación actual y proyecciones 2030/2050/2080. Licencia CC BY 4.0.
descargar(
    "https://files.wri.org/aqueduct/aqueduct-4-0-country-rankings.zip",
    DESTINO / "wri_aqueduct40_rankings_pais_provincia.zip",
    "WRI Aqueduct 4.0", "Estrés hídrico por provincia: actual y proyecciones 2030-2080",
)
