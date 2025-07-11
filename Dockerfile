# ---- Base Stage ----
FROM python:3.11-alpine as base
ARG APP_DIR=/app
WORKDIR ${APP_DIR}
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Variables para uv/pip
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    UV_EXTRA_INDEX_URL=''

# Crear usuario no-root
ARG UID=10001
RUN useradd -m -u ${UID} -s /bin/bash appuser

# Instalar uv usando el instalador oficial
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    apt-get purge -y --auto-remove curl && rm -rf /var/lib/apt/lists/*
ENV PATH="/root/.cargo/bin:$PATH"

# ---- Builder Stage ----
FROM base as builder
COPY pyproject.toml requirements.lock* ./

# Instala dependencias de producción desde el lockfile
RUN uv pip sync --system requirements.lock

# ---- Final Stage ----
FROM base as final
ARG APP_DIR

# Copia dependencias instaladas
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copia el código fuente y la configuración
COPY --chown=appuser:appuser ./src ${APP_DIR}/src
COPY --chown=appuser:appuser ./config ${APP_DIR}/config

# Cambiar al usuario no-root
USER appuser

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando por defecto para producción
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
