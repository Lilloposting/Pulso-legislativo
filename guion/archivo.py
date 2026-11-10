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


def escribir_md(ep: dict, guion: dict, destino: Path) -> None:
    por_id = {it["id"]: it for it in ep["items"]}
    out = [f"# Guion · {ep['fecha']}", "",
           "<!-- Edita el texto libremente. Las líneas con > son los datos oficiales del hecho (no se leen).",
           "     Cada número que escribas tiene que estar en esos datos: el generador lo revisa.",
           f"     Para regenerar voz y video:  python -m guion.generar --desde-guion {destino.as_posix()} -->", "",
           "## GANCHO", guion["gancho"], ""]
    for e in guion["escenas"]:
        out += [f"## ESCENA {e['item_id']}", f"titular: {e['titular']}"]
        out += [f"> {l}" for l in _ficha(por_id[e["item_id"]])]
        out += [e["narracion"], ""]
    out += ["## CIERRE", guion["cierre"], ""]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(out), encoding="utf-8")


def leer_md(origen: Path) -> dict:
    texto = re.sub(r"<!--.*?-->", "", origen.read_text(encoding="utf-8"), flags=re.S)
    guion = {"gancho": "", "escenas": [], "cierre": "", "generado_por": "editado a mano"}
    for bloque in re.split(r"^## ", texto, flags=re.M)[1:]:
        cabecera, _, cuerpo = bloque.partition("\n")
        lineas = [l for l in cuerpo.splitlines() if not l.lstrip().startswith(">")]
        titular = ""
        resto = []
        for l in lineas:
            if l.lower().startswith("titular:"):
                titular = l.split(":", 1)[1].strip()
            else:
                resto.append(l)
        narracion = re.sub(r"\s+", " ", " ".join(resto)).strip()
        cab = cabecera.strip().upper()
        if cab == "GANCHO":
            guion["gancho"] = narracion
        elif cab == "CIERRE":
            guion["cierre"] = narracion
        elif cab.startswith("ESCENA"):
            guion["escenas"].append({"item_id": cabecera.split(None, 1)[1].strip(), "titular": titular,
                                     "narracion": narracion})
    return guion
