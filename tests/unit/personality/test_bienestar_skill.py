"""Subagente de bienestar: autorización, consultas y escrituras con confirmación."""

import json
import re

import pytest
import respx
from httpx import Response
from pydantic import SecretStr

from src.core.config import settings
from src.personality.skills.bienestar import tools as bt
from src.personality.skills.bienestar.domain_http import _PENDIENTES

BASE = "http://127.0.0.1:8101"
CHAT = "chat-dueno"


@pytest.fixture
def cfg(monkeypatch):
    monkeypatch.setattr(settings, "BIENESTAR_DOMAIN_URL", BASE)
    monkeypatch.setattr(settings, "BIENESTAR_SYNC_TOKEN", SecretStr("tok-test"))
    monkeypatch.setattr(settings, "BIENESTAR_ALLOWED_CHAT_IDS", [CHAT])
    monkeypatch.setattr(settings, "ADMIN_CHAT_ID", None)
    monkeypatch.setattr(settings, "BIENESTAR_TZ", "America/Bogota")
    _PENDIENTES.clear()
    yield
    _PENDIENTES.clear()


def _hash_de(texto):
    m = re.search(r"sí ([0-9a-f]{12})", texto)
    assert m, texto
    return m.group(1)


@pytest.mark.asyncio
async def test_deniega_chat_no_autorizado(cfg):
    r = await bt.bienestar_tool.ainvoke({
        "user_message": "qué entrené hoy",
        "chat_id": "otro-chat",
    })
    assert "privado" in r


@pytest.mark.asyncio
@respx.mock
async def test_consulta_sesion_vacia_y_con_datos(cfg):
    respx.get(f"{BASE}/api/v1/sesion").mock(
        side_effect=[
            Response(200, json={"schema_version": 1, "has_data": False, "sets": []}),
            Response(
                200,
                json={
                    "schema_version": 1,
                    "has_data": True,
                    "sets": [
                        {
                            "ejercicio": "Press",
                            "kg": 80.0,
                            "reps": 8.0,
                            "rir": 1.0,
                            "rm": 104.0,
                        }
                    ],
                },
            ),
        ]
    )
    r = await bt.bienestar_tool.ainvoke({
        "user_message": "qué entrené hoy",
        "chat_id": CHAT,
    })
    assert "sin registros" in r
    r = await bt.bienestar_tool.ainvoke({
        "user_message": "qué entrené ayer",
        "chat_id": CHAT,
    })
    assert "Press" in r and "RM 104" in r


@pytest.mark.asyncio
async def test_fecha_ambigua_pide_aclaracion(cfg):
    r = await bt.bienestar_tool.ainvoke({"user_message": "rumbo", "chat_id": CHAT})
    assert "consultar o registrar" in r or "fecha" in r


@pytest.mark.asyncio
@respx.mock
async def test_escritura_preview_y_confirmacion(cfg):
    dia = {"schema_version": 1, "has_data": False, "sets": []}
    get = respx.get(f"{BASE}/api/v1/sesion").mock(return_value=Response(200, json=dia))
    post = respx.post(f"{BASE}/api/v1/sesion").mock(
        return_value=Response(
            200,
            json={
                "schema_version": 1,
                "saved_count": 1,
                "sets": [
                    {
                        "ejercicio": "Press",
                        "kg": 80.0,
                        "reps": 8.0,
                        "rir": 1.0,
                        "rm": 104.0,
                    }
                ],
            },
        )
    )
    prev = await bt.bienestar_tool.ainvoke({
        "user_message": "guarda Press 80x8 rir1 hoy",
        "chat_id": CHAT,
    })
    assert post.called is False
    h = _hash_de(prev)
    r = await bt.bienestar_tool.ainvoke({"user_message": f"sí {h}", "chat_id": CHAT})
    assert post.called is True
    assert "Guardado" in r and "104" in r
    assert get.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_confirmacion_con_dia_cambiado_409(cfg):
    import json as _json

    dia = {"schema_version": 1, "has_data": False, "sets": [], "base_hash": "a"}
    respx.get(f"{BASE}/api/v1/sesion").mock(return_value=Response(200, json=dia))
    post = respx.post(f"{BASE}/api/v1/sesion").mock(
        return_value=Response(409, json={"detail": "El día cambió desde la lectura."})
    )
    prev = await bt.bienestar_tool.ainvoke({
        "user_message": "guarda Press 80x8 hoy",
        "chat_id": CHAT,
    })
    r = await bt.bienestar_tool.ainvoke({
        "user_message": f"sí {_hash_de(prev)}",
        "chat_id": CHAT,
    })
    assert post.called is True
    body = _json.loads(post.calls[0].request.content)
    assert body["base_hash"] == "a"
    assert "Pide de nuevo" in r


