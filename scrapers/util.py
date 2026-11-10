"""Utilidades de parseo compartidas."""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from zoneinfo import ZoneInfo

from lxml import etree

SANTIAGO = ZoneInfo("America/Santiago")
_PARSER = etree.XMLParser(recover=True, huge_tree=True)


def xml(cuerpo: bytes) -> etree._Element:
    """Parsea y elimina namespaces para poder usar rutas simples (la Cámara usa xmlns v1)."""
    raiz = etree.fromstring(cuerpo, _PARSER)
    for el in raiz.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    etree.cleanup_namespaces(raiz)
    return raiz


def txt(el, ruta: str) -> str | None:
    """Texto limpio de un sub-elemento o None si no existe / está vacío."""
    if el is None:
        return None
    hijo = el.find(ruta)
    if hijo is None or hijo.text is None:
        return None
    t = re.sub(r"\s+", " ", hijo.text).strip()
    return t or None


def entero(el, ruta: str) -> int | None:
    t = txt(el, ruta)
    try:
        return int(t) if t is not None else None
    except ValueError:
        return None


def fecha_dmy(t: str | None) -> date | None:
    """'29/01/2024' -> date (formato Senado)."""
    if not t:
        return None
    try:
        return datetime.strptime(t.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def fecha_iso(t: str | None) -> date | None:
    """'2026-01-05T17:00:00' -> date (formato Cámara)."""
    if not t:
        return None
    try:
        return datetime.fromisoformat(t.strip()).date()
    except ValueError:
        return None


def fechahora_iso(t: str | None) -> datetime | None:
    """'2026-11-09T19:54:50' (hora de Chile, sin zona) -> datetime con zona America/Santiago."""
    if not t:
        return None
    try:
        return datetime.fromisoformat(t.strip()).replace(tzinfo=SANTIAGO)
    except ValueError:
        return None


_RE_BOLETIN = re.compile(r"(\d{1,3}(?:\.\d{3})+|\d{1,6})\s*-\s*(\d{1,2})\b")


def boletin_de_texto(t: str | None) -> str | None:
    """Extrae un boletín normalizado ('16621-05') de textos como 'Boletín N° 16.621-05'."""
    if not t:
        return None
    m = _RE_BOLETIN.search(t)
    if not m:
        return None
    return f"{m.group(1).replace('.', '')}-{int(m.group(2)):02d}"


def boletin_num(boletin: str) -> int:
    return int(boletin.split("-")[0].replace(".", ""))


def normalizar(t: str | None) -> str:
    """minúsculas, sin tildes ni espacios extra: para comparar nombres."""
    if not t:
        return ""
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip().lower()


def camara_de_texto(t: str | None) -> str | None:
    n = normalizar(t)
    if not n:
        return None
    if "senado" in n:
        return "senado"
    if "diputad" in n or n.startswith("c."):
        return "camara"
    return None


def tipo_urgencia(t: str | None) -> str | None:
    n = normalizar(t)
    if "inmediata" in n:
        return "discusion_inmediata"
    if "suma" in n:
        return "suma"
    if "simple" in n:
        return "simple"
    return None
