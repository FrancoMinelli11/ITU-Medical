# Trazabilidad

Mapa de planificación. Al cerrar cada hito se reemplazan los archivos previstos
por los reales y se agrega el test que cubre cada requisito.

## Estado implementado

### H2.1 — auth-core

| Requisito | Implementación | Test |
|---|---|---|
| RF-03 (login y control de roles) | `app/services/auth_service.py`, `app/api/v1/endpoints/auth.py`, `app/api/deps.py` | `test_auth_login.py`, `test_auth_cookies.py` |
| RF-19 (operaciones de identidad) | `app/services/auditoria_service.py` | `test_auditoria.py` |
| RF-27 (login: 5/DNI y 20/IP) | `app/core/rate_limit.py`, `app/core/config.py` | `test_rate_limits.py` |
| RN-01, RN-30 (DNI de 7-8 dígitos) | `app/schemas/auth.py` (`LoginRequest`) + `CHECK dni_formato` (migración `0001`) | `test_auth_login.py`, `integration/test_migration.py` |
| RN-29 (cambio obligatorio) | `app/api/deps.py::require_password_actualizada` | `test_auth_primer_ingreso.py` |
| RN-37 (límites de login) | `core/rate_limit.py`, `core/config.py` | `test_rate_limits.py` |
| RNF-01, RNF-03 (CSRF, permisos) | `app/core/csrf.py`, `app/api/deps.py::require_roles` | `test_auth_csrf.py`, `test_auth_cookies.py` |
| P-05, P-06, P-07 | — | `test_auth_login.py` |
| P-30 (operaciones de identidad) | — | `test_auditoria.py` |
| P-33 (login con contraseña temporal) | — | `test_auth_primer_ingreso.py` |
| P-36 (límite de intentos) | — | `test_rate_limits.py` |
| P-44 (access 15 min, refresh 7 días) | `core/security.py`, `services/refresh_service.py` | `test_tokens.py` (el turno de las 23:30 es H4) |

Decisiones con impacto en trazabilidad:

| Decisión | Efecto | Dónde queda cubierto |
|---|---|---|
| **Q1 = A**: contraseña temporal = DNI literal | Excepción **documentada** a RN-28 para las cuentas creadas por recepción, porque RF-02, CU-13 y P-04 exigen que la primera credencial sea el DNI. RN-29 sigue vigente vía `debe_cambiar_password`. | `test_auth_primer_ingreso.py::test_login_con_password_temporal` |
| **C1**: 401 uniforme en el login | Un DNI inexistente, una contraseña incorrecta y una cuenta deshabilitada devuelven lo mismo; la causa real solo queda en `AUDITORIA`. | `test_auth_login.py`, `test_auditoria.py` |
| **C2**: el restablecimiento revoca todas las sesiones | `refresh_service.revocar_sesiones_usuario` (se usa en H2.3). | Pendiente en H2.3 |
| **C3**: `/auth/me` responde 200 con `debe_cambiar_password` | El SPA distingue "sesión inválida" de "falta cambiar la contraseña". | `test_auth_primer_ingreso.py` |
| Sin `slowapi` | `key_func` síncrona no puede leer el body y RN-37 cuenta intentos fallidos: se usan contadores propios en Redis. | `test_rate_limits.py` |
| CSRF como dependencia global del router | Un endpoint nuevo queda protegido por defecto y `POST` a una ruta solo-`GET` sigue dando `405`. | `test_auth_csrf.py`, `test_health.py` |

## Requerimientos funcionales

| RF | Módulo previsto |
|---|---|
| RF-01, RF-02 | `auth_service`, `paciente_service` |
| RF-03 | `auth_service`, `core/rate_limit`, dependencias |
| RF-04, RF-05 | `agenda_service`, `turno_service` |
| RF-06 | `turno_service` + constraint SQL |
| RF-07 | `turno_service` |
| RF-08, RF-09, RF-10 | `cancelacion_service` |
| RF-11, RF-12, RF-13 | `llegada_service`, `turno_service`, `domain/orden_atencion` |
| RF-14 | `nota_service` |
| RF-15, RF-16 | `turno_service`, `restriccion_service` |
| RF-17, RF-18 | `agenda_service` |
| RF-19 | `auditoria_service` |
| RF-20, RF-21, RF-22, RF-23 | `auth_service`, `notificacion_service` |
| RF-24, RF-25, RF-26, RF-27 | `cancelacion_service`, `turno_service`, `agenda_service`, rate limit |

