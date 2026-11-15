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

### H2.2 — registro, verificación y pacientes

| Requisito | Implementación | Test |
|---|---|---|
| RF-01 (alta web, correo único y verificación) | `app/services/paciente_service.py::registrar_web`, `app/api/v1/endpoints/auth.py` | `test_auth_registro.py` |
| RF-02 (alta desde recepción) | `app/services/paciente_service.py::crear_desde_recepcion`, `app/api/v1/endpoints/pacientes.py` | `test_pacientes.py` |
| RF-19 (auditoría de las nuevas operaciones) | `Accion.ALTA_PACIENTE_WEB`, `ALTA_PACIENTE_RECEPCION`, `MODIFICACION_PACIENTE`, `VERIFICACION_EMAIL_ENVIADA`, `EMAIL_VERIFICADO` | `test_auth_registro.py`, `test_auth_verificacion.py`, `test_pacientes.py` |
| RF-20, CU-11 (verificar correo) | `app/services/verificacion_service.py`, `POST /auth/verificar-email` | `test_auth_verificacion.py` |
| RF-22, RNF-11 (correo asíncrono e idempotente) | `app/services/notificacion_service.py`, `app/workers/notificaciones.py`, `app/services/email_service.py` | `test_notificaciones.py`, `test_workers.py` |
| RN-28 (política de contraseñas) | `app/schemas/auth.py::PasswordFuerte` | `test_auth_registro.py` |
| RN-29 (cambio obligatorio en el primer ingreso) | `app/api/deps.py::require_roles` + `require_password_actualizada` | `test_pacientes.py::test_cuenta_de_recepcion_usa_el_dni_y_bloquea_el_resto` |
| RN-31 (tokens hasheados, un solo uso) | `verificacion_service.generar/consumir` (`sha256_hex`) | `test_auth_registro.py`, `test_auth_verificacion.py` |
| RN-32 (un token vigente; no duplicar notificación) | `verificacion_service.generar` invalida el anterior; `enviar_email` no reenvía una fila `ENVIADA` | `test_auth_verificacion.py::test_reenvio_invalida_el_token_anterior`, `test_notificaciones.py::test_worker_es_idempotente` |
| RN-37 (reenvío: 3 por correo por hora) | `verificacion_service.reenviar` con `RateLimiter` | `test_auth_verificacion.py::test_reenvio_tiene_rate_limit` |
| RNF-03 (permisos server-side en `/pacientes`) | `pacientes.py::StaffDep` | `test_pacientes.py` |
| P-01, P-02, P-03, P-31 | — | `test_auth_registro.py` |
| P-04 (alta desde recepción y primer ingreso) | — | `test_pacientes.py` |
| P-41 (token válido/expirado/usado/inexistente y reenvío) | — | `test_auth_verificacion.py` |
| P-43 (fallo de SMTP: la operación sigue y la fila queda `FALLIDA`) | — | `test_notificaciones.py` |

### H2.3 — recuperación y cambio de contraseña

| Requisito | Implementación | Test |
|---|---|---|
| RF-21, CU-12 (recuperación con correo + DNI) | `app/services/recuperacion_service.py`, `POST /auth/recuperar-password` y `/auth/restablecer-password` | `test_auth_recuperacion.py` |
| RF-23, CU-13 (cambio obligatorio en el primer ingreso) | `app/services/password_service.py::primer_ingreso`, `POST /auth/primer-ingreso` | `test_auth_cambiar_password.py` |
| RN-28 (política aplicada a la nueva contraseña) | `PasswordFuerte` en `RestablecerPasswordRequest`, `CambiarPasswordRequest` y `PrimerIngresoRequest` | `test_auth_recuperacion.py`, `test_auth_cambiar_password.py` |
| RN-31, RN-32 (token hasheado, 1 h, uno vigente) | `recuperacion_service._generar` invalida el anterior; `restablecer` lo consume | `test_auth_recuperacion.py` |
| RN-37 (3 solicitudes por correo por hora) | `recuperacion_service.solicitar` con `RateLimiter` | `test_auth_recuperacion.py::test_solicitud_tiene_rate_limit` |
| **C2** (el restablecimiento revoca todas las sesiones) | `refresh_service.revocar_sesiones_usuario` en `recuperacion_service.restablecer` y `password_service._aplicar` | `test_auth_recuperacion.py::test_restablecer_revoca_las_sesiones`, `test_auth_cambiar_password.py::test_cambiar_password_revoca_las_sesiones` |
| P-33 (primer login de cuenta de recepción) | — | `test_auth_cambiar_password.py` |
| P-34 (recuperación con datos inexistentes) | — | `test_auth_recuperacion.py` |
| P-35 (token de recuperación expirado) | — | `test_auth_recuperacion.py` |

