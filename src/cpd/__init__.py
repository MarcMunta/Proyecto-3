"""Paquete principal del sistema de viabilidad de CPD (data center).

Módulos:
- config: carga de config/settings.yaml y rutas del proyecto.
- simulator: fórmulas de energía, agua, costes, CO2, latencia y finanzas.
- scoring: filtros eliminatorios, sub-scores, score global y ranking.
- forecast: previsión de demanda eléctrica a 10 años (línea base).
- etl: extractores de datos reales (REData / Red Eléctrica).
"""

__version__ = "0.1.0"
