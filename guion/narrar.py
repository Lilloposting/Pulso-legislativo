"""Voz del narrador: texto → MP3 + tiempos por palabra (para subtítulos sincronizados).

Dos motores:
- ElevenLabs (recomendado: suena humano). Se activa si existe ELEVENLABS_API_KEY.
  Voz: ELEVENLABS_VOICE_ID (elige una voz femenina con acento chileno en la Voice Library de ElevenLabs).
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
ELEVEN_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voz}/with-timestamps"
# Ajustes de voz: estabilidad baja = más natural y expresiva; style suave para un tono cálido y cercano.
ELEVEN_AJUSTES = {"stability": 0.38, "similarity_boost": 0.8, "style": 0.3, "use_speaker_boost": True, "speed": 1.0}


def motor() -> str:
    return "elevenlabs" if os.getenv("ELEVENLABS_API_KEY") else "edge-tts"


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
    voz = os.getenv("ELEVENLABS_VOICE_ID")
    if not voz:
        raise SystemExit("Falta ELEVENLABS_VOICE_ID (id de la voz elegida en ElevenLabs)")
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
        async for ch in edge_tts.Communicate(texto, VOZ_EDGE, boundary="WordBoundary").stream():
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


def censurar(palabras: list[dict]) -> list[dict]:
    """Marca las palabras fuertes: el video les pone pitido y *** en subtítulos."""
    for p in palabras:
        n = _normal(p["texto"])
        p["censurada"] = bool(n) and any(n.startswith(g) for g in _GARABATOS)
    return palabras


def narrar(texto: str, destino: Path, texto_previo: str | None = None, texto_siguiente: str | None = None) -> dict:
    destino.parent.mkdir(parents=True, exist_ok=True)
    texto = re.sub(r"\s+", " ", texto).strip()
    if motor() == "elevenlabs":
        palabras = _elevenlabs(texto, destino, texto_previo, texto_siguiente)
    else:
        palabras = asyncio.run(_edge(texto, destino))
    return {"texto": texto, "audio": destino.name, "duracion_ms": int(MP3(destino).info.length * 1000),
            "palabras": censurar(palabras), "motor": motor()}


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
