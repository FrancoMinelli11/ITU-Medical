"""Fixtures compartidas.

Las fixtures de PostgreSQL real, factory-boy y mailpit se agregan en FASE 3.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# pytest no lee `.env` por sí solo: se carga acá para que los tests de
# integración del host encuentren `TEST_DATABASE_URL`/`TEST_REDIS_URL`.
# `override=False` respeta el entorno que ya define Compose: dentro del
# contenedor `api` esas variables apuntan a la red interna (`db`, `redis`),
# mientras que en el host apuntan a `localhost` con `DB_PORT`.
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
