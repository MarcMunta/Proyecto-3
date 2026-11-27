import type { Prediccion } from "../data/prediccion";
import type { EvaluacionModelo, Previsiones } from "../data/previsiones";
import { num } from "../format";

const FORMULA_WAPE = "WAPE = 100 × Σ |real − previsto| ÷ Σ |real|";
const FORMULA_CLASIFICACION = "Acierto = 100 × número de clasificaciones correctas ÷ número de casos";
const porcentaje = (valor: number | null) => valor === null ? "—" : num(valor, 1) + " %";
const METODOS: Record<string, string> = {
  estructural_demanda: "Estima el precio a partir del gas, la generación renovable y la demanda eléctrica.",
  estructural_gas_tiempo: "Estima el precio a partir del gas y de la generación eólica, solar e hidráulica.",
  ets: "Suaviza el nivel, la tendencia y la estacionalidad de la serie histórica.",
  ets_5_anios: "Ajusta el suavizado exponencial a los últimos cinco años.",
  ets_5_anios_sin_tendencia: "Ajusta el nivel y la estacionalidad de los últimos cinco años.",
  ets_5_anios_log: "Aplica suavizado exponencial al logaritmo de la serie de los últimos cinco años.",
  ets_dias_habiles: "Prevé la cifra por día hábil y la multiplica por los días hábiles de cada mes.",
  ets_5_anios_sin_tendencia_dias_habiles: "Ajusta la estacionalidad por día hábil en cinco años y vuelve a escalar al mes.",
  estacional: "Utiliza el valor del mismo mes del año anterior.",
  ridge: "Ajusta una regresión regularizada con el historial y el calendario.",
  ridge_anomalias: "Estima desviaciones respecto al patrón estacional con información de los embalses.",
  anomalia_persistente: "Ajusta el patrón mensual con la desviación reciente y su persistencia.",
  anomalia_por_cuenca: "Ajusta la persistencia de la desviación mensual por cuenca.",
  anomalia_por_provincia: "Ajusta la persistencia de la desviación mensual por provincia.",
  anomalia_por_comunidad: "Ajusta la persistencia de la desviación mensual por comunidad.",
  climatologia: "Usa el patrón mensual medio del historial.",
  tecnologias_hidro_embalses: "Suma las previsiones por tecnología y ajusta la hidráulica con las reservas.",
  suma_tecnologias: "Suma las previsiones independientes de cada tecnología renovable.",
  holt_amortiguado: "Extrapola una tendencia que pierde peso al avanzar el horizonte.",
  tendencia_lineal: "Proyecta mediante una recta ajustada a la serie histórica.",
  media_10_anios: "Mantiene la media de los últimos diez años.",
  media_larga: "Mantiene la media de la serie histórica.",
  sin_cambio: "Mantiene el último valor anual observado.",
};

function diferenciaWape(valor: number | null): string | null {
  return valor === null ? null : "100 % − " + porcentaje(100 - valor) + " = " + porcentaje(valor);
}

/** Aclara la magnitud evaluada en las filas que agregan o encadenan varios cálculos. */
function magnitudEvaluada(modelo: string): string | null {
  if (modelo.startsWith("Precio de la luz") && modelo.includes("media de 12 meses"))
    return "Se promedian los 12 precios mensuales reales y los 12 previstos antes de medir el error.";
  if (modelo.startsWith("Precio de la luz"))
    return "Se compara mes a mes el precio spot nacional observado con el previsto.";
  if (modelo.startsWith("Generación renovable") && modelo.includes("total"))
    return "Se suman los MWh de 12 meses antes de comparar lo real con lo previsto.";
  if (modelo.startsWith("Renovables por comunidad"))
    return "Cuota renovable = 100 × generación renovable ÷ generación total.";
  if (modelo.startsWith("Reservas de agua") && modelo.includes("media de la década"))
    return "Se comparan las reservas medias de los 10 años reales y previstos.";
  if (modelo.startsWith("Operación del CPD") && modelo.includes("consumo"))
    return "Consumo anual (MWh) = potencia TI (MW) × factor de carga × PUE estimado con la temperatura × horas del año.";
  if (modelo.startsWith("Operación del CPD") && modelo.includes("emisiones"))
    return "Emisiones = consumo × fracción no renovable × factor de emisión.";
  if (modelo.startsWith("Impacto eléctrico local"))
    return "Impacto = 100 × consumo del CPD ÷ demanda eléctrica de su comunidad.";
  if (modelo.startsWith("Atracción empresarial") && modelo.includes("total anual"))
    return "Se suman las constituciones de sociedades de los 12 meses antes de medir el error.";
  if (modelo.startsWith("Presencia actual de CPD"))
    return "Se evalúa si la provincia ya tiene un CPD. Cada pliegue deja una comunidad autónoma completa fuera.";
  if (modelo.startsWith("Riesgo sísmico"))
    return "La etiqueta indica si se registró al menos un terremoto de magnitud 3 o superior al año siguiente.";
  return null;
}

