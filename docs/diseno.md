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

### 5.1 Flujo

1. `GET /auth/csrf` entrega la cookie `csrf_token` (bootstrap del SPA, 204).
2. `POST /auth/login` valida DNI + contraseña y devuelve el access token en el body.
3. El refresh token va en cookie `httpOnly`, `SameSite=Lax`, `Secure` en producción.
4. El SPA guarda el access token solo en memoria; al recargar llama a `/auth/refresh`.
5. Las mutaciones envían `X-CSRF-Token` (double-submit contra la cookie).
6. Logout, cambio de contraseña, restablecimiento y reutilización de refresh
   revocan la sesión.

### 5.2 Cookies

| Cookie | `HttpOnly` | `Path` | Vida | Propósito |
|---|---|---|---|---|
| `refresh_token` | sí | `/api/v1/auth` | 7 días | Sesión renovable. |
| `csrf_token` | no | `/api/v1` | 7 días | Double-submit legible por el SPA. |

`Secure` sale de `COOKIE_SECURE` (`false` en desarrollo y tests, `true` en
producción). Ninguna cookie se lee desde JavaScript salvo `csrf_token`, que es
justamente el token que hay que repetir en el header.

### 5.3 Tokens

- **Access**: JWT HS256 con `sub`, `rol`, `sid` (familia de refresh), `iss`,
  `aud`, `iat`, `exp` (15 min, UTC). Se verifica firma, issuer, audience y
  expiración en cada request. Sin lista de revocación: un access emitido vive
  como máximo 15 minutos.
- **Refresh**: token opaco (`secrets.token_urlsafe`) con rotación en cada uso.
  Se persiste **hasheado con SHA-256** en Redis (`REFRESH_REDIS_URL`, DB 3):
  - `refresh:tok:<sha256>` → `{id_usuario, family, usado}`, TTL 7 días;
  - `refresh:family:<uuid>` → `{id_usuario, revocada}`, mismo TTL;
  - `refresh:user:<uuid>` → set de familias, para revocar todas juntas.
  La rotación es un único `EVAL` de Lua: si el token ya estaba `usado`, la
  familia entera se revoca y la respuesta es `401 SESION_INVALIDA`
  (`REFRESH_REUTILIZADO` queda en `AUDITORIA`). La limpieza es solo por TTL.

### 5.4 CSRF

Se implementa como **dependencia global del router** (`api_router`), no como
middleware: así el chequeo corre después del ruteo, un `POST` a una ruta
solo-`GET` sigue dando `405` y todo endpoint nuevo queda protegido por defecto.

Rutas exentas (no hay sesión todavía): `/auth/login`, `/auth/registro`,
`/auth/recuperar-password`, `/auth/restablecer-password`,
`/auth/verificar-email`, `/auth/reenviar-verificacion`. El resto de las
mutaciones, incluido `/auth/refresh`, exigen `X-CSRF-Token` igual a la cookie;
si falta o no coincide: `403 CSRF_INVALIDO` con `Cache-Control: no-store`.

### 5.5 Rate limiting (RN-37)

No se usa el decorador de `slowapi`: su `key_func` es síncrona, no puede leer el
body (DNI y email viven ahí) y RN-37 cuenta **intentos fallidos**, no requests.
Se usan contadores propios sobre `RATE_LIMIT_STORAGE_URL` (`INCR` + `EXPIRE` en
un `EVAL`, ventana fija desde el primer intento):

| Clave | Límite | Configurable con |
|---|---|---|
| DNI | 5 / 15 min | `RATE_LIMIT_LOGIN_DNI` |
| IP | 20 / 15 min | `RATE_LIMIT_LOGIN_IP` |
| Recuperación | 3 / hora | `RATE_LIMIT_PASSWORD_RESET` |
| Reenvío de verificación | 3 / hora | `RATE_LIMIT_VERIFICATION_RESEND` |
| Reserva de turnos | 10 / hora | `RATE_LIMIT_BOOKING` |

El bloqueo se evalúa **antes** de verificar la contraseña: el intento siguiente
devuelve `429 RATE_LIMIT_EXCEDIDO` con `Retry-After` y no gasta argon2id. Un
login exitoso borra el contador del DNI.

### 5.6 Primer ingreso (RN-29)

Las cuentas creadas por recepción llevan `debe_cambiar_password = true` y su
contraseña temporal es el **DNI literal** (decisión Q1 = A), exenta de RN-28.
Mientras el flag siga en `true`:

