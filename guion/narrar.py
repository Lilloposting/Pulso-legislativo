"""Voz del narrador: texto → MP3 + tiempos por palabra (para subtítulos sincronizados).

Dos motores:
- ElevenLabs (recomendado: suena humano). Se activa si existe ELEVENLABS_API_KEY.
  Voz: la del canal (VOZ_CANAL); ELEVENLABS_VOICE_ID permite probar otra.
- edge-tts (gratis, de respaldo): voces neuronales de Microsoft. Suena más sintético.
"""
from __future__ import annotations

import asyncio
import base64
import os
import re
from pathlib import Path

import requests
from mutagen.mp3 import MP3

VOZ_EDGE = "es-CL-CatalinaNeural"  # mujer, Chile (respaldo)
VELOCIDAD_EDGE = "+18%"  # ritmo de redes: rápido pero entendible
ELEVEN_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voz}/with-timestamps"
# Voz oficial del canal (elegida en la Voice Library de ElevenLabs): https://elevenlabs.io/voices/dZFAIFXrSaHlJY1R7xj2
VOZ_CANAL = "dZFAIFXrSaHlJY1R7xj2"
# Ajustes de voz: estabilidad baja = más natural y expresiva; style suave para un tono cálido y cercano.
ELEVEN_AJUSTES = {"stability": 0.38, "similarity_boost": 0.8, "style": 0.3, "use_speaker_boost": True, "speed": 1.12}


CACHE = Path(__file__).with_name(".cache_voz")
_FORZAR_GRATIS = False


def usar_voz_gratis(si: bool = True) -> None:
    """Modo borrador: siempre edge-tts, no gasta créditos de ElevenLabs."""
    global _FORZAR_GRATIS
    _FORZAR_GRATIS = si


def motor() -> str:
    return "elevenlabs" if os.getenv("ELEVENLABS_API_KEY") and not _FORZAR_GRATIS else "edge-tts"


def _clave(texto: str) -> str:
    """Identifica una narración: mismo texto + misma voz/ajustes = mismo audio (no se vuelve a pagar)."""
    import hashlib
    import json
    if motor() == "elevenlabs":
        base = ["elevenlabs", os.getenv("ELEVENLABS_VOICE_ID") or VOZ_CANAL,
                os.getenv("ELEVENLABS_MODELO", "eleven_multilingual_v2"), ELEVEN_AJUSTES, texto]
    else:
        base = ["edge-tts", VOZ_EDGE, VELOCIDAD_EDGE, texto]
    return hashlib.sha1(json.dumps(base, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:20]


def texto_para_voz(texto: str) -> str:
    """Texto exacto que se enviará a la voz (sin marcas [[...]] ni espacios extra)."""
    return _quitar_marcas(re.sub(r"\s+", " ", texto).strip())[0]


def en_cache(texto: str) -> bool:
    return (CACHE / f"{_clave(texto_para_voz(texto))}.mp3").exists()


# ---------------------------------------------------------------- ElevenLabs
def _palabras_desde_caracteres(al: dict) -> list[dict]:
    """Convierte la alineación por carácter de ElevenLabs en tiempos por palabra."""
    palabras, actual, desde, hasta = [], "", None, None
    for ch, ini, fin in zip(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]):
        if ch.isspace():
            if actual:
                palabras.append({"texto": actual, "desde_ms": int(desde * 1000), "hasta_ms": int(hasta * 1000)})
            actual, desde = "", None
            continue
        if desde is None:
            desde = ini
        actual += ch
        hasta = fin
    if actual:
        palabras.append({"texto": actual, "desde_ms": int(desde * 1000), "hasta_ms": int(hasta * 1000)})
    return palabras


def _elevenlabs(texto: str, destino: Path, texto_previo: str | None, texto_siguiente: str | None) -> list[dict]:
    voz = os.getenv("ELEVENLABS_VOICE_ID") or VOZ_CANAL
    cuerpo = {"text": texto, "model_id": os.getenv("ELEVENLABS_MODELO", "eleven_multilingual_v2"),
              "voice_settings": ELEVEN_AJUSTES}
    # el contexto de los segmentos vecinos mantiene una entonación continua entre escenas
    if texto_previo:
        cuerpo["previous_text"] = texto_previo
    if texto_siguiente:
        cuerpo["next_text"] = texto_siguiente
    r = requests.post(ELEVEN_URL.format(voz=voz), params={"output_format": "mp3_44100_128"},
                      headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]}, json=cuerpo, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:300]}")
    d = r.json()
    destino.write_bytes(base64.b64decode(d["audio_base64"]))
    return _palabras_desde_caracteres(d["alignment"])


