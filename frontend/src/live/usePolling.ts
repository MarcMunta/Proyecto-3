import { useCallback, useEffect, useRef, useState } from "react";

export interface EnVivo<T> {
  datos: T | null;
  error: string | null;
  cargando: boolean;
  /** Momento de la última respuesta correcta. */
  actualizado: number | null;
  reintentar: () => void;
}

/**
 * Pide datos al montar y cada `cadaMs`. Se pausa con la pestaña oculta y refresca al volver.
 * Si una actualización falla, conserva el último dato bueno y expone el error.
 */
export function usePolling<T>(pedir: (signal: AbortSignal) => Promise<T>, cadaMs: number): EnVivo<T> {
  const [estado, setEstado] = useState<Omit<EnVivo<T>, "reintentar">>({
    datos: null,
    error: null,
    cargando: true,
    actualizado: null,
  });
  const pedirRef = useRef(pedir);
  pedirRef.current = pedir;
  const controlRef = useRef<AbortController | null>(null);

  const ejecutar = useCallback(async () => {
    controlRef.current?.abort();
    const control = new AbortController();
    controlRef.current = control;
    setEstado((e) => ({ ...e, cargando: true }));
    try {
      const datos = await pedirRef.current(control.signal);
      if (!control.signal.aborted) setEstado({ datos, error: null, cargando: false, actualizado: Date.now() });
    } catch (err) {
      if (control.signal.aborted) return;
      const crudo = err instanceof Error ? err.message : String(err);
      // "Failed to fetch" / "NetworkError…" son los mensajes del navegador cuando no hay respuesta.
      const mensaje = !crudo || /failed to fetch|networkerror|load failed/i.test(crudo) ? "sin respuesta de la red" : crudo;
      setEstado((e) => ({ ...e, error: mensaje, cargando: false }));
    }
  }, []);

  useEffect(() => {
    void ejecutar();
    const id = window.setInterval(() => {
      if (!document.hidden) void ejecutar();
    }, cadaMs);
    const alVolver = () => {
      if (!document.hidden) void ejecutar();
    };
    document.addEventListener("visibilitychange", alVolver);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", alVolver);
      controlRef.current?.abort();
    };
  }, [ejecutar, cadaMs]);

  return { ...estado, reintentar: ejecutar };
}