- `GET /auth/me`, `/auth/refresh` y `/auth/logout` responden normal;
- el resto de los endpoints autenticados devuelve `403 CAMBIO_PASSWORD_REQUERIDO`
  (dependencia `require_password_actualizada`).

El flag se lee de la fila `USUARIO` en cada request, nunca del JWT.

### 5.7 Permisos

- El rol se valida en el servidor en cada endpoint (`require_roles`); ocultar
  botones no cuenta.
- Falta de credenciales o token inválido → `401` con `WWW-Authenticate`.
- Rol insuficiente → `403 SIN_PERMISO`.
- Cuenta deshabilitada: `401 CREDENCIALES_INVALIDAS` en el login (no confirma
  que el DNI exista) y `403 CUENTA_DESHABILITADA` en una sesión ya abierta.

### 5.8 Contraseñas

`argon2id` con parámetros configurables (`ARGON2_TIME_COST`,
`ARGON2_MEMORY_COST`, `ARGON2_PARALLELISM`). El login ejecuta argon2id
**exactamente una vez en todos los caminos**, comparando contra un hash dummy
cuando el DNI no existe: el tiempo de respuesta no enumera cuentas. La causa
real del rechazo (`USUARIO_INEXISTENTE`, `PASSWORD_INCORRECTA`,
`CUENTA_DESHABILITADA`) queda solo en `AUDITORIA`.

### 5.9 Registro y verificación de correo (RF-01, RF-20, RN-31, RN-32)

- `POST /auth/registro` crea `USUARIO` (rol `PACIENTE`, `email_verificado =
  false`) y `PACIENTE` en **una sola transacción**. Si el DNI o el correo ya
  existen responde `409 DNI_DUPLICADO` / `409 EMAIL_DUPLICADO`.
- El token de verificación es opaco y se guarda **hasheado** (SHA-256), con
  expiración de 24 h. Cada emisión marca como usado el token anterior del mismo
  usuario: solo hay uno vigente (RN-32).
- La fila de `NOTIFICACION` se crea en la misma transacción; el encolado en ARQ
  ocurre **después del commit** y es *best effort*: si Redis o SMTP fallan, la
  cuenta queda creada y la notificación en `PENDIENTE`/`FALLIDA` (RNF-11).
- `POST /auth/verificar-email` consume el token (`400 TOKEN_INVALIDO`,
  `TOKEN_USADO` o `TOKEN_EXPIRADO`) y marca `email_verificado = true`.
- `POST /auth/reenviar-verificacion` responde **siempre** `202` con el mismo
  mensaje, exista o no la cuenta, y aplica RN-37 (3 por correo por hora).
- Un paciente sin verificar **puede iniciar sesión**, pero no reservar turnos
  (la reserva se implementa en H3 y valida `email_verificado`).
- El alta desde recepción (`POST /pacientes`) no envía correo: marca
  `email_verificado = true`, usa el DNI como contraseña temporal y exige el
  cambio en el primer ingreso (RF-02, RN-29).

### 5.10 Recuperación y cambio de contraseña (RF-21, RF-23, C2)

- `POST /auth/recuperar-password` pide **correo + DNI juntos** y responde siempre
  lo mismo (`200`), exista o no el par, para no enumerar cuentas. Aplica RN-37
  (3 solicitudes por correo por hora) y solo genera token si el usuario está
  habilitado.
- El token de recuperación es opaco, se guarda hasheado (SHA-256), expira en
  1 hora, es de un solo uso y cada solicitud invalida el anterior (RN-31/32).
- `POST /auth/restablecer-password` consume el token, valida RN-28, actualiza la
  contraseña, deja `debe_cambiar_password = false` y **revoca todas las familias
  de refresh del usuario** (C2).
- `POST /auth/cambiar-password` (autenticado) exige la contraseña actual;
  `POST /auth/primer-ingreso` (autenticado, `CU-13`) solo pide la nueva porque la
  sesión ya se abrió con la temporal. Ambos revocan todas las sesiones abiertas:
  el SPA debe volver al login después de cambiar la contraseña.
- `PASSWORD_SIN_CAMBIOS` evita reutilizar la misma contraseña; el cambio queda en
  `AUDITORIA` (`RECUPERACION_SOLICITADA`, `RECUPERACION_CONSUMIDA`,
  `PASSWORD_CAMBIADA`, `PRIMER_INGRESO_COMPLETADO`).

## 6. Notificaciones

