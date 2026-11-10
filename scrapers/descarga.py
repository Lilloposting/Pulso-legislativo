"""Descarga con reintentos, pausa de cortesía y respaldo del dato crudo en data/raw."""
from __future__ import annotations

import gzip
import logging
import os
import re
import threading
import time
from datetime import date
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parent.parent
DIR_RAW = RAIZ / "data" / "raw"
PAUSA = float(os.getenv("PAUSA_SEGUNDOS", "0.3"))
GUARDAR_RAW = os.getenv("GUARDAR_RAW", "1") != "0"

_local = threading.local()


def _sesion() -> requests.Session:
    s = getattr(_local, "s", None)
    if s is None:
        s = requests.Session()
        s.headers["User-Agent"] = "PulsoLegislativo/0.1 (datos abiertos; github.com/pulso-legislativo)"
        reintentos = Retry(total=5, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504),
                           allowed_methods=("GET",))
        s.mount("https://", HTTPAdapter(max_retries=reintentos))
        s.mount("http://", HTTPAdapter(max_retries=reintentos))
        _local.s = s
    return s


class ErrorFuente(Exception):
    """La fuente respondió algo que no es el XML esperado."""


def obtener(url: str, params: dict | None, fuente: str, nombre: str, formato: str = "xml") -> bytes:
    """GET que devuelve el cuerpo en bytes y lo respalda comprimido en data/raw/<fuente>/<fecha>/."""
    r = _sesion().get(url, params=params, timeout=120)
    time.sleep(PAUSA)
    r.raise_for_status()
    cuerpo = r.content
    if GUARDAR_RAW:
        carpeta = DIR_RAW / fuente / date.today().isoformat()
        carpeta.mkdir(parents=True, exist_ok=True)
        seguro = re.sub(r"[^A-Za-z0-9_.-]+", "_", nombre)
        with gzip.open(carpeta / f"{seguro}.{formato}.gz", "wb") as f:
            f.write(cuerpo)
    if formato == "json":
        if not cuerpo.lstrip().startswith((b"{", b"[")):
            raise ErrorFuente(f"{fuente}/{nombre}: respuesta no JSON")
        return cuerpo
    inicio = cuerpo.lstrip()[:20].lower()
    es_xml = inicio.startswith(b"<?xml") or (re.match(rb"<[a-z_]+>", inicio) and not inicio.startswith(b"<div"))
    if not es_xml:
        texto = re.sub(rb"<[^>]+>", b" ", cuerpo[:500]).decode("utf-8", "replace").strip()
        raise ErrorFuente(f"{fuente}/{nombre}: respuesta no XML: {texto[:200]}")
    return cuerpo
