import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Hemiciclo } from "../componentes/Hemiciclo";
import { Marca } from "../componentes/Marca";
import { color, fuenteTexto, fuenteTitulos, nombreCamara } from "../tema";
import type { Dato } from "../tipos";

const Barra: React.FC<{ etiqueta: string; valor: number; max: number; tono: string; retraso: number }> = ({
  etiqueta,
  valor,
  max,
  tono,
  retraso,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - retraso, fps, config: { damping: 20, mass: 0.8 } });
  const n = Math.round(valor * s);
  return (
    <div style={{ marginBottom: 34 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontFamily: fuenteTexto, color: color.blanco, fontSize: 40, marginBottom: 12 }}>
        <span style={{ fontWeight: 600 }}>{etiqueta}</span>
        <span style={{ fontWeight: 800 }}>{n}</span>
      </div>
      <div style={{ height: 34, background: "rgba(255,255,255,.08)", borderRadius: 17, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${(max ? valor / max : 0) * 100 * s}%`, background: tono, borderRadius: 17 }} />
      </div>
    </div>
  );
};

const Sello: React.FC<{ texto: string; desde: number; tono: string }> = ({ texto, desde, tono }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - desde, fps, config: { damping: 9, stiffness: 160 } });
  return (
    <div
      style={{
        alignSelf: "center",
        marginTop: 20,
        padding: "14px 48px",
        border: `7px solid ${tono}`,
        borderRadius: 14,
        color: tono,
        fontFamily: fuenteTexto,
        fontWeight: 800,
        fontSize: 64,
        letterSpacing: 8,
        transform: `rotate(-6deg) scale(${interpolate(s, [0, 1], [2.2, 1])})`,
        opacity: s,
      }}
    >
      {texto}
    </div>
  );
};

export const Noticia: React.FC<{ titular: string; dato: Dato; indice: number; total: number }> = ({ titular, dato, indice, total }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const entrada = spring({ frame, fps, config: { damping: 16 } });
  const salida = interpolate(frame, [durationInFrames - 8, durationInFrames], [1, 0], { extrapolateLeft: "clamp" });
  const vp = dato.votacion_principal;
  const resultado = (vp?.resultado ?? "").toUpperCase();
  const tonoSello = resultado.startsWith("RECHAZ") ? color.contra : color.favor;
  const titulo = dato.titulo && dato.titulo.length > 170 ? `${dato.titulo.slice(0, 167)}…` : dato.titulo;

  return (
    <AbsoluteFill style={{ background: `linear-gradient(160deg, ${color.azul}, ${color.noche} 65%)`, opacity: salida }}>
      <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 40 }}>
        <Hemiciclo total={dato.camara === "senado" ? 50 : 155} ancho={1200} opacidad={0.12} />
      </AbsoluteFill>
      <div style={{ position: "absolute", inset: 0, padding: "110px 80px", display: "flex", flexDirection: "column" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Marca escala={0.75} />
          <div style={{ fontFamily: fuenteTexto, color: color.gris, fontSize: 30, fontWeight: 600 }}>
            {indice} / {total}
          </div>
        </div>

        <div style={{ marginTop: 70, transform: `translateX(${(1 - entrada) * 120}px)`, opacity: entrada }}>
          <span style={{ background: color.rojo, color: color.blanco, fontFamily: fuenteTexto, fontWeight: 800, fontSize: 28, letterSpacing: 4, padding: "10px 22px", borderRadius: 8 }}>
            {nombreCamara(dato.camara)}
          </span>
          <div style={{ fontFamily: fuenteTitulos, fontWeight: 900, color: color.blanco, fontSize: 92, lineHeight: 1.05, marginTop: 36 }}>
            {titular}
          </div>
          {titulo ? (
            <div style={{ fontFamily: fuenteTexto, color: color.gris, fontSize: 32, lineHeight: 1.35, marginTop: 26 }}>{titulo}</div>
          ) : null}
        </div>

        <div style={{ marginTop: 60, display: "flex", flexDirection: "column" }}>
          {dato.tipo === "ley_publicada" ? (
            <>
              <Sello texto="NUEVA LEY" desde={12} tono={color.oro} />
              {dato.dias_de_tramitacion ? (
                <div style={{ textAlign: "center", marginTop: 50, fontFamily: fuenteTexto, color: color.blanco }}>
                  <div style={{ fontSize: 150, fontWeight: 800, lineHeight: 1 }}>
                    {Math.round(interpolate(frame, [15, 60], [0, dato.dias_de_tramitacion], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }))}
                  </div>
                  <div style={{ fontSize: 38, color: color.gris }}>días desde que ingresó</div>
                </div>
              ) : null}
            </>
          ) : vp ? (
            <>
              {(() => {
                const max = Math.max(vp.si ?? 0, vp.no ?? 0, vp.abstencion ?? 0);
                return (
                  <>
                    <Barra etiqueta="A favor" valor={vp.si ?? 0} max={max} tono={color.favor} retraso={6} />
                    <Barra etiqueta="En contra" valor={vp.no ?? 0} max={max} tono={color.contra} retraso={9} />
                    <Barra etiqueta="Abstención" valor={vp.abstencion ?? 0} max={max} tono={color.abstencion} retraso={12} />
                  </>
                );
              })()}
              {resultado ? <Sello texto={resultado} desde={Math.round(durationInFrames * 0.3)} tono={tonoSello} /> : null}
              <div style={{ textAlign: "center", fontFamily: fuenteTexto, color: color.gris, fontSize: 28, marginTop: 30 }}>
                {[vp.tipo && `Votación ${vp.tipo.toLowerCase()}`, vp.quorum, vp.tramite].filter(Boolean).join(" · ")}
              </div>
            </>
          ) : null}
        </div>

        <div style={{ marginTop: "auto", fontFamily: fuenteTexto, color: color.gris, fontSize: 26 }}>
          Fuente: senado.cl / camara.cl · Boletín {dato.boletin}
        </div>
      </div>
    </AbsoluteFill>
  );
};
