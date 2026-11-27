# Cuadro de mandos, visualización y casos de prueba · F2 / F4 / F7

## Lectura del mapa

El mapa enseña la clase de rentabilidad del escenario provincial. El ranking presenta los mismos resultados con texto e iconos para que la lectura también funcione con teclado y sin depender del color. La ficha distingue la rentabilidad de las comprobaciones técnicas auditablemente pendientes.

La escala territorial se declara con cada indicador. El precio eléctrico es nacional, varias medidas de energía se publican por CCAA, las reservas son por ámbito hidrográfico y el score visible se calcula por provincia. Los municipios del mapa sirven como contexto territorial.

Las series se muestran al abrir una provincia. El histórico observado y la previsión tienen estilos distintos. Las bandas muestran los cuantiles estimados. Para temperatura a diez años hay diagnóstico por horizonte en el informe generado, con error en °C, sesgo y cobertura observada.

## Tres casos para la demostración

| Caso | Pasos | Evidencia esperada |
|---|---|---|
| **Requisito técnico comprobado** | Abrir Madrid en la publicación de octubre y revisar capacidad de red | Se distingue el motivo del descarte de los supuestos de VAN. |
| **Datos insuficientes** | Abrir Zaragoza y desplegar la auditoría de filtros | Los filtros que requieren datos del emplazamiento aparecen pendientes. El mapa conserva los datos provinciales disponibles. |
| **Sensibilidad económica** | Abrir la luz y comparar base, escenario previsto y equilibrio. Repetir con los controles de Streamlit | El usuario puede ver cómo cambia el resultado y qué variables usa cada escenario. La demo municipal lleva su etiqueta. |

Para grabar el recorrido, empieza en el ranking, realiza los tres casos y termina mostrando el panel fechado y los avisos de la publicación. Documenta en el vídeo el identificador de lote utilizado.
