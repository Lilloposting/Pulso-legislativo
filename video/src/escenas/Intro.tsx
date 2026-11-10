import {
  AbsoluteFill,
  Easing,
  OffthreadVideo,
  interpolate,
  random,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Hemiciclo } from "../componentes/Hemiciclo";
import { Marca } from "../componentes/Marca";
import { color, fuenteTexto, fuenteTitulos } from "../tema";
import { fechaLarga } from "../tiempos";

const PUERTA = { x: 540, y: 1360 }; // punto hacia donde avanza la cámara

/** Bandera chilena flameando: se corta en franjas verticales que ondulan. */
const Bandera: React.FC<{ x: number; y: number; ancho: number; frame: number }> = ({ x, y, ancho, frame }) => {
  const alto = (ancho * 2) / 3;
  const franjas = 24;
  const w = ancho / franjas;
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect x={-6} y={0} width={6} height={alto * 2.6} fill="#cfd6e6" />
      {Array.from({ length: franjas }, (_, i) => {
        const dy = Math.sin(frame / 6 - i / 3) * (i / franjas) * 14;
        return (
          <svg key={i} x={i * w} y={dy} width={w + 2} height={alto} viewBox={`${i * w} 0 ${w + 2} ${alto}`} shapeRendering="crispEdges">
            <rect x={0} y={alto / 2} width={ancho} height={alto / 2} fill={color.rojo} />
            <rect x={0} y={0} width={ancho} height={alto / 2} fill={color.blanco} />
            <rect x={0} y={0} width={ancho / 3} height={alto / 2} fill="#0039a6" />
            <polygon
              transform={`translate(${ancho / 6} ${alto / 4}) scale(${alto / 14})`}
              points="0,-1 0.2245,-0.309 0.951,-0.309 0.363,0.118 0.588,0.809 0,0.382 -0.588,0.809 -0.363,0.118 -0.951,-0.309 -0.2245,-0.309"
              fill={color.blanco}
            />
          </svg>
        );
      })}
    </g>
  );
};

/** Fachada del Congreso (estilizada, no es una réplica del edificio real). */
const Fachada: React.FC<{ frame: number; apertura: number }> = ({ frame, apertura }) => {
  const columnas = 8;
  return (
    <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{ position: "absolute" }}>
      <defs>
        <linearGradient id="muro" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#d9d4c7" />
          <stop offset="100%" stopColor="#8f8a7f" />
        </linearGradient>
        <radialGradient id="luzPuerta" cx="50%" cy="60%" r="60%">
          <stop offset="0%" stopColor="#fff4cf" />
          <stop offset="100%" stopColor="#e8c46a" stopOpacity={0} />
        </radialGradient>
      </defs>
      {/* frontón y cúpula */}
      <ellipse cx={540} cy={860} rx={170} ry={150} fill="#b9b3a5" />
      <rect x={390} y={850} width={300} height={70} fill="#a39d90" />
      <Bandera x={540} y={560} ancho={150} frame={frame} />
      <polygon points="120,1000 540,860 960,1000" fill="url(#muro)" stroke="#6f6a60" strokeWidth={4} />
      <rect x={120} y={1000} width={840} height={40} fill="#c9c3b5" />
      {/* columnas */}
      {Array.from({ length: columnas }, (_, i) => {
        const x = 160 + i * (760 / (columnas - 1));
        if (i === 3 || i === 4) return null; // espacio de la puerta
        return (
          <g key={i}>
            <rect x={x - 26} y={1040} width={52} height={380} fill="url(#muro)" />
            <rect x={x - 34} y={1040} width={68} height={18} fill="#e6e1d4" />
            <rect x={x - 34} y={1402} width={68} height={18} fill="#e6e1d4" />
          </g>
        );
      })}
      {/* ventanas encendidas */}
      {[230, 340, 740, 850].map((x) => (
        <rect key={x} x={x - 22} y={1150} width={44} height={110} rx={22} fill={color.oro} opacity={0.55 + 0.2 * Math.sin(frame / 9 + x)} />
      ))}
      {/* puerta: la luz aparece al abrirse */}
      <rect x={440} y={1150} width={200} height={270} fill="url(#luzPuerta)" opacity={apertura} />
      <rect x={440 - apertura * 95} y={1150} width={100} height={270} fill="#5e391f" stroke="#3b2414" strokeWidth={4} />
      <rect x={540 + apertura * 95} y={1150} width={100} height={270} fill="#5e391f" stroke="#3b2414" strokeWidth={4} />
      {/* escalinata */}
      {Array.from({ length: 6 }, (_, i) => (
        <rect key={i} x={100 - i * 30} y={1420 + i * 28} width={880 + i * 60} height={28} fill={i % 2 ? "#a7a194" : "#bdb7aa"} />
      ))}
      <rect x={0} y={1588} width={1080} height={332} fill="#1b2235" />
    </svg>
  );
};

