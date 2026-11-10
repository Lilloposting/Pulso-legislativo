import { interpolate, useCurrentFrame } from "remotion";
import { color, fuenteTexto } from "../tema";

/** Logo: "PULSO LEGISLATIVO" con una línea de pulso que se dibuja. */
export const Marca: React.FC<{ escala?: number; dibujarDesde?: number }> = ({ escala = 1, dibujarDesde = 0 }) => {
  const frame = useCurrentFrame();
  const largo = 520;
  const avance = interpolate(frame - dibujarDesde, [0, 25], [largo, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 18 * escala, transform: `scale(${escala})` }}>
      <svg width={150} height={60} viewBox="0 0 150 60">
        <path
          d="M0 30 H40 L52 8 L66 52 L80 18 L90 30 H150"
          fill="none"
          stroke={color.rojo}
          strokeWidth={7}
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeDasharray={largo}
          strokeDashoffset={avance}
        />
      </svg>
      <div style={{ fontFamily: fuenteTexto, fontWeight: 800, color: color.blanco, fontSize: 40, letterSpacing: 6, lineHeight: 1 }}>
        PULSO
        <br />
        <span style={{ fontWeight: 400, fontSize: 30, letterSpacing: 8 }}>LEGISLATIVO</span>
      </div>
    </div>
  );
};