@pytest.mark.asyncio
async def test_hash_ajeno_se_rechaza(cfg):
    r = await bt.bienestar_tool.ainvoke({
        "user_message": "sí abcdef123456",
        "chat_id": CHAT,
    })
    assert "no corresponde" in r


@pytest.mark.asyncio
@respx.mock
async def test_undo_con_preview(cfg):
    respx.get(f"{BASE}/api/v1/undo/peek").mock(
        return_value=Response(
            200,
            json={
                "schema_version": 1,
                "kind": "sesion",
                "entry_id": 41,
                "fecha_iso": "2026-10-04",
            },
        )
    )
    post = respx.post(f"{BASE}/api/v1/undo").mock(
        return_value=Response(200, json={"schema_version": 1, "kind": "sesion"})
    )
    prev = await bt.bienestar_tool.ainvoke({
        "user_message": "deshaz lo último",
        "chat_id": CHAT,
    })
    assert post.called is False
    assert "entrada #41" in prev
    r = await bt.bienestar_tool.ainvoke({
        "user_message": f"sí {_hash_de(prev)}",
        "chat_id": CHAT,
    })
    assert "Deshecho" in r
    body = json.loads(post.calls[0].request.content)
    assert body["expected"] == {"id": 41, "kind": "sesion"}


@pytest.mark.asyncio
@respx.mock
async def test_undo_aborta_si_lectura_de_huella_falla(cfg):
    dia = {"schema_version": 1, "has_data": False, "sets": [], "base_hash": "a"}
    respx.get(f"{BASE}/api/v1/sesion").mock(return_value=Response(200, json=dia))
    respx.post(f"{BASE}/api/v1/sesion").mock(
        return_value=Response(
            200,
            json={"schema_version": 1, "saved_count": 1, "sets": [], "base_hash": "b"},
        )
    )
    prev = await bt.bienestar_tool.ainvoke({
        "user_message": "guarda Press 80x8 el 2026-10-04",
        "chat_id": CHAT,
    })
    await bt.bienestar_tool.ainvoke({
        "user_message": f"sí {_hash_de(prev)}",
        "chat_id": CHAT,
    })
    respx.get(f"{BASE}/api/v1/undo/peek").mock(
        return_value=Response(
            200,
            json={
                "schema_version": 1,
                "kind": "sesion",
                "entry_id": 7,
                "fecha_iso": "2026-10-04",
            },
        )
    )
    respx.get(f"{BASE}/api/v1/sesion").mock(
        return_value=Response(500, json={"detail": "x"})
    )
    post = respx.post(f"{BASE}/api/v1/undo").mock(
        return_value=Response(200, json={"schema_version": 1, "kind": "sesion"})
    )
    prev = await bt.bienestar_tool.ainvoke({
        "user_message": "deshaz lo último",
        "chat_id": CHAT,
    })
    r = await bt.bienestar_tool.ainvoke({
        "user_message": f"sí {_hash_de(prev)}",
        "chat_id": CHAT,
    })
    assert post.called is False
    assert "No pude comprobar" in r


@pytest.mark.asyncio
@respx.mock
async def test_undo_409_ante_escritura_intermedia_mismo_tipo(cfg):
    respx.get(f"{BASE}/api/v1/undo/peek").mock(
        return_value=Response(
            200, json={"schema_version": 1, "kind": "sesion", "entry_id": 7}
        )
    )
    post = respx.post(f"{BASE}/api/v1/undo").mock(
        return_value=Response(
            409, json={"detail": "La pila de undo cambió desde el preview."}
        )
    )
    prev = await bt.bienestar_tool.ainvoke({
        "user_message": "deshaz lo último",
        "chat_id": CHAT,
    })
    r = await bt.bienestar_tool.ainvoke({
        "user_message": f"sí {_hash_de(prev)}",
        "chat_id": CHAT,
    })
    assert post.called is True
    body = json.loads(post.calls[0].request.content)
    assert body["expected"] == {"id": 7, "kind": "sesion"}
    assert "cambió" in r or "Pide" in r


@pytest.mark.asyncio
@respx.mock
async def test_credencial_rechazada_sin_filtraciones(cfg):
    respx.get(f"{BASE}/api/v1/sesion").mock(return_value=Response(401))
    r = await bt.bienestar_tool.ainvoke({
        "user_message": "qué entrené hoy",
        "chat_id": CHAT,
    })
    assert "Credencial" in r and "tok-test" not in r


