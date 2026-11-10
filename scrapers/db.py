"""Escritura en Supabase (Postgres) mediante upserts idempotentes.

Correr el mismo scraper dos veces no duplica nada: cada tabla tiene una llave natural.
"""
from __future__ import annotations

import json
import os
from contextlib import contextmanager

import psycopg
from psycopg.types.json import Jsonb

COLUMNAS_PROYECTO_BASICO = ["boletin", "boletin_num", "titulo", "fecha_ingreso", "iniciativa", "camara_origen",
                            "camara_id", "admisible"]
COLUMNAS_PROYECTO_FICHA = ["boletin", "boletin_num", "titulo", "fecha_ingreso", "iniciativa", "camara_origen",
                           "urgencia_actual", "etapa", "subetapa", "ley_numero", "fecha_diario_oficial", "estado",
                           "refundidos", "url_documento", "autores", "materias"]
COLUMNAS_VOTACION = ["camara", "id_fuente", "boletin", "fecha", "sesion", "descripcion", "articulo", "tramite",
                     "tramite_reglamentario", "tipo", "quorum", "resultado", "si", "no", "abstencion", "pareo",
                     "dispensado"]
JSON_COLS = {"autores", "ministerios", "parametros", "conteos", "fuentes"}


def conectar() -> psycopg.Connection:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("Falta DATABASE_URL (ver .env.example)")
    # prepare_threshold=None: compatible con el pooler de Supabase
    return psycopg.connect(url, autocommit=False, prepare_threshold=None)


def _valor(col, v):
    if col in JSON_COLS and v is not None:
        return Jsonb(v)
    return v


def upsert(cur, tabla: str, filas: list[dict], llave: list[str], columnas: list[str] | None = None,
           no_pisar_con_null: bool = False) -> int:
    """INSERT ... ON CONFLICT (llave) DO UPDATE.

    no_pisar_con_null=True conserva el valor existente cuando el nuevo es NULL
    (útil cuando dos fuentes aportan campos distintos de una misma fila).
    """
    if not filas:
        return 0
    columnas = columnas or list(filas[0].keys())
    actualizar = [c for c in columnas if c not in llave]
    if no_pisar_con_null:
        sets = [f"{c} = coalesce(excluded.{c}, {tabla}.{c})" for c in actualizar]
    else:
        sets = [f"{c} = excluded.{c}" for c in actualizar]
    if "actualizado_en" in _columnas_tabla(cur, tabla):
        sets.append("actualizado_en = now()")
    accion = f"do update set {', '.join(sets)}" if sets else "do nothing"
    sql = (f"insert into {tabla} ({', '.join(columnas)}) values ({', '.join(['%s'] * len(columnas))}) "
           f"on conflict ({', '.join(llave)}) {accion}")
    vistos, datos = set(), []
    for f in filas:  # sin llaves repetidas en un mismo lote
        k = tuple(f.get(c) for c in llave)
        if k in vistos:
            continue
        vistos.add(k)
        datos.append([_valor(c, f.get(c)) for c in columnas])
    cur.executemany(sql, datos)
    return len(datos)


_cache_cols: dict[str, set[str]] = {}


def _columnas_tabla(cur, tabla: str) -> set[str]:
    if tabla not in _cache_cols:
        cur.execute("select column_name from information_schema.columns where table_schema='public' "
                    "and table_name=%s", (tabla,))
        _cache_cols[tabla] = {r[0] for r in cur.fetchall()}
    return _cache_cols[tabla]


def reemplazar_hijos(cur, tabla: str, boletin: str, filas: list[dict]) -> int:
    """Borra y vuelve a insertar las filas de un boletín (trámites, urgencias, documentos).

    La fuente entrega siempre la lista completa, así que reemplazar es más simple y seguro que
    intentar calzar filas que pueden cambiar de orden.
    """
    cur.execute(f"delete from {tabla} where boletin = %s", (boletin,))
    if not filas:
        return 0
    cols = list(filas[0].keys())
    cur.executemany(f"insert into {tabla} ({', '.join(cols)}) values ({', '.join(['%s'] * len(cols))})",
                    [[f[c] for c in cols] for f in filas])
    return len(filas)


def guardar_votaciones(cur, votaciones: list[dict], no_pisar_con_null: bool = True) -> dict[str, int]:
    """Upsert de votaciones; devuelve {id_fuente: id interno}. Si traen 'votos', también los guarda."""
    if not votaciones:
        return {}
    upsert(cur, "votaciones", votaciones, ["camara", "id_fuente"], COLUMNAS_VOTACION, no_pisar_con_null)
    camara = votaciones[0]["camara"]
    cur.execute("select id_fuente, id from votaciones where camara = %s and id_fuente = any(%s)",
                (camara, [v["id_fuente"] for v in votaciones]))
    ids = dict(cur.fetchall())
    for v in votaciones:
        if "votos" in v:
            guardar_votos(cur, ids[v["id_fuente"]], v["votos"])
    return ids


def guardar_votos(cur, votacion_id: int, votos: list[dict]) -> None:
    cur.execute("delete from votos where votacion_id = %s", (votacion_id,))
    vistos = set()
    filas = []
    for v in votos:
        if v["votante"] in vistos:
            continue
        vistos.add(v["votante"])
        filas.append((votacion_id, v["votante"], v.get("parlamentario_id"), v["opcion"]))
    if filas:
        cur.executemany("insert into votos (votacion_id, votante, parlamentario_id, opcion) values (%s,%s,%s,%s)",
                        filas)
    cur.execute("update votaciones set detalle_sync_en = now() where id = %s", (votacion_id,))


@contextmanager
def ejecucion(conn, tipo: str, parametros: dict):
    """Registra cada corrida en la tabla `ejecuciones` (inicio, fin, conteos, error)."""
    with conn.cursor() as cur:
        cur.execute("insert into ejecuciones (tipo, parametros) values (%s, %s) returning id",
                    (tipo, Jsonb(parametros)))
        eid = cur.fetchone()[0]
    conn.commit()
    conteos: dict[str, int] = {}
    try:
        yield conteos
    except BaseException as e:
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute("update ejecuciones set fin=now(), estado='error', conteos=%s, error=%s where id=%s",
                        (Jsonb(conteos), f"{type(e).__name__}: {e}"[:4000], eid))
        conn.commit()
        raise
    with conn.cursor() as cur:
        estado = "ok_con_errores" if conteos.get("errores") else "ok"
        cur.execute("update ejecuciones set fin=now(), estado=%s, conteos=%s where id=%s",
                    (estado, Jsonb(conteos), eid))
    conn.commit()


def dumps(x) -> str:
    return json.dumps(x, ensure_ascii=False, default=str)
