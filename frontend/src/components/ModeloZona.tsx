import { useState, type ReactNode } from "react";
import type { Prediccion } from "../data/prediccion";
import type { Previsiones } from "../data/previsiones";
import { EvaluacionesModelos } from "./EvaluacionesModelos";

interface Props {
  titulo: string;
  alcance: string;
  cifra?: string;
  aviso?: string;
  previsiones: Previsiones | null;
  prediccion: Prediccion;
  evaluaciones?: string[];
  children: ReactNode;
}

/** Mantiene visible la cifra del territorio y carga el detalle al desplegar la fila. */
export function ModeloZona({ titulo, alcance, cifra, aviso, previsiones, prediccion, evaluaciones = [], children }: Props) {
  const [abierto, setAbierto] = useState(false);
  const filas = abierto && previsiones
    ? previsiones.control.filter((fila) => evaluaciones.some((prefijo) => fila.modelo.startsWith(prefijo)))
    : [];

  return (
    <details className="modelo-fila modelo-zona" onToggle={(evento) => setAbierto(evento.currentTarget.open)}>
      <summary>
        <span className="modelo-zona-nombre">
          <strong>{titulo}</strong>
          <small>{alcance}</small>
        </span>
        {cifra && <span className="modelo-zona-cifra">{cifra}</span>}
        {aviso && <span className="modelo-zona-aviso">{aviso}</span>}
      </summary>
      {abierto && (
        <div className="modelo-zona-detalle">
          {children}
          {previsiones && filas.length > 0 && (
            <div className="evaluaciones-zona">
              <p className="dato-linea"><b>Evaluación general del modelo</b></p>
              <EvaluacionesModelos filas={filas} previsiones={previsiones} prediccion={prediccion} />
            </div>
          )}
        </div>
      )}
    </details>
  );
}
