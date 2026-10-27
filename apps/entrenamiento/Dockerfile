# Dockerfile de Senda (fusión SDD 001) — PROPUESTA para revisión, no construido.

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Dependencias bloqueadas del dominio (uv.lock de apps/entrenamiento).
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --locked --no-dev

# El entorno de producción ya está instalado. No sincronizar ni descargar
# herramientas de desarrollo durante el arranque de uv run.
ENV UV_NO_SYNC=1

COPY app.py config.py ./
COPY src/ ./src/
COPY templates/ ./templates/
COPY static/ ./static/
COPY scripts/ ./scripts/

# Datos, secretos y venv nunca entran en la imagen (ver .dockerignore).
# Arranque real: scripts/start_server.sh (puerta 8000, solo red interna).

EXPOSE 8000

CMD ["bash", "scripts/start_server.sh"]
