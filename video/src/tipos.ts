// Estructura de public/episodios/<fecha>/props.json (la genera `python -m guion.generar`).

export type Palabra = { texto: string; desde_ms: number; hasta_ms: number; censurada?: boolean };

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

export type Persona = { nombre: string; partido: string; registro?: string };

export type Jornada = {
  camara: {
    lista_votaron: Persona[];
    lista_no_votaron: Persona[];
    asistencia_publicada: boolean;
    lista_ausentes: Persona[];
    diputados_ausentes: number | null;
    sesiones: { numero: number; tipo: string; inicio: string; termino: string | null }[];
    horas_en_sala: number;
    minutos_en_sala_resto: number;
    minutos_en_sala_total: number;
    votaciones: number;
    proyectos_votados: number;
    diputados_que_votaron: number;
    total_diputados: number;
    diputados_que_no_votaron_nunca: number | null;
  };
  senado: { votaciones: number; proyectos_votados: number };
  leyes_publicadas: number;
};

export type Cahuin = {
  tipo: "voto_contra_su_partido" | "reserva_de_constitucionalidad" | "no_votaron";
  nombre?: string;
  partido?: string;
  voto?: string;
  mayoria_del_partido?: string;
  votos_mayoria?: number;
  detalle?: string;
  cantidad?: number;
  boletin?: string;
  titulo?: string | null;
};

export type Escena =
  | { tipo: "intro"; voz: Voz }
  | { tipo: "jornada"; voz: Voz; jornada: Jornada }
  | { tipo: "cahuin"; voz: Voz; cahuines: Cahuin[] }
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
