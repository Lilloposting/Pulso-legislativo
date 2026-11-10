import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Hemiciclo } from "../componentes/Hemiciclo";
import { Marca } from "../componentes/Marca";
import { color, fuenteTexto, fuenteTitulos } from "../tema";
import { fechaLarga } from "../tiempos";

export const Cierre: React.FC<{ fecha: string; fuentes: string[] }> = ({ fecha, fuentes }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 14 } });
  return (
    <AbsoluteFill style={{ background: `radial-gradient(circle at 50% 40%, ${color.azul}, ${color.noche} 70%)`, alignItems: "center", justifyContent: "center" }}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 380 }}>
        <Hemiciclo total={155} encendido={frame * 2} ancho={980} opacidad={0.35} />
      </AbsoluteFill>
      <div style={{ transform: `scale(${0.8 + 0.2 * s})`, opacity: s, display: "flex", flexDirection: "column", alignItems: "center", marginTop: -420 }}>
        <Marca escala={1.6} dibujarDesde={4} />
        <div style={{ fontFamily: fuenteTitulos, fontWeight: 900, fontSize: 76, color: color.blanco, marginTop: 70, textAlign: "center", lineHeight: 1.1 }}>
          Sigue el pulso
          <br />
          del Congreso
        </div>
        <div style={{ fontFamily: fuenteTexto, fontSize: 32, color: color.gris, marginTop: 40, textAlign: "center", lineHeight: 1.5 }}>
          {fuentes.length} {fuentes.length === 1 ? "fuente oficial" : "fuentes oficiales"} en la descripción
          <br />
          <span>{fechaLarga(fecha)}</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