@pytest.mark.asyncio
@respx.mock
async def test_diario_por_gramos_llega_a_preview(cfg):
    respx.get(f"{BASE}/api/v1/diario").mock(
        return_value=Response(
            200, json={"schema_version": 1, "has_data": False, "entradas": []}
        )
    )
    r = await bt.bienestar_tool.ainvoke({
        "user_message": "registra 50 g de avena hoy",
        "chat_id": CHAT,
    })
    assert "Avena" in r and _hash_de(r)


TRES_SETS = [
    {"ejercicio": "Press", "kg": 60.0, "reps": 10.0},
    {"ejercicio": "Press", "kg": 70.0, "reps": 8.0},
    {"ejercicio": "Remo", "kg": 50.0, "reps": 12.0},
]


@pytest.mark.asyncio
@respx.mock
async def test_anadir_conserva_existentes(cfg):
    dia = {"schema_version": 1, "has_data": True, "sets": TRES_SETS, "base_hash": "abc"}
    respx.get(f"{BASE}/api/v1/sesion").mock(return_value=Response(200, json=dia))
    post = respx.post(f"{BASE}/api/v1/sesion").mock(
        return_value=Response(
            200,
            json={
                "schema_version": 1,
                "saved_count": 4,
                "sets": [],
                "base_hash": "def",
            },
        )
    )
    prev = await bt.bienestar_tool.ainvoke({
        "user_message": "añade Press 80x8 hoy",
        "chat_id": CHAT,
    })
    assert prev.count("• ") == 4
    assert "conserva las 3" in prev
    await bt.bienestar_tool.ainvoke({
        "user_message": f"sí {_hash_de(prev)}",
        "chat_id": CHAT,
    })
    assert (
        len(
            post.calls[0].request.content
            and __import__("json").loads(post.calls[0].request.content)["sets"]
        )
        == 4
    )


@pytest.mark.asyncio
@respx.mock
async def test_reemplazo_total_se_declara(cfg):
    dia = {"schema_version": 1, "has_data": True, "sets": TRES_SETS, "base_hash": "abc"}
    respx.get(f"{BASE}/api/v1/sesion").mock(return_value=Response(200, json=dia))
    respx.post(f"{BASE}/api/v1/sesion").mock(
        return_value=Response(
            200,
            json={
                "schema_version": 1,
                "saved_count": 1,
                "sets": [],
                "base_hash": "def",
            },
        )
    )
    prev = await bt.bienestar_tool.ainvoke({
        "user_message": "guarda Press 80x8 hoy",
        "chat_id": CHAT,
    })
    assert "REEMPLAZO TOTAL" in prev


@pytest.mark.asyncio
@respx.mock
async def test_diario_no_elimina_mismo_alimento(cfg):
    dia = {
        "schema_version": 1,
        "has_data": True,
        "entradas": [
            {"alimento": "Avena", "cantidad_g": 30.0},
            {"alimento": "Avena", "cantidad_g": 20.0},
        ],
        "base_hash": "abc",
    }
    respx.get(f"{BASE}/api/v1/diario").mock(return_value=Response(200, json=dia))
    post = respx.post(f"{BASE}/api/v1/diario").mock(
        return_value=Response(
            200,
            json={"schema_version": 1, "consumido": {"kcal": 1}, "base_hash": "def"},
        )
    )
    prev = await bt.bienestar_tool.ainvoke({
        "user_message": "registra 50 g de avena hoy",
        "chat_id": CHAT,
    })
    assert "conserva las 2" in prev
    await bt.bienestar_tool.ainvoke({
        "user_message": f"sí {_hash_de(prev)}",
        "chat_id": CHAT,
    })
    body = __import__("json").loads(post.calls[0].request.content)
    assert [e["cantidad_g"] for e in body["entradas"]] == [30.0, 20.0, 50.0]


@pytest.mark.asyncio
@respx.mock
async def test_respiracion_respeta_fecha_y_repite_identico(cfg):
    respx.post(f"{BASE}/api/v1/respiracion/sesion").mock(
        return_value=Response(
            200,
            json={
                "schema_version": 1,
                "saved": True,
                "ciclos_completados": 1,
                "fecha": "2026-09-13",
            },
        )
    )
    prev = await bt.bienestar_tool.ainvoke({
        "user_message": "registra 4/0/6/0 120 segundos el 2026-09-13",
        "chat_id": CHAT,
    })
    h = _hash_de(prev)
    r = await bt.bienestar_tool.ainvoke({"user_message": f"sí {h}", "chat_id": CHAT})
    assert "2026-09-13" in r


