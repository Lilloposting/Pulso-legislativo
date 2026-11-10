"""Genera un episodio: datos del día → guion editable → voz → props.json para Remotion.

Uso:
  python -m guion.generar --fecha 2026-11-09            # datos + guion (Claude o plantilla) + voz
  python -m guion.generar --fecha 2026-11-09 --sin-ia   # guion con plantilla fija
  python -m guion.generar --desde-guion guiones/2026-11-09.md   # tras editar el guion a mano

El guion queda en guiones/<fecha>.md (texto editable con los datos oficiales de cada escena)
y los datos en guiones/<fecha>.datos.json.

Después:
  cd video && npx remotion render Episodio out/<fecha>.mp4 --props=public/episodios/<fecha>/props.json
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from . import archivo, datos, escribir, narrar  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
PUBLIC = RAIZ / "video" / "public"
GUIONES = RAIZ / "guiones"


def producir(ep: dict, guion: dict) -> None:
    """Voz + props.json a partir de datos y guion ya decididos."""
    carpeta = PUBLIC / "episodios" / ep["fecha"]
    rel = f"episodios/{ep['fecha']}"
    segmentos = [("intro", guion["gancho"], None)]
    segmentos += [("noticia", e["narracion"], e) for e in guion["escenas"]]
    segmentos += [("cierre", guion["cierre"], None)]
    por_id = {it["id"]: it for it in ep["items"]}
    escenas = []
    for i, (tipo, texto, esc) in enumerate(segmentos):
        previo = segmentos[i - 1][1] if i > 0 else None
        siguiente = segmentos[i + 1][1] if i + 1 < len(segmentos) else None
        voz = narrar.narrar(texto, carpeta / f"{i:02d}-{tipo}.mp3", previo, siguiente)
        voz["audio"] = f"{rel}/{voz['audio']}"
        escena = {"tipo": tipo, "voz": voz}
        if esc:
            escena.update(titular=esc["titular"], dato=por_id[esc["item_id"]])
        escenas.append(escena)
    props = {"fecha": ep["fecha"], "generado_por": guion["generado_por"], "escenas": escenas,
             "fuentes": sorted({it["fuente"] for it in ep["items"]})}
    (carpeta / "props.json").write_text(json.dumps(props, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    total = sum(e["voz"]["duracion_ms"] for e in escenas) / 1000
    print(f"\nEpisodio {ep['fecha']}: {len(escenas)} escenas, ~{total:.0f} s de voz "
          f"(guion: {guion['generado_por']}, voz: {narrar.motor()})")
    print(f"Render:  cd video && npx remotion render Episodio out/{ep['fecha']}.mp4 --props=public/{rel}/props.json")
    print("Fuentes para la descripción del post:\n  " + "\n  ".join(props["fuentes"]))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fecha", type=date.fromisoformat)
    ap.add_argument("--desde-guion", type=Path, help="usar un guion .md editado a mano")
    ap.add_argument("--sin-ia", action="store_true")
    ap.add_argument("--forzar", action="store_true", help="producir aunque el guion tenga números no verificados")
    ap.add_argument("--max-items", type=int, default=4)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if a.desde_guion:
        ep = json.loads(a.desde_guion.with_suffix("").with_suffix(".datos.json").read_text(encoding="utf-8"))
        guion = archivo.leer_md(a.desde_guion)
        errores = escribir.validar(guion, ep)
        if errores:
            print("Revisa el guion:\n- " + "\n- ".join(errores))
            if not a.forzar:
                raise SystemExit("No se produjo nada. Corrige el guion o usa --forzar.")
        producir(ep, guion)
        return

    if a.fecha:
        ep = datos.recolectar(a.fecha, a.max_items)
    else:  # el último día con actividad
        for atras in range(1, 8):
            ep = datos.recolectar(date.today() - timedelta(days=atras), a.max_items)
            if ep["items"]:
                break
    if not ep["items"]:
        raise SystemExit(f"Sin actividad legislativa el {ep['fecha']}")

    guion = escribir.escribir(ep, usar_ia=not a.sin_ia)
    md = GUIONES / f"{ep['fecha']}.md"
    (GUIONES / f"{ep['fecha']}.datos.json").parent.mkdir(parents=True, exist_ok=True)
    (GUIONES / f"{ep['fecha']}.datos.json").write_text(json.dumps(ep, ensure_ascii=False, indent=1, default=str),
                                                       encoding="utf-8")
    archivo.escribir_md(ep, guion, md)
    print(f"Guion editable: {md}")
    producir(ep, guion)


if __name__ == "__main__":
    main()
