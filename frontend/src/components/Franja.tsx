import { useEffect, useState } from "react";
import type { Demanda, Mix, Precios } from "../live/redata";
import type { EnVivo } from "../live/usePolling";
import { hora, horaSeg, num, pct } from "../format";
import { Flap } from "./Flap";

interface Props {
  precios: EnVivo<Precios>;
  demanda: EnVivo<Demanda>;
  mix: EnVivo<Mix>;
  sintetico: boolean;
}

function Reloj() {
  const [ahora, setAhora] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setAhora(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);
  return (
    <div className="reloj">
      <Flap texto={horaSeg(ahora)} etiqueta={`Hora peninsular ${horaSeg(ahora)}`} />
      <span>hora peninsular</span>
    </div>
  );
}

/** Una lectura de la línea de teletipo: etiqueta, valor en paletas, unidad y hora del dato. */
function Lectura({ etiqueta, valor, unidad, vivo, momento }: { etiqueta: string; valor: string; unidad: string; vivo: EnVivo<unknown>; momento?: number | null }) {
  const t = momento ?? vivo.actualizado;
  return (
    <span className="teletipo-dato">
      <span className="teletipo-et">{etiqueta}</span>
      {vivo.cargando && !vivo.datos ? (
        <span className="cargando">cargando…</span>
      ) : vivo.error && !vivo.datos ? (
        <span className="teletipo-error">— sin conexión</span>
      ) : (
        <>
          <Flap texto={valor} />
          {unidad && <span className="cifra-unidad">{unidad}</span>}
          {t && <span className="teletipo-hora">{hora(t)}</span>}
        </>
      )}
    </span>
  );
}

export function Franja({ precios, demanda, mix, sintetico }: Props) {
  const pr = precios.datos;
  return (
    <header className="franja">
      <div className="marca">
        <span className="marca-sigla" aria-hidden="true">
          CPD
        </span>
        <div>
          <h1>¿Dónde construir un centro de datos en España?</h1>
          <p>Viabilidad y rentabilidad de un CPD, provincia a provincia</p>
        </div>
      </div>
      <Reloj />
      {sintetico && (
        <p className="sello" title="Los indicadores municipales del modelo son sintéticos. Los datos en directo y los límites geográficos son reales.">
          Datos de demostración
        </p>
      )}
      <div className="teletipo" role="group" aria-label="Red eléctrica en directo: datos nacionales del sistema peninsular">
        <span className="teletipo-sello">
          <i aria-hidden="true" />
          En directo · Red Eléctrica · nacional
        </span>
        <Lectura etiqueta="Luz spot" valor={num(pr?.spotAhora?.v, 1)} unidad="€/MWh" vivo={precios} momento={pr?.spotAhora?.t} />
        <Lectura etiqueta="Media hoy" valor={num(pr?.spotMediaHoy, 1)} unidad="€/MWh" vivo={precios} />
        <Lectura etiqueta="Demanda" valor={num(demanda.datos?.ahora?.v)} unidad="MW" vivo={demanda} momento={demanda.datos?.ahora?.t} />
        <Lectura etiqueta="Renovable ayer" valor={pct(mix.datos?.renovableAyer?.v)} unidad="" vivo={mix} />
      </div>
    </header>
  );
}
