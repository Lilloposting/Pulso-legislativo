"""Carga histórica: descarga todos los años disponibles en un rango. Es reanudable.

Uso:
  python -m scrapers.historico --desde 2018 --hasta 2026
  python -m scrapers.historico --desde 2022 --solo proyectos        # solo un paso
  python -m scrapers.historico --desde 2018 --votos-desde 2022      # voto a voto solo desde 2022

Pasos (--solo): base, proyectos, fichas, votaciones, sesiones.
- Las fichas ya sincronizadas se saltan (usa --refrescar para volver a bajarlas).
- El voto a voto y la asistencia pesan mucho (~200 mil filas por año en la Cámara);
  por defecto se bajan desde 2022 para no pasar el límite gratuito de Supabase (500 MB).
"""
from __future__ import annotations

import argparse
import logging
from datetime import date

from dotenv import load_dotenv

load_dotenv()

from . import camara, carga, db  # noqa: E402

PASOS = ["base", "proyectos", "fichas", "votaciones", "sesiones"]


def main() -> None:
    hoy = date.today()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desde", type=int, default=2018)
    ap.add_argument("--hasta", type=int, default=hoy.year)
    ap.add_argument("--votos-desde", type=int, default=2022, help="año desde el que se baja voto a voto y asistencia")
    ap.add_argument("--solo", choices=PASOS, action="append", help="ejecutar solo estos pasos (repetible)")
    ap.add_argument("--refrescar", action="store_true", help="volver a bajar fichas ya sincronizadas")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    pasos = a.solo or PASOS
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("pulso")
    annos = list(range(a.desde, a.hasta + 1))

    conn = db.conectar()
    with db.ejecucion(conn, "historico", vars(a)) as c:
        if "base" in pasos:
            log.info("base: legislaturas y parlamentarios por período")
            carga.sync_legislaturas(conn, c)
            periodos = [p["id"] for p in camara.bajar_periodos()
                        if p["fecha_termino"] and p["fecha_termino"].year > a.desde]
            carga.sync_parlamentarios(conn, c, periodos_camara=periodos)

        if "proyectos" in pasos:
            for anno in annos:
                log.info("proyectos %s", anno)
                carga.sync_proyectos_anno(conn, anno, c)

        if "fichas" in pasos:
            boletines = carga.boletines_sin_sync(conn, date(a.desde, 1, 1), date(a.hasta, 12, 31),
                                                 solo_pendientes=not a.refrescar)
            log.info("fichas: %d boletines por sincronizar", len(boletines))
            carga.sync_boletines(conn, boletines, c, a.workers)

        if "votaciones" in pasos:
            for anno in annos:
                log.info("votaciones Cámara %s", anno)
                carga.sync_votaciones_anno(conn, anno, c)
            log.info("voto a voto Cámara desde %s", a.votos_desde)
            carga.sync_votos_pendientes(conn, date(max(a.votos_desde, a.desde), 1, 1), c, a.workers)

        if "sesiones" in pasos:
            for anno in annos:
                log.info("sesiones Cámara %s", anno)
                carga.sync_sesiones_anno(conn, anno, c, con_asistencia=anno >= a.votos_desde, workers=a.workers)

        log.info("listo: %s", db.dumps(c))
    conn.close()


if __name__ == "__main__":
    main()
