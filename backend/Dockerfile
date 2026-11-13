FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/workspace/backend

WORKDIR /workspace

RUN pip install --no-cache-dir "uv>=0.5,<1.0"

COPY backend/pyproject.toml backend/uv.lock* ./backend/
RUN cd backend && uv sync

COPY backend ./backend
COPY alembic.ini ./alembic.ini
COPY scripts ./scripts

ENV PATH="/workspace/backend/.venv/bin:${PATH}"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