- Se persisten en `notificacion` antes de encolarse.
- ARQ procesa `PENDIENTE -> ENVIADA/FALLIDA`.
- Reintentos máximos: 3, con backoff `60, 300, 900` segundos.
- El fallo de SMTP no revierte la operación de negocio.
- `RECORDATORIO_24H` solo se crea si el turno tiene al menos 23 h 30 min de
  anticipación.

Implementado en H2.2:

- `app/services/notificacion_service.py`: `crear` (fila, sin commit),
  `despachar` (encola `enviar_email` en ARQ y **nunca** lanza) y los cuerpos de
  verificación y recuperación.
- `app/workers/notificaciones.py::enviar_email`: incrementa `intentos`, envía
  por SMTP en un hilo aparte y deja la fila `ENVIADA` o `FALLIDA`. Si ya está
  `ENVIADA` no reenvía (idempotencia). Ante error con intentos disponibles lanza
  `Retry(defer=...)` para que ARQ reprograme el job.
- `app/services/email_service.py`: SMTP directo (`smtplib`), compatible con
  Mailpit en desarrollo y con STARTTLS/credenciales en producción.

## 7. API

Base `/api/v1`. Respuestas exitosas con el recurso directo o
`{items, page, page_size, total, pages}`. Errores con RFC 7807
(`application/problem+json`) y campo estable `code`.

Implementado en H2.1 (auth-core):

| Método y ruta | Auth | Éxito | Errores propios |
|---|---|---|---|
| `GET /health` | — | `200 {status: ok}` | — |
| `GET /ready` | — | `200 {status, checks{database, redis, smtp}}` | `503 BASE_NO_DISPONIBLE`, `503 REDIS_NO_DISPONIBLE` |
| `GET /auth/csrf` | — | `204` + cookie | — |
| `POST /auth/login` | — | `200 {access_token, token_type, expires_in, usuario, debe_cambiar_password}` | `400 VALIDACION`, `401 CREDENCIALES_INVALIDAS`, `429 RATE_LIMIT_EXCEDIDO` |
| `POST /auth/refresh` | cookie + CSRF | `200 {access_token, expires_in, usuario}` | `401 NO_AUTENTICADO`, `401 SESION_INVALIDA`, `403 CSRF_INVALIDO` |
| `POST /auth/logout` | cookie + CSRF | `204` (idempotente) | `403 CSRF_INVALIDO` |
| `GET /auth/me` | Bearer | `200 UsuarioOut` | `401 NO_AUTENTICADO`, `401 TOKEN_INVALIDO`, `403 CUENTA_DESHABILITADA` |

`/auth/logout` no exige un access token válido a propósito: si la pestaña quedó
abierta más de 15 minutos, un logout con `401` dejaría el refresh vivo y la
sesión "reviviría" en la próxima recarga. Revoca la familia desde la cookie y
limpia ambas cookies.

Implementado en H2.2 (registro, verificación y pacientes):

| Método y ruta | Auth | Éxito | Errores propios |
|---|---|---|---|
| `POST /auth/registro` | — (sin CSRF) | `201 PacienteOut` | `400 VALIDACION`, `409 DNI_DUPLICADO`, `409 EMAIL_DUPLICADO` |
| `POST /auth/verificar-email` | — (sin CSRF) | `200 {email_verificado, mensaje}` | `400 TOKEN_INVALIDO`, `400 TOKEN_USADO`, `400 TOKEN_EXPIRADO` |
| `POST /auth/reenviar-verificacion` | — (sin CSRF) | `202 {mensaje}` (genérico) | `400 VALIDACION`, `429 RATE_LIMIT_EXCEDIDO` |
| `GET /pacientes` | Recepción/Admin + CSRF n/a | `200 {items, page, page_size, total, pages}` | `401 NO_AUTENTICADO`, `403 SIN_PERMISO`, `403 CAMBIO_PASSWORD_REQUERIDO` |
| `POST /pacientes` | Recepción/Admin + CSRF | `201 PacienteOut` | `409 DNI_DUPLICADO`, `409 EMAIL_DUPLICADO` |
| `GET /pacientes/{id}` | Recepción/Admin | `200 PacienteOut` | `404 PACIENTE_NO_ENCONTRADO` |
| `PATCH /pacientes/{id}` | Recepción/Admin + CSRF | `200 PacienteOut` | `400 VALIDACION`, `409 EMAIL_DUPLICADO`, `404 PACIENTE_NO_ENCONTRADO` |

Implementado en H2.3 (recuperación y cambio de contraseña):

