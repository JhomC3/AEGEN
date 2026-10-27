"""Tests de Rumbo simple: validación en borde y scores derivados."""

from datetime import date, timedelta

import pytest

from src.database import init_db
from src.models import RumboDiaInput, RumboYoInput, ValidationError
from src.rumbo_simple_service import (
    guardar_dia,
    guardar_yo,
    score_dia,
    score_semana,
    serie_anual_52,
)


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "gym.db")
    init_db(path)
    return path


def test_yo_guarda_y_lee_con_defaults(db):
    yo = guardar_yo(db, RumboYoInput(quien_soy="Yo", quien_no="No-yo", construyendo="Vida"))
    assert yo["quien_soy"] == "Yo"
    assert yo["t1_nombre"] == "Tarea 1"
    with pytest.raises(ValidationError):
        guardar_yo(db, RumboYoInput(quien_soy="x" * 501))


def test_dia_score_y_reemplazo_idempotente(db):
    hoy = date.today().isoformat()
    r = guardar_dia(db, RumboDiaInput(fecha=hoy, t1=8, t2="7", t3=9))
    assert r == {"fecha": hoy, "t1": 8, "t2": 7, "t3": 9, "score": 24}
    r2 = guardar_dia(db, RumboDiaInput(fecha=hoy, t1=10, t2=10, t3=10))
    assert r2["score"] == 30
    assert score_dia(1, 1, 1) == 3


def test_dia_rechaza_bordes(db):
    hoy = date.today().isoformat()
    with pytest.raises(ValidationError):
        guardar_dia(db, RumboDiaInput(fecha="mala", t1=5, t2=5, t3=5))
    with pytest.raises(ValidationError):
        guardar_dia(db, RumboDiaInput(fecha=hoy, t1=0, t2=5, t3=5))
    with pytest.raises(ValidationError):
        guardar_dia(db, RumboDiaInput(fecha=hoy, t1=11, t2=5, t3=5))
    with pytest.raises(ValidationError):
        guardar_dia(db, RumboDiaInput(fecha=hoy, t1="mucho", t2=5, t3=5))


def test_semana_con_huecos_neutros(db):
    hoy = date.today()
    lunes = (hoy - timedelta(days=hoy.weekday())).isoformat()
    guardar_dia(db, RumboDiaInput(fecha=lunes, t1=10, t2=10, t3=10))
    sem = score_semana(db, hoy.isoformat())
    assert sem["lunes"] == lunes
    assert sem["puntos"] == 30
    assert sem["max"] == 210
    assert len(sem["dias"]) == 7
    assert sem["dias"][0] == {"fecha": lunes, "puntos": 30}
    with pytest.raises(ValidationError):
        score_semana(db, "mala")


def test_serie_anual_52_vacia_y_con_datos(db):
    hoy = date.today().isoformat()
    serie = serie_anual_52(db, hoy)
    assert len(serie) == 52
    assert all(p["puntos"] == 0 for p in serie)
    guardar_dia(db, RumboDiaInput(fecha=hoy, t1=5, t2=5, t3=5))
    serie2 = serie_anual_52(db, hoy)
    assert serie2[-1]["puntos"] == 15
    assert sum(p["puntos"] for p in serie2) == 15


def test_respuesta_apila_y_vigente_es_ultima(db):
    from src.rumbo_simple_service import (
        guardar_respuesta,
        historial_pregunta,
        preguntas_con_estado,
        vigente_pregunta,
    )

    r1 = guardar_respuesta(db, "ex01", "Primera versión")
    r2 = guardar_respuesta(db, "ex01", "Segunda versión")
    assert r1["pregunta"] == "ex01"
    assert vigente_pregunta(db, "ex01")["respuesta"] == "Segunda versión"
    hist = historial_pregunta(db, "ex01")
    assert [h["respuesta"] for h in hist][:2] == ["Segunda versión", "Primera versión"]
    assert hist[-1]["origen"] == "chat"
    assert r2["id"] > r1["id"]
    grupos = preguntas_con_estado(db)
    assert [g["grupo"] for g in grupos] == [
        "Excavación",
        "Piloto automático",
        "Síntesis",
        "Videojuego",
    ]
    total = sum(len(g["preguntas"]) for g in grupos)
    assert total == 36
    ex01 = next(p for g in grupos for p in g["preguntas"] if p["id"] == "ex01")
    assert ex01["respondida"] is True
    ex02 = next(p for g in grupos for p in g["preguntas"] if p["id"] == "ex02")
    assert ex02["respondida"] is True
    assert ex02["vigente"].startswith("Me quejo")


def test_respuesta_rechaza_bordes(db):
    from src.rumbo_simple_service import guardar_respuesta, historial_pregunta, vigente_pregunta

    with pytest.raises(ValidationError):
        guardar_respuesta(db, "no-existe", "texto")
    with pytest.raises(ValidationError):
        guardar_respuesta(db, "ex01", "   ")
    with pytest.raises(ValidationError):
        guardar_respuesta(db, "ex01", "x" * 2001)
    assert vigente_pregunta(db, "ju06")["origen"] == "chat"
    assert len(historial_pregunta(db, "ju06")) == 1


def test_preguntas_anterior_siguiente_bordes():
    from src.rumbo_preguntas import GRUPOS, PREGUNTAS, anterior, siguiente

    assert len(PREGUNTAS) == 36
    assert len(GRUPOS) == 4
    primera, ultima = PREGUNTAS[0]["id"], PREGUNTAS[-1]["id"]
    assert anterior(primera) is None
    assert siguiente(ultima) is None
    assert anterior("xx") is None
    assert siguiente("xx") is None
    assert siguiente(primera)["id"] == PREGUNTAS[1]["id"]
    assert anterior(ultima)["id"] == PREGUNTAS[-2]["id"]
    assert anterior("pa01")["id"] == "ex14"
    assert siguiente("si07")["id"] == "ju01"