# ---------------------------------------------------------------- edge-tts (respaldo)
async def _edge(texto: str, destino: Path) -> list[dict]:
    import edge_tts

    palabras = []
    with destino.open("wb") as f:
        async for ch in edge_tts.Communicate(texto, VOZ_EDGE, rate=VELOCIDAD_EDGE, boundary="WordBoundary").stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":  # unidades de 100 ns
                palabras.append({"texto": ch["text"], "desde_ms": ch["offset"] // 10_000,
                                 "hasta_ms": (ch["offset"] + ch["duration"]) // 10_000})
    return palabras


_GARABATOS = [l.strip() for l in (Path(__file__).with_name("garabatos.txt")).read_text(encoding="utf-8").splitlines()
              if l.strip() and not l.startswith("#")]


def _normal(p: str) -> str:
    import unicodedata
    p = unicodedata.normalize("NFKD", p.lower())
    return re.sub(r"[^a-zñ]", "", "".join(c for c in p if not unicodedata.combining(c)))


def separar(palabras: list[dict]) -> list[dict]:
    """La voz a veces junta dos palabras en una marca ("8 ctm"): se separan repartiendo el tiempo."""
    out = []
    for p in palabras:
        partes = p["texto"].split()
        if len(partes) <= 1:
            out.append(p)
            continue
        total = sum(len(x) for x in partes)
        t0, dur = p["desde_ms"], p["hasta_ms"] - p["desde_ms"]
        for x in partes:
            d = dur * len(x) / total
            out.append({"texto": x, "desde_ms": int(t0), "hasta_ms": int(t0 + d)})
            t0 += d
    return out


def marcar_frases(palabras: list[dict], texto: str) -> list[dict]:
    """Marca la palabra que cierra una frase o una pausa (punto, coma, ?, !, :) según el texto original."""
    cursor = 0
    bajo = texto.lower()
    for p in palabras:
        if p["texto"][-1:] in ".,;:?!…":  # ElevenLabs deja la puntuación pegada a la palabra
            p["fin_frase"] = True
            cursor = max(cursor, bajo.find(p["texto"].lower(), cursor) + len(p["texto"]))
            continue
        i = bajo.find(p["texto"].lower(), cursor)
        if i < 0:
            p["fin_frase"] = False
            continue
        cursor = i + len(p["texto"])
        resto = texto[cursor:cursor + 2]
        p["fin_frase"] = bool(resto) and resto.lstrip(" ")[:1] in ".,;:?!…" if resto.strip() else True
    return palabras


def censurar(palabras: list[dict]) -> list[dict]:
    """Marca las palabras fuertes: el video les pone pitido y *** en subtítulos."""
    for p in palabras:
        n = _normal(p["texto"])
        p["censurada"] = bool(n) and any(n.startswith(g) for g in _GARABATOS)
    return palabras


_MARCA = re.compile(r"\[\[(\w+)\]\]")


def _quitar_marcas(texto: str) -> tuple[str, dict[str, int]]:
    """'[[votaron]]estos sí votaron' -> texto limpio + {marca: índice de la palabra que sigue}."""
    marcas, limpio, pos = {}, [], 0
    for m in _MARCA.finditer(texto):
        antes = texto[pos:m.start()]
        limpio.append(antes)
        marcas[m.group(1)] = len(" ".join(limpio).split())
        pos = m.end()
    limpio.append(texto[pos:])
    return re.sub(r"\s+", " ", " ".join(limpio)).strip(), marcas


def narrar(texto: str, destino: Path, texto_previo: str | None = None, texto_siguiente: str | None = None) -> dict:
    """Las marcas [[nombre]] del guion no se leen: indican en qué palabra cambia algo en pantalla."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    texto, marcas = _quitar_marcas(re.sub(r"\s+", " ", texto).strip())
    texto_previo = _quitar_marcas(texto_previo)[0] if texto_previo else None
    texto_siguiente = _quitar_marcas(texto_siguiente)[0] if texto_siguiente else None
    import json
    import shutil
    usado = motor()
    clave = _clave(texto)
    en_c = CACHE / f"{clave}.mp3"
    if en_c.exists():  # ya pagado: se reutiliza
        shutil.copyfile(en_c, destino)
        guardado = json.loads((CACHE / f"{clave}.json").read_text(encoding="utf-8"))
        return {**guardado, "audio": destino.name}
    if usado == "elevenlabs":
        try:
            palabras = _elevenlabs(texto, destino, texto_previo, texto_siguiente)
        except RuntimeError as e:  # p. ej. 402: el plan gratis no permite voces de la Voice Library
            import logging
            logging.getLogger("pulso").warning("ElevenLabs no disponible (%s); uso edge-tts", str(e)[:160])
            usado = "edge-tts"
            palabras = asyncio.run(_edge(texto, destino))
    else:
        palabras = asyncio.run(_edge(texto, destino))
    palabras = censurar(marcar_frases(separar(palabras), texto))
    tiempos = {k: palabras[min(i, len(palabras) - 1)]["desde_ms"] for k, i in marcas.items() if palabras}
    out = {"texto": texto, "audio": destino.name, "duracion_ms": int(MP3(destino).info.length * 1000),
           "palabras": palabras, "marcas": tiempos, "motor": usado}
    if usado == motor():  # no guardar un respaldo de edge-tts bajo la clave de ElevenLabs
        CACHE.mkdir(exist_ok=True)
        shutil.copyfile(destino, en_c)
        (CACHE / f"{clave}.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def crear_pitido(destino: Path, segundos: float = 1.0, hz: int = 1000) -> None:
    """El clásico pitido de censura (onda senoidal), para tapar garabatos."""
    import math
    import struct
    import wave
    if destino.exists():
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    tasa = 44100
    with wave.open(str(destino), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(tasa)
        w.writeframes(b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * hz * i / tasa)))
                               for i in range(int(tasa * segundos))))
