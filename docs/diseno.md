# FASE 2 — Diseño técnico

Este documento complementa `docs/requisitos.md`. No repite requisitos: fija las
decisiones de arquitectura, datos, API y despliegue para la implementación.

## 1. Arquitectura

```text
React SPA  ->  /api/v1  ->  FastAPI (async)  ->  PostgreSQL 16
                                      |-> Redis 7 (rate limit + ARQ)
                                      |-> ARQ worker/scheduler -> Mailpit/SMTP
```

- Backend en capas: `api -> services -> domain/db`.
- Ningún endpoint accede a SQLAlchemy directamente; los servicios concentran reglas.
- El frontend solo habla con la API mediante `src/api/`; no usa `localStorage`.
- Fechas en UTC en la base; las reglas locales usan `America/Argentina/Buenos_Aires`.

## 2. Decisiones cerradas en FASE 1

| Tema | Decisión |
|---|---|
| DER incompleto | Se completó el esquema mínimo en la migración inicial. |
| Email | Canónico en `usuario.email`, único global; no se duplica en `paciente`. |
| Exclusión | Incluye `RESERVADO`, `EN_ESPERA` y `ATENDIDO`. |
| Reasignación por baja de médico | Cancelar el turno anterior y crear uno nuevo en una transacción, con auditoría. |
| Notificaciones por agenda | Solo `TURNO_AFECTADO_POR_AGENDA` para `BLOQUEO_AGENDA` y `CAMBIO_HORARIO`. |
| Usuario rojo | `activa = TRUE` y `fecha_fin > ahora`; sin cron. |
| Contraseñas | `argon2id`. |
| Tokens | JWT de acceso corto; refresh rotativo en cookie `httpOnly`; CSRF double-submit. |

## 3. Modelo de datos

Entidades: `usuario`, `paciente`, `medico`, `especialidad`, `horario_medico`,
`bloqueo_agenda`, `turno`, `nota_seguimiento`, `solicitud_cancelacion`,
`restriccion_usuario`, `auditoria`, `verificacion_email`,
`recuperacion_password` y `notificacion`.

Reglas físicas principales:

- `usuario.dni VARCHAR(8) UNIQUE` con `CHECK` de 7-8 dígitos.
- `usuario.email UNIQUE NOT NULL`.
- `turno` tiene dos `EXCLUDE USING gist` parciales, una por `id_medico` y otra
  por `id_paciente`, sobre `rango_turno(fecha_hora, duracion_minutos)`.
  La función `rango_turno` es `IMMUTABLE` y calcula el rango en UTC explícito:
  `timestamptz + interval` es `STABLE` (depende del `TimeZone` de la sesión) y
  PostgreSQL rechaza expresiones no inmutables dentro de un índice. Para
  intervalos de solo minutos, la aritmética en UTC es equivalente a la absoluta.
- `restriccion_usuario` tiene un único registro activo por usuario.
- `notificacion` tiene unicidad parcial para confirmación/recordatorio y para
  cancelación por `(id_turno, tipo, subtipo)`.
- Los turnos no se borran; los estados terminales son `ATENDIDO`, `CANCELADO` y
  `AUSENTE`.

## 4. Estados y transiciones

| Desde | Hacia | Actor |
|---|---|---|
| `RESERVADO` | `EN_ESPERA` | Recepción |
| `RESERVADO` | `CANCELADO` | Paciente o recepción |
| `RESERVADO` | `AUSENTE` | Recepción |
| `EN_ESPERA` | `ATENDIDO` | Médico |
| `EN_ESPERA` | `CANCELADO` | Recepción |

Cualquier otra transición devuelve `409` con código `TRANSICION_INVALIDA`.

## 5. Autenticación y sesión

1. `GET /auth/csrf` entrega el token CSRF.
2. `POST /auth/login` valida DNI + contraseña y devuelve access token en el body.
3. El refresh token va en cookie `httpOnly`, `SameSite=Lax`, `Secure` en producción.
4. El SPA guarda el access token solo en memoria; al recargar llama a `/auth/refresh`.
5. Las mutaciones envían `X-CSRF-Token`.
6. Logout, cambio de contraseña y reutilización de refresh revocan la sesión.

## 6. Notificaciones

- Se persisten en `notificacion` antes de encolarse.
- ARQ procesa `PENDIENTE -> ENVIADA/FALLIDA`.
- Reintentos máximos: 3, con backoff `60, 300, 900` segundos.
- El fallo de SMTP no revierte la operación de negocio.
- `RECORDATORIO_24H` solo se crea si el turno tiene al menos 23 h 30 min de
  anticipación.