export const Intro: React.FC<{ fecha: string; video?: string }> = ({ fecha, video }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const corte = Math.round(durationInFrames * 0.4); // momento en que cruzamos la puerta

  if (video) {
    return (
      <AbsoluteFill>
        <OffthreadVideo src={staticFile(video)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        <Titulo fecha={fecha} desde={Math.round(durationInFrames * 0.35)} />
      </AbsoluteFill>
    );
  }

  // --- exterior: la cámara avanza hacia la puerta
  const avance = interpolate(frame, [0, corte], [0, 1], { extrapolateRight: "clamp", easing: Easing.in(Easing.cubic) });
  const escala = 1 + 3.2 * avance;
  const apertura = interpolate(frame, [corte * 0.45, corte * 0.85], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const destello = interpolate(frame, [corte - 8, corte, corte + 10], [0, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  // --- interior: travelling sobre la sala
  const t = frame - corte;
  const dolly = interpolate(t, [0, durationInFrames - corte], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.quad) });

  return (
    <AbsoluteFill style={{ background: `linear-gradient(${color.noche}, ${color.azul} 70%, #1b2235)` }}>
      {frame < corte ? (
        <AbsoluteFill style={{ transform: `scale(${escala})`, transformOrigin: `${PUERTA.x}px ${PUERTA.y}px` }}>
          {Array.from({ length: 70 }, (_, i) => (
            <div
              key={i}
              style={{
                position: "absolute",
                left: random(`x${i}`) * 1080,
                top: random(`y${i}`) * 820,
                width: 3,
                height: 3,
                borderRadius: 3,
                background: color.blanco,
                opacity: 0.3 + 0.7 * Math.abs(Math.sin(frame / 12 + i)),
              }}
            />
          ))}
          <Fachada frame={frame} apertura={apertura} />
        </AbsoluteFill>
      ) : (
        <AbsoluteFill style={{ perspective: 1400, alignItems: "center", justifyContent: "center", background: "radial-gradient(circle at 50% 30%, #1d3f8f, #061433 70%)" }}>
          <div
            style={{
              transform: `translateY(${interpolate(dolly, [0, 1], [380, 120])}px) rotateX(${interpolate(dolly, [0, 1], [62, 48])}deg) scale(${interpolate(dolly, [0, 1], [1.5, 1.05])})`,
              transformOrigin: "50% 0%",
            }}
          >
            <Hemiciclo total={155} encendido={t} ancho={1060} />
          </div>
          <Titulo fecha={fecha} desde={8} relativo={t} />
        </AbsoluteFill>
      )}
      <AbsoluteFill style={{ background: "#fff8e1", opacity: destello }} />
      {frame < corte ? (
        <div style={{ position: "absolute", top: 120, width: "100%", display: "flex", justifyContent: "center", opacity: interpolate(frame, [0, 15], [0, 1]) }}>
          <Marca escala={1.1} />
        </div>
      ) : null}
    </AbsoluteFill>
  );

  function Titulo({ fecha, desde, relativo }: { fecha: string; desde: number; relativo?: number }) {
    const f = relativo ?? frame;
    const s = spring({ frame: f - desde, fps, config: { damping: 14 } });
    return (
      <AbsoluteFill style={{ alignItems: "center", paddingTop: 210 }}>
        <div style={{ transform: `translateY(${(1 - s) * -60}px)`, opacity: s, textAlign: "center" }}>
          <div style={{ fontFamily: fuenteTexto, fontWeight: 800, letterSpacing: 10, color: color.oro, fontSize: 34 }}>
            HOY EN EL CONGRESO
          </div>
          <div style={{ fontFamily: fuenteTitulos, fontWeight: 900, color: color.blanco, fontSize: 84, marginTop: 18, lineHeight: 1.05 }}>
            {fechaLarga(fecha)}
          </div>
          <div style={{ height: 8, width: 220 * s, background: color.rojo, margin: "34px auto 0", borderRadius: 4 }} />
        </div>
      </AbsoluteFill>
    );
  }
};
