"""Guion editable en Markdown: guiones/<fecha>.md

Formato:
    ## GANCHO
    texto que se lee

    ## ESCENA C-18551-04
    titular: lo que aparece escrito en pantalla
    > líneas que empiezan con ">" son datos de referencia: no se leen
    texto que se lee

    ## CIERRE
    texto que se lee
"""
from __future__ import annotations

import re
from pathlib import Path

CAMARAS = {"camara": "Cámara", "senado": "Senado", "ambas": "Congreso"}


def _ficha(it: dict) -> list[str]:
    """Datos del hecho en líneas cortas, para escribir con ellos a mano."""
    L = []
    L.append(f"{CAMARAS.get(it['camara'], it['camara'])} · boletín {it['boletin']}")
    if it.get("titulo"):
        L.append(f"Título oficial: {it['titulo']}")
    vp = it.get("votacion_principal")
    if vp:
        L.append(f"Votación principal ({(vp.get('tipo') or '').lower()}): {vp.get('resultado')} — "
                 f"{vp.get('si')} a favor, {vp.get('no')} en contra, {vp.get('abstencion')} abstenciones"
                 + (f" · quórum: {vp['quorum']}" if vp.get("quorum") else "")
                 + (f" · {vp['tramite']}" if vp.get("tramite") else ""))
    if vp and vp.get("por_partido"):
        L.append("Cómo votó cada partido (a favor / en contra / abstención):")
        for f in vp["por_partido"]:
            L.append(f"  · {f['partido']}: {f['si']} / {f['no']} / {f['abstencion']}")
    if it.get("votaciones_del_dia"):
        L.append(f"Votaciones ese día: {it['votaciones_del_dia']} ({it.get('aprobadas', 0)} aprobadas, "
                 f"{it.get('rechazadas', 0)} rechazadas)")
    for p in it.get("votaciones_particulares") or []:
        L.append(f"  · {p['resultado']} {p['si']}-{p['no']}-{p['abstencion']}: {p['tema']}")
    if it.get("tipo") == "ley_publicada":
        L.append(f"Publicada en el Diario Oficial: {it.get('ley_numero')} · {it.get('dias_de_tramitacion')} días de tramitación")
    for clave, nombre in (("etapa", "Etapa"), ("subetapa", "Subetapa"), ("urgencia_actual", "Urgencia"),
                          ("iniciativa", "Origen"), ("fecha_ingreso", "Ingresó"),
                          ("dias_desde_ingreso", "Días desde que ingresó"), ("urgencias_recibidas", "Urgencias recibidas")):
        if it.get(clave) not in (None, ""):
            L.append(f"{nombre}: {it[clave]}")
    for clave, nombre in (("ministerios", "Ministerios"), ("autores", "Autores"), ("materias", "Materias")):
        if it.get(clave):
            L.append(f"{nombre}: {', '.join(it[clave])}")
    for tr in it.get("ultimos_tramites") or []:
        L.append(f"  · {tr['fecha']} ({CAMARAS.get(tr['camara'] or '', '')}): {tr['descripcion']}")
    L.append(f"Fuente: {it['fuente']}")
    return L


TITULOS = {"GANCHO": "Apertura (mientras la cámara entra al Congreso)",
           "JORNADA": "¿Cuánto trabajaron? (pasan las listas de nombres)",
           "CAHUIN": "Cahuín del día", "CIERRE": "Cierre"}


def escribir_md(ep: dict, guion: dict, destino: Path) -> None:
    """Guion limpio para leer y editar: solo lo que dice la narradora."""
    out = [f"# Guion · {ep['fecha']}", "",
           "Edita el texto como quieras. Reglas:",
           "- Cada bloque empieza con una línea `## ...`: no la borres.",
           "- `titular:` es lo que sale escrito en pantalla.",
           "- Para dejar un comentario, empieza la línea con `//` (no se lee en el video).",
           "- `…` es una pausa. `[[no_votaron]]` y `[[votaron]]` marcan cuándo aparece cada lista: muévelos, pero no los borres.",
           "- Cada número tiene que estar en los datos oficiales: " + destino.with_name(destino.stem + ".datos.md").name,
           "",
           "## GANCHO", f"<!-- {TITULOS['GANCHO']} -->", guion["gancho"], "",
           "## JORNADA", f"<!-- {TITULOS['JORNADA']} -->", guion.get("jornada", ""), ""]
    por_id = {it["id"]: it for it in ep["items"]}
    for e in guion["escenas"]:
        it = por_id.get(e["item_id"], {})
        out += [f"## ESCENA {e['item_id']}", f"<!-- {CAMARAS.get(it.get('camara', ''), '')}: {it.get('titulo', '')} -->",
                f"titular: {e['titular']}", e["narracion"], ""]
    out += ["## CAHUIN", f"<!-- {TITULOS['CAHUIN']}: déjalo vacío si no hay -->", guion.get("cahuin", ""), "",
            "## CIERRE", f"<!-- {TITULOS['CIERRE']} -->", guion["cierre"], ""]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(out), encoding="utf-8")
    escribir_datos_md(ep, destino.with_name(destino.stem + ".datos.md"))


