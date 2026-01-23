# ---- Base Stage ----
FROM python:3.13-slim AS base
ARG APP_DIR=/app
WORKDIR ${APP_DIR}
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Variables para uv/pip
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    UV_EXTRA_INDEX_URL=''

# Instalar dependencias básicas (shadow para useradd, curl para uv)
RUN apt-get update &&     apt-get install -y --no-install-recommends curl passwd ffmpeg &&     rm -rf /var/lib/apt/lists/* # Limpiar cache de apt


# Crear usuario no-root
ARG UID=10001
RUN useradd -m -u ${UID} -s /bin/bash appuser

# Instalar uv usando el instalador oficial
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Añadir uv al PATH para que esté disponible en los siguientes pasos
ENV PATH="/root/.local/bin:$PATH"
ENV PATH="/root/.cargo/bin:$PATH"

# ---- Builder Stage ----
FROM base AS builder
COPY pyproject.toml requirements.lock* ./

# Instala dependencias de producción desde el lockfile
RUN uv pip sync --system requirements.lock

# ---- Final Stage ----
FROM base AS final
ARG APP_DIR

# Copia dependencias instaladas
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copia el código fuente y la configuración
COPY --chown=appuser:appuser ./src ${APP_DIR}/src


# Crear un directorio para logs y darle permisos al appuser
RUN mkdir -p ${APP_DIR}/logs && chown appuser:appuser ${APP_DIR}/logs

# Cambiar al usuario no-root
USER appuser

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/system/health || exit 1

# Comando por defecto para producción
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
