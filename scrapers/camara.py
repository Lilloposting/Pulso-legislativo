"""Cámara de Diputadas y Diputados: servicios web de datos abiertos (opendata.camara.cl).

Cada función `bajar_*` descarga y devuelve registros listos para la base (dicts).
"""
from __future__ import annotations

from .descarga import obtener
from .util import (boletin_de_texto, boletin_num, entero, fecha_iso, fechahora_iso, txt, xml)

BASE = "https://opendata.camara.cl/camaradiputados/WServices"
FUENTE = "camara"

OPCION_VOTO = {
    "afirmativo": "si", "en contra": "no", "abstencion": "abstencion", "abstención": "abstencion",
    "dispensado": "dispensado", "pareo": "pareo", "no vota": "no_vota",
}


def _get(servicio: str, metodo: str, nombre: str, **params):
    return xml(obtener(f"{BASE}/{servicio}.asmx/{metodo}", params or None, FUENTE, nombre))


# ---------------------------------------------------------------- legislaturas / períodos
def bajar_legislaturas() -> list[dict]:
    raiz = _get("WSLegislativo", "retornarLegislaturas", "legislaturas")
    return [{
        "id": entero(l, "Id"), "numero": entero(l, "Numero"),
        "fecha_inicio": fecha_iso(txt(l, "FechaInicio")), "fecha_termino": fecha_iso(txt(l, "FechaTermino")),
        "tipo": txt(l, "Tipo"),
    } for l in raiz.iter("Legislatura")]


def bajar_periodos() -> list[dict]:
    raiz = _get("WSLegislativo", "retornarPeriodosLegislativos", "periodos")
    return [{
        "id": entero(p, "Id"), "nombre": txt(p, "Nombre"),
        "fecha_inicio": fecha_iso(txt(p, "FechaInicio")), "fecha_termino": fecha_iso(txt(p, "FechaTermino")),
    } for p in raiz.findall("PeriodoLegislativo")]


# ---------------------------------------------------------------- diputados
def _diputados(raiz) -> tuple[list[dict], list[dict], list[dict]]:
    parl, mandatos, milit = [], [], []
    for dp in raiz.iter("DiputadoPeriodo"):
        d = dp.find("Diputado")
        pid = f"D-{entero(d, 'Id')}"
        nombres = " ".join(x for x in (txt(d, "Nombre"), txt(d, "Nombre2")) if x)
        ms = []
        for m in d.iter("Militancia"):
            ms.append({
                "parlamentario_id": pid, "partido_id": txt(m, "Partido/Id") or "?",
                "partido_nombre": txt(m, "Partido/Nombre"),
                "fecha_inicio": fecha_iso(txt(m, "FechaInicio")), "fecha_termino": fecha_iso(txt(m, "FechaTermino")),
            })
        actual = max(ms, key=lambda x: x["fecha_inicio"] or fecha_iso("1900-01-01"), default=None)
        parl.append({
            "id": pid, "camara": "camara", "id_fuente": entero(d, "Id"),
            "nombre": nombres or None, "apellido_paterno": txt(d, "ApellidoPaterno"),
            "apellido_materno": txt(d, "ApellidoMaterno"), "sexo": txt(d, "Sexo"),
            "fecha_nacimiento": fecha_iso(txt(d, "FechaNacimiento")),
            "partido_actual": actual["partido_nombre"] if actual else None,
            "distrito": txt(dp, "Distrito/Numero"),
        })
        mandatos.append({
            "parlamentario_id": pid, "camara": "camara", "fecha_inicio": fecha_iso(txt(dp, "FechaInicio")),
            "fecha_termino": fecha_iso(txt(dp, "FechaTermino")), "distrito": txt(dp, "Distrito/Numero"),
        })
        milit.extend(x for x in ms if x["fecha_inicio"])
    return parl, [m for m in mandatos if m["fecha_inicio"]], milit


def bajar_diputados_actuales():
    return _diputados(_get("WSDiputado", "retornarDiputadosPeriodoActual", "diputados_actual"))


def bajar_diputados_periodo(periodo_id: int):
    return _diputados(_get("WSDiputado", "retornarDiputadosXPeriodo", f"diputados_periodo_{periodo_id}",
                           prmPeriodoID=periodo_id))


# ---------------------------------------------------------------- proyectos
def _proyecto_basico(p) -> dict | None:
    b = boletin_de_texto(txt(p, "NumeroBoletin"))
    if not b:
        return None
    ini = (txt(p, "TipoIniciativa") or "").lower()
    co = (txt(p, "CamaraOrigen") or "").lower()
    adm = txt(p, "Admisible")
    return {
        "boletin": b, "boletin_num": boletin_num(b), "titulo": txt(p, "Nombre"),
        "fecha_ingreso": fecha_iso(txt(p, "FechaIngreso")),
        "iniciativa": "mensaje" if "mensaje" in ini else "mocion" if "moci" in ini else None,
        "camara_origen": "senado" if "senado" in co else "camara" if co else None,
        "camara_id": entero(p, "Id"),
        "admisible": None if adm is None else adm.lower() == "true",
    }


