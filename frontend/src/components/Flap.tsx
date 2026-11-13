import { useEffect, useRef, useState } from "react";
import { useMovimientoReducido } from "./useMovimientoReducido";

const JUEGO = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";

function ajustar(texto: string, largo: number | undefined, alinear: "izq" | "der"): string {
  const t = texto.toUpperCase();
  if (!largo) return t;
  if (t.length >= largo) return t.slice(0, largo);
  return alinear === "der" ? t.padStart(largo) : t.padEnd(largo);
}

interface Props {
  texto: string;
  /** Número fijo de casillas (como un panel real). Sin él, una casilla por carácter. */
  largo?: number;
  alinear?: "izq" | "der";
  /** Texto para lectores de pantalla si difiere del visible. */
  etiqueta?: string;
  /** Retardo antes de girar (ms), para escalonar filas. */
  retardo?: number;
  className?: string;
}

/**
 * Texto de panel split-flap: cada casilla gira por varias letras hasta asentarse en la nueva.
 * Con "reducir movimiento" el cambio es instantáneo.
 */
export function Flap({ texto, largo, alinear = "izq", etiqueta, retardo = 0, className }: Props) {
  const reducir = useMovimientoReducido();
  const destino = ajustar(texto, largo, alinear);
  const [visible, setVisible] = useState(() => (reducir ? destino : " ".repeat(destino.length)));
  const actual = useRef(visible);

  useEffect(() => {
    const poner = (s: string) => {
      actual.current = s;
      setVisible(s);
    };
    if (reducir) {
      poner(destino);
      return;
    }
    const desde = actual.current.padEnd(destino.length).slice(0, destino.length);
    const pasos = [...destino].map((c, i) => (desde[i] === c ? 0 : 2 + ((i * 7 + c.charCodeAt(0)) % 4) + Math.floor(i / 2)));
    if (pasos.every((p) => p === 0)) {
      poner(destino);
      return;
    }
    let tick = 0;
    let intervalo = 0;
    const inicio = window.setTimeout(() => {
      intervalo = window.setInterval(() => {
        tick++;
        const s = [...destino]
          .map((c, i) => {
            const p = pasos[i] ?? 0;
            if (tick >= p) return c;
            if (c === " " && tick >= p - 1) return " ";
            return JUEGO[(tick * 5 + i * 11) % JUEGO.length]!;
          })
          .join("");
        poner(s);
        if (s === destino) window.clearInterval(intervalo);
      }, 55);
    }, retardo);
    return () => {
      window.clearTimeout(inicio);
      window.clearInterval(intervalo);
    };
  }, [destino, reducir, retardo]);

  return (
    <span className={`flap ${className ?? ""}`}>
      <span className="sr-only">{etiqueta ?? texto}</span>
      <span className="flap-celdas" aria-hidden="true">
        {[...visible].map((c, i) => (
          <span className="flap-c" key={i}>
            <span className="flap-g" key={c}>
              {c === " " ? " " : c}
            </span>
          </span>
        ))}
      </span>
    </span>
  );
}
