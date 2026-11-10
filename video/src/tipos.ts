// Estructura de public/episodios/<fecha>/props.json (la genera `python -m guion.generar`).

export type Palabra = { texto: string; desde_ms: number; hasta_ms: number };

export type Voz = {
  texto: string;
  audio: string; // ruta relativa a public/
  duracion_ms: number;
  palabras: Palabra[];
};

export type Votacion = {
  si: number | null;
  no: number | null;
  abstencion: number | null;
  resultado: string | null;
  tipo: string | null;
  quorum: string | null;
  tramite: string | null;
};

export type Dato = {
  id: string;
  camara: "camara" | "senado" | "ambas";
  boletin: string;
  titulo: string | null;
  tipo?: "ley_publicada";
  etapa?: string | null;
  urgencia_actual?: string | null;
  votaciones_del_dia?: number;
  aprobadas?: number;
  rechazadas?: number;
  votacion_principal?: Votacion;
  ley_numero?: string | null;
  dias_de_tramitacion?: number | null;
  fuente: string;
};

export type Escena =
  | { tipo: "intro"; voz: Voz }
  | { tipo: "noticia"; voz: Voz; titular: string; dato: Dato }
  | { tipo: "cierre"; voz: Voz };

export type EpisodioProps = {
  fecha: string;
  generado_por: string;
  escenas: Escena[];
  fuentes: string[];
  /** Opcional: clip de apertura (p. ej. generado con IA) en public/, reemplaza la intro animada. */
  introVideo?: string;
  /** Opcional: música de fondo en public/ (se mezcla bajo la voz). */
  musica?: string;
};