function DetalleEvaluacion({ fila, previsiones, prediccion }: {
  fila: EvaluacionModelo; previsiones: Previsiones; prediccion: Prediccion | undefined;
}) {
  const wape = /WAPE/i.test(fila.definicion ?? "");
  const clasificacion = /accuracy/i.test(fila.definicion ?? "");
  const temperatura = fila.modelo.startsWith("Temperatura");
  const magnitud = magnitudEvaluada(fila.modelo);
  const precio = fila.modelo.startsWith("Precio de la luz") ? previsiones.precio : null;
  const tempCorta = temperatura && fila.modelo.includes("a 1 año") ? previsiones.temperatura.values().next().value : undefined;
  const tempLarga = temperatura && fila.modelo.includes("a 10 años") ? previsiones.medioPlazo.values().next().value : undefined;
  const clasificador = fila.modelo.startsWith("Presencia actual de CPD") ? prediccion?.modelos?.prob_cpd : undefined;
  const metodo = fila.metodo?.nombre ?? clasificador?.modelo;
  const miembros = fila.metodo?.miembros ?? [];
  const combinado = metodo === "combinacion" && miembros.length > 0;
  return (
    <div className="modelo-detalle">
      {combinado ? (
        <>
          <p><strong>Previsión combinada</strong> = suma de las {miembros.length} previsiones ÷ {miembros.length}.</p>
          <ul className="modelo-metodos">
            {miembros.map((nombre) => (
              <li key={nombre}><strong>{nombre.replaceAll("_", " ")}</strong>{METODOS[nombre] && <> · {METODOS[nombre]}</>}</li>
            ))}
          </ul>
        </>
      ) : metodo && <p>Método elegido <strong>{metodo.replaceAll("_", " ")}</strong>{METODOS[metodo] && <> · {METODOS[metodo]}</>}</p>}
      {magnitud && <p>{magnitud}</p>}
      {fila.definicion && <p>Evaluación · {fila.definicion}</p>}
      {wape && (
        <>
          <p className="modelo-formula">{FORMULA_WAPE}</p>
          <dl className="modelo-operaciones">
            {fila.aciertoValidacion !== null && <div><dt>Validación</dt><dd>{diferenciaWape(fila.aciertoValidacion)}</dd></div>}
            {fila.aciertoTest !== null && <div><dt>Prueba</dt><dd>{diferenciaWape(fila.aciertoTest)}</dd></div>}
          </dl>
        </>
      )}
      {clasificacion && <p className="modelo-formula">{FORMULA_CLASIFICACION}</p>}
      {precio?.errorTest != null && fila.modelo.includes("a 1 año") && (
        <p>MAE mensual en la evaluación retrospectiva · <strong>{num(precio.errorTest, 1)} €/MWh</strong>.</p>
      )}
      {temperatura && <p>El 100 − WAPE en °C depende de la escala. El MAE mide el error en grados.</p>}
      {tempCorta?.errorTest != null && <p>MAE en prueba · <strong>{num(tempCorta.errorTest, 2)} °C</strong> al mes.</p>}
      {tempLarga?.maeTemperaturaFinal != null && (
        <p>Décimo año de prueba · MAE <strong>{num(tempLarga.maeTemperaturaFinal, 2)} °C</strong>
          {tempLarga.coberturaTemperaturaFinalPct != null && <> · cobertura observada de la banda <strong>{porcentaje(tempLarga.coberturaTemperaturaFinalPct)}</strong></>}.</p>
      )}
      {clasificador?.roc_auc != null && <p>ROC-AUC con validación geográfica · <strong>{num(clasificador.roc_auc, 3)}</strong>.</p>}
      {fila.aciertoTest === null && <p>No hay un resultado de prueba separado publicado.</p>}
    </div>
  );
}

/** Resultados de prueba del modelo completo. Las salidas del territorio se muestran en su ficha. */
export function EvaluacionesModelos({ filas, previsiones, prediccion }: {
  filas: EvaluacionModelo[]; previsiones: Previsiones; prediccion?: Prediccion;
}) {
  if (!filas.length) return null;
  return (
    <>
      <div className="modelo-columnas modelo-cabecera" aria-hidden="true">
        <span>Modelo</span><span>Validación</span><span>Prueba</span>
      </div>
      {filas.map((fila) => (
        <details className="modelo-fila" key={fila.modelo}>
          <summary className="modelo-columnas">
            <span className="modelo-nombre">{fila.modelo}<small>{fila.estado}</small></span>
            <span className="modelo-cifra"><span className="sr-only">Validación </span>{porcentaje(fila.aciertoValidacion)}</span>
            <span className="modelo-cifra"><span className="sr-only">Prueba </span>{porcentaje(fila.aciertoTest)}</span>
          </summary>
          <DetalleEvaluacion fila={fila} previsiones={previsiones} prediccion={prediccion} />
        </details>
      ))}
    </>
  );
}

