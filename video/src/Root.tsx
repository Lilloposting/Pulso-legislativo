import { CalculateMetadataFunction, Composition } from "remotion";
import { Episodio } from "./Episodio";
import { ANCHO, ALTO, FPS } from "./tema";
import { duracionEscena } from "./tiempos";
import type { EpisodioProps } from "./tipos";
import ejemplo from "./ejemplo.json";

const calcular: CalculateMetadataFunction<EpisodioProps> = ({ props }) => ({
  durationInFrames: props.escenas.reduce((t, e) => t + duracionEscena(e), 0),
});

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Episodio"
    component={Episodio}
    width={ANCHO}
    height={ALTO}
    fps={FPS}
    durationInFrames={FPS * 30}
    defaultProps={ejemplo as unknown as EpisodioProps}
    calculateMetadata={calcular}
  />
);
