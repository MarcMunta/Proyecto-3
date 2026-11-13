import { useSyncExternalStore } from "react";

const consulta = "(prefers-reduced-motion: reduce)";

function suscribir(aviso: () => void) {
  const mq = window.matchMedia(consulta);
  mq.addEventListener("change", aviso);
  return () => mq.removeEventListener("change", aviso);
}

export function useMovimientoReducido(): boolean {
  return useSyncExternalStore(
    suscribir,
    () => window.matchMedia(consulta).matches,
    () => false,
  );
}
