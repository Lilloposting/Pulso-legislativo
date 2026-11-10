import { interpolate } from "remotion";
import { color } from "../tema";

type Asiento = { x: number; y: number; fila: number; orden: number };

/** Asientos de una sala en semicírculo (vista en planta). 155 = Cámara, 50 = Senado. */
export const asientos = (total: number, filas: number, radio0: number, paso: number): Asiento[] => {
  const largos = Array.from({ length: filas }, (_, f) => radio0 + f * paso);
  const sumaLargos = largos.reduce((a, b) => a + b, 0);
  const out: Asiento[] = [];
  let orden = 0;
  largos.forEach((r, f) => {
    const n = f === filas - 1 ? total - out.length : Math.round((total * r) / sumaLargos);
    for (let i = 0; i < n; i++) {
      // de 15° a 165°: la mesa (testera) queda al centro, arriba
      const ang = (Math.PI * (15 + (150 * (i + 0.5)) / n)) / 180;
      out.push({ x: Math.cos(ang) * r, y: Math.sin(ang) * r, fila: f, orden: orden++ });
    }
  });
  return out;
};

/** Dibuja la sala. `encendido` (frames desde que empieza a iluminarse) anima una ola de luz por los asientos. */
export const Hemiciclo: React.FC<{
  total?: number;
  encendido?: number;
  ancho?: number;
  opacidad?: number;
}> = ({ total = 155, encendido = 1000, ancho = 1000, opacidad = 1 }) => {
  const filas = total > 60 ? 8 : 4;
  const radio0 = total > 60 ? 170 : 220;
  const paso = total > 60 ? 42 : 60;
  const lista = asientos(total, filas, radio0, paso);
  const rmax = radio0 + paso * (filas - 1) + 40;
  return (
    <svg width={ancho} height={(ancho * (rmax + 60)) / (2 * rmax)} viewBox={`${-rmax} -60 ${2 * rmax} ${rmax + 60}`} style={{ opacity: opacidad }}>
      <defs>
        <radialGradient id="piso" cx="50%" cy="0%" r="100%">
          <stop offset="0%" stopColor="#1d3f8f" />
          <stop offset="100%" stopColor={color.noche} />
        </radialGradient>
      </defs>
      <path d={`M ${-rmax} 0 A ${rmax} ${rmax} 0 0 0 ${rmax} 0 Z`} fill="url(#piso)" />
      {/* testera */}
      <rect x={-110} y={-50} width={220} height={60} rx={8} fill="#7a4b2a" stroke={color.oro} strokeWidth={3} />
      <rect x={-20} y={-90} width={40} height={40} rx={4} fill="#5e391f" />
      {lista.map((a) => {
        const t = encendido - (a.orden % 40) * 0.6 - a.fila * 3;
        const luz = interpolate(t, [0, 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        return (
          <g key={a.orden} transform={`translate(${a.x} ${a.y})`}>
            <rect x={-11} y={-9} width={22} height={18} rx={5} fill={luz > 0.5 ? color.azulClaro : "#152a5c"} opacity={0.35 + 0.65 * luz} />
            <circle r={4} cy={-14} fill={color.blanco} opacity={luz * 0.9} />
          </g>
        );
      })}
    </svg>
  );
};
