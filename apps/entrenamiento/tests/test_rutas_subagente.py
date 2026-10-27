"""Rutas del subagente en la allow-list remota (fusión SDD 001).

El subagente llama desde otro contenedor (peer no-loopback): toda ruta que
usa debe estar en ALLOWED_REMOTE_ROUTES o el gate la devuelve 403.
"""

from src.network_access import ALLOWED_REMOTE_ROUTES

RUTAS_SUBAGENTE = [
    ("GET", "/api/v1/sesion"),
    ("POST", "/api/v1/sesion"),
    ("GET", "/api/v1/diario"),
    ("POST", "/api/v1/diario"),
    ("GET", "/api/v1/alimentos"),
    ("GET", "/api/v1/plantillas"),
    ("POST", "/api/v1/plantilla/aplicar"),
    ("GET", "/api/v1/cardio"),
    ("POST", "/api/v1/cardio/anotacion"),
    ("GET", "/api/v1/respiracion/sesiones"),
    ("POST", "/api/v1/respiracion/sesion"),
    ("GET", "/api/v1/rumbo/dia"),
    ("POST", "/api/v1/rumbo/dia"),
    ("POST", "/api/v1/rumbo/yo"),
    ("GET", "/api/v1/rumbo/preguntas"),
    ("GET", "/api/v1/rumbo/respuestas"),
    ("POST", "/api/v1/rumbo/respuesta"),
    ("GET", "/api/v1/sugerencia"),
    ("GET", "/api/v1/undo/peek"),
    ("POST", "/api/v1/undo"),
]


def test_rutas_subagente_permitidas_en_remoto():
    faltan = [r for r in RUTAS_SUBAGENTE if r not in ALLOWED_REMOTE_ROUTES]
    assert not faltan, f"rutas sin allow-list: {faltan}"
