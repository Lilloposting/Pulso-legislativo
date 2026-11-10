import { AbsoluteFill, Audio, Series, staticFile } from "remotion";
import { Cierre } from "./escenas/Cierre";
import { Intro } from "./escenas/Intro";
import { Noticia } from "./escenas/Noticia";
import { Subtitulos } from "./componentes/Subtitulos";
import { color } from "./tema";
import { duracionEscena } from "./tiempos";
import type { EpisodioProps } from "./tipos";

export const Episodio: React.FC<EpisodioProps> = (props) => (
  <AbsoluteFill style={{ backgroundColor: color.noche }}>
    {props.musica ? <Audio src={staticFile(props.musica)} volume={0.12} loop /> : null}
    <Series>
      {props.escenas.map((e, i) => (
        <Series.Sequence key={i} durationInFrames={duracionEscena(e)}>
          {e.tipo === "intro" ? (
            <Intro fecha={props.fecha} video={props.introVideo} />
          ) : e.tipo === "noticia" ? (
            <Noticia titular={e.titular} dato={e.dato} indice={i} total={props.escenas.length - 2} />
          ) : (
            <Cierre fecha={props.fecha} fuentes={props.fuentes} />
          )}
          <Audio src={staticFile(e.voz.audio)} />
          <Subtitulos palabras={e.voz.palabras} />
        </Series.Sequence>
      ))}
    </Series>
  </AbsoluteFill>
);