### H2.4 — frontend de autenticación

| Requisito | Implementación | Test |
|---|---|---|
| RF-01 (registro web desde el SPA) | `frontend/src/features/auth/RegistroPage.tsx` | `RegistroPage.test.tsx` |
| RF-19, RF-22 (login y cierre de sesión) | `LoginPage.tsx`, `AuthProvider.logout`, `InicioPage.tsx` | `LoginPage.test.tsx`, `App.test.tsx` |
| RF-20 (verificación de correo) | `VerificarEmailPage.tsx` (token desde el query y reenvío) | `VerificarEmailPage.test.tsx` |
| RF-21, CU-12 (recuperación desde el SPA) | `RecuperarPasswordPage.tsx`, `RestablecerPasswordPage.tsx` | `RecuperarPasswordPage.test.tsx`, `RestablecerPasswordPage.test.tsx` |
| RF-23, RN-29, CU-13 (primer ingreso) | `PrimerIngresoPage.tsx` + guard de `debe_cambiar_password` | `PrimerIngresoPage.test.tsx`, `RutaProtegida.test.tsx` |
| RN-28 (política reflejada en el cliente) | `features/auth/validacion.ts` (`passwordSchema`) | `RegistroPage.test.tsx` |
| RNF-01, RNF-02 (tokens fuera de `localStorage`) | `AuthProvider` (access en un `ref`) y `api/client.ts` | `client.test.ts`, `App.test.tsx` |
| RNF-10 (errores RFC 7807 en pantalla) | `lib/problem.ts` (`mensajeDeError`) | `client.test.ts`, páginas de auth |
| **C3** (el SPA distingue sesión de cambio pendiente) | `routes/RutaProtegida.tsx` redirige a `/primer-ingreso` | `RutaProtegida.test.tsx` |
| CSRF double-submit legible por el SPA | cookie `csrf_token` con `Path=/` + `api/client.ts` | `test_auth_cookies.py`, `client.test.ts` |

La UI reproduce RN-28 en el cliente, pero el servidor la vuelve a validar: los
tests de las páginas cubren el mensaje local y los del backend el `400 VALIDACION`.


### H3 — agenda, especialidades y médicos

| Requisito | Implementación | Test |
|---|---|---|
| RF-04 (consulta de disponibilidad) | `app/services/agenda_service.py::calcular_disponibilidad`, `GET /medicos/{id}/disponibilidad` | `test_agenda.py::test_consultar_disponibilidad_y_agenda` |
| RF-17 (gestión de horarios y conflicto) | `app/services/agenda_service.py::configurar_horarios`, `GET/PUT /medicos/{id}/horarios` | `test_agenda.py::test_configurar_horarios_ok`, `test_agenda.py::test_cambio_horarios_afecta_turnos_rechazado` |
| RF-18 (especialidades y médicos) | `especialidad_service.py`, `medico_service.py`, `/especialidades`, `/medicos` | `test_especialidades.py`, `test_medicos.py` |
| RF-26 (bloqueos de agenda con turnos afectados) | `agenda_service.py::crear_bloqueo`, `POST /medicos/{id}/bloqueos` | `test_agenda.py::test_bloqueo_con_turnos_rechazado_y_bloqueo_ok` |
| RN-06 (médico asociado a especialidad) | `Medico.id_especialidad`, `medico_service.py` | `test_medicos.py::test_crear_medico_admin` |
| RN-07, RN-08 (horarios sin superposición interna) | `agenda_service.py::configurar_horarios` | `test_agenda.py::test_horarios_superpuestos_rechazados` |
| RN-38 (bloqueos rechazan si hay turnos) | `agenda_service.py::crear_bloqueo` (HTTP 409) | `test_agenda.py::test_bloqueo_con_turnos_rechazado_y_bloqueo_ok` |
| P-27 (horarios superpuestos rechazados) | — | `test_agenda.py::test_horarios_superpuestos_rechazados` |
| P-28 (cambios de agenda con turnos afectados) | — | `test_agenda.py::test_cambio_horarios_afecta_turnos_rechazado` |
| P-40 (bloqueo que solapa turnos existentes) | — | `test_agenda.py::test_bloqueo_con_turnos_rechazado_y_bloqueo_ok` |

### H4 — turnos y reservas

