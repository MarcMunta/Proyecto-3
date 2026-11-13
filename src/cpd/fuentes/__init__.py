"""Capa de datos por API del proyecto (provincia a provincia).

Cada módulo conecta con una fuente pública (API o descarga programática), guarda la
respuesta cruda en ``data/raw/api/<fuente>/`` y devuelve una tabla ``pandas`` ordenada
(formato largo) con clave ``codigo_provincia`` (dos dígitos INE: "01" a "52") y, si es
una serie temporal, una columna de fecha.

Módulos:
- http: cliente HTTP común (reintentos, pausas, caché y registro de descargas).
- provincias: las 52 provincias, su CCAA, polígonos y asignación punto -> provincia.
- meteo: Open-Meteo (clima diario, horas de free-cooling y clima actual).
- ree: Red Eléctrica (REData): demanda y generación por CCAA, CO2, precios y tiempo real.
- omie: precio horario/cuartohorario del mercado diario (fichero marginalpdbc).
- ine: población por provincia (Tempus3 API del INE).
- sepe: paro registrado por municipio agregado a provincia.
- peeringdb: centros de datos e IXP de España.
- sismicidad: terremotos (EMSC FDSN) asignados a provincias.
- red_capacidad: capacidad de acceso a la red de transporte (REE) por CCAA.
- subestaciones: subestaciones de 220/400 kV desde OpenStreetMap (Overpass).
- natura: superficie de Red Natura 2000 por provincia (EEA ArcGIS REST).
- curado: construye ``panel_provincia_mes`` y ``provincias_actual``.
- actualizar: línea de comandos ``python -m cpd.fuentes.actualizar [--rapido]``.

Regla general: si una fuente falla no se inventan valores; la celda queda vacía (NaN)
y el fallo se informa en el resumen de la actualización.
"""