## Reglas de negocio

| RN | Módulo previsto |
|---|---|
| RN-01..RN-03, RN-26..RN-30 | `auth_service`, `paciente_service`, modelos |
| RN-04..RN-06 | `usuario_service`, `turno_service` |
| RN-07..RN-09, RN-33, RN-35 | `turno_service`, `domain/estados`, constraints |
| RN-10..RN-14, RN-34 | `cancelacion_service` |
| RN-15..RN-19 | `llegada_service`, `domain/orden_atencion` |
| RN-20..RN-22, RN-36 | `restriccion_service` |
| RN-23, RN-24 | `nota_service` |
| RN-25, RN-38 | `agenda_service` |
| RN-31, RN-32 | `auth_service`, `notificacion_service` |
| RN-37 | `core/rate_limit` |

## Plan de pruebas

| P | Archivo |
|---|---|
| P-01..P-04, P-31, P-41 | `backend/tests/test_auth_registro.py`, `test_auth_verificacion.py` (H2.2) |
| P-05..P-07, P-33, P-36 | `backend/tests/test_auth_login.py`, `test_auth_primer_ingreso.py`, `test_rate_limits.py` (H2.1) |
| P-08..P-11, P-37, P-38, P-42 | `backend/tests/integration/test_turnos_reserva.py`, `test_turnos_concurrencia.py` |
| P-12..P-16 | `backend/tests/integration/test_turnos_cancelacion.py` |
| P-17..P-21 | `backend/tests/integration/test_turnos_llegada.py`, `test_turnos_orden.py`, `test_turnos_ausencia.py` |
| P-22, P-23 | `backend/tests/integration/test_notas.py` |
| P-24..P-26 | `backend/tests/integration/test_restricciones.py` |
| P-27, P-28, P-40 | `backend/tests/integration/test_agenda_*.py` |
| P-29 | `backend/tests/test_permisos.py` |
| P-30 | `backend/tests/test_auditoria.py` (H2.1; cada hito suma sus acciones) |
| P-32, P-34, P-35 | `backend/tests/test_auth_recuperacion.py` (H2.3; P-32 se difiere a H4) |
| P-39, P-43 | `backend/tests/integration/test_scheduler_recordatorio.py`, `test_smtp_failure.py` |
| P-44 | `backend/tests/test_tokens.py` (parcial, H2.1) + `test_zona_horaria.py` (H4) |
| P-45 | `backend/tests/integration/test_backup_restore.py` |

Tests complementarios por vacíos del plan original:

- `T-RF13`: `backend/tests/integration/test_turnos_atencion.py`.
- `T-RF18`: `backend/tests/integration/test_medicos_deshabilitacion.py`.

## Verificación de esquema (FASE 2)

`scripts/verify_migration.py` corre en CI contra PostgreSQL real y cubre:

| Verificación | Requisito |
|---|---|
| `ex_turno_medico` rechaza solapamiento del mismo médico | RF-06, RN-07, RNF-04 |
| `ex_turno_paciente` rechaza solapamiento del mismo paciente | RF-06, RN-07 |
| `btree_gist` instalada | RNF-04 |
| Turnos contiguos y simultáneos con otro médico se aceptan | RF-06 |
| `rango_turno` es `IMMUTABLE` (requisito del índice) | RNF-04 |
| Un turno `CANCELADO` libera el horario | RN-08, RN-09 |
| `CHECK` de DNI (7-8 dígitos, solo números) | RN-01 |
| `CHECK` de duración positiva | RN-07 |
| Confirmación y recordatorio idempotentes por turno | RN-32, RNF-06 |
| Una sola restricción activa por usuario | RN-20 |
| `downgrade base` + `upgrade head` | RNF-09 |
