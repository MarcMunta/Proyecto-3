# Manual de instalación y uso · F8 / F9

## Instalación local

La instalación se verificó en entornos nuevos con Python 3.13 y Node 24. Ejecuta los comandos desde la raíz del proyecto en PowerShell.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -e .
cd frontend
npm ci
cd ..
```

Restaura `data/raw`, `data/curated` y `data/clean` en la raíz a partir de la release de datos aprobada por el equipo. Comprueba los hashes de su manifiesto. El código y la demo territorial se pueden probar sin descargar esa copia.

## Generar y abrir el mapa

```powershell
.\.venv\Scripts\python.exe -m cpd.publicar
cd frontend
npm run dev
```

Abre la URL que indica Vite. Si el control rechaza cobertura insuficiente de demanda y se necesita reproducir la instantánea documentada de octubre de 2026, usa `--permitir-demanda-incompleta`. El mapa señalará esa carencia. `--reentrenar` recalcula las previsiones y los informes en un espacio temporal. El proceso completo puede tardar varios minutos.

`npm run build` genera `frontend/dist` después de activar el lote que se vaya a distribuir. Conserva la carpeta completa al copiar la compilación.

## Interpretar el resultado

1. Selecciona una provincia en el ranking o en el mapa. Los límites municipales permiten orientarte geográficamente.
2. Consulta el estado técnico y su cobertura. **Pendiente de verificar** indica que uno o más filtros críticos carecen de datos.
3. Compara el VAN, el coste y el precio eléctrico de equilibrio. El precio de equilibrio es el precio al que el VAN del escenario llega a cero.
4. Revisa la fecha del panel y los avisos. Los ficheros de una publicación comparten versión. Las series se cargan al abrir la ficha.
5. En **Modelos de la zona**, revisa las cifras del panel derecho. Despliega cada fila para ver su gráfico o cálculo y la evaluación general del modelo. La luz es peninsular, la demanda y el mix son autonómicos y las reservas se muestran por ámbito hidrográfico.
6. **Todas las evaluaciones** abre el catálogo en el mismo panel y conserva la provincia seleccionada. En el precio de la luz se distingue el acierto mensual del acierto del precio medio de doce meses.
7. Usa **Toda España** o `Esc` para volver desde la ficha a la vista nacional.

El simulador parametrizable en Streamlit se abre con `.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py`. Prueba allí potencia, CAPEX, refrigeración o una subida de luz. Sus indicadores municipales están marcados como demostración sintética.

## Diagnóstico

- El comando `python -m cpd.almacen --publicado` indica la ruta de DuckDB del mismo lote que el mapa.
- Una publicación rechazada mantiene activa la versión anterior. Revisa el mensaje de cobertura y el manifiesto.
- Si el tiempo en directo o la geometría municipal fallan, la ficha conserva los indicadores provinciales y muestra el aviso.
- Las previsiones son escenarios y cada ficha indica sus unidades y periodo. La elegibilidad por parcela requiere datos de emplazamiento.
