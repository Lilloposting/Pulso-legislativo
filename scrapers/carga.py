"""Pasos de sincronización reutilizados por la carga diaria y la histórica.

Regla: las descargas corren en paralelo (hilos); las escrituras en la base, en el hilo principal.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from . import camara, db, senado

log = logging.getLogger("pulso")


def _sumar(conteos: dict, clave: str, n: int = 1) -> None:
    conteos[clave] = conteos.get(clave, 0) + n


def _en_paralelo(func, items, workers: int, conteos: dict, etiqueta: str):
    """Ejecuta func(item) en paralelo y entrega (item, resultado). Los errores se registran y se cuentan."""
    items = list(items)
    if not items:
        return
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futuros = {ex.submit(func, it): it for it in items}
        for i, fut in enumerate(as_completed(futuros), 1):
            it = futuros[fut]
            try:
                yield it, fut.result()
            except Exception as e:  # una fuente caída no detiene la corrida completa
                _sumar(conteos, "errores")
                log.warning("%s %s: %s", etiqueta, it, e)
            if i % 100 == 0 or i == len(items):
                log.info("%s: %d/%d", etiqueta, i, len(items))


# ---------------------------------------------------------------- parlamentarios
COLS_PARL = ["id", "camara", "id_fuente", "nombre", "apellido_paterno", "apellido_materno", "sexo",
             "fecha_nacimiento", "region", "circunscripcion", "distrito", "partido_actual", "email",
             "url_curriculum", "vigente", "url_foto", "comite"]


def sync_parlamentarios(conn, conteos: dict, periodos_camara: list[int] | None = None) -> None:
    """Diputados (actuales o de los períodos indicados) y senadores vigentes."""
    lotes = []
    if periodos_camara:
        for pid in periodos_camara:
            lotes.append((False, *camara.bajar_diputados_periodo(pid)))
    lotes.append((True, *camara.bajar_diputados_actuales()))
    with conn.cursor() as cur:
        for vigente, parl, mandatos, milit in lotes:
            for p in parl:
                p["vigente"] = vigente
            if vigente:
                cur.execute("update parlamentarios set vigente = false where camara = 'camara'")
            _sumar(conteos, "parlamentarios", db.upsert(cur, "parlamentarios", parl, ["id"], COLS_PARL,
                                                        no_pisar_con_null=True))
            db.upsert(cur, "mandatos", mandatos, ["parlamentario_id", "fecha_inicio"])
            db.upsert(cur, "militancias", milit, ["parlamentario_id", "partido_id", "fecha_inicio"])
        senadores, mandatos_sen = senado.bajar_senadores(todos=bool(periodos_camara))
        cur.execute("update parlamentarios set vigente = false where camara = 'senado'")
        _sumar(conteos, "parlamentarios", db.upsert(cur, "parlamentarios", senadores, ["id"], COLS_PARL,
                                                    no_pisar_con_null=True))
        db.upsert(cur, "mandatos", mandatos_sen, ["parlamentario_id", "fecha_inicio"])
    conn.commit()


def sync_legislaturas(conn, conteos: dict) -> None:
    with conn.cursor() as cur:
        _sumar(conteos, "legislaturas", db.upsert(cur, "legislaturas", camara.bajar_legislaturas(), ["id"]))
    conn.commit()


# ---------------------------------------------------------------- proyectos
def sync_proyectos_anno(conn, anno: int, conteos: dict) -> list[str]:
    """Inserta/actualiza los datos básicos de los proyectos ingresados en el año. Devuelve sus boletines."""
    proyectos = camara.bajar_proyectos_anno(anno)
    with conn.cursor() as cur:
        _sumar(conteos, "proyectos_basicos", db.upsert(cur, "proyectos", proyectos, ["boletin"],
                                                       db.COLUMNAS_PROYECTO_BASICO, no_pisar_con_null=True))
    conn.commit()
    return [p["boletin"] for p in proyectos]


def _mapa_senadores(conn) -> dict[str, str]:
    with conn.cursor() as cur:
        cur.execute("select id, nombre, apellido_paterno from parlamentarios where camara = 'senado'")
        return {senado.clave_nombre_senador({"nombre": n, "apellido_paterno": a}): i for i, n, a in cur.fetchall()}


def _descargar_boletin(boletin: str, ficha: dict | None) -> dict:
    ficha = ficha or senado.bajar_ficha(boletin)
    vot_senado = senado.bajar_votaciones(boletin)
    p_camara, vot_camara = camara.bajar_proyecto(boletin)
    return {"ficha": ficha, "vot_senado": vot_senado, "p_camara": p_camara, "vot_camara": vot_camara}


def sync_boletines(conn, boletines: list[str], conteos: dict, workers: int = 3,
                   fichas: dict[str, dict] | None = None) -> None:
    """Ficha completa de cada boletín: tramitación (Senado), votaciones de ambas cámaras y ministerios."""
    fichas = fichas or {}
    senadores = _mapa_senadores(conn)
    pendientes = 0
    for boletin, r in _en_paralelo(lambda b: _descargar_boletin(b, fichas.get(b)), boletines, workers,
                                   conteos, "boletines"):
        with conn.cursor() as cur:
            ficha = r["ficha"]
            if ficha:
                db.upsert(cur, "proyectos", [ficha["proyecto"]], ["boletin"], db.COLUMNAS_PROYECTO_FICHA,
                          no_pisar_con_null=True)
            if r["p_camara"]:
                pc = r["p_camara"]
                db.upsert(cur, "proyectos", [pc], ["boletin"], db.COLUMNAS_PROYECTO_BASICO + ["ministerios"],
                          no_pisar_con_null=True)
            cur.execute("select 1 from proyectos where boletin = %s", (boletin,))
            if cur.fetchone() is None:
                _sumar(conteos, "boletines_sin_datos")
                continue
            if ficha:
                _sumar(conteos, "tramites", db.reemplazar_hijos(cur, "tramites", boletin, ficha["tramites"]))
                _sumar(conteos, "urgencias", db.reemplazar_hijos(cur, "urgencias", boletin, ficha["urgencias"]))
                _sumar(conteos, "documentos", db.reemplazar_hijos(cur, "documentos", boletin, ficha["documentos"]))
            for v in r["vot_senado"]:
                for voto in v["votos"]:
                    voto["parlamentario_id"] = senadores.get(senado.clave_nombre_voto(voto["votante"]))
            _sumar(conteos, "votaciones_senado", len(db.guardar_votaciones(cur, r["vot_senado"])))
            _sumar(conteos, "votaciones_camara", len(db.guardar_votaciones(cur, r["vot_camara"])))
            cur.execute("update proyectos set tramitacion_sync_en = now() where boletin = %s", (boletin,))
        _sumar(conteos, "boletines")
        pendientes += 1
        if pendientes >= 25:
            conn.commit()
            pendientes = 0
    conn.commit()


def boletines_sin_sync(conn, desde: date, hasta: date, solo_pendientes: bool) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("select boletin from proyectos where fecha_ingreso between %s and %s "
                    + ("and tramitacion_sync_en is null " if solo_pendientes else "")
                    + "order by fecha_ingreso", (desde, hasta))
        return [r[0] for r in cur.fetchall()]


# ---------------------------------------------------------------- votaciones Cámara
def sync_votaciones_anno(conn, anno: int, conteos: dict) -> None:
    vots = camara.bajar_votaciones_anno(anno)
    with conn.cursor() as cur:
        _sumar(conteos, "votaciones_camara", len(db.guardar_votaciones(cur, vots)))
    conn.commit()


def sync_votos_pendientes(conn, desde: date, conteos: dict, workers: int = 3) -> None:
    """Descarga el voto a voto de las votaciones de la Cámara que aún no lo tienen."""
    with conn.cursor() as cur:
        cur.execute("select id, id_fuente from votaciones where camara = 'camara' and detalle_sync_en is null "
                    "and fecha >= %s order by fecha", (desde,))
        pendientes = dict((f, i) for i, f in cur.fetchall())
    n = 0
    for id_fuente, votos in _en_paralelo(camara.bajar_votos, list(pendientes), workers, conteos, "votos camara"):
        with conn.cursor() as cur:
            db.guardar_votos(cur, pendientes[id_fuente], votos)
        _sumar(conteos, "votos_camara", len(votos))
        n += 1
        if n % 50 == 0:
            conn.commit()
    conn.commit()


# ---------------------------------------------------------------- sesiones Cámara
def sync_sesiones_anno(conn, anno: int, conteos: dict, con_asistencia: bool, workers: int = 3) -> None:
    sesiones = camara.bajar_sesiones_anno(anno)
    with conn.cursor() as cur:
        _sumar(conteos, "sesiones", db.upsert(cur, "sesiones", sesiones, ["id"],
                                              [c for c in sesiones[0] if c != "legislatura"] if sesiones else None))
        if not con_asistencia:
            conn.commit()
            return
        cur.execute("select id_fuente from sesiones where camara = 'camara' and asistencia_sync_en is null "
                    "and estado = 'Celebrada' and extract(year from fecha_inicio) = %s", (anno,))
        pendientes = [r[0] for r in cur.fetchall()]
    conn.commit()
    for sid, asis in _en_paralelo(camara.bajar_asistencia, pendientes, workers, conteos, "asistencia"):
        with conn.cursor() as cur:
            cur.execute("delete from asistencia where sesion_id = %s", (f"C-{sid}",))
            db.upsert(cur, "asistencia", asis, ["sesion_id", "parlamentario_id"])
            cur.execute("update sesiones set asistencia_sync_en = now() where id = %s", (f"C-{sid}",))
        _sumar(conteos, "asistencia", len(asis))
    conn.commit()
