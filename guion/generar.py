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


def segmentos_de(guion: dict) -> list[tuple]:
    seg = [("intro", guion["gancho"], None)]
    if guion.get("jornada"):
        seg.append(("jornada", guion["jornada"], None))
    seg += [("noticia", e["narracion"], e) for e in guion["escenas"]]
    if guion.get("cahuin"):
        seg.append(("cahuin", guion["cahuin"], None))
    seg.append(("cierre", guion["cierre"], None))
    return seg


def presupuesto(guion: dict) -> int:
    """Muestra qué escenas se van a narrar y cuántos caracteres de ElevenLabs cuesta. Devuelve el total."""
    total = 0
    print(f"\nVoz: {narrar.motor()}")
    for tipo, texto, _ in segmentos_de(guion):
        limpio = narrar.texto_para_voz(texto)
        cache = narrar.en_cache(texto)
        costo = 0 if cache or narrar.motor() != "elevenlabs" else len(limpio)
        total += costo
        print(f"  {tipo:8s} {len(limpio):4d} caracteres  {'(ya generado, gratis)' if cache else ''}")
    if narrar.motor() == "elevenlabs":
        print(f"  Costo en ElevenLabs: {total} caracteres")
    return total


def producir(ep: dict, guion: dict) -> None:
    """Voz + props.json a partir de datos y guion ya decididos."""
    carpeta = PUBLIC / "episodios" / ep["fecha"]
    rel = f"episodios/{ep['fecha']}"
    narrar.crear_pitido(PUBLIC / "pitido.wav")
    segmentos = segmentos_de(guion)
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
        elif tipo == "jornada":
            escena["jornada"] = ep.get("jornada")
        elif tipo == "cahuin":
            escena["cahuines"] = ep.get("cahuines")
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
    ap.add_argument("--borrador", action="store_true", help="voz gratis (edge-tts) para revisar sin gastar créditos")
    ap.add_argument("--si", action="store_true", help="no pedir confirmación antes de gastar créditos de ElevenLabs")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if a.borrador:
        narrar.usar_voz_gratis()

    def confirmar(guion: dict) -> None:
        costo = presupuesto(guion)
        if costo and not a.si:
            if input("¿Generar la voz con ElevenLabs? [s/N] ").strip().lower() not in ("s", "si", "sí"):
                raise SystemExit("Cancelado. Usa --borrador para revisar con la voz gratis.")

    if a.desde_guion:
        ep = json.loads(a.desde_guion.with_suffix("").with_suffix(".datos.json").read_text(encoding="utf-8"))
        guion = archivo.leer_md(a.desde_guion)
        errores = escribir.validar(guion, ep)
        if errores:
            print("Revisa el guion:\n- " + "\n- ".join(errores))
            if not a.forzar:
                raise SystemExit("No se produjo nada. Corrige el guion o usa --forzar.")
        confirmar(guion)
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
    if narrar.motor() == "elevenlabs" and not a.si:  # primero se revisa el guion; la voz se paga después
        print("Revisa y edita el guion; después produce la voz con:\n"
              f"  python -m guion.generar --desde-guion {md.relative_to(RAIZ).as_posix()}"
              "   (o agrega --borrador para la voz gratis)")
        return
    producir(ep, guion)


if __name__ == "__main__":
    main()