def bajar_proyectos_anno(anno: int) -> list[dict]:
    """Todas las mociones y mensajes ingresados en el año (ambas cámaras de origen)."""
    out = []
    for metodo, nombre in (("retornarMocionesXAnno", "mociones"), ("retornarMensajesXAnno", "mensajes")):
        raiz = _get("WSLegislativo", metodo, f"{nombre}_{anno}", prmAnno=anno)
        out.extend(x for x in map(_proyecto_basico, raiz.iter("ProyectoLey")) if x)
    return out


def bajar_proyecto(boletin: str) -> tuple[dict | None, list[dict]]:
    """Ficha Cámara de un boletín: datos básicos + ministerios + votaciones con artículo y trámite."""
    raiz = _get("WSLegislativo", "retornarProyectoLey", f"proyecto_{boletin}", prmNumeroBoletin=boletin)
    if raiz.find("NumeroBoletin") is None:
        return None, []
    p = _proyecto_basico(raiz)
    if p:
        p["ministerios"] = [txt(m, "Nombre") for m in raiz.iter("Ministerio") if txt(m, "Nombre")] or None
    votos = [_votacion(v, p["boletin"] if p else None) for v in raiz.iter("VotacionProyectoLey")]
    return p, votos


# ---------------------------------------------------------------- votaciones
def _votacion(v, boletin: str | None = None) -> dict:
    return {
        "camara": "camara", "id_fuente": txt(v, "Id"),
        "boletin": boletin or boletin_de_texto(txt(v, "Descripcion")),
        "fecha": fechahora_iso(txt(v, "Fecha")), "descripcion": txt(v, "Descripcion"),
        "articulo": txt(v, "Articulo"), "tramite": txt(v, "TramiteConstitucional"),
        "tramite_reglamentario": txt(v, "TramiteReglamentario"),
        "tipo": txt(v, "TipoVotacionProyectoLey") or txt(v, "Tipo"),
        "quorum": txt(v, "Quorum"), "resultado": txt(v, "Resultado"),
        "si": entero(v, "TotalSi"), "no": entero(v, "TotalNo"), "abstencion": entero(v, "TotalAbstencion"),
        "dispensado": entero(v, "TotalDispensado"), "pareo": None, "sesion": None,
    }


def bajar_votaciones_anno(anno: int) -> list[dict]:
    raiz = _get("WSLegislativo", "retornarVotacionesXAnno", f"votaciones_{anno}", prmAnno=anno)
    return [_votacion(v) for v in raiz.iter("Votacion")]


def bajar_votos(votacion_id_fuente: str) -> list[dict]:
    raiz = _get("WSLegislativo", "retornarVotacionDetalle", f"votacion_{votacion_id_fuente}",
                prmVotacionId=votacion_id_fuente)
    out = []
    for v in raiz.iter("Voto"):
        did = entero(v, "Diputado/Id")
        if did is None:
            continue
        op = (txt(v, "OpcionVoto") or "").lower()
        out.append({"votante": f"D-{did}", "parlamentario_id": f"D-{did}",
                    "opcion": OPCION_VOTO.get(op, "no_vota")})
    return out


# ---------------------------------------------------------------- sesiones de Sala
def bajar_sesiones_anno(anno: int) -> list[dict]:
    raiz = _get("WSSala", "retornarSesionesXAnno", f"sesiones_{anno}", prmAnno=anno)
    return [{
        "id": f"C-{txt(s, 'Id')}", "camara": "camara", "id_fuente": txt(s, "Id"), "numero": entero(s, "Numero"),
        "fecha_inicio": fechahora_iso(txt(s, "FechaInicio")), "fecha_termino": fechahora_iso(txt(s, "FechaTermino")),
        "tipo": txt(s, "Tipo"), "estado": txt(s, "Estado"), "legislatura": None,
    } for s in raiz.iter("Sesion")]


def bajar_asistencia(sesion_id_fuente: str) -> list[dict]:
    raiz = _get("WSSala", "retornarSesionAsistencia", f"asistencia_{sesion_id_fuente}",
                prmSesionId=sesion_id_fuente)
    out = []
    for a in raiz.iter("Asistencia"):
        did = entero(a, "Diputado/Id")
        if did is not None:
            out.append({"sesion_id": f"C-{sesion_id_fuente}", "parlamentario_id": f"D-{did}",
                        "tipo": txt(a, "TipoAsistencia")})
    return out