| Método y ruta | Auth | Éxito | Errores propios |
|---|---|---|---|
| `POST /auth/recuperar-password` | — (sin CSRF) | `200 {mensaje}` (genérico) | `400 VALIDACION`, `429 RATE_LIMIT_EXCEDIDO` |
| `POST /auth/restablecer-password` | — (sin CSRF) | `200 {mensaje}` | `400 TOKEN_INVALIDO`, `400 TOKEN_USADO`, `400 TOKEN_EXPIRADO`, `400 PASSWORD_SIN_CAMBIOS` |
| `POST /auth/cambiar-password` | Bearer + CSRF | `204` | `400 PASSWORD_ACTUAL_INCORRECTA`, `400 PASSWORD_SIN_CAMBIOS`, `403 CSRF_INVALIDO` |
| `POST /auth/primer-ingreso` | Bearer + CSRF | `204` | `400 PRIMER_INGRESO_YA_REALIZADO`, `400 PASSWORD_SIN_CAMBIOS` |

Resto del contrato (FASE 3):

| Método y ruta | Rol | Propósito |
|---|---|---|
| `GET /health`, `GET /ready` | Público | Salud y readiness. |
| `GET /auth/csrf` | Público | Bootstrap CSRF. |
| `POST /auth/login` | Público | Login por DNI. |
| `POST /auth/refresh`, `/auth/logout` | Sesión | Rotación/cierre. |
| `GET /auth/me` | Autenticado | Perfil. |
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
- Cada worker de xdist corre contra su propia base (`turnos_test_<worker>`), su
  propia DB de Redis y su propia base descartable para el test de migración; las
  fixtures de sesión comparten un único event loop por worker
  (`asyncio_default_fixture_loop_scope = session`).
- Frontend: Vitest + Testing Library + `msw`.
- CI: ruff, mypy, pytest, eslint, tsc, Vitest y build de Vite.
- La migración se aplica en CI antes de los tests de integración.
- `scripts/verify_migration.py` valida el esquema contra PostgreSQL real:
  exclusion constraints por médico y paciente, CHECK de DNI y duración,
  unicidad parcial de notificaciones y de restricción activa, inmutabilidad y
  zona horaria de `rango_turno`, y el ciclo `downgrade base` + `upgrade head`.
  Son 21 comprobaciones. Corre en CI y **borra el esquema** de la base indicada,
  por lo que dentro de Compose debe apuntarse a una base descartable, nunca a
  `turnos`:
  `python scripts/verify_migration.py --url postgresql://postgres:postgres@db:5432/turnos_verify`.
- arq 0.28 arma el `Worker` con `WorkerSettings.__dict__`, sin recorrer la MRO.
  Una subclase que solo declare `cron_jobs` pierde `functions` y
  `redis_settings` heredados, arranca con `RedisSettings()` por defecto
  (`localhost:6379`) y entra en crash loop. Por eso `scheduler.WorkerSettings`
  declara `functions` y `redis_settings` de forma explícita en vez de heredar.
  `backend/tests/test_workers.py` lo cubre como regresión.

## 10. Operación

- `docker compose up -d` levanta api, worker, scheduler, web, db, redis y mailpit.
- Compose **no** aplica migraciones ni seed al arrancar. Después del primer
  `up`: `docker compose exec api alembic upgrade head` y
  `docker compose exec api python scripts/seed.py`.
- `/api/v1/ready` verifica conectividad (`SELECT 1` + `ping` a Redis), no el
  esquema: puede devolver 200 con la base sin migrar. Para el esquema, `alembic
  check`. El chequeo de SMTP es informativo: si mailpit está caído,
  `checks.smtp` queda en `error` y el estado sigue siendo 200, porque las
  notificaciones son asíncronas (RNF-11).
- Redis usa DB separadas por uso: `0` general, `1` rate limit, `2` ARQ,
  `3` refresh tokens. En tests cada worker de xdist usa su propia DB lógica y su
  propia base de PostgreSQL (`turnos_test_<worker>`), así un `FLUSHDB` o un
  `TRUNCATE` no pisa a los demás workers.
- `alembic upgrade head` es el único mecanismo de cambio de esquema.
- `alembic check` debe reportar "No new upgrade operations detected" (modelos y
  migración sincronizados).
- `scripts/seed.py` es idempotente y solo para desarrollo/demo.
- `scripts/backup.sh` y `restore.sh` implementan RNF-08 con retención de 30 días.
