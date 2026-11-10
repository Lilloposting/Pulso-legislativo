import { FPS, MARGEN_ESCENA, MIN_INTRO, VELOCIDAD_VOZ } from "./tema";
import type { Escena, Voz } from "./tipos";

/** Tiempos de la voz en el reloj del video (cuando el audio se reproduce acelerado). */
export const acelerar = (v: Voz): Voz => {
  const k = 1 / VELOCIDAD_VOZ;
  return {
    ...v,
    duracion_ms: v.duracion_ms * k,
    palabras: v.palabras.map((p) => ({ ...p, desde_ms: p.desde_ms * k, hasta_ms: p.hasta_ms * k })),
    marcas: v.marcas ? Object.fromEntries(Object.entries(v.marcas).map(([n, ms]) => [n, ms * k])) : v.marcas,
  };
};

export const duracionEscena = (e: Escena) => {
  const voz = Math.ceil((acelerar(e.voz).duracion_ms / 1000) * FPS) + MARGEN_ESCENA;
  if (e.tipo === "intro") return Math.max(voz, MIN_INTRO);
  if (e.tipo === "noticia") return Math.max(voz, 3 * FPS);
  if (e.tipo === "jornada") return Math.max(voz, 5 * FPS);
  if (e.tipo === "cahuin") return Math.max(voz, 3 * FPS);
  return Math.max(voz, Math.round(2.5 * FPS));
};

/** "2026-11-09" -> "lunes 9 de noviembre de 2026" */
export const fechaLarga = (iso: string) => {
  const d = new Date(`${iso}T12:00:00`);
  const s = d.toLocaleDateString("es-CL", { weekday: "long", day: "numeric", month: "long", year: "numeric" }).replace(",", "");
  return s.charAt(0).toUpperCase() + s.slice(1);
};
