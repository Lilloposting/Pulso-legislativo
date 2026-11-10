import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { color, fuenteTexto, fuenteTitulos } from "../tema";
import type { Cahuin as TCahuin } from "../tipos";

const VOTO: Record<string, string> = { si: "a favor", no: "en contra", abstencion: "abstención" };

const texto = (c: TCahuin) => {
  if (c.tipo === "voto_contra_su_partido")
    return { titulo: c.nombre ?? "", cuerpo: `${c.partido}: votó ${VOTO[c.voto ?? ""] ?? c.voto} y su partido ${VOTO[c.mayoria_del_partido ?? ""] ?? c.mayoria_del_partido}` };
  if (c.tipo === "reserva_de_constitucionalidad")
    return {
      titulo: `${(c.detalle ?? "").replace(/^(El|La) diputad[oa] /, "").replace(/ formula reserva.*$/i, "") || "Reserva de constitucionalidad"}: reserva de constitucionalidad`,
      cuerpo: "Dejó avisado que cree que la ley choca con la Constitución. Así puede pedir después que el Tribunal Constitucional la revise.",
    };
  return { titulo: `${c.cantidad} no votaron`, cuerpo: c.detalle ?? "" };
};

/** "Cahuín del día": solo hechos del registro oficial, en tarjetas estilo farándula. */
export const Cahuin: React.FC<{ cahuines: TCahuin[] }> = ({ cahuines }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const lista = cahuines.filter((c) => c.tipo !== "no_votaron").slice(0, 5);
  const sello = spring({ frame, fps, config: { damping: 8, stiffness: 180 } });
  const paso = Math.max(8, Math.floor((durationInFrames * 0.45) / Math.max(1, lista.length)));
  return (
    <AbsoluteFill style={{ background: `repeating-linear-gradient(135deg, #1a0a0a 0 40px, #240d0d 40px 80px)`, padding: "150px 60px" }}>
      <div
        style={{
          alignSelf: "center",
          background: color.oro,
          color: "#1a0a0a",
          fontFamily: fuenteTitulos,
          fontWeight: 900,
          fontSize: 96,
          padding: "6px 40px",
          transform: `rotate(-4deg) scale(${0.6 + 0.4 * sello})`,
          boxShadow: `12px 12px 0 ${color.rojo}`,
        }}
      >
        OJO CON ESTO
      </div>
      <div style={{ textAlign: "center", fontFamily: fuenteTexto, fontWeight: 800, color: color.blanco, letterSpacing: 6, fontSize: 30, marginTop: 30 }}>
        VOTARON DISTINTO A SU PARTIDO · REGISTRO OFICIAL
      </div>
      <div style={{ marginTop: 60, display: "flex", flexDirection: "column", gap: 26 }}>
        {lista.map((c, i) => {
          const s = spring({ frame: frame - 4 - i * paso, fps, config: { damping: 15, stiffness: 220 } });
          const t = texto(c);
          return (
            <div
              key={i}
              style={{
                opacity: s,
                transform: `translateX(${(1 - s) * (i % 2 ? 300 : -300)}px) rotate(${i % 2 ? 1 : -1}deg)`,
                background: color.blanco,
                borderLeft: `14px solid ${color.rojo}`,
                padding: "22px 30px",
                borderRadius: 6,
              }}
            >
              <div style={{ fontFamily: fuenteTexto, fontWeight: 800, fontSize: 40, color: "#1a0a0a" }}>{t.titulo}</div>
              <div style={{ fontFamily: fuenteTexto, fontSize: 28, color: "#3b2a2a", marginTop: 6 }}>{t.cuerpo}</div>
              {c.boletin ? <div style={{ fontFamily: fuenteTexto, fontSize: 20, color: "#7a6a6a", marginTop: 6 }}>Boletín {c.boletin}</div> : null}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
