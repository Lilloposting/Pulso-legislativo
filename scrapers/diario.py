"""Carga diaria: lo que se movió en el Congreso en los últimos días.

Uso:  python -m scrapers.diario [--dias 3] [--workers 3]

1. Parlamentarios vigentes (diputados y senadores).
2. Proyectos ingresados este año (Cámara) → detecta boletines nuevos.
3. Fichas del Senado con movimiento desde hace N días → trámites, urgencias, documentos, votaciones.
4. Votaciones del año en la Cámara + voto a voto de las nuevas.
5. Sesiones de Sala de la Cámara del año + asistencia de las nuevas.
"""
from __future__ import annotations

import argparse
import logging
from datetime import date, timedelta

from dotenv import load_dotenv

load_dotenv()

from . import carga, db, senado  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dias", type=int, default=3, help="días hacia atrás para buscar movimientos (máx. 30)")
    ap.add_argument("--workers", type=int, default=3, help="descargas en paralelo")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("pulso")

    hoy = date.today()
    desde = hoy - timedelta(days=min(a.dias, 30))
    conn = db.conectar()
    with db.ejecucion(conn, "diario", {"dias": a.dias, "desde": desde.isoformat()}) as c:
        log.info("1/5 parlamentarios")
        carga.sync_parlamentarios(conn, c)

        log.info("2/5 proyectos ingresados en %s", hoy.year)
        anno = carga.sync_proyectos_anno(conn, hoy.year, c)
        if hoy.month == 1 and hoy.day <= a.dias:  # cambio de año: no perder los de fines de diciembre
            anno += carga.sync_proyectos_anno(conn, hoy.year - 1, c)

        log.info("3/5 fichas con movimiento desde %s", desde)
        fichas = {f["proyecto"]["boletin"]: f for f in senado.bajar_fichas_desde(desde)}
        nuevos = carga.boletines_sin_sync(conn, date(hoy.year - 1, 1, 1), hoy, solo_pendientes=True)
        boletines = sorted(set(fichas) | set(nuevos))
        log.info("   %d con movimiento + %d nuevos sin ficha = %d", len(fichas), len(nuevos), len(boletines))
        carga.sync_boletines(conn, boletines, c, a.workers, fichas)

        log.info("4/5 votaciones Cámara %s", hoy.year)
        carga.sync_votaciones_anno(conn, hoy.year, c)
        carga.sync_votos_pendientes(conn, desde - timedelta(days=30), c, a.workers)

        log.info("5/5 sesiones Cámara %s", hoy.year)
        carga.sync_sesiones_anno(conn, hoy.year, c, con_asistencia=True, workers=a.workers)

        log.info("listo: %s", db.dumps(c))
    conn.close()


if __name__ == "__main__":
    main()
