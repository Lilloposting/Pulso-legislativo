import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { color, fuenteTexto } from "../tema";
import type { Palabra } from "../tipos";

const POR_BLOQUE = 5;

/** Subtítulos estilo redes: bloques de pocas palabras, la palabra que suena resaltada. */
export const Subtitulos: React.FC<{ palabras: Palabra[] }> = ({ palabras }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ms = (frame / fps) * 1000;
  if (!palabras.length) return null;

  let actual = palabras.findIndex((p) => ms < p.hasta_ms);
  if (actual === -1) actual = palabras.length - 1;
  if (ms < palabras[0].desde_ms - 150) return null;
  const inicio = Math.floor(actual / POR_BLOQUE) * POR_BLOQUE;
  const bloque = palabras.slice(inicio, inicio + POR_BLOQUE);

  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 260 }}>
      <div
        style={{
          maxWidth: 900,
          textAlign: "center",
          fontFamily: fuenteTexto,
          fontWeight: 800,
          fontSize: 62,
          lineHeight: 1.2,
          color: color.blanco,
          textShadow: "0 4px 18px rgba(0,0,0,.85), 0 0 2px #000",
        }}
      >
        {bloque.map((p, i) => {
          const activa = inicio + i === actual && ms >= p.desde_ms;
          return (
            <span key={i} style={{ color: activa ? color.oro : color.blanco, marginRight: 16 }}>
              {p.censurada ? "***" : p.texto}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
