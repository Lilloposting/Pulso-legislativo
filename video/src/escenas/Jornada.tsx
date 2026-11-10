import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Marca } from "../componentes/Marca";
import { color, fuenteTexto, fuenteTitulos } from "../tema";
import type { Jornada as TJornada, Palabra, Persona } from "../tipos";

const normal = (s: string) => s.toLowerCase().normalize("NFD").replace(/[^a-zñ]/g, "");

/** Frames donde la narradora empieza "todos estos…" (lista de votantes) y el siguiente "estos…" (los que no). */
const marcas = (palabras: Palabra[], fps: number) => {
  const i1 = palabras.findIndex((p) => normal(p.texto) === "todos");
  const i2 = i1 >= 0 ? palabras.findIndex((p, k) => k > i1 + 1 && normal(p.texto) === "estos") : -1;
  const f = (i: number) => (i >= 0 ? Math.round((palabras[i].desde_ms / 1000) * fps) : null);
  return [f(i1), f(i2)] as const;
};

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const Cifra: React.FC<{ valor: string; etiqueta: string; desde: number }> = ({ valor, etiqueta, desde }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - desde, fps, config: { damping: 14 } });
  return (
    <div style={{ opacity: s, transform: `translateY(${(1 - s) * 40}px)`, textAlign: "center" }}>
      <div style={{ fontFamily: fuenteTitulos, fontWeight: 900, fontSize: 120, color: color.blanco, lineHeight: 1 }}>{valor}</div>
      <div style={{ fontFamily: fuenteTexto, fontSize: 34, color: color.gris, marginTop: 10 }}>{etiqueta}</div>
    </div>
  );
};

/** Lista de nombres que pasa rápido (para pausar el video y leerla). */
const Lista: React.FC<{
  titulo: string;
  tono: string;
  personas: Persona[];
  desde: number;
  hasta: number;
  columnas: number;
  nota?: string;
}> = ({ titulo, tono, personas, desde, hasta, columnas, nota }) => {
  const frame = useCurrentFrame();
  const visible = frame >= desde && frame < hasta;
  if (!visible) return null;
  const grande = columnas === 1;
  const alto_fila = grande ? 96 : 62;
  const filas = Math.ceil(personas.length / columnas);
  const altoLista = filas * alto_fila;
  const ventana = 1040;
  const desplazamiento = interpolate(frame, [desde + 10, hasta - 6], [0, Math.max(0, altoLista - ventana)], clamp);
  const entrada = interpolate(frame, [desde, desde + 6], [0, 1], clamp);
  return (
    <AbsoluteFill style={{ padding: "330px 60px 0", opacity: entrada }}>
      <div style={{ fontFamily: fuenteTexto, fontWeight: 800, fontSize: 56, color: tono, letterSpacing: 3 }}>
        {titulo} <span style={{ color: color.blanco }}>({personas.length})</span>
      </div>
      {nota ? <div style={{ fontFamily: fuenteTexto, fontSize: 24, color: color.gris, marginTop: 8 }}>{nota}</div> : null}
      <div style={{ height: ventana, overflow: "hidden", marginTop: 26, borderTop: `4px solid ${tono}` }}>
        <div style={{ transform: `translateY(${-desplazamiento}px)`, display: "grid", gridTemplateColumns: `repeat(${columnas}, minmax(0, 1fr))`, columnGap: 18 }}>
          {personas.map((p, i) => (
            <div key={i} style={{ height: alto_fila, display: "flex", flexDirection: "column", justifyContent: "center", borderBottom: "1px solid rgba(255,255,255,.08)" }}>
              <div style={{ fontFamily: fuenteTexto, fontWeight: 700, fontSize: grande ? 44 : 23, color: color.blanco, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {p.nombre}
              </div>
              <div style={{ fontFamily: fuenteTexto, fontSize: grande ? 28 : 16, color: color.gris, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {p.partido}
                {p.registro ? ` · ${p.registro}` : ""}
              </div>
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const Jornada: React.FC<{ jornada: TJornada; palabras: Palabra[] }> = ({ jornada, palabras }) => {
  const frame = useCurrentFrame();
  const { durationInFrames, fps } = useVideoConfig();
  const c = jornada.camara;
  const [m1, m2] = marcas(palabras, fps);
  const fin1 = m1 ?? Math.round(durationInFrames * 0.3);
  const fin2 = m2 && m2 > fin1 + fps ? m2 : Math.round(fin1 + (durationInFrames - fin1) * 0.5);
  const faltaron = c.asistencia_publicada;
  const segunda = faltaron ? c.lista_ausentes : c.lista_no_votaron;
  const tiempo = c.minutos_en_sala_total
    ? `${c.horas_en_sala} h ${String(c.minutos_en_sala_resto).padStart(2, "0")} min`
    : "0 h";

  return (
    <AbsoluteFill style={{ background: `linear-gradient(180deg, ${color.noche}, ${color.azul})` }}>
      <div style={{ position: "absolute", top: 110, left: 80 }}>
        <Marca escala={0.75} />
      </div>
      <div style={{ position: "absolute", top: 230, width: "100%", textAlign: "center", fontFamily: fuenteTexto, fontWeight: 800, letterSpacing: 8, fontSize: 34, color: color.oro }}>
        ¿CUÁNTO TRABAJARON?
      </div>

      {frame < fin1 ? (
        <AbsoluteFill style={{ justifyContent: "center", gap: 70, paddingBottom: 200 }}>
          <Cifra valor={tiempo} etiqueta="en la Sala de la Cámara" desde={4} />
          <div style={{ display: "flex", justifyContent: "space-around" }}>
            <Cifra valor={String(c.proyectos_votados)} etiqueta="proyectos votados" desde={12} />
            <Cifra valor={String(c.votaciones)} etiqueta="votaciones" desde={18} />
          </div>
          <div style={{ opacity: interpolate(frame, [20, 30], [0, 1], clamp), textAlign: "center", fontFamily: fuenteTexto, color: color.gris, fontSize: 28 }}>
            {c.sesiones.map((s) => `Sesión ${s.numero} (${s.tipo.toLowerCase()}): ${s.inicio}–${s.termino ?? "?"}`).join("  ·  ")}
          </div>
        </AbsoluteFill>
      ) : null}

      <Lista titulo="VOTARON" tono={color.favor} personas={c.lista_votaron} desde={fin1} hasta={fin2} columnas={3} />
      <Lista
        titulo={faltaron ? "FALTARON" : "NO VOTARON"}
        tono={color.contra}
        personas={segunda}
        desde={fin2}
        hasta={durationInFrames}
        columnas={segunda.length > 12 ? 2 : 1}
        nota={faltaron ? "Registro oficial de asistencia de la Cámara" : "No votaron en ninguna votación del día (ausencia, pareo u otra razón: el registro no lo distingue)"}
      />
      <div style={{ position: "absolute", bottom: 90, width: "100%", textAlign: "center", fontFamily: fuenteTexto, color: color.gris, fontSize: 22 }}>
        Fuente: camara.cl · votaciones y sesiones de Sala
      </div>
    </AbsoluteFill>
  );
};
