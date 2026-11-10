import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { color, fuenteTexto } from "../tema";
import type { Palabra } from "../tipos";

const MAX_PALABRAS = 4;
const MAX_LETRAS = 26;

/** Agrupa palabras en bloques cortos que terminan en una pausa natural (punto, coma) o al llenarse. */
const bloques = (palabras: Palabra[]): Palabra[][] => {
  const out: Palabra[][] = [];
  let actual: Palabra[] = [];
  for (const p of palabras) {
    const letras = actual.reduce((n, x) => n + x.texto.length + 1, 0) + p.texto.length;
    if (actual.length && (actual.length >= MAX_PALABRAS || letras > MAX_LETRAS)) {
      out.push(actual);
      actual = [];
    }
    actual.push(p);
    if (p.fin_frase) {
      out.push(actual);
      actual = [];
    }
  }
  if (actual.length) out.push(actual);
  return out;
};

/** Subtítulos estilo redes: bloques de pocas palabras, la palabra que suena resaltada. */
export const Subtitulos: React.FC<{ palabras: Palabra[] }> = ({ palabras }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ms = (frame / fps) * 1000;
  const grupos = bloques(palabras);
  const i = grupos.findIndex((g, k) => {
    const desde = g[0].desde_ms - 120;
    const siguiente = grupos[k + 1]?.[0].desde_ms - 120;
    const hasta = Math.min(siguiente ?? Infinity, g[g.length - 1].hasta_ms + 700);
    return ms >= desde && ms < hasta;
  });
  if (i < 0) return null;

  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 260 }}>
      <div
        style={{
          maxWidth: 940,
          textAlign: "center",
          fontFamily: fuenteTexto,
          fontWeight: 800,
          fontSize: 66,
          lineHeight: 1.2,
          color: color.blanco,
          textShadow: "0 4px 18px rgba(0,0,0,.85), 0 0 2px #000",
        }}
      >
        {grupos[i].map((p, k) => {
          const activa = ms >= p.desde_ms && ms < p.hasta_ms + 80;
          return (
            <span key={k} style={{ color: activa ? color.oro : color.blanco, marginRight: 16 }}>
              {p.censurada ? "***" : p.texto}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