## 7. API

Base `/api/v1`. Respuestas exitosas con el recurso directo o
`{items, page, page_size, total, pages}`. Errores con RFC 7807
(`application/problem+json`) y campo estable `code`.

| Método y ruta | Rol | Propósito |
|---|---|---|
| `GET /health`, `GET /ready` | Público | Salud y readiness. |
| `GET /auth/csrf` | Público | Bootstrap CSRF. |
| `POST /auth/registro` | Público | Alta web de paciente. |
| `POST /auth/login` | Público | Login por DNI. |
| `POST /auth/refresh`, `/auth/logout` | Sesión | Rotación/cierre. |
| `GET /auth/me` | Autenticado | Perfil. |
| `POST /auth/verificar-email`, `/auth/reenviar-verificacion` | Público | Verificación. |
| `POST /auth/recuperar-password`, `/auth/restablecer-password` | Público | Recuperación. |
| `POST /auth/cambiar-password`, `/auth/primer-ingreso` | Autenticado | Contraseña. |
| `GET/POST /pacientes`, `GET/PATCH /pacientes/{id}` | Recepción/Admin | Pacientes. |
| `GET /pacientes/{id}/turnos` | Recepción/Admin/Paciente | Historial. |
| `GET/POST/PATCH /pacientes/{id}/restricciones` | Recepción/Admin | Usuario rojo. |
| `GET/POST/PATCH /especialidades` | Autenticado/Admin | Catálogo. |
| `GET/POST/PATCH /medicos` | Autenticado/Admin | Profesionales. |
| `GET /medicos/{id}/disponibilidad` | Autenticado | Slots libres. |
| `GET /medicos/{id}/agenda` | Médico/Recepción/Admin | Agenda. |
| `GET/PUT /medicos/{id}/horarios` | Admin | Horarios. |
| `GET/POST/PATCH /medicos/{id}/bloqueos` | Admin/Recepción | Bloqueos. |
| `GET/POST /turnos`, `GET /turnos/mios`, `GET /turnos/{id}` | Paciente/Recepción/Médico | Turnos. |
| `POST /turnos/{id}/llegada`, `/atender`, `/ausente` | Recepción/Médico | Transiciones. |
| `POST /turnos/{id}/cancelar`, `/solicitud-cancelacion`, `/cancelar-recepcion` | Paciente/Recepción | Cancelaciones. |
| `GET /turnos/orden-atencion` | Recepción/Médico | Cola. |
| `GET /solicitudes-cancelacion`, `POST /solicitudes-cancelacion/{id}/resolver` | Recepción | Solicitudes. |
| `GET/POST /turnos/{id}/notas`, `PATCH /notas/{id}` | Médico autor | Notas. |
| `GET/POST/PATCH /usuarios` | Admin | Usuarios. |
| `GET /auditoria`, `GET /reportes/resumen` | Admin | Control. |

## 8. Frontend

- `src/api/` centraliza el cliente y los tipos.
- `src/features/` agrupa auth, turnos, agenda, recepción, médico y admin.
- `src/lib/dates.ts` formatea en la zona local; la API entrega UTC.
- Formularios con `react-hook-form` + `zod`.
- Datos remotos con TanStack Query.
- Rutas protegidas por rol en `src/routes/`.
- Sin `localStorage` para tokens.

## 9. Pruebas y CI

- Backend: unitarios de dominio y servicios, integración contra Postgres real y
  mailpit. `pytest-xdist` por defecto; `@pytest.mark.serial` para concurrencia.
- Frontend: Vitest + Testing Library + `msw`.
- CI: ruff, mypy, pytest, eslint, tsc, Vitest y build de Vite.
- La migración se aplica en CI antes de los tests de integración.
- `scripts/verify_migration.py` valida el esquema contra PostgreSQL real:
  exclusion constraints por médico y paciente, CHECK de DNI y duración,
  unicidad parcial de notificaciones y de restricción activa, y el ciclo
  `downgrade base` + `upgrade head`. Corre en CI y **borra el esquema** de la
  base indicada.

## 10. Operación

- `docker compose up -d` levanta api, worker, scheduler, web, db, redis y mailpit.
- `alembic upgrade head` es el único mecanismo de cambio de esquema.
- `alembic check` debe reportar "No new upgrade operations detected" (modelos y
  migración sincronizados).
- `scripts/seed.py` es idempotente y solo para desarrollo/demo.
- `scripts/backup.sh` y `restore.sh` implementan RNF-08 con retención de 30 días.
