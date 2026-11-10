import { AbsoluteFill, Audio, Sequence, Series, staticFile } from "remotion";
import { Cahuin } from "./escenas/Cahuin";
import { Jornada } from "./escenas/Jornada";
import { Cierre } from "./escenas/Cierre";
import { Intro } from "./escenas/Intro";
import { Noticia } from "./escenas/Noticia";
import { Subtitulos } from "./componentes/Subtitulos";
import { FPS, VELOCIDAD_VOZ, color } from "./tema";
import { acelerar, duracionEscena } from "./tiempos";
import type { EpisodioProps, Voz } from "./tipos";

/** Voz con los garabatos tapados: silencio en la palabra + pitido encima. */
const VozCensurada: React.FC<{ voz: Voz }> = ({ voz }) => {
  const tapadas = voz.palabras.filter((p) => p.censurada);
  const enPitido = (f: number) => tapadas.some((p) => f >= (p.desde_ms / 1000) * FPS - 1 && f <= (p.hasta_ms / 1000) * FPS + 1);
  return (
    <>
      <Audio src={staticFile(voz.audio)} playbackRate={VELOCIDAD_VOZ} volume={(f) => (enPitido(f) ? 0 : 1)} />
      {tapadas.map((p, i) => (
        <Sequence key={i} from={Math.floor((p.desde_ms / 1000) * FPS) - 1}
          durationInFrames={Math.max(4, Math.ceil(((p.hasta_ms - p.desde_ms) / 1000) * FPS) + 3)}>
          <Audio src={staticFile("pitido.wav")} volume={0.35} />
        </Sequence>
      ))}
    </>
  );
};

export const Episodio: React.FC<EpisodioProps> = (props) => {
  const totalNoticias = props.escenas.filter((e) => e.tipo === "noticia").length;
  const numeroNoticia = (i: number) => props.escenas.slice(0, i + 1).filter((e) => e.tipo === "noticia").length;
  return (
  <AbsoluteFill style={{ backgroundColor: color.noche }}>
    {props.musica ? <Audio src={staticFile(props.musica)} volume={0.12} loop /> : null}
    <Series>
      {props.escenas.map((e, i) => {
        const voz = acelerar(e.voz);
        return (
        <Series.Sequence key={i} durationInFrames={duracionEscena(e)}>
          {e.tipo === "intro" ? (
            <Intro fecha={props.fecha} video={props.introVideo} />
          ) : e.tipo === "jornada" ? (
            <Jornada jornada={e.jornada} palabras={voz.palabras} cues={voz.marcas} />
          ) : e.tipo === "cahuin" ? (
            <Cahuin cahuines={e.cahuines} />
          ) : e.tipo === "noticia" ? (
            <Noticia titular={e.titular} dato={e.dato} indice={numeroNoticia(i)} total={totalNoticias} />
          ) : (
            <Cierre fecha={props.fecha} fuentes={props.fuentes} />
          )}
          <VozCensurada voz={voz} />
          <Subtitulos palabras={voz.palabras} />
        </Series.Sequence>
        );
      })}
    </Series>
  </AbsoluteFill>
);
};
