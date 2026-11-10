"""Reúne los hechos de un día en el Congreso: SOLO datos estructurados de las fuentes oficiales.

Todo número que aparezca en el video sale de aquí; la IA solo redacta.
Hoy lee directo de las fuentes (scrapers). Cuando la base esté cargada, se puede cambiar por consultas a Supabase.
"""
from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import date

from scrapers import camara, senado

log = logging.getLogger("pulso")


def url_senado(boletin: str) -> str:
    return f"https://tramitacion.senado.cl/appsenado/templates/tramitacion/index.php?boletin_ini={boletin}"


def _voto_principal(vots: list[dict]) -> dict:
    """La votación más representativa: en general si existe; si no, la de más participación."""
    generales = [v for v in vots if (v.get("tipo") or "").lower().startswith(("general", "discusión general"))]
    base = generales or vots
    v = max(base, key=lambda x: (x.get("si") or 0) + (x.get("no") or 0) + (x.get("abstencion") or 0))
    out = {k: v.get(k) for k in ("si", "no", "abstencion", "resultado", "tipo", "quorum", "tramite")}
    out["_camara"], out["_id"] = v.get("camara"), v.get("id_fuente")
    out["_votos"] = v.get("votos")
    return out


_PARTIDOS: dict[str, str] = {}
_NOMBRES: dict[str, str] = {}
_COMPLETOS: dict[str, str] = {}


def _cargar_diputados() -> None:
    if not _COMPLETOS:
        parl, _, _ = camara.bajar_diputados_actuales()
        _PARTIDOS.update({p["id"]: p["partido_actual"] or "Sin dato" for p in parl})
        _NOMBRES.update({p["id"]: f"{p['nombre'].split()[0]} {p['apellido_paterno']}" for p in parl if p["nombre"]})
        _COMPLETOS.update({p["id"]: " ".join(x for x in (p["nombre"], p["apellido_paterno"], p["apellido_materno"]) if x)
                           for p in parl})
SIN_PARTIDO = {"Independientes", "Independiente", "Sin dato"}


def _discolos(vp: dict) -> list[dict]:
    """Parlamentarios que votaron distinto a la mayoría de su propio partido (si/no)."""
    por_partido: dict[str, list] = defaultdict(list)
    for pid, partido, op in vp.get("_individuales") or []:
        if partido not in SIN_PARTIDO and op in ("si", "no"):
            por_partido[partido].append((pid, op))
    out = []
    for partido, votos in por_partido.items():
        c = Counter(op for _, op in votos)
        if len(votos) < 3 or len(c) < 2:
            continue
        mayoria, n_mayoria = c.most_common(1)[0]
        for pid, op in votos:
            if op != mayoria:
                out.append({"nombre": _NOMBRES.get(pid, pid), "partido": partido, "voto": op,
                            "mayoria_del_partido": mayoria, "votos_mayoria": n_mayoria, "votos_en_contra_de_su_partido": len(votos) - n_mayoria})
    return out