| Requisito | Implementación | Test |
|---|---|---|
| RF-05 (reserva web, verificación requerida) | `app/services/turno_service.py::reservar_web`, `POST /turnos` | `test_turnos.py::test_reserva_web_ok_y_notificacion` |
| RF-06 (prevención turnos duplicados mismo médico) | `turno_service.py` + `ex_turno_medico` | `test_turnos.py::test_reserva_duplicada_mismo_medico_falla` |
| RF-07 (creación de turnos desde recepción) | `app/services/turno_service.py::reservar_recepcion`, `POST /turnos/recepcion` | `test_turnos.py::test_reserva_recepcion_ok` |
| RF-25, RN-33 (prevención solapamiento mismo paciente) | `turno_service.py` + `ex_turno_paciente` | `test_turnos.py::test_reserva_solapada_mismo_paciente_distintos_medicos_falla` |
| RN-05, RN-06 (validación de agenda médica) | `turno_service.py::_validar_horario_agenda` | `test_turnos.py::test_reserva_fuera_de_agenda_o_bloqueada_rechazada` |
| RN-21, RN-36 (restricción Usuario rojo) | `turno_service.py::es_usuario_rojo` (403 web, recepción permitida) | `test_turnos.py::test_reserva_web_usuario_rojo_rechazada` |
| RN-32 (confirmación única e idempotente) | `notificacion_service.crear` + `uq_notificacion_confirmacion_recordatorio` | `test_turnos.py::test_reserva_web_ok_y_notificacion` |
| RN-37 (rate limit reservas: 10/hora) | `RateLimiter(prefijo="booking:paciente", limite="10/hour")` | `test_turnos.py` |
| RNF-02 (integridad y transaccionalidad atómica) | Rollback total ante `IntegrityError`, exclusion constraints con `btree_gist` | `test_turnos.py::test_reserva_concurrente_mismo_slot` |
| RNF-03 (permisos server-side en turnos) | `turnos.py`, `turno_service.listar_turnos`, `obtener_turno` | `test_turnos.py::test_listar_turnos_permisos_y_filtros` |
| P-08, P-09, P-10, P-11, P-32, P-37, P-38 | — | `test_turnos.py` |

### H5 — cancelaciones y solicitudes rápidas

| Requisito | Implementación | Test |
|---|---|---|
| RF-08 (cancelación habitual >= 24 hs, libera horario) | `app/services/cancelacion_service.py::cancelar_turno_paciente`, `POST /turnos/{id}/cancelar` | `test_cancelaciones.py::test_cancelacion_habitual_mas_de_24hs_y_libera_horario` |
| RF-09 (solicitud rápida < 24 hs, resolución recepción) | `cancelacion_service.py::solicitar_cancelacion_rapida`, `POST /turnos/{id}/solicitar-cancelacion` | `test_cancelaciones.py::test_cancelacion_menos_de_24hs_rechaza_habitual_y_permite_rapida` |
| RF-10, RF-24, RN-34 (cancelación desde recepción) | `cancelacion_service.py::cancelar_turno_recepcion`, `POST /turnos/{id}/cancelar-recepcion` | `test_cancelaciones.py::test_cancelacion_desde_recepcion_con_motivo_y_trazabilidad` |
| RF-22 (notificación CANCELACION_TURNO) | `notificacion_service.cuerpo_cancelacion_turno` | `test_cancelaciones.py::test_cancelacion_habitual_mas_de_24hs_y_libera_horario` |
| RN-10..RN-14 (reglas de cancelación y liberación) | `cancelacion_service.py` | `test_cancelaciones.py` |
| P-12 (cancelación habitual >= 24 hs) | — | `test_cancelaciones.py::test_cancelacion_habitual_mas_de_24hs_y_libera_horario` |
| P-13 (cancelación rápida < 24 hs) | — | `test_cancelaciones.py::test_cancelacion_menos_de_24hs_rechaza_habitual_y_permite_rapida` |
| P-14 (solicitud con motivo) | — | `test_cancelaciones.py::test_solicitud_cancelacion_rapida_valida_motivo` |
| P-15 (resolución de solicitud por recepción) | — | `test_cancelaciones.py::test_resolucion_solicitud_cancelacion_por_recepcion` |
| P-16 (cancelación desde recepción con motivo) | — | `test_cancelaciones.py::test_cancelacion_desde_recepcion_con_motivo_y_trazabilidad` |

### H6 — recepción: llegadas, orden de atención y ausencias

