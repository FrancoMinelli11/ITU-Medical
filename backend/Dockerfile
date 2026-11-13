FROM python:3.12-slim

# El entorno virtual vive fuera de /workspace/backend para que el bind mount del
# código en desarrollo (docker compose) no lo tape. Cambiar dependencias requiere
# reconstruir la imagen: `docker compose build api worker scheduler`.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/workspace/backend \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /workspace

RUN pip install --no-cache-dir "uv>=0.5,<1.0"

COPY backend/pyproject.toml backend/uv.lock ./backend/
RUN cd backend && uv sync --frozen

COPY backend ./backend
COPY alembic.ini ./alembic.ini
COPY scripts ./scripts

ENV PATH="/opt/venv/bin:${PATH}"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]