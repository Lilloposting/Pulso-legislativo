"""Senado: servicio público de tramitación (tramitacion.senado.cl/wspublico).

La ficha de tramitación es la fuente más completa del recorrido de un boletín en ambas cámaras:
trámites, urgencias, informes, oficios, materias, ley y fecha en el Diario Oficial.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, time

from .descarga import obtener
from .util import (boletin_de_texto, boletin_num, camara_de_texto, entero, fecha_dmy, normalizar, tipo_urgencia,
                   txt, xml, SANTIAGO)

BASE = "https://tramitacion.senado.cl/wspublico"
FUENTE = "senado"

OPCION_VOTO = {"si": "si", "no": "no", "abstencion": "abstencion", "pareo": "pareo"}


# ---------------------------------------------------------------- ficha de tramitación
def _ficha(p) -> dict | None:
    d = p.find("descripcion")
    b = boletin_de_texto(txt(d, "boletin"))
    if not b:
        return None
    ini = normalizar(txt(d, "iniciativa"))
    proyecto = {
        "boletin": b, "boletin_num": boletin_num(b), "titulo": txt(d, "titulo"),
        "fecha_ingreso": fecha_dmy(txt(d, "fecha_ingreso")),
        "iniciativa": "mensaje" if "mensaje" in ini else "mocion" if "mocion" in ini else None,
        "camara_origen": camara_de_texto(txt(d, "camara_origen")),
        "urgencia_actual": txt(d, "urgencia_actual"), "etapa": txt(d, "etapa"),
        "subetapa": (txt(d, "subetapa") or "").strip(" /") or None,
        "ley_numero": txt(d, "leynro"), "fecha_diario_oficial": fecha_dmy(txt(d, "diariooficial")),
        "estado": txt(d, "estado"), "refundidos": txt(d, "refundidos"),
        "url_documento": txt(d, "link_mensaje_mocion"),
        "autores": [t for a in p.iter("autor") if (t := txt(a, "PARLAMENTARIO"))] or None,
        "materias": [t for m in p.iter("materia") if (t := txt(m, "DESCRIPCION"))] or None,
    }
    tramites = [{
        "boletin": b, "orden": i, "fecha": fecha_dmy(txt(t, "FECHA")),
        "sesion": None if (s := txt(t, "SESION")) in (None, "/") else s,
        "descripcion": txt(t, "DESCRIPCIONTRAMITE"), "etapa": txt(t, "ETAPDESCRIPCION"),
        "camara": camara_de_texto(txt(t, "CAMARATRAMITE")),
    } for i, t in enumerate(p.iter("tramite"))]
    urgencias = [{
        "boletin": b, "orden": i, "tipo": tipo_urgencia(txt(u, "TIPO")),
        "fecha_ingreso": fecha_dmy(txt(u, "FECHAINGRESO")), "mensaje_ingreso": txt(u, "MENSAJEINGRESO"),
        "camara_ingreso": camara_de_texto(txt(u, "CAMARAINGRESO")),
        "fecha_retiro": fecha_dmy(txt(u, "FECHARETIRO")), "mensaje_retiro": txt(u, "MENSAJERETIRO"),
        "camara_retiro": camara_de_texto(txt(u, "CAMARARETIRO")),
    } for i, u in enumerate(p.iter("urgencia"))]

    documentos = []
    for tipo, tag, link, fecha in (("informe", "informe", "LINK_INFORME", "FECHAINFORME"),
                                    ("oficio", "oficio", "LINK_OFICIO", "FECHA"),
                                    ("comparado", "comparado", "LINK_COMPARADO", None),
                                    ("indicacion", "indicacion", "LINK_INDICACION", "FECHA")):
        for el in p.iter(tag):
            documentos.append({
                "boletin": b, "tipo": tipo, "fecha": fecha_dmy(txt(el, fecha)) if fecha else None,
                "numero": txt(el, "NUMERO"), "etapa": txt(el, "ETAPA"),
                "tramite": txt(el, "TRAMITE") or txt(el, "COMPARADO"),
                "camara": camara_de_texto(txt(el, "CAMARA")), "descripcion": txt(el, "DESCRIPCION"),
                "url": txt(el, link),
            })
    for i, doc in enumerate(documentos):
        doc["orden"] = i
    return {"proyecto": proyecto, "tramites": tramites, "urgencias": urgencias, "documentos": documentos}


def bajar_ficha(boletin: str) -> dict | None:
    """Ficha completa de un boletín (acepta '16621-05' o '16621')."""
    num = str(boletin_num(boletin))
    raiz = xml(obtener(f"{BASE}/tramitacion.php", {"boletin": num}, FUENTE, f"tramitacion_{num}"))
    fichas = [f for f in map(_ficha, raiz.iter("proyecto")) if f]
    return fichas[0] if fichas else None


def bajar_fichas_desde(desde: date) -> list[dict]:
    """Fichas de todos los proyectos con movimiento desde `desde` (el Senado acepta como máximo 1 mes atrás)."""
    f = desde.strftime("%d/%m/%Y")
    raiz = xml(obtener(f"{BASE}/tramitacion.php", {"fecha": f}, FUENTE, f"tramitacion_desde_{desde.isoformat()}"))
    return [x for x in map(_ficha, raiz.iter("proyecto")) if x]


# ---------------------------------------------------------------- votaciones del Senado
def bajar_votaciones(boletin: str) -> list[dict]:
    """Votaciones en Sala del Senado para un boletín, con el voto de cada senador.

    El Senado no entrega un id de votación: se genera uno estable con un hash del contenido
    (más un correlativo si hay dos votaciones idénticas en el mismo boletín).
    """
    num = str(boletin_num(boletin))
    raiz = xml(obtener(f"{BASE}/votaciones.php", {"boletin": num}, FUENTE, f"votaciones_{num}"))
    out, vistos = [], {}
    for v in raiz.iter("votacion"):
        tema = txt(v, "TEMA")
        b = boletin_de_texto(tema) or boletin
        clave = "|".join(str(x) for x in (b, txt(v, "SESION"), txt(v, "FECHA"), tema, txt(v, "TIPOVOTACION"),
                                           txt(v, "ETAPA"), txt(v, "SI"), txt(v, "NO"), txt(v, "ABSTENCION"),
                                           txt(v, "PAREO")))
        h = hashlib.sha1(clave.encode()).hexdigest()[:16]
        vistos[h] = vistos.get(h, 0) + 1
        id_fuente = h if vistos[h] == 1 else f"{h}-{vistos[h]}"
        votos = []
        for voto in v.iter("VOTO"):
            nombre = txt(voto, "PARLAMENTARIO")
            if nombre:
                votos.append({"votante": nombre, "parlamentario_id": None,
                              "opcion": OPCION_VOTO.get(normalizar(txt(voto, "SELECCION")), "no_vota")})
        out.append({
            "camara": "senado", "id_fuente": id_fuente, "boletin": b,
            "fecha": _medianoche(fecha_dmy(txt(v, "FECHA"))), "sesion": txt(v, "SESION"), "descripcion": tema,
            "articulo": None, "tramite": txt(v, "ETAPA"), "tramite_reglamentario": None,
            "tipo": txt(v, "TIPOVOTACION"), "quorum": txt(v, "QUORUM"),
            "resultado": _resultado(tema), "si": entero(v, "SI"), "no": entero(v, "NO"),
            "abstencion": entero(v, "ABSTENCION"), "pareo": entero(v, "PAREO"), "dispensado": None,
            "votos": votos,
        })
    return out


def _medianoche(d: date | None) -> datetime | None:
    return datetime.combine(d, time(0), SANTIAGO) if d else None


def _resultado(tema: str | None) -> str | None:
    n = normalizar(tema)
    for clave, valor in (("rechazad", "Rechazado"), ("aprobad", "Aprobado")):
        if clave in n[-40:]:
            return valor
    return None


# ---------------------------------------------------------------- senadores
URL_SENADORES = "https://web-back.senado.cl/api/hemicycle"


def bajar_senadores(todos: bool = False) -> tuple[list[dict], list[dict]]:
    """Senadores desde la API del sitio web del Senado (senado.cl).

    todos=False: los 50 en ejercicio. todos=True: también los históricos (~190), para vincular votos antiguos.

    Reemplaza a wspublico/senadores_vigentes.php, que quedó desactualizado (31 senadores, incluye salientes).
    Devuelve (parlamentarios, mandatos). PARLID es el mismo id en ambas fuentes.
    """
    params = {"camara": "S", "limit": 1000} if todos else {"vigentes": 1, "camara": "S", "limit": 100}
    cuerpo = obtener(URL_SENADORES, params, FUENTE, "senadores_todos" if todos else "senadores_vigentes",
                     formato="json")
    datos = json.loads(cuerpo)["data"]["parlamentarios"]["data"]
    parl, mandatos = [], []
    for s in datos:
        pid = f"S-{s['ID_PARLAMENTARIO']}"
        parl.append({
            "id": pid, "camara": "senado", "id_fuente": s["ID_PARLAMENTARIO"],
            "nombre": s.get("NOMBRE"), "apellido_paterno": s.get("APELLIDO_PATERNO"),
            "apellido_materno": s.get("APELLIDO_MATERNO"),
            "sexo": {"Hombre": "Masculino", "Mujer": "Femenino"}.get(s.get("SEXO_ETIQUETA"), s.get("SEXO_ETIQUETA")),
            "region": s.get("REGION"),
            "circunscripcion": str(s["CIRCUNSCRIPCION_ID"]) if s.get("CIRCUNSCRIPCION_ID") else None,
            "partido_actual": s.get("PARTIDO"), "comite": (s.get("COMITE") or {}).get("NOMBRE"),
            "email": s.get("EMAIL"), "url_foto": s.get("IMAGEN_600") or s.get("IMAGEN"),
            "url_curriculum": f"https://www.senado.cl/senadoras-y-senadores/listado-de-senadoras-y-senadores/{s['SLUG']}"
            if s.get("SLUG") else None,
            "vigente": any(per.get("VIGENTE") == 1 and per.get("CAMARA") == "S" for per in s.get("PERIODOS") or []),
        })
        vistos = set()
        for per in s.get("PERIODOS") or []:
            clave = (per.get("CAMARA"), per.get("DESDE"))
            if clave in vistos or not per.get("DESDE"):
                continue
            vistos.add(clave)
            mandatos.append({
                "parlamentario_id": pid, "camara": "senado" if per.get("CAMARA") == "S" else "camara",
                "fecha_inicio": date(int(per["DESDE"]), 3, 11),
                "fecha_termino": date(int(per["HASTA"]), 3, 10) if per.get("HASTA") else None,
                "distrito": None,
            })
    return parl, mandatos


def bajar_hemiciclo() -> list:
    """Distribución de asientos de la Sala del Senado (ids de senador por sector y fila). Útil para gráficos."""
    cuerpo = obtener(URL_SENADORES, {"vigentes": 1, "camara": "S", "limit": 100}, FUENTE, "senadores_hemiciclo",
                     formato="json")
    return json.loads(cuerpo)["data"]["hemiciclo"]


def clave_nombre_voto(nombre: str) -> str:
    """'Van Rysselberghe H., Enrique' -> 'van rysselberghe|enrique' (para vincular votos con senadores)."""
    apellidos, _, nombres = nombre.partition(",")
    partes = [p for p in apellidos.split() if not p.endswith(".")]
    return f"{normalizar(' '.join(partes))}|{normalizar(nombres).split(' ')[0] if nombres.strip() else ''}"


def clave_nombre_senador(s: dict) -> str:
    return f"{normalizar(s.get('apellido_paterno'))}|{normalizar(s.get('nombre')).split(' ')[0]}"