| Requisito | Implementación | Test |
|---|---|---|
| RF-11 (registro de llegada, prevención duplicados) | `app/services/llegada_service.py::registrar_llegada`, `POST /recepcion/turnos/{id}/llegada` | `test_llegadas_y_orden.py::test_registro_llegada_ok_y_duplicada_rechazada` |
| RF-12, RN-15..RN-19 (orden de atención y tolerancia 10 min) | `app/domain/orden_atencion.py`, `llegada_service.py::obtener_sala_espera` | `test_llegadas_y_orden.py::test_orden_atencion_y_tolerancia_10_minutos` |
| RF-15 (ausencias individuales y cierre de jornada) | `llegada_service.py::registrar_ausencia_individual`, `cerrar_jornada_ausencias` | `test_llegadas_y_orden.py::test_registro_ausencias_individual_y_cierre_jornada` |
| P-17 (registro de llegada) | — | `test_llegadas_y_orden.py::test_registro_llegada_ok_y_duplicada_rechazada` |
| P-18 (llegada duplicada prevenida) | — | `test_llegadas_y_orden.py::test_registro_llegada_ok_y_duplicada_rechazada` |
| P-19 (orden de atención de pacientes puntuales) | — | `test_llegadas_y_orden.py::test_orden_atencion_y_tolerancia_10_minutos` |
| P-20 (tolerancia: llegada > 10 min pierde prioridad) | — | `test_llegadas_y_orden.py::test_orden_atencion_y_tolerancia_10_minutos` |
| P-21 (confirmación de ausencias) | — | `test_llegadas_y_orden.py::test_registro_ausencias_individual_y_cierre_jornada` |

Decisiones con impacto en trazabilidad:

| Decisión | Efecto | Dónde queda cubierto |
|---|---|---|
| **Q1 = A**: contraseña temporal = DNI literal | Excepción **documentada** a RN-28 para las cuentas creadas por recepción, porque RF-02, CU-13 y P-04 exigen que la primera credencial sea el DNI. RN-29 sigue vigente vía `debe_cambiar_password`. | `test_auth_primer_ingreso.py::test_login_con_password_temporal` |
| **C1**: 401 uniforme en el login | Un DNI inexistente, una contraseña incorrecta y una cuenta deshabilitada devuelven lo mismo; la causa real solo queda en `AUDITORIA`. | `test_auth_login.py`, `test_auditoria.py` |
| **C2**: el restablecimiento revoca todas las sesiones | `refresh_service.revocar_sesiones_usuario` se llama en el restablecimiento y en cualquier cambio de contraseña; el refresh posterior devuelve `401 SESION_INVALIDA`. | `test_auth_recuperacion.py`, `test_auth_cambiar_password.py` |
| **C3**: `/auth/me` responde 200 con `debe_cambiar_password` | El SPA distingue "sesión inválida" de "falta cambiar la contraseña"; con el flag activo el resto de los endpoints devuelve `403 CAMBIO_PASSWORD_REQUERIDO` (validado también e2e sobre `/pacientes`). | `test_auth_primer_ingreso.py`, `test_pacientes.py` |
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
| P-01..P-04, P-31, P-41, P-43 | `backend/tests/test_auth_registro.py`, `test_auth_verificacion.py`, `test_pacientes.py`, `test_notificaciones.py` (H2.2) |
| P-05..P-07, P-33, P-36 | `backend/tests/test_auth_login.py`, `test_auth_primer_ingreso.py`, `test_auth_cambiar_password.py`, `test_rate_limits.py` (H2.1/H2.3) |
| P-08..P-11, P-37, P-38, P-42 | `backend/tests/integration/test_turnos_reserva.py`, `test_turnos_concurrencia.py` |
| P-12..P-16 | `backend/tests/integration/test_turnos_cancelacion.py` |
| P-17..P-21 | `backend/tests/integration/test_turnos_llegada.py`, `test_turnos_orden.py`, `test_turnos_ausencia.py` |
| P-22, P-23 | `backend/tests/integration/test_notas.py` |
| P-24..P-26 | `backend/tests/integration/test_restricciones.py` |
| P-27, P-28, P-40 | `backend/tests/integration/test_agenda_*.py` |
| P-29 | `backend/tests/test_permisos.py` |
| P-30 | `backend/tests/test_auditoria.py` (H2.1; cada hito suma sus acciones) |
| P-32, P-34, P-35 | `backend/tests/test_auth_recuperacion.py` (H2.3; P-32 se difiere a H4) |
| P-39 | `backend/tests/integration/test_scheduler_recordatorio.py` |
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