def _jornada(dia: date, vots_camara: list[dict], items: dict) -> dict:
    """Cuánto trabajaron: sesiones y horas en Sala, quiénes votaron, cuántos proyectos se votaron."""
    ses = [s for s in camara.bajar_sesiones_anno(dia.year)
           if s["fecha_inicio"] and s["fecha_inicio"].date() == dia and s["estado"] == "Celebrada"]
    minutos = sum(int((s["fecha_termino"] - s["fecha_inicio"]).total_seconds() // 60) for s in ses if s["fecha_termino"])
    votantes = set()
    for v in vots_camara[:60]:  # voto a voto de las votaciones del día (tope de cortesía)
        try:
            votantes |= {x["votante"] for x in camara.bajar_votos(v["id_fuente"]) if x["opcion"] != "no_vota"}
        except Exception as e:
            log.warning("sin detalle de votación %s: %s", v["id_fuente"], e)
    _cargar_diputados()
    en_ejercicio = set(_COMPLETOS)
    # asistencia oficial (la Cámara la publica con días de atraso; si no está, la lista es "no votaron")
    asistencia: dict[str, str] = {}
    for s in ses:
        try:
            for a in camara.bajar_asistencia(s["id_fuente"]):
                if asistencia.get(a["parlamentario_id"]) != "Asiste":
                    asistencia[a["parlamentario_id"]] = a["tipo"] or "Sin dato"
        except Exception as e:
            log.warning("sin asistencia de la sesión %s: %s", s["id"], e)
    ausentes = sorted(({"nombre": _COMPLETOS.get(p, p), "partido": _PARTIDOS.get(p, "Sin dato"), "registro": tipo}
                       for p, tipo in asistencia.items() if tipo != "Asiste"), key=lambda x: x["nombre"])
    ficha = lambda pid: {"nombre": _COMPLETOS.get(pid, pid), "partido": _PARTIDOS.get(pid, "Sin dato")}
    lista_votaron = sorted((ficha(p) for p in votantes & en_ejercicio), key=lambda x: x["nombre"])
    lista_no = sorted((ficha(p) for p in en_ejercicio - votantes), key=lambda x: x["nombre"]) if votantes else []
    return {
        "camara": {
            "lista_votaron": lista_votaron,
            "lista_no_votaron": lista_no,
            "asistencia_publicada": bool(asistencia),
            "lista_ausentes": ausentes,
            "diputados_ausentes": len(ausentes) if asistencia else None,
            "sesiones": [{"numero": s["numero"], "tipo": s["tipo"], "inicio": s["fecha_inicio"].strftime("%H:%M"),
                          "termino": s["fecha_termino"].strftime("%H:%M") if s["fecha_termino"] else None} for s in ses],
            "horas_en_sala": minutos // 60, "minutos_en_sala_resto": minutos % 60, "minutos_en_sala_total": minutos,
            "votaciones": len(vots_camara),
            "proyectos_votados": len({v["boletin"] for v in vots_camara if v["boletin"]}),
            "diputados_que_votaron": len(lista_votaron), "total_diputados": len(en_ejercicio),
            "diputados_que_no_votaron_nunca": len(lista_no) if votantes else None,
        },
        "senado": {
            "votaciones": sum(it.get("votaciones_del_dia", 0) for it in items.values() if it["camara"] == "senado"),
            "proyectos_votados": sum(1 for it in items.values() if it["camara"] == "senado"),
        },
        "leyes_publicadas": sum(1 for it in items.values() if it.get("tipo") == "ley_publicada"),
    }


def _por_partido(vp: dict) -> list[dict]:
    """Cuántos de cada partido votaron a favor / en contra / abstención (Cámara: por id; Senado: por nombre)."""
    if vp.get("_camara") == "camara":
        if not _PARTIDOS:
            parl, _, _ = camara.bajar_diputados_actuales()
            _PARTIDOS.update({p["id"]: p["partido_actual"] or "Sin dato" for p in parl})
            _NOMBRES.update({p["id"]: f"{p['nombre'].split()[0]} {p['apellido_paterno']}" for p in parl if p["nombre"]})
            _COMPLETOS.update({p["id"]: " ".join(x for x in (p["nombre"], p["apellido_paterno"], p["apellido_materno"]) if x)
                               for p in parl})
        votos = [(v["parlamentario_id"], v["opcion"]) for v in camara.bajar_votos(vp["_id"])]
        partido = lambda pid: _PARTIDOS.get(pid, "Sin dato")
    else:
        if not _PARTIDOS.get("_senado"):
            sen, _ = senado.bajar_senadores(todos=True)
            _PARTIDOS["_senado"] = "ok"
            _PARTIDOS.update({senado.clave_nombre_senador(s): s["partido_actual"] or "Sin dato" for s in sen})
        votos = [(senado.clave_nombre_voto(v["votante"]), v["opcion"]) for v in vp.get("_votos") or []]
        partido = lambda k: _PARTIDOS.get(k, "Sin dato")
    vp["_individuales"] = [(pid, partido(pid), op) for pid, op in votos]
    tabla: dict[str, dict] = {}
    for pid, op in votos:
        fila = tabla.setdefault(partido(pid), {"partido": partido(pid), "si": 0, "no": 0, "abstencion": 0})
        if op in ("si", "no", "abstencion"):
            fila[op] += 1
    return sorted(tabla.values(), key=lambda f: -(f["si"] + f["no"] + f["abstencion"]))


def _particulares(vots: list[dict], maximo: int = 4) -> list[dict]:
    """Algunas votaciones por artículo (las más reñidas primero), para dar contexto."""
    parts = [v for v in vots if not (v.get("tipo") or "").lower().startswith(("general", "discusión general"))]
    parts.sort(key=lambda v: abs((v.get("si") or 0) - (v.get("no") or 0)))
    return [{"tema": (v.get("articulo") or v.get("descripcion") or "")[:260], "si": v.get("si"), "no": v.get("no"),
             "abstencion": v.get("abstencion"), "resultado": v.get("resultado")} for v in parts[:maximo]]


def _enriquecer(it: dict, dia: date) -> None:
    """Contexto del proyecto desde su ficha del Senado: etapa, urgencia, antigüedad, autores, materias."""
    try:
        f = senado.bajar_ficha(it["boletin"])
    except Exception as e:  # el hecho sigue sirviendo sin contexto
        log.warning("sin ficha para %s: %s", it["boletin"], e)
        return
    if not f:
        return
    pr = f["proyecto"]
    ing = pr["fecha_ingreso"]
    it.update({
        "titulo": it.get("titulo") or pr["titulo"],
        "iniciativa": {"mensaje": "mensaje (lo presentó el Presidente de la República)",
                       "mocion": "moción (lo presentaron parlamentarios)"}.get(pr["iniciativa"], pr["iniciativa"]),
        "camara_origen": pr["camara_origen"], "etapa": pr["etapa"], "subetapa": pr["subetapa"],
        "urgencia_actual": pr["urgencia_actual"], "estado": pr["estado"],
        "fecha_ingreso": ing.isoformat() if ing else None,
        "dias_desde_ingreso": (dia - ing).days if ing else None,
        "autores": (pr["autores"] or [])[:6] or None, "materias": (pr["materias"] or [])[:6] or None,
        "urgencias_recibidas": len(f["urgencias"]),
        "ultimos_tramites": [{"fecha": tr["fecha"].isoformat() if tr["fecha"] else None,
                              "camara": tr["camara"], "descripcion": tr["descripcion"]}
                             for tr in f["tramites"] if tr["fecha"] and tr["fecha"] <= dia][-4:],
    })


def recolectar(dia: date, max_items: int = 4) -> dict:
    items: dict[str, dict] = {}

    # ---- Cámara: votaciones del día agrupadas por boletín
    vots = [v for v in camara.bajar_votaciones_anno(dia.year) if v["fecha"] and v["fecha"].date() == dia]
    por_boletin = defaultdict(list)
    for v in vots:
        if v["boletin"]:
            por_boletin[v["boletin"]].append(v)
    for b, vs in por_boletin.items():
        p, detalle = camara.bajar_proyecto(b)
        detalle = [d for d in detalle if d["fecha"] and d["fecha"].date() == dia] or vs
        items[f"C-{b}"] = {
            "id": f"C-{b}", "camara": "camara", "boletin": b, "titulo": p["titulo"] if p else None,
            "votaciones_del_dia": len(vs),
            "aprobadas": sum(1 for d in detalle if (d.get("resultado") or "").lower().startswith("aprob")),
            "rechazadas": sum(1 for d in detalle if (d.get("resultado") or "").lower().startswith("rechaz")),
            "votacion_principal": _voto_principal(detalle),
            "ministerios": (p or {}).get("ministerios"),
            "votaciones_particulares": _particulares(detalle),
            "fuente": url_senado(b),
        }

    # ---- Senado: proyectos con movimiento ese día (votaciones en Sala y leyes publicadas)
    for f in senado.bajar_fichas_desde(dia):
        pr = f["proyecto"]
        b = pr["boletin"]
        tram_dia = [t for t in f["tramites"] if t["fecha"] == dia]
        if pr["fecha_diario_oficial"] == dia:
            items[f"L-{b}"] = {
                "id": f"L-{b}", "camara": "ambas", "boletin": b, "titulo": pr["titulo"], "tipo": "ley_publicada",
                "ley_numero": pr["ley_numero"], "fecha_diario_oficial": dia.isoformat(),
                "fecha_ingreso": pr["fecha_ingreso"].isoformat() if pr["fecha_ingreso"] else None,
                "dias_de_tramitacion": (dia - pr["fecha_ingreso"]).days if pr["fecha_ingreso"] else None,
                "fuente": url_senado(b),
            }
        if not any(t["camara"] == "senado" for t in tram_dia):
            continue
        vs = [v for v in senado.bajar_votaciones(b) if v["fecha"] and v["fecha"].date() == dia]
        if vs:
            items[f"S-{b}"] = {
                "id": f"S-{b}", "camara": "senado", "boletin": b, "titulo": pr["titulo"],
                "etapa": pr["etapa"], "urgencia_actual": pr["urgencia_actual"],
                "votaciones_del_dia": len(vs),
                "aprobadas": sum(1 for v in vs if v["resultado"] == "Aprobado"),
                "rechazadas": sum(1 for v in vs if v["resultado"] == "Rechazado"),
                "votacion_principal": _voto_principal(vs), "votaciones_particulares": _particulares(vs),
                "fuente": url_senado(b),
            }
        # completar etapa/urgencia de lo votado en la Cámara
        if f"C-{b}" in items:
            items[f"C-{b}"].update(etapa=pr["etapa"], urgencia_actual=pr["urgencia_actual"])

    def peso(it):
        if it.get("tipo") == "ley_publicada":
            return 10_000
        vp = it.get("votacion_principal") or {}
        return (vp.get("si") or 0) + (vp.get("no") or 0) + 5 * it.get("votaciones_del_dia", 0)

    elegidos = sorted(items.values(), key=peso, reverse=True)[:max_items]
    for it in elegidos:
        _enriquecer(it, dia)
        vp = it.get("votacion_principal")
        if vp:
            try:
                vp["por_partido"] = _por_partido(vp)
            except Exception as e:
                log.warning("sin votos por partido para %s: %s", it["id"], e)
            vp["discolos"] = _discolos(vp)
            for k in ("_camara", "_id", "_votos", "_individuales"):
                vp.pop(k, None)
    jornada = _jornada(dia, vots, items)
    cahuines = []
    for it in elegidos:
        for d in (it.get("votacion_principal") or {}).get("discolos", []):
            cahuines.append({"tipo": "voto_contra_su_partido", "boletin": it["boletin"], "titulo": it.get("titulo"),
                             **d, "fuente": it["fuente"]})
        for tr in it.get("ultimos_tramites") or []:
            if tr["fecha"] == dia.isoformat() and "reserva de constitucionalidad" in (tr["descripcion"] or "").lower():
                cahuines.append({"tipo": "reserva_de_constitucionalidad", "boletin": it["boletin"],
                                 "titulo": it.get("titulo"), "detalle": tr["descripcion"], "fuente": it["fuente"]})
    if jornada["camara"]["diputados_que_no_votaron_nunca"]:
        cahuines.append({"tipo": "no_votaron", "cantidad": jornada["camara"]["diputados_que_no_votaron_nunca"],
                         "detalle": "diputados que no votaron en ninguna votación del día", "fuente": "camara.cl"})
    log.info("%s: %d hechos encontrados, %d elegidos", dia, len(items), len(elegidos))
    return {"fecha": dia.isoformat(), "jornada": jornada, "cahuines": cahuines, "items": elegidos,
            "total_hechos": len(items), "contexto": _contexto()}


def _contexto() -> dict:
    """Datos fijos verificados a mano (p. ej. la dieta parlamentaria), en guion/contexto.json."""
    import json
    from pathlib import Path
    p = Path(__file__).with_name("contexto.json")
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
