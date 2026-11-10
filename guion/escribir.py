"""Redacta el guion del episodio con Claude, a partir de los hechos de `datos.recolectar`.

- El prompt vive en guion/prompt_sistema.md para irlo afinando sin tocar código.
- Validación: cada número de la narración debe existir en los datos de su hecho. Si falla, se reintenta
  una vez explicando el error; si vuelve a fallar, se usa la plantilla fija (sin IA).
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

log = logging.getLogger("pulso")

MODELO = os.getenv("GUION_MODELO", "claude-opus-5-5")
PROMPT = Path(__file__).with_name("prompt_sistema.md")

ESQUEMA = {
    "type": "object",
    "properties": {
        "gancho": {"type": "string"},
        "escenas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "string"},
                    "titular": {"type": "string"},
                    "narracion": {"type": "string"},
                },
                "required": ["item_id", "titular", "narracion"],
                "additionalProperties": False,
            },
        },
        "cierre": {"type": "string"},
    },
    "required": ["gancho", "escenas", "cierre"],
    "additionalProperties": False,
}


def _numeros(texto: str) -> set[str]:
    return {n.replace(".", "") for n in re.findall(r"\d[\d.]*", texto)}


def validar(guion: dict, episodio: dict) -> list[str]:
    """Devuelve la lista de problemas (vacía si el guion es válido)."""
    errores = []
    por_id = {it["id"]: it for it in episodio["items"]}
    for e in guion["escenas"]:
        it = por_id.get(e["item_id"])
        if not it:
            errores.append(f"item_id desconocido: {e['item_id']}")
            continue
        permitidos = _numeros(json.dumps(it, ensure_ascii=False, default=str))
        for n in _numeros(e["narracion"]) - permitidos:
            errores.append(f"{e['item_id']}: el número {n} no está en los datos")
        if len(e["titular"].split()) > 10:
            errores.append(f"{e['item_id']}: titular de más de 10 palabras")
    fecha_ok = _numeros(episodio["fecha"])
    for campo in ("gancho", "cierre"):
        for n in _numeros(guion[campo]) - fecha_ok:
            errores.append(f"{campo}: el número {n} no corresponde a un dato")
    return errores


def con_claude(episodio: dict) -> dict:
    import anthropic

    client = anthropic.Anthropic()
    mensajes = [{"role": "user", "content": "Hechos del día (JSON):\n\n"
                 + json.dumps(episodio, ensure_ascii=False, indent=1, default=str)}]
    for intento in range(2):
        r = client.beta.messages.create(
            model=MODELO,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",  # si el modelo declina, el servidor reintenta con el modelo recomendado
            system=PROMPT.read_text(encoding="utf-8"),
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": ESQUEMA}},
            messages=mensajes,
        )
        if r.stop_reason == "refusal":
            raise RuntimeError(f"Claude declinó escribir el guion: {r.stop_details}")
        texto = next(b.text for b in r.content if b.type == "text")
        guion = json.loads(texto)
        errores = validar(guion, episodio)
        if not errores:
            guion["generado_por"] = r.model
            return guion
        log.warning("guion inválido (intento %d): %s", intento + 1, errores)
        mensajes += [{"role": "assistant", "content": r.content},
                     {"role": "user", "content": "El guion no pasó la validación:\n- " + "\n- ".join(errores)
                      + "\nCorrígelo respetando las reglas."}]
    raise ValueError(f"guion inválido tras 2 intentos: {errores}")


VERBOS = {"modifica", "establece", "crea", "declara", "dicta", "regula", "prohíbe", "otorga", "autoriza", "sanciona",
          "introduce", "reforma", "incorpora", "concede", "fortalece", "amplía", "permite", "aprueba", "deroga",
          "extiende", "fija", "perfecciona", "adecúa", "reconoce", "consagra", "tipifica", "aumenta", "suprime"}


def _resumen(titulo: str) -> str:
    """Título oficial más corto y en minúscula inicial, para leerlo en voz alta."""
    t = re.split(r",? con (la finalidad|el objeto|el objetivo|el fin) de", titulo)[0]
    t = re.sub(r"\s*\(bolet[ií]n[^)]*\)", "", t, flags=re.I)
    palabras = t.split()
    t = " ".join(palabras[:22]) + ("…" if len(palabras) > 22 else "")
    return t[0].lower() + t[1:] if t else t


def con_plantilla(episodio: dict) -> dict:
    """Guion determinista, sin IA: sirve para probar el video y como respaldo."""
    escenas = []
    for it in episodio["items"]:
        titulo = (it.get("titulo") or "un proyecto de ley").rstrip(".")
        corto = " ".join(titulo.split()[:8])
        if it.get("tipo") == "ley_publicada":
            n = f"Ya es ley y salió publicada en el Diario Oficial: {titulo}."
            if it.get("dias_de_tramitacion"):
                n += f" Desde que entró al Congreso pasaron {it['dias_de_tramitacion']} días."
        else:
            vp = it["votacion_principal"]
            sala = "la Cámara" if it["camara"] == "camara" else "el Senado"
            res = (vp.get("resultado") or "").lower()
            verbo = "aprobó" if res.startswith("aprob") else "rechazó" if res.startswith("rechaz") else "votó"
            abst = vp.get("abstencion")
            res_t = _resumen(titulo)
            es_verbo = res_t.split()[0] in VERBOS if res_t else False
            n = (f"{sala[0].upper() + sala[1:]} {verbo} en {(vp.get('tipo') or 'general').lower()} "
                 f"{'el proyecto que ' + res_t if es_verbo else 'el proyecto de ' + res_t if res_t.startswith('ley ') else 'el proyecto: ' + res_t}. "
                 f"Quedó con {vp.get('si')} votos a favor, {vp.get('no')} en contra"
                 + (f" y {abst} {'abstención' if abst == 1 else 'abstenciones'}." if abst else "."))
        escenas.append({"item_id": it["id"], "titular": corto, "narracion": n})
    return {
        "gancho": "Te cuento lo que pasó en el Congreso.",
        "escenas": escenas,
        "cierre": "Las fuentes oficiales están en la descripción. Mañana te cuento más.",
        "generado_por": "plantilla",
    }


def escribir(episodio: dict, usar_ia: bool = True) -> dict:
    if usar_ia and (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")):
        try:
            return con_claude(episodio)
        except Exception as e:  # el video sale igual, con la plantilla
            log.error("falló el guion con Claude, uso plantilla: %s", e)
    elif usar_ia:
        log.warning("sin ANTHROPIC_API_KEY: uso la plantilla fija")
    return con_plantilla(episodio)
