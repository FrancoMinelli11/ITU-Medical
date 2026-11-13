# Trazabilidad inicial

Mapa de planificación. Se actualizará al cerrar cada hito con el archivo real y el
test que cubre cada requisito.

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

| P | Archivo previsto |
|---|---|
| P-01..P-07, P-31..P-36, P-41, P-44 | `backend/tests/integration/test_auth_*`, `test_rate_limits.py`, `test_zona_horaria.py` |
| P-08..P-11, P-37, P-38, P-42 | `backend/tests/integration/test_turnos_reserva.py`, `test_turnos_concurrencia.py` |
| P-12..P-16 | `backend/tests/integration/test_turnos_cancelacion.py` |
| P-17..P-21 | `backend/tests/integration/test_turnos_llegada.py`, `test_turnos_orden.py`, `test_turnos_ausencia.py` |
| P-22, P-23 | `backend/tests/integration/test_notas.py` |
| P-24..P-26 | `backend/tests/integration/test_restricciones.py` |
| P-27, P-28, P-40 | `backend/tests/integration/test_agenda_*.py` |
| P-29, P-30 | `backend/tests/integration/test_permisos.py`, `test_auditoria.py` |
| P-39, P-43 | `backend/tests/integration/test_scheduler_recordatorio.py`, `test_smtp_failure.py` |
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