def escribir_datos_md(ep: dict, destino: Path) -> None:
    """Los datos oficiales del día, para consultar mientras se escribe (no se leen en el video)."""
    out = [f"# Datos oficiales · {ep['fecha']}", "", "Referencia para escribir el guion. Nada de esto se lee en voz alta.", ""]
    j = ep.get("jornada") or {}
    jc, js = j.get("camara", {}), j.get("senado", {})
    out += ["## Jornada",
            f"- Cámara: {len(jc.get('sesiones', []))} sesiones: "
            + ", ".join(f"n° {s['numero']} {s['tipo']} {s['inicio']}-{s['termino']}" for s in jc.get("sesiones", [])),
            f"- {jc.get('horas_en_sala')} h {jc.get('minutos_en_sala_resto')} min en Sala · {jc.get('votaciones')} votaciones · "
            f"{jc.get('proyectos_votados')} proyectos votados",
            f"- {jc.get('diputados_que_votaron')} de {jc.get('total_diputados')} diputados votaron al menos una vez; "
            f"{jc.get('diputados_que_no_votaron_nunca')} no votaron nunca"
            + (" (asistencia oficial publicada)" if jc.get("asistencia_publicada") else " (la asistencia oficial aún no se publica)"),
            "- No votaron: " + ", ".join(f"{p['nombre']} ({p['partido']})" for p in jc.get("lista_no_votaron", [])),
            f"- Senado: {js.get('votaciones')} votaciones · {js.get('proyectos_votados')} proyectos · "
            f"leyes publicadas: {j.get('leyes_publicadas')}", ""]
    for it in ep["items"]:
        out += [f"## {it['id']}"] + [f"- {l}" for l in _ficha(it)] + [""]
    out += ["## Cahuines"]
    for c in ep.get("cahuines") or []:
        if c["tipo"] == "voto_contra_su_partido":
            out.append(f"- {c['nombre']} ({c['partido']}) votó {c['voto']} y su partido {c['mayoria_del_partido']} "
                       f"({c['votos_mayoria']} votos) · boletín {c['boletin']}")
        elif c["tipo"] == "reserva_de_constitucionalidad":
            out.append(f"- {c['detalle']} · boletín {c['boletin']}")
        else:
            out.append(f"- {c.get('cantidad')} {c.get('detalle')}")
    ctx = {k: v for k, v in (ep.get("contexto") or {}).items() if not k.startswith("_") and v is not None}
    if ctx:
        out += ["", "## Contexto fijo"] + [f"- {k}: {v}" for k, v in ctx.items()]
    destino.write_text("\n".join(out) + "\n", encoding="utf-8")


def leer_md(origen: Path) -> dict:
    texto = re.sub(r"<!--.*?-->", "", origen.read_text(encoding="utf-8"), flags=re.S)
    guion = {"gancho": "", "jornada": "", "escenas": [], "cahuin": "", "cierre": "", "generado_por": "editado a mano"}
    for bloque in re.split(r"^## ", texto, flags=re.M)[1:]:
        cabecera, _, cuerpo = bloque.partition("\n")
        # ">" = datos de referencia, "//" = comentarios del editor: ninguno se lee en el video
        lineas = [l for l in cuerpo.splitlines() if not l.lstrip().startswith((">", "//"))]
        titular = ""
        resto = []
        for l in lineas:
            if l.lower().startswith("titular:"):
                titular = l.split(":", 1)[1].strip()
            else:
                resto.append(l)
        narracion = re.sub(r"\s+", " ", " ".join(resto)).strip()
        cab = cabecera.strip().upper()
        if cab in ("GANCHO", "JORNADA"):
            guion[cab.lower()] = narracion
        elif cab in ("CAHUIN", "CAHUÍN"):
            guion["cahuin"] = narracion
        elif cab == "CIERRE":
            guion["cierre"] = narracion
        elif cab.startswith("ESCENA"):
            guion["escenas"].append({"item_id": cabecera.split(None, 1)[1].strip(), "titular": titular,
                                     "narracion": narracion})
    return guion