@pytest.mark.asyncio
@respx.mock
async def test_conflicto_409_pide_regenerar(cfg):
    dia = {"schema_version": 1, "has_data": False, "sets": [], "base_hash": "a"}
    respx.get(f"{BASE}/api/v1/sesion").mock(return_value=Response(200, json=dia))
    respx.post(f"{BASE}/api/v1/sesion").mock(
        return_value=Response(409, json={"detail": "El día cambió desde la lectura."})
    )
    prev = await bt.bienestar_tool.ainvoke({
        "user_message": "guarda Press 80x8 hoy",
        "chat_id": CHAT,
    })
    r = await bt.bienestar_tool.ainvoke({
        "user_message": f"sí {_hash_de(prev)}",
        "chat_id": CHAT,
    })
    assert "Pide de nuevo" in r


@pytest.mark.asyncio
@respx.mock
async def test_timeout_post_es_incierto(cfg):
    import httpx as _httpx

    dia = {"schema_version": 1, "has_data": False, "sets": [], "base_hash": "a"}
    respx.get(f"{BASE}/api/v1/sesion").mock(return_value=Response(200, json=dia))
    respx.post(f"{BASE}/api/v1/sesion").mock(side_effect=_httpx.TimeoutException("t"))
    prev = await bt.bienestar_tool.ainvoke({
        "user_message": "guarda Press 80x8 hoy",
        "chat_id": CHAT,
    })
    r = await bt.bienestar_tool.ainvoke({
        "user_message": f"sí {_hash_de(prev)}",
        "chat_id": CHAT,
    })
    assert "No se sabe si se guardó" in r


@pytest.mark.asyncio
@respx.mock
async def test_error_get_no_parece_vacio(cfg):
    from src.personality.skills.bienestar.domain_http import _err, _get

    respx.get(f"{BASE}/api/v1/sesion").mock(
        return_value=Response(400, json={"detail": "Fecha inválida."})
    )
    d = await _get("/api/v1/sesion", {"fecha": "2026-10-04"})
    assert _err(d) == "No se pudo hacer: Fecha inválida."
    assert "has_data" not in d


@pytest.mark.asyncio
@respx.mock
async def test_version_desconocida_es_error(cfg):
    respx.get(f"{BASE}/api/v1/sesion").mock(
        return_value=Response(200, json={"schema_version": 99, "sets": []})
    )
    r = await bt.bienestar_tool.ainvoke({
        "user_message": "qué entrené hoy",
        "chat_id": CHAT,
    })
    assert "Versión" in r


@pytest.mark.asyncio
@respx.mock
async def test_plantilla_preview_sin_escribir(cfg):
    respx.get(f"{BASE}/api/v1/plantillas").mock(
        return_value=Response(
            200,
            json={"schema_version": 1, "plantillas": [{"id": 7, "nombre": "Tiron"}]},
        )
    )
    post = respx.post(f"{BASE}/api/v1/plantilla/aplicar").mock(
        return_value=Response(200, json={"schema_version": 1, "sets": []})
    )
    r = await bt.bienestar_tool.ainvoke({
        "user_message": "aplica mi plantilla tiron hoy",
        "chat_id": CHAT,
    })
    assert "no escribí nada" in r
    assert post.called is True


@pytest.mark.asyncio
@respx.mock
async def test_alimento_y_pregunta(cfg):
    respx.get(f"{BASE}/api/v1/alimentos").mock(
        return_value=Response(
            200,
            json={
                "schema_version": 1,
                "count": 1,
                "alimentos": [
                    {
                        "nombre": "Avena",
                        "kcal": 389.0,
                        "proteina": 1.0,
                        "carbohidratos": 2.0,
                        "grasa": 3.0,
                    }
                ],
            },
        )
    )
    r = await bt.bienestar_tool.ainvoke({
        "user_message": "cuántas calorías tiene la avena por cada 100",
        "chat_id": CHAT,
    })
    assert "389" in r
    respx.get(f"{BASE}/api/v1/rumbo/respuestas").mock(
        return_value=Response(
            200,
            json={
                "schema_version": 1,
                "vigente": {"respuesta": "X", "origen": "chat"},
                "historial": [{}, {}],
            },
        )
    )
    r = await bt.bienestar_tool.ainvoke({
        "user_message": "qué respondí a ex01",
        "chat_id": CHAT,
    })
    assert "[2 en historial]" in r
