import { FPS, MARGEN_ESCENA, MIN_INTRO } from "./tema";
import type { Escena } from "./tipos";

export const duracionEscena = (e: Escena) => {
  const voz = Math.ceil((e.voz.duracion_ms / 1000) * FPS) + MARGEN_ESCENA;
  if (e.tipo === "intro") return Math.max(voz, MIN_INTRO);
  if (e.tipo === "noticia") return Math.max(voz, 4 * FPS);
  return Math.max(voz, 3 * FPS);
};

/** "2026-11-09" -> "lunes 9 de noviembre de 2026" */
export const fechaLarga = (iso: string) => {
  const d = new Date(`${iso}T12:00:00`);
  const s = d.toLocaleDateString("es-CL", { weekday: "long", day: "numeric", month: "long", year: "numeric" }).replace(",", "");
  return s.charAt(0).toUpperCase() + s.slice(1);
};
