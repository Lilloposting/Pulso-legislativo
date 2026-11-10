import { loadFont as cargarTitulos } from "@remotion/google-fonts/PlayfairDisplay";
import { loadFont as cargarTexto } from "@remotion/google-fonts/Inter";

export const fuenteTitulos = cargarTitulos("normal", { weights: ["700", "900"], subsets: ["latin"] }).fontFamily;
export const fuenteTexto = cargarTexto("normal", { weights: ["400", "600", "800"], subsets: ["latin"] }).fontFamily;

// Paleta inspirada en la bandera; el rojo y el azul se usan como acentos, nunca para codificar partidos.
export const color = {
  noche: "#061433",
  azul: "#0b2a6f",
  azulClaro: "#2f5fd0",
  rojo: "#d52b1e",
  blanco: "#f7f5ef",
  gris: "#9aa6c2",
  oro: "#e8c46a",
  favor: "#2fbf71",
  contra: "#e5484d",
  abstencion: "#9aa6c2",
};

export const FPS = 30;
export const ANCHO = 1080;
export const ALTO = 1920;
export const MARGEN_ESCENA = 12; // frames extra al final de cada escena
export const MIN_INTRO = 5 * FPS;

export const nombreCamara = (c: string) =>
  c === "senado" ? "SENADO" : c === "camara" ? "CÁMARA DE DIPUTADAS Y DIPUTADOS" : "CONGRESO NACIONAL";
