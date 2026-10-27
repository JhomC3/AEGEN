"""Persistencia de Rumbo simple: identidad (1 fila) y día (fecha + 3 valores)."""

from datetime import datetime

from src.db_connection import _use_conn, read_connection

YO_DEFAULT = {
    "quien_soy": "",
    "quien_no": "",
    "construyendo": "",
    "t1_nombre": "Tarea 1",
    "t2_nombre": "Tarea 2",
    "t3_nombre": "Tarea 3",
    "updated_at": "",
}


def get_yo(db_path: str) -> dict:
    with read_connection(db_path) as conn:
        row = conn.execute(
            "SELECT quien_soy, quien_no, construyendo, t1_nombre, t2_nombre, "
            "t3_nombre, updated_at FROM rumbo_yo WHERE id = 1"
        ).fetchone()
    if row is None:
        return dict(YO_DEFAULT)
    return dict(row)


def save_yo(
    db_path: str,
    quien_soy: str,
    quien_no: str,
    construyendo: str,
    t1_nombre: str,
    t2_nombre: str,
    t3_nombre: str,
    conn=None,
) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _use_conn(db_path, conn) as tx:
        tx.execute(
            "INSERT INTO rumbo_yo (id, quien_soy, quien_no, construyendo, "
            "t1_nombre, t2_nombre, t3_nombre, updated_at) "
            "VALUES (1, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (id) DO UPDATE SET quien_soy = excluded.quien_soy, "
            "quien_no = excluded.quien_no, construyendo = excluded.construyendo, "
            "t1_nombre = excluded.t1_nombre, t2_nombre = excluded.t2_nombre, "
            "t3_nombre = excluded.t3_nombre, updated_at = excluded.updated_at",
            (quien_soy, quien_no, construyendo, t1_nombre, t2_nombre, t3_nombre, now),
        )


def get_dia(db_path: str, fecha: str) -> dict | None:
    with read_connection(db_path) as conn:
        row = conn.execute(
            "SELECT fecha, t1, t2, t3 FROM rumbo_dia WHERE fecha = ?", (fecha,)
        ).fetchone()
    return dict(row) if row else None


def save_dia(
    db_path: str,
    fecha: str,
    t1: int,
    t2: int,
    t3: int,
    base_hash: str | None = None,
    conn=None,
) -> None:
    from src.http_shared import hash_estado
    from src.models import ConflictError

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _use_conn(db_path, conn, immediate=base_hash is not None) as tx:
        if base_hash is not None:
            actual = get_dia(db_path, fecha)
            if hash_estado(actual) != base_hash:
                raise ConflictError("Rumbo cambió desde la lectura; relee antes de guardar.")
        tx.execute(
            "INSERT INTO rumbo_dia (fecha, t1, t2, t3, updated_at) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT (fecha) DO UPDATE SET t1 = excluded.t1, t2 = excluded.t2, "
            "t3 = excluded.t3, updated_at = excluded.updated_at",
            (fecha, t1, t2, t3, now),
        )


def get_dias_rango(db_path: str, desde: str, hasta: str) -> list[dict]:
    with read_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT fecha, t1, t2, t3 FROM rumbo_dia "
            "WHERE fecha >= ? AND fecha <= ? ORDER BY fecha",
            (desde, hasta),
        ).fetchall()
    return [dict(r) for r in rows]


def get_respuesta_vigente(db_path: str, pregunta: str) -> dict | None:
    with read_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, pregunta, respuesta, origen, created_at FROM rumbo_respuestas "
            "WHERE pregunta = ? ORDER BY id DESC LIMIT 1",
            (pregunta,),
        ).fetchone()
    return dict(row) if row else None


def get_respuesta_historial(db_path: str, pregunta: str) -> list[dict]:
    with read_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT id, pregunta, respuesta, origen, created_at FROM rumbo_respuestas "
            "WHERE pregunta = ? ORDER BY id DESC",
            (pregunta,),
        ).fetchall()
    return [dict(r) for r in rows]


def guardar_respuesta(
    db_path: str, pregunta: str, respuesta: str, origen: str = "manual", conn=None
) -> int:
    from datetime import datetime

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _use_conn(db_path, conn) as tx:
        cur = tx.execute(
            "INSERT INTO rumbo_respuestas (pregunta, respuesta, origen, created_at) "
            "VALUES (?, ?, ?, ?)",
            (pregunta, respuesta, origen, now),
        )
        pid = cur.lastrowid
        if pid is None:
            raise RuntimeError("No se pudo guardar la respuesta.")
        return int(pid)


def snapshot_rumbo_simple(db_path: str, conn=None) -> dict:
    with _use_conn(db_path, conn) as tx:
        yo = tx.execute("SELECT * FROM rumbo_yo WHERE id = 1").fetchone()
        dias = tx.execute("SELECT fecha, t1, t2, t3, updated_at FROM rumbo_dia").fetchall()
        respuestas = tx.execute(
            "SELECT id, pregunta, respuesta, origen, created_at FROM rumbo_respuestas ORDER BY id"
        ).fetchall()
    return {
        "yo": dict(yo) if yo else None,
        "dias": [dict(r) for r in dias],
        "respuestas": [dict(r) for r in respuestas],
    }


def restore_rumbo_simple(db_path: str, snapshot: dict, conn=None) -> None:
    with _use_conn(db_path, conn) as tx:
        tx.execute("DELETE FROM rumbo_dia")
        tx.execute("DELETE FROM rumbo_yo")
        tx.execute("DELETE FROM rumbo_respuestas")
        yo = snapshot.get("yo")
        if yo:
            tx.execute(
                "INSERT INTO rumbo_yo (id, quien_soy, quien_no, construyendo, "
                "t1_nombre, t2_nombre, t3_nombre, updated_at) "
                "VALUES (1, ?, ?, ?, ?, ?, ?, ?)",
                (
                    yo.get("quien_soy", ""),
                    yo.get("quien_no", ""),
                    yo.get("construyendo", ""),
                    yo.get("t1_nombre", "Tarea 1"),
                    yo.get("t2_nombre", "Tarea 2"),
                    yo.get("t3_nombre", "Tarea 3"),
                    yo.get("updated_at", ""),
                ),
            )
        for d in snapshot.get("dias", []):
            tx.execute(
                "INSERT INTO rumbo_dia (fecha, t1, t2, t3, updated_at) VALUES (?, ?, ?, ?, ?)",
                (d.get("fecha"), d.get("t1"), d.get("t2"), d.get("t3"), d.get("updated_at", "")),
            )
        for r in snapshot.get("respuestas", []):
            tx.execute(
                "INSERT INTO rumbo_respuestas (id, pregunta, respuesta, origen, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    r.get("id"),
                    r.get("pregunta"),
                    r.get("respuesta"),
                    r.get("origen", "manual"),
                    r.get("created_at", ""),
                ),
            )
