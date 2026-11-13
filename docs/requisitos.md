# PROYECTO: SISTEMA WEB DE GESTIÓN DE TURNOS MÉDICOS

## 1. DESCRIPCIÓN DEL PROYECTO

El proyecto consiste en desarrollar un sistema web para gestionar los turnos de un
centro médico que brinda consultas programadas.

El sistema permitirá que los pacientes se registren, inicien sesión, consulten la
disponibilidad de los profesionales y soliciten o cancelen turnos de acuerdo con las
condiciones establecidas.

También permitirá que el personal de recepción gestione los pacientes, registre sus
llegadas, cree turnos en nombre de ellos, administre situaciones excepcionales y
controle las inasistencias.

Por su parte, los médicos podrán consultar sus agendas y registrar anotaciones breves
sobre los avances o mejoras de los pacientes, con el objetivo de mantener organizado
su seguimiento y posteriormente trasladar esa información a sus respectivas historias
clínicas.

El sistema estará destinado exclusivamente a la gestión administrativa de turnos y al
registro de anotaciones de seguimiento. **No reemplazará ni incluirá una historia
clínica digital.**

## 2. PROBLEMA QUE SE BUSCA RESOLVER

La gestión manual de turnos puede ocasionar superposiciones de horarios, errores en las
reservas, dificultades para localizar información de los pacientes y problemas para
organizar la atención.

También pueden presentarse inconvenientes relacionados con las cancelaciones fuera de
término, las inasistencias reiteradas y la falta de información sobre la llegada de los
pacientes.

El sistema busca centralizar la información, evitar reservas duplicadas, mejorar la
organización de las agendas médicas y facilitar el trabajo de pacientes, recepcionistas,
médicos y administradores.

## 3. OBJETIVOS

### Objetivo general

Desarrollar un sistema web que permita gestionar de manera organizada, segura y
eficiente los turnos de un centro médico.

### Objetivos específicos

- Permitir el registro e inicio de sesión de los pacientes.
- Facilitar la consulta de disponibilidad y solicitud de turnos.
- Evitar que dos pacientes reserven el mismo horario con un mismo médico.
- Permitir la cancelación de turnos respetando las condiciones establecidas.
- Incorporar un procedimiento de solicitud de cancelación rápida para situaciones
  excepcionales.
- Facilitar la creación y administración de turnos desde recepción.
- Registrar la llegada de los pacientes y organizar el orden de atención.
- Permitir que los médicos consulten sus agendas y registren anotaciones de
  seguimiento.
- Controlar las inasistencias y cancelaciones reiteradas.
- Administrar los horarios de atención de los profesionales.
- Proteger los datos personales y garantizar la integridad de la información.
- **`[NUEVO]`** Verificar el correo electrónico de los pacientes y permitir la
  recuperación segura de contraseñas.
- **`[NUEVO]`** Enviar notificaciones por correo ante eventos relevantes del ciclo de
  vida del turno.

## 4. ALCANCE DEL SISTEMA

El sistema incluirá:

- Registro e inicio de sesión de pacientes.
- **`[CAMBIO]`** Verificación de correo electrónico obligatoria antes de poder reservar.
- **`[CAMBIO]`** Recuperación de contraseña por correo electrónico.
- **`[NUEVO]`** Cambio obligatorio de contraseña en el primer ingreso de cuentas
  creadas por recepción.
- **`[NUEVO]`** Notificaciones por correo ante eventos del ciclo de vida del turno
  (lista cerrada, ver RF-22).
- Gestión de usuarios y permisos según el rol.
- Registro de pacientes desde recepción en casos excepcionales.
- Consulta de especialidades, profesionales y horarios disponibles.
- Solicitud y reserva de turnos.
- Prevención de reservas duplicadas.
- **`[NUEVO]`** Prevención de turnos solapados del mismo paciente.
- Cancelación habitual y solicitud de cancelación rápida.
- **`[CAMBIO]`** Cancelación desde recepción (habitual y rápida) con motivo
  obligatorio, usuario responsable y fecha/hora.
- Gestión de pacientes y turnos desde recepción.
- Registro de llegada y organización del orden de atención.
- Registro de ausencias.
- Clasificación de usuarios como «Usuario rojo» y aplicación de restricciones
  temporales.
- Consulta de agenda médica.
- Registro de anotaciones sobre avances o mejoras de los pacientes.
- Gestión de horarios y bloqueos de agenda.
- Registro de acciones importantes para mantener la trazabilidad.

Quedan fuera del alcance:

- Atención de emergencias.
- Internaciones.
- Facturación.
- Gestión de farmacias.
- Elaboración y administración de historias clínicas.
- Registro de diagnósticos, recetas y tratamientos médicos.

Las anotaciones realizadas por los médicos en el sistema serán únicamente herramientas
de organización y seguimiento. La historia clínica continuará siendo responsabilidad
del profesional y se gestionará fuera de esta plataforma.

## 5. USUARIOS DEL SISTEMA Y SUS FUNCIONES

### 5.1. Paciente

Podrá:

- Registrarse desde la página web.
- **`[CAMBIO]`** Verificar su correo electrónico mediante un enlace enviado al
  registrarse.
- Iniciar sesión mediante DNI y contraseña.
- **`[CAMBIO]`** Recuperar su contraseña por correo electrónico.
- Consultar especialidades y profesionales.
- Visualizar los horarios disponibles.
- **`[CAMBIO]`** Reservar turnos (solo si su correo está verificado y no tiene
  restricción de Usuario rojo vigente).
- Consultar sus próximos turnos y su historial de turnos.
- Cancelar turnos cuando cumplan el plazo establecido.
- Solicitar una cancelación rápida cuando falten menos de 24 horas, explicando el
  motivo.
- **`[CAMBIO]`** Cancelar turnos desde la web aun estando clasificado como Usuario rojo
  (la restricción solo impide **reservar**, no cancelar).

Si el paciente tiene una restricción de Usuario rojo, no podrá reservar desde la
página web durante el período establecido.

### 5.2. Recepcionista

Podrá:

- Iniciar sesión con sus credenciales.
- Buscar pacientes mediante su DNI.
- Registrar pacientes en casos excepcionales.
- **`[NUEVO]`** Marcar el correo del paciente como verificado al crear la cuenta.
- Crear turnos en nombre de los pacientes.
- Consultar y administrar los turnos.
- Registrar la llegada de los pacientes.
- Consultar el orden de atención.
- Gestionar las solicitudes de cancelación rápida.
- **`[CAMBIO]`** Realizar cancelaciones desde recepción (habituales o rápidas) con
  motivo, usuario y fecha/hora.
- Revisar y registrar las ausencias al finalizar la jornada.
- Marcar a un paciente como Usuario rojo cuando presente reiteradas inasistencias o
  cancelaciones.
- Consultar las restricciones vigentes de los pacientes.
- **`[NUEVO]`** Resolver las situaciones derivadas de bloqueos de agenda que afecten
  turnos ya reservados (cancelación con motivo `BLOQUEO_AGENDA`).

### 5.3. Médico

Podrá:

- Iniciar sesión con sus credenciales.
- Consultar su agenda de turnos.
- Visualizar los pacientes que se encuentran en espera.
- Consultar los datos necesarios para identificar al paciente.
- Registrar anotaciones breves sobre los avances, mejoras o aspectos de seguimiento de
  los pacientes.
- Consultar sus anotaciones anteriores para organizar el seguimiento.

Las anotaciones no constituyen una historia clínica. El médico será responsable de
trasladar la información que corresponda a la historia clínica que gestione por fuera
del sistema.

### 5.4. Administrador

Podrá:

- Gestionar los usuarios del sistema.
- Crear, modificar, habilitar o deshabilitar cuentas.
- **`[NUEVO]`** Resolver los turnos afectados antes de deshabilitar a un médico con
  turnos futuros.
- Gestionar médicos y especialidades.
- Configurar los horarios de atención.
- Establecer la duración de los turnos.
- **`[CAMBIO]`** Registrar bloqueos de agenda por licencias, vacaciones u otros
  motivos. Si el bloqueo afecta turnos existentes, el sistema exigirá resolverlos antes
  de confirmar (ver RF-26).
- Consultar información general de la gestión de turnos.
- Administrar los permisos correspondientes a cada rol.

## 6. ENTREVISTA PARA LA OBTENCIÓN DE REQUERIMIENTOS

**Entrevista 1: Administradora General (Lic. María Elena Gómez)**

**Pregunta 1:** *¿Qué problemas sufren actualmente con los turnos y la agenda médica?*

- **Respuesta:** "Tenemos muchas superposiciones de horarios y a veces dos pacientes
  quedan citados a la misma hora con el mismo médico. Necesitamos que el sistema impida
  reservas duplicadas en tiempo real y que nos permita configurar bien las
  especialidades, los horarios de cada médico y bloquear agendas cuando se toman
  vacaciones o licencias."
- **Definimos:** **RF-04**, **RF-05**, **RF-06**, **RF-17**, **RF-18** y **`[NUEVO]`
  RF-26**.

**Pregunta 2:** *¿Tienen problemas con la privacidad de los datos o la seguridad de los
accesos?*

- **Respuesta:** "Sí, cada perfil debe ver únicamente lo que le corresponde. Los
  pacientes no pueden ver información de otros, la base de datos debe respaldarse y
  todo debe ser seguro y trazable."
- **Definimos:** **RF-03**, **RF-19**, **`[NUEVO]` RF-20**, **`[NUEVO]` RF-21**,
  **RNF-01**, **RNF-03**, **RNF-06** y **RNF-08**.

**Entrevista 2: Médico Generalista (Dr. Roberto Martínez)**

**Pregunta 3:** *¿Cómo gestiona actualmente sus consultas y el seguimiento del
paciente?*

- **Respuesta:** "A mí me interesa ver desde el sistema quiénes ya llegaron y están en
  la sala de espera. Al terminar la consulta me sirve dejar una anotación breve de
  seguimiento (si mejoró, si se le pidió un estudio), pero aclaro que la historia
  clínica oficial y las recetas las llevo por fuera de la plataforma."
- **Definimos:** **RF-13**, **RF-14**, **RNF-02** y **RN-23/RN-24**.

**Entrevista 3: Supervisora de Recepción (Srta. Lucía Fernández)**

**Pregunta 4:** *¿Qué inconvenientes tienen en la atención diaria con las llegadas y
las ausencias?*

- **Respuesta:** "Llega mucha gente junta. Necesitamos buscar rápido al paciente por
  DNI, marcar su llegada para cambiar el estado a 'En espera' y que el sistema ordene
  la atención priorizando la hora del turno (dando 10 min de tolerancia). Además, hay
  adultos mayores que no manejan la web y debemos registrarlos o darles turno
  nosotros."
- **Definimos:** **RF-02**, **RF-07**, **RF-11**, **RF-12** y **`[NUEVO]` RF-23**.

**Pregunta 5:** *¿Qué ocurre si un paciente falta mucho o cancela a último momento?*

- **Respuesta:** "Las cancelaciones a menos de 24 hs nos dejan huecos vacíos. El
  paciente debería enviar un pedido de cancelación rápida justificando la causa para
  que nosotras lo evaluemos. Y si alguien falta o cancela reiteradamente, queremos
  poder clasificarlo como 'Usuario rojo' para suspenderle la reserva web por un mes."
- **Definimos:** **RF-08**, **RF-09**, **RF-10**, **`[NUEVO]` RF-24**, **RF-15** y
  **RF-16**.

**`[NUEVO]` Entrevista 4: Responsable de Sistemas (Ing. Pablo Suárez)**

**Pregunta 6:** *¿Cómo quieren manejar la comunicación con los pacientes y la
seguridad de las cuentas?*

- **Respuesta:** "Necesitamos que el correo sea obligatorio y único, que se verifique
  antes de dejar reservar, que el paciente pueda recuperar su contraseña sin llamarnos
  y que le lleguen mails de confirmación, cancelación y recordatorio. Los envíos no
  pueden hacer fallar la operación principal: si el SMTP se cae, el turno se reserva
  igual."
- **Definimos:** **`[NUEVO]` RF-20**, **RF-21**, **RF-22**, **RF-25**, **RF-27**,
  **RN-26** a **RN-38**, **RNF-10** y **RNF-11**.

## 7. REQUERIMIENTOS FUNCIONALES

### RF-01. Registro de pacientes **`[CAMBIO]`**

El sistema deberá permitir que los pacientes se registren desde la página web
ingresando sus datos personales, DNI, contraseña y **correo electrónico obligatorio**.
El número de celular será **opcional**.

El **correo electrónico** deberá ser único a nivel global y se utilizará como medio de
contacto y para notificaciones.

El DNI deberá ser único y se utilizará como identificador para iniciar sesión.

El sistema deberá verificar que el DNI y el correo electrónico no se encuentren
registrados previamente.

Al confirmar el registro, el sistema enviará un correo de verificación y la cuenta
quedará en estado **no verificada** hasta que el paciente confirme el enlace (ver
RF-20). Hasta entonces, el paciente podrá iniciar sesión, pero **no podrá reservar
turnos**.

**`CU-01: Registrar un paciente desde la web`**.

### RF-02. Registro de pacientes desde recepción **`[CAMBIO]`**

El sistema deberá permitir que la recepcionista cree una cuenta para un paciente en
situaciones excepcionales, como personas adultas o personas que tengan dificultades
para utilizar la página web.

Para realizar el registro, la recepcionista deberá solicitar los datos personales del
paciente, DNI y **correo electrónico obligatorio**. El teléfono es opcional.

La contraseña inicial será el DNI del paciente, que deberá ser cambiada
obligatoriamente en el primer ingreso (ver RF-23).

**`[CAMBIO]`** El correo electrónico ingresado por la recepcionista se considerará
**verificado al momento de la creación de la cuenta**, dado que la recepcionista
confirma el contacto en forma presencial con el paciente. No se enviará correo de
verificación para estas cuentas.

**`[SUPOSICIÓN]`** Si el paciente no dispone de correo propio y se utiliza el correo
de un familiar, ese correo igualmente deberá ser único: el familiar deberá emplear un
alias (por ejemplo, `nombre+paciente1@dominio.com`) o crear una casilla adicional.

**`CU-02: Crear un paciente desde la recepción`**.

### RF-03. Inicio de sesión y control de roles

El sistema deberá permitir el inicio de sesión mediante DNI y contraseña.

Las funcionalidades disponibles dependen del rol asignado a cada usuario: Paciente,
Recepcionista, Médico o Administrador.

El sistema deberá validar las credenciales, impedir el acceso a cuentas deshabilitadas
y restringir el acceso a funciones no autorizadas.

**`[CAMBIO]`** El sistema deberá aplicar un límite de intentos fallidos de inicio de
sesión (ver RN-37 y RF-27).

(**Aplica a todos los CUs**).

### RF-04. Consulta de disponibilidad

El sistema deberá permitir que los pacientes consulten las especialidades, los
profesionales y los horarios disponibles.

La disponibilidad deberá actualizarse de acuerdo con los turnos ya reservados y los
bloqueos de agenda registrados.

**`CU-04: Crear un turno desde recepción`**.

### RF-05. Solicitud y reserva de turnos

El sistema deberá permitir que los pacientes soliciten turnos seleccionando una
especialidad, un profesional y un horario disponible.

Antes de confirmar la reserva, el sistema deberá verificar nuevamente que el horario
continúe disponible.

Una vez confirmada la operación, el turno quedará registrado con estado RESERVADO.

**`[CAMBIO]`** El sistema solo permitirá reservar a pacientes cuyo correo electrónico
esté verificado y que no tengan una restricción vigente de Usuario rojo.

**`[CAMBIO]`** Al confirmar la reserva, el sistema encolará el envío de la notificación
`CONFIRMACION_TURNO` al correo del paciente (ver RF-22).

**`CU-03: Solicitar un turno`**.

### RF-06. Prevención de turnos duplicados

El sistema deberá impedir que dos pacientes reserven el mismo horario con el mismo
médico.

La validación deberá realizarse al momento de confirmar la reserva y deberá garantizar
que dos solicitudes simultáneas no puedan ocupar el mismo horario.

**`[CAMBIO]`** La garantía deberá implementarse **en la base de datos** mediante una
restricción de exclusión (ver RNF-02 y RN-09) sobre los turnos en estado activo, además
de la validación en la lógica de negocio.

Si el horario ya fue reservado, el sistema informará que no se encuentra disponible y
permitirá seleccionar otro.

**`CU-04: Crear un turno desde recepción`**.

### RF-07. Creación de turnos desde recepción

El sistema deberá permitir que la recepcionista cree turnos en nombre de los pacientes.

Para ello podrá buscar al paciente mediante su DNI, seleccionar el profesional y elegir
un horario disponible.

El sistema deberá aplicar las mismas validaciones de disponibilidad que utiliza para
las reservas realizadas por los pacientes desde la web.

Además, deberá registrar qué usuario de recepción realizó la operación.

**`CU-04: Crear un turno desde recepción`**.

### RF-08. Cancelación habitual de turnos

El sistema deberá permitir que los pacientes cancelen sus turnos desde la página web
cuando falten al menos 24 horas para el horario programado.

Al realizar la cancelación, el sistema deberá cambiar el estado del turno a CANCELADO y
liberar el horario para que pueda ser reservado nuevamente.

**`[CAMBIO]`** Al confirmar la cancelación se encolará la notificación
`CANCELACION_TURNO` (subtipo `HABITUAL`) al correo del paciente.

**`CU-05: Cancelar un turno`**.

### RF-09. Solicitud de cancelación rápida por parte del paciente

Cuando falten menos de 24 horas para el turno, el sistema deberá deshabilitar la opción
de cancelación habitual del paciente.

En su lugar, deberá habilitar la opción «Solicitud de cancelación rápida».

El paciente deberá seleccionar el turno que desea cancelar y explicar el motivo de la
solicitud.

La solicitud quedará pendiente de revisión por parte de recepción.

Si la solicitud es aprobada, el turno cambiará a CANCELADO y se liberará el horario. Si
es rechazada, el turno conservará su estado original.

**`[CAMBIO]`** Al resolverse la solicitud (aprobada o rechazada), se encolará la
notificación `CANCELACION_TURNO` con el subtipo correspondiente al correo del paciente.

**`CU-06: Solicitar una cancelación rápida`**.

### RF-10. Cancelación rápida desde recepción

El sistema deberá permitir que la recepcionista realice una cancelación rápida cuando
se presente una situación excepcional, por ejemplo, si un paciente sufre un incidente
que le impide asistir.

La operación deberá registrar el motivo, la fecha y hora y el usuario responsable de
realizarla.

Una vez confirmada la cancelación, el turno cambiará a CANCELADO y el horario quedará
disponible nuevamente.

**`[CAMBIO]`** Se encolará la notificación `CANCELACION_TURNO` (subtipo `RAPIDA`) al
correo del paciente.

**`CU-06: Solicitar una cancelación rápida`** (resolución por recepción).

### RF-11. Registro de llegada

El sistema deberá permitir que recepción busque al paciente mediante su DNI, consulte
sus turnos y registre su llegada.

Cuando se confirme la llegada, el estado del turno cambiará de RESERVADO a EN_ESPERA.

El sistema deberá guardar la fecha y hora exactas de llegada.

No se permitirá registrar dos veces la llegada de un mismo turno.

**`CU-07: Registrar la llegada de un paciente`**.

### RF-12. Organización del orden de atención

El sistema deberá facilitar la organización de los pacientes que se encuentran
esperando.

**`[CAMBIO]`** El orden de atención se calculará así:

1. Primero los pacientes que llegaron **dentro de los 10 minutos de tolerancia**
   posteriores al horario programado, ordenados por **horario programado** y, en caso
   de empate, por **hora de llegada**.
2. Luego los pacientes que llegaron **fuera de la tolerancia**, ordenados por **hora
   de llegada**.

Llegar antes no permitirá adelantar a una persona que tenga un turno programado
previamente.

**`CU-07: Registrar la llegada de un paciente`** y **`CU-08: Consultar agenda y
registrar anotaciones`**.

### RF-13. Registro de atención y finalización del turno

El sistema permitirá que el médico consulte los turnos en espera y, una vez finalizada
la consulta, que el turno sea registrado como ATENDIDO.

El cambio de estado tendrá una finalidad administrativa y no implicará el registro de
una historia clínica.

**`CU-08: Consultar agenda y registrar anotaciones`**.

### RF-14. Registro de anotaciones médicas

El sistema deberá permitir que el médico registre anotaciones breves sobre los avances,
mejoras o aspectos relevantes del seguimiento de los pacientes.

Estas anotaciones permitirán mantener una mejor organización de la información y
servirán como referencia para que el profesional posteriormente las incorpore a su
historia clínica externa.

El sistema no deberá funcionar como una historia clínica digital ni incluir
diagnósticos, recetas o tratamientos.

**`CU-08: Consultar agenda y registrar anotaciones`**.

### RF-15. Registro de ausencias

El sistema deberá permitir que recepción revise los turnos que permanecen en estado
RESERVADO y que no registraron llegada.

Al finalizar la jornada, la recepcionista podrá confirmar individualmente las ausencias
y cambiar el estado correspondiente a AUSENTE.

El sistema deberá conservar el registro de estas operaciones.

**`[NUEVO]` Caso de Uso Secundario / Proceso final de jornada: Registrar ausencias**.

### RF-16. Clasificación de usuarios como Usuario rojo

El sistema deberá permitir que la recepcionista marque a un paciente como «Usuario
rojo» cuando presente reiteradas inasistencias o cancelaciones de turnos.

La clasificación será realizada por recepción y no se aplicará automáticamente.

Al marcar al paciente, el sistema deberá establecer una restricción de un mes durante
la cual no podrá reservar turnos desde la página web.

Durante ese período, el paciente deberá solicitar sus turnos presencialmente en
recepción.

Una vez cumplido el mes, el sistema deberá levantar la restricción y habilitar
nuevamente las reservas desde la web.

**`[CAMBIO]`** El estado «Usuario rojo» se deriva de la existencia de una fila vigente
en la tabla `RESTRICCION_USUARIO` (`activa = TRUE` y `fecha_fin > ahora`). **No existe
un flag en `PACIENTE`.** La restricción se evalúa por fecha al consultar, sin depender
de tareas programadas.

**`[CAMBIO]`** Al crear la restricción se encolará la notificación
`RESTRICCION_USUARIO_ROJO` al correo del paciente.

**`CU-10: Clasificar un Usuario rojo`**.

### RF-17. Gestión de horarios médicos

El sistema deberá permitir que el administrador gestione los días y horarios de
atención de cada profesional, la duración de los turnos y los períodos en los que no
estará disponible.

**`[CAMBIO]`** Antes de confirmar una modificación, deberá verificar que no se generen
superposiciones ni conflictos con turnos ya reservados. Si existieran turnos afectados,
el sistema rechazará la operación y devolverá la lista de turnos afectados (ver RF-26).

**`CU-09: Gestionar horarios médicos`**.

### RF-18. Gestión de especialidades y profesionales

El sistema deberá permitir que el administrador registre, modifique y habilite o
deshabilite especialidades y profesionales.

**`[NUEVO]`** Al deshabilitar un médico que tenga turnos futuros en estado RESERVADO o
EN_ESPERA, el sistema exigirá resolver esos turnos antes de confirmar (cancelación con
motivo `DESHABILITACION_MEDICO` o reasignación desde recepción). Cada cancelación
notificará al paciente afectado.

**`[NUEVO]` Caso de Uso Administrador: Gestionar especialidades y profesionales`**.

### RF-19. Registro de acciones

El sistema deberá conservar información sobre las operaciones importantes realizadas
por los usuarios, especialmente las reservas, cancelaciones, modificaciones de agenda,
solicitudes rápidas y restricciones de usuarios.

Se deberá identificar quién realizó cada operación y cuándo.

**`[CAMBIO]`** Además, se registrarán: verificación de correo, solicitudes y
resoluciones de recuperación de contraseña, cambios de contraseña, alta/baja de
usuarios, bloqueos de agenda, marcado y levantamiento de Usuario rojo, y registro de
ausencias.

(**Aplica a todos los casos de uso**).

### `[NUEVO]` RF-20. Verificación de correo electrónico

Al registrarse desde la web, el sistema deberá enviar un correo con un enlace único de
verificación al correo ingresado.

El enlace contendrá un token de un solo uso, almacenado **hasheado** en la base de
datos, con expiración de 24 horas.

Al hacer clic, el sistema marcará el correo como verificado y habilitará al paciente
para reservar turnos.

El sistema deberá ofrecer un mecanismo de reenvío del correo de verificación con límite
de frecuencia (ver RN-37).

Las cuentas creadas por recepción no requieren verificación de correo (ver RF-02).

**`CU-11: Verificar correo electrónico`**.

### `[NUEVO]` RF-21. Recuperación de contraseña

El sistema deberá permitir que un paciente o un usuario del centro solicite la
recuperación de su contraseña desde la pantalla de inicio de sesión.

El formulario solicitará **correo electrónico y DNI juntos**. La respuesta será
**siempre la misma** («si los datos coinciden, se envió un correo») con independencia
de si el par existe o no, para no permitir enumeración de cuentas.

Si el par coincide, el sistema enviará un correo con un enlace de restablecimiento que
contendrá un token de un solo uso, almacenado hasheado, con expiración de 1 hora.

Al hacer clic, el usuario podrá definir una nueva contraseña. La nueva contraseña deberá
cumplir la política de RN-28.

**`CU-12: Recuperar contraseña`**.

### `[NUEVO]` RF-22. Notificaciones por correo electrónico

El sistema deberá enviar notificaciones por correo ante los siguientes eventos (lista
cerrada):

| Tipo | Disparador |
|---|---|
| `VERIFICACION_EMAIL` | Alta de paciente desde la web |
| `RECUPERACION_PASSWORD` | Solicitud de recuperación de contraseña |
| `CONFIRMACION_TURNO` | Confirmación de reserva (web o recepción) |
| `CANCELACION_TURNO` | Cancelación (habitual, rápida aprobada, rápida rechazada, por bloqueo) |
| `TURNO_AFECTADO_POR_AGENDA` | Cancelación por bloqueo o cambio de horario |
| `RESTRICCION_USUARIO_ROJO` | Marcado como Usuario rojo |
| `RECORDATORIO_24H` | Recordatorio 24 hs antes del turno |

El envío será **asíncrono**: no deberá hacer fallar la operación principal que lo
dispara. El fallo de envío se registrará en la tabla `NOTIFICACION` con estado
`FALLIDA`, junto con el motivo del error y el número de intentos.

**`[CAMBIO]`** Cada notificación se identificará de forma que el sistema no la envíe dos
veces por el mismo evento (ver RN-32).

**`[CAMBIO]`** El recordatorio de 24 hs se enviará solo si el turno fue creado con al
menos 23 h 30 min de anticipación; caso contrario se omite y se registra el motivo.

### `[NUEVO]` RF-23. Cambio obligatorio de contraseña en primer ingreso

Las cuentas creadas por recepción (RF-02) tendrán como contraseña inicial el DNI del
paciente y deberán **cambiar la contraseña en el primer inicio de sesión** antes de
poder acceder a cualquier otra funcionalidad.

**`CU-13: Cambiar contraseña en primer ingreso`**.

### `[NUEVO]` RF-24. Cancelación desde recepción (habitual y rápida)

El sistema deberá permitir que la recepcionista cancele cualquier turno en estado
RESERVADO o EN_ESPERA, en cualquier momento, con independencia del plazo de 24 hs.

La operación deberá registrar obligatoriamente:

- El motivo (`HABITUAL`, `RAPIDA`, `BLOQUEO_AGENDA`, `CAMBIO_HORARIO`,
  `DESHABILITACION_MEDICO`, `DESHABILITACION_PACIENTE`, `RETIRO_VOLUNTARIO`, `OTRO`).
- Detalle libre cuando corresponda (por ejemplo, para `OTRO`).
- Usuario responsable.
- Fecha y hora de la cancelación.

El turno cambiará a CANCELADO y se encolará la notificación correspondiente al paciente.

**`CU-14: Cancelar turno desde recepción`** (complementa CU-06).

### `[NUEVO]` RF-25. Prevención de solapamiento del mismo paciente

El sistema no deberá permitir que un mismo paciente tenga dos turnos activos
(`RESERVADO` o `EN_ESPERA`) cuyos horarios se superpongan, aun cuando sean con médicos
distintos.

**`[SUPOSICIÓN]`** Esta restricción se implementará en la base de datos con la misma
técnica que la de solapamiento por médico (exclusion constraint con `btree_gist`).

La validación deberá rechazar la reserva con un mensaje claro que informe el turno ya
existente.

### `[NUEVO]` RF-26. Gestión de bloqueos de agenda con turnos afectados

El sistema deberá permitir al administrador registrar bloqueos de agenda (licencias,
vacaciones, etc.).

Si al crear o modificar un bloqueo, o al modificar los horarios habituales, existieran
turnos en estado RESERVADO o EN_ESPERA que se solapen con el nuevo rango, el sistema
deberá:

1. Rechazar la operación con código HTTP 409.
2. Devolver la lista de turnos afectados.
3. Exigir que el administrador (o recepción) cancele explícitamente cada turno afectado
   con motivo `BLOQUEO_AGENDA` o `CAMBIO_HORARIO`.
4. Encolar la notificación `TURNO_AFECTADO_POR_AGENDA` para cada paciente afectado.
5. Una vez resueltos todos los turnos, permitir confirmar el bloqueo o cambio de
   horario.

**`CU-15: Gestionar bloqueos de agenda`**.

### `[NUEVO]` RF-27. Control de intentos fallidos y rate limiting

El sistema deberá aplicar los siguientes límites (ver RN-37):

- Inicio de sesión: máximo 5 intentos fallidos por DNI en 15 minutos; al superarlos, la
  cuenta quedará bloqueada por 15 minutos.
- Inicio de sesión: máximo 20 intentos fallidos por IP en 15 minutos.
- Recuperación de contraseña: máximo 3 solicitudes por correo en 1 hora.
- Reenvío de verificación de correo: máximo 3 solicitudes por correo en 1 hora.
- Reservas: máximo 10 reservas por paciente en 1 hora.

Alcanzados los límites, el sistema responderá con código 429 y un mensaje que no
revele información sensible.

## 8. REQUERIMIENTOS NO FUNCIONALES

### RNF-01. Seguridad

Las contraseñas deberán almacenarse mediante mecanismos seguros (argon2id o bcrypt). El
sistema deberá verificar los permisos de cada usuario antes de permitir el acceso a las
funcionalidades.

**`[CAMBIO]`** Los tokens de verificación de correo y de recuperación de contraseña se
almacenarán **hasheados**. La autenticación se realizará con JWT de corta duración en
cookie `httpOnly` con `SameSite=Lax` y token CSRF adicional para métodos no
idempotentes.

### RNF-02. Integridad

El sistema deberá mantener la consistencia de los datos y evitar reservas duplicadas,
registros incompletos o relaciones inválidas.

**`[CAMBIO]`** La prevención de turnos superpuestos del mismo médico y del mismo
paciente se garantizará **en la base de datos** mediante restricciones de exclusión
(PostgreSQL `EXCLUDE` con `btree_gist` y `tstzrange`), además de la validación en la
lógica de negocio. Las reservas se realizarán en transacciones atómicas.

### RNF-03. Confidencialidad

Cada usuario solo podrá acceder a la información que corresponda a su rol y a sus
permisos.

Los pacientes no podrán consultar información privada de otros pacientes.

### RNF-04. Usabilidad

La interfaz deberá ser clara, sencilla e intuitiva, facilitando su utilización por
personas con distintos niveles de experiencia tecnológica.

**`[CAMBIO]`** Deberá ser responsive y cumplir criterios básicos de accesibilidad
(etiquetas accesibles, contraste AA, navegación por teclado).

### RNF-05. Consistencia

Los estados de los turnos deberán actualizarse correctamente según las operaciones
realizadas y respetando la tabla de transiciones permitidas (sección 10).

### RNF-06. Trazabilidad

Las operaciones importantes deberán registrar el usuario responsable, la fecha y la hora
en que fueron realizadas.

**`[CAMBIO]`** Toda operación crítica se registrará en la tabla `AUDITORIA`.

### RNF-07. Mantenimiento

El sistema deberá organizarse de manera que facilite futuras correcciones y
ampliaciones.

### RNF-08. Respaldo

Deberán realizarse copias de seguridad periódicas para permitir la recuperación de la
información ante posibles fallas.

**`[CAMBIO]`** Se proveerá un script de respaldo (`pg_dump` comprimido, retención de 30
días) y un script de restauración documentado.

### RNF-09. Disponibilidad

El sistema deberá encontrarse disponible para que los usuarios puedan consultar y
gestionar los turnos, excepto durante tareas de mantenimiento o interrupciones
justificadas.

### `[NUEVO]` RNF-10. Zona horaria

La base de datos almacenará todas las fechas y horas en UTC. Las reglas de negocio que
dependen de la hora local (ventana de 24 hs para cancelación, tolerancia de 10 minutos,
cálculo del día de la semana para horarios, recordatorio 24 hs) se calcularán en la zona
`America/Argentina/Buenos_Aires`.

### `[NUEVO]` RNF-11. Resiliencia de notificaciones

El envío de correos se realizará de forma asíncrona mediante un worker. El fallo de
envío no deberá abortar la operación principal. Las notificaciones fallidas se
reintentarán con backoff exponencial hasta un máximo de 3 intentos; superado ese
límite, quedarán en estado `FALLIDA` para revisión manual.

## 9. REGLAS DE NEGOCIO

**RN-01. Identificación de pacientes:** cada paciente deberá tener un DNI único
registrado como texto y no como número.

**RN-02. `[CAMBIO]` Datos de contacto:** cada paciente deberá registrar un **correo
electrónico obligatorio y único a nivel global**. El número de celular será opcional.

**RN-03. Credenciales:** los pacientes iniciarán sesión mediante DNI y contraseña. En
los registros excepcionales realizados por recepción, la contraseña inicial será el DNI
del paciente y deberá cambiarse en el primer ingreso.

**RN-04. Identificación de usuarios:** cada usuario tendrá un identificador único y un
rol asignado.

**RN-05. Asociación de turnos:** cada turno deberá estar asociado a un paciente y a un
médico.

**RN-06. Especialidades:** cada médico deberá estar asociado a una especialidad.

**RN-07. Disponibilidad médica:** un médico no podrá tener dos turnos cuyos horarios se
superpongan.

**RN-08. Horarios habilitados:** los turnos solo podrán reservarse dentro de los
horarios habilitados del profesional.

**RN-09. Prevención de reservas duplicadas:** el sistema deberá impedir que dos
pacientes reserven el mismo horario con el mismo médico, incluso cuando las solicitudes
se realicen simultáneamente. La garantía deberá instrumentarse en la base de datos.

**RN-10. Conservación de turnos:** los turnos cancelados no deberán eliminarse
físicamente de la base de datos; deberán conservarse con el estado CANCELADO.

**RN-11. Plazo de cancelación habitual:** el paciente podrá cancelar un turno desde la
web cuando falten al menos 24 horas para su horario programado.

**RN-12. Cancelación rápida:** cuando falten menos de 24 horas, el paciente no podrá
utilizar la cancelación habitual y deberá realizar una solicitud de cancelación rápida
explicando el motivo.

**RN-13. Resolución de solicitudes:** las solicitudes de cancelación rápida deberán ser
revisadas por recepción antes de modificar el estado del turno.

**RN-14. Cancelación excepcional desde recepción:** recepción podrá realizar una
cancelación rápida ante situaciones excepcionales, registrando el motivo y el usuario
responsable.

**RN-15. Registro de llegada:** recepción solo podrá registrar la llegada de un paciente
para un turno válido que corresponda.

**RN-16. Prioridad de atención:** tendrán prioridad los pacientes que hayan llegado a
tiempo para su turno, respetando el horario programado.

**RN-17. Desempate:** cuando dos pacientes tengan el mismo horario programado, se
utilizará la hora de llegada como criterio de desempate.

**RN-18. Tolerancia:** se contemplará una tolerancia de 10 minutos posteriores al
horario programado. Superado ese tiempo, el paciente perderá la prioridad de su turno.

**RN-19. Ausencias:** recepción revisará los turnos sin llegada al finalizar la jornada
y confirmará individualmente cuáles quedarán registrados como AUSENTE.

**RN-20. Usuario rojo:** recepción podrá clasificar como Usuario rojo a un paciente que
presente reiteradas inasistencias o cancelaciones.

**RN-21. Restricción temporal:** el Usuario rojo no podrá reservar turnos desde la web
durante un mes y deberá solicitarlos presencialmente en recepción. **`[CAMBIO]`** Podrá
iniciar sesión, consultar sus turnos y cancelarlos.

**RN-22. Finalización de la restricción:** una vez cumplido el mes, el sistema deberá
habilitar nuevamente la reserva de turnos por internet. **`[CAMBIO]`** La restricción se
evalúa por fecha al consultar, sin tareas programadas.

**RN-23. Anotaciones médicas:** el médico podrá registrar anotaciones breves de
seguimiento, pero estas no reemplazarán la historia clínica ni constituirán un registro
clínico integral.

**RN-24. Acceso a anotaciones:** únicamente el médico autorizado podrá registrar o
modificar sus anotaciones de seguimiento.

**RN-25. Cambios de horarios:** las modificaciones en los horarios habituales de los
médicos no deberán alterar automáticamente los turnos ya reservados. Los conflictos
deberán resolverse antes de confirmar el cambio (ver RF-26).

### `[NUEVO]` RN-26. Unicidad y obligatoriedad del correo

Todo paciente deberá tener un correo electrónico único a nivel global. El correo es
obligatorio incluso en cuentas creadas por recepción. El teléfono es opcional.

### `[NUEVO]` RN-27. Verificación de correo

Los pacientes registrados desde la web deberán verificar su correo electrónico antes de
poder reservar turnos. Las cuentas creadas por recepción se consideran verificadas al
momento de su creación.

### `[NUEVO]` RN-28. Política de contraseñas

Las contraseñas deberán tener al menos 10 caracteres y contener al menos una letra y un
dígito. La validación se realizará tanto en el cliente como en el servidor.

### `[NUEVO]` RN-29. Cambio obligatorio de contraseña

Las cuentas creadas por recepción deberán cambiar la contraseña en el primer inicio de
sesión antes de acceder a cualquier otra funcionalidad.

### `[NUEVO]` RN-30. Formato de DNI

El DNI se almacenará como texto, admitirá entre 7 y 8 dígitos numéricos y será único.

### `[NUEVO]` RN-31. Tokens de verificación y recuperación

Los tokens de verificación de correo y de recuperación de contraseña serán de un solo
uso, se almacenarán hasheados en la base de datos y tendrán expiración (24 horas para
verificación, 1 hora para recuperación).

### `[NUEVO]` RN-32. Idempotencia de notificaciones

El sistema no deberá enviar dos veces la misma notificación para el mismo evento:

- `CONFIRMACION_TURNO` y `RECORDATORIO_24H`: únicos por turno.
- `CANCELACION_TURNO`: única por (turno, subtipo).
- `VERIFICACION_EMAIL`: se puede reenviar, pero cada envío invalida el token anterior.
- `RECUPERACION_PASSWORD`: se puede solicitar varias veces, cada solicitud invalida la
  anterior.

### `[NUEVO]` RN-33. Solapamiento del mismo paciente

Un paciente no podrá tener dos turnos activos (RESERVADO o EN_ESPERA) cuyos horarios se
superpongan, con independencia del médico.

### `[NUEVO]` RN-34. Cancelación desde recepción

Recepción podrá cancelar cualquier turno en estado RESERVADO o EN_ESPERA, en cualquier
momento, con motivo obligatorio, usuario responsable y fecha/hora.

### `[NUEVO]` RN-35. Transiciones de estado permitidas

Los cambios de estado de los turnos solo podrán realizarse según la tabla de
transiciones de la sección 10.

### `[NUEVO]` RN-36. Derivación del estado Usuario rojo

El estado «Usuario rojo» no se almacena como flag. Se deriva de la existencia de una
restricción vigente (`RESTRICCION_USUARIO.activa = TRUE` y `fecha_fin > ahora`).

### `[NUEVO]` RN-37. Límites de intentos y frecuencia

Se aplicarán los siguientes límites:

- Login por DNI: 5 intentos fallidos en 15 minutos → bloqueo 15 minutos.
- Login por IP: 20 intentos fallidos en 15 minutos → bloqueo 15 minutos.
- Recuperación de contraseña: 3 solicitudes por correo en 1 hora.
- Reenvío de verificación: 3 solicitudes por correo en 1 hora.
- Reservas: 10 por paciente en 1 hora.

Superados los límites, se responderá con código 429 sin revelar información sensible.

### `[NUEVO]` RN-38. Bloqueos de agenda y turnos afectados

Un bloqueo de agenda o un cambio de horario que afecte turnos ya reservados solo podrá
confirmarse después de que esos turnos hayan sido cancelados explícitamente por el
administrador o por recepción, con motivo `BLOQUEO_AGENDA` o `CAMBIO_HORARIO`. Cada
cancelación disparará la notificación `TURNO_AFECTADO_POR_AGENDA`.

## 10. ESTADOS DE LOS TURNOS Y TRANSICIONES

Estados posibles:

- **RESERVADO:** el turno fue confirmado y está asignado a un paciente.
- **EN_ESPERA:** el paciente llegó al centro médico y recepción registró su llegada.
- **ATENDIDO:** la consulta fue finalizada y el turno quedó registrado administrativamente
  como atendido.
- **CANCELADO:** el turno fue cancelado por el procedimiento habitual, por una
  cancelación rápida autorizada, por cancelación desde recepción o por bloqueo de
  agenda.
- **AUSENTE:** recepción confirmó que el paciente no asistió al turno.

**`[NUEVO]`** Tabla de transiciones permitidas:

| Desde | Hacia | Actor |
|---|---|---|
| RESERVADO | EN_ESPERA | Recepción (registro de llegada) |
| RESERVADO | CANCELADO | Paciente (habitual o rápida aprobada), Recepción |
| RESERVADO | AUSENTE | Recepción (fin de jornada) |
| EN_ESPERA | ATENDIDO | Médico |
| EN_ESPERA | CANCELADO | Recepción |
| ATENDIDO / CANCELADO / AUSENTE | — | Estados terminales |

Cualquier otro cambio deberá rechazarse con error de transición inválida.

## 11. PROCEDIMIENTOS PRINCIPALES

### 11.1. Registro de pacientes

**Registro desde la web:**

1. El paciente ingresa a la página web.
2. Selecciona la opción de registrarse.
3. Completa sus datos personales.
4. Ingresa su DNI, una contraseña y su correo electrónico.
5. El sistema verifica que el DNI y el correo no estén registrados.
6. El sistema crea la cuenta en estado **no verificado**.
7. El sistema envía un correo con un enlace de verificación.
8. El paciente hace clic en el enlace y su correo queda verificado.
9. A partir de ese momento, podrá reservar turnos.

**Registro desde recepción:**

1. El paciente solicita ayuda para registrarse.
2. La recepcionista solicita sus datos personales, DNI y correo electrónico.
3. El sistema crea la cuenta con el correo marcado como **verificado** y el DNI como
   contraseña inicial.
4. El paciente deberá cambiar la contraseña en el primer ingreso.

### 11.2. Reserva de turnos

1. El paciente inicia sesión.
2. Selecciona una especialidad.
3. Selecciona un profesional.
4. El sistema muestra los horarios disponibles.
5. El paciente selecciona un horario.
6. El sistema vuelve a verificar que el horario continúe disponible, que el paciente no
   tenga turnos solapados y que no esté restringido como Usuario rojo.
7. El paciente confirma la reserva.
8. El sistema registra el turno como RESERVADO y encola la notificación
   `CONFIRMACION_TURNO`.

Si el horario ya fue reservado, el sistema impedirá confirmar la operación y solicitará
seleccionar otro.

### 11.3. Cancelación habitual

1. El paciente inicia sesión.
2. Consulta sus próximos turnos.
3. Selecciona el turno que desea cancelar.
4. El sistema verifica que falten al menos 24 horas.
5. El paciente confirma la cancelación.
6. El sistema cambia el estado a CANCELADO y encola `CANCELACION_TURNO`.
7. El horario queda disponible para otra reserva.

### 11.4. Solicitud de cancelación rápida

1. El paciente inicia sesión.
2. Selecciona el turno que necesita cancelar.
3. El sistema detecta que faltan menos de 24 horas.
4. La opción de cancelación habitual aparece deshabilitada.
5. El sistema habilita la opción de solicitud de cancelación rápida.
6. El paciente explica el motivo.
7. La solicitud queda pendiente.
8. Recepción revisa la solicitud.
9. Si la aprueba, el turno se cancela y se libera el horario, encolando
   `CANCELACION_TURNO` (subtipo aprobada).
10. Si la rechaza, el turno conserva su estado RESERVADO y se encola
    `CANCELACION_TURNO` (subtipo rechazada).

### 11.5. Cancelación desde recepción (habitual o rápida)

1. La recepcionista busca al paciente.
2. Selecciona el turno correspondiente.
3. Selecciona el tipo de cancelación (habitual o rápida) o el motivo
   (`BLOQUEO_AGENDA`, `CAMBIO_HORARIO`, `DESHABILITACION_MEDICO`, etc.).
4. Ingresa el motivo detallado cuando corresponda.
5. Confirma la operación.
6. El sistema registra al usuario responsable y la fecha y hora.
7. El turno pasa a CANCELADO y el horario queda disponible.
8. Se encola la notificación correspondiente al paciente.

### 11.6. Registro de llegada y orden de atención

1. El paciente llega al centro médico.
2. Recepción busca al paciente mediante su DNI.
3. Consulta los turnos del día.
4. Selecciona el turno correspondiente.
5. Registra la llegada.
6. El sistema guarda la hora exacta y cambia el estado a EN_ESPERA.
7. El sistema calcula el orden de atención según la sección 5.1.

### 11.7. Registro de ausencias

1. Al finalizar la jornada, recepción consulta los turnos del día.
2. El sistema muestra los turnos que continúan en estado RESERVADO y no tienen llegada
   registrada.
3. La recepcionista revisa cada caso.
4. Confirma las ausencias correspondientes.
5. El sistema cambia esos turnos a AUSENTE.

### 11.8. Clasificación de Usuario rojo

1. Recepción consulta el historial de turnos de un paciente.
2. Detecta reiteradas inasistencias o cancelaciones.
3. La recepcionista evalúa la situación.
4. Si corresponde, lo marca como Usuario rojo.
5. El sistema registra la fecha de inicio y la fecha de finalización de la restricción.
6. Se encola la notificación `RESTRICCION_USUARIO_ROJO`.
7. Durante un mes, el paciente no podrá reservar desde la web.
8. El paciente deberá solicitar sus turnos presencialmente.
9. Cumplido el mes, el sistema levanta la restricción (evaluación por fecha).

### 11.9. Registro de anotaciones médicas

1. El médico inicia sesión.
2. Consulta su agenda.
3. Selecciona al paciente correspondiente.
4. Registra una anotación breve sobre los avances o mejoras observados.
5. El sistema guarda la anotación vinculada al paciente y al turno correspondiente.
6. El médico podrá consultar esa información posteriormente para organizar su
   seguimiento y trasladarla a la historia clínica externa.

### `[NUEVO]` 11.10. Verificación de correo electrónico

1. El paciente se registra desde la web.
2. El sistema genera un token, lo guarda hasheado y envía el correo.
3. El paciente hace clic en el enlace del correo.
4. El sistema valida el token (existencia, no expirado, no usado).
5. El correo se marca como verificado y el token se invalida.

### `[NUEVO]` 11.11. Recuperación de contraseña

1. El usuario ingresa su correo y DNI en el formulario.
2. El sistema responde con un mensaje genérico.
3. Si el par coincide, genera un token, lo guarda hasheado y envía el correo.
4. El usuario hace clic en el enlace.
5. Define una nueva contraseña (validada por política).
6. El token se invalida y se registra la acción en auditoría.

### `[NUEVO]` 11.12. Cancelación masiva por bloqueo de agenda

1. El administrador intenta registrar o modificar un bloqueo.
2. El sistema detecta turnos afectados y rechaza la operación con la lista.
3. El administrador (o recepción) cancela cada turno con motivo `BLOQUEO_AGENDA` o
   `CAMBIO_HORARIO`.
4. Cada cancelación encola `TURNO_AFECTADO_POR_AGENDA`.
5. Una vez cancelados todos los turnos afectados, el bloqueo se confirma.

## 12. CASOS DE USO PRINCIPALES

(Los casos CU-01 a CU-10 conservan la redacción original, con los cambios indicados en
RF-01, RF-02, RF-05, RF-08, RF-09, RF-10, RF-16, RF-17 y RF-18).

### `[NUEVO]` CU-11. Verificar correo electrónico

**Actor principal:** Paciente.

**Precondición:** el paciente se registró desde la web y no verificó aún su correo.

**Flujo principal:**

1. El paciente recibe el correo con el enlace de verificación.
2. Hace clic en el enlace.
3. El sistema valida el token.
4. Marca el correo como verificado.
5. Informa el éxito y permite reservar turnos.

**Flujos alternativos:**

- Token inexistente, expirado o ya usado: se informa el error y se ofrece reenvío.
- Reenvío: se aplica rate limit (RN-37).

### `[NUEVO]` CU-12. Recuperar contraseña

**Actor principal:** Paciente / Recepcionista / Médico / Administrador.

**Precondición:** el usuario tiene cuenta registrada.

**Flujo principal:**

1. El usuario ingresa correo y DNI en el formulario.
2. El sistema responde genéricamente.
3. Si el par coincide, envía correo con enlace de restablecimiento.
4. El usuario hace clic en el enlace.
5. Ingresa la nueva contraseña (cumpliendo RN-28).
6. El sistema actualiza la contraseña e invalida el token.

**Flujos alternativos:**

- Par inexistente: respuesta genérica, sin envío.
- Token expirado: se informa y se puede solicitar uno nuevo.
- Se supera el límite de intentos: 429.

### `[NUEVO]` CU-13. Cambiar contraseña en primer ingreso

**Actor principal:** Paciente (cuenta creada por recepción).

**Precondición:** el paciente inicia sesión por primera vez.

**Flujo principal:**

1. El paciente ingresa con DNI y la contraseña inicial (DNI).
2. El sistema detecta que debe cambiar contraseña y redirige al formulario.
3. El paciente ingresa la nueva contraseña (cumpliendo RN-28).
4. El sistema actualiza y marca el primer ingreso como completado.

### `[NUEVO]` CU-14. Cancelar turno desde recepción

**Actor principal:** Recepcionista.

**Precondición:** la recepcionista inició sesión y el turno está en RESERVADO o
EN_ESPERA.

**Flujo principal:**

1. La recepcionista busca al paciente y el turno.
2. Selecciona la opción de cancelar desde recepción.
3. Selecciona el motivo e ingresa el detalle cuando corresponde.
4. Confirma.
5. El sistema registra usuario, fecha/hora y motivo, cambia el estado a CANCELADO y
   encola la notificación al paciente.

### `[NUEVO]` CU-15. Gestionar bloqueos de agenda

**Actor principal:** Administrador.

**Precondición:** el administrador inició sesión.

**Flujo principal:**

1. El administrador selecciona un médico y crea o modifica un bloqueo.
2. El sistema detecta turnos afectados.
3. Si hay turnos afectados, la operación se rechaza con la lista.
4. El administrador (o recepción) cancela cada turno afectado.
5. Cada cancelación encola `TURNO_AFECTADO_POR_AGENDA`.
6. Una vez resueltos todos, el bloqueo se confirma.

## 13. DISEÑO DE LA BASE DE DATOS: MODELO ENTIDAD-RELACIÓN (DER)

### 13.1. USUARIO

Sin cambios respecto del original, **agregando**:

- `email_verificado` (BOOLEAN, default FALSE).
- `debe_cambiar_password` (BOOLEAN, default FALSE). `[NUEVO]` para cuentas creadas por
  recepción.

### 13.2. PACIENTE **`[CAMBIO]`**

- `id_paciente`: PK.
- `id_usuario`: FK hacia USUARIO.
- `nombre`.
- `apellido`.
- `fecha_nacimiento`.
- `email`: **obligatorio, `VARCHAR`, `UNIQUE` a nivel global, `NOT NULL`**.
- `telefono`: **opcional, `VARCHAR`, `NULL`**.

El DNI se almacena en `USUARIO` como `VARCHAR(8)`, `UNIQUE` y `NOT NULL`, con validación
en aplicación (7-8 dígitos).

### 13.3. MEDICO

Sin cambios. La matrícula es única cuando corresponde.

### 13.4. ESPECIALIDAD

Sin cambios.

### 13.5. TURNO **`[CAMBIO]`**

- `id_turno`: PK.
- `id_paciente`: FK hacia PACIENTE.
- `id_medico`: FK hacia MEDICO.
- `fecha_hora`: `TIMESTAMPTZ`.
- `duracion_minutos`: INTEGER.
- `estado`: `RESERVADO | EN_ESPERA | ATENDIDO | CANCELADO | AUSENTE`.
- `fecha_hora_llegada`: `TIMESTAMPTZ`, NULL.
- `fecha_hora_cancelacion`: `TIMESTAMPTZ`, NULL.
- `id_usuario_creador`: FK hacia USUARIO.
- **`[NUEVO]`** `motivo_cancelacion`: `VARCHAR NULL` (`HABITUAL | RAPIDA |
  BLOQUEO_AGENDA | CAMBIO_HORARIO | DESHABILITACION_MEDICO | DESHABILITACION_PACIENTE |
  RETIRO_VOLUNTARIO | OTRO`).
- **`[NUEVO]`** `detalle_cancelacion`: `TEXT NULL`.
- **`[NUEVO]`** `id_usuario_cancelacion`: FK hacia USUARIO, NULL.

Restricciones:

- `EXCLUDE USING gist (id_medico WITH =, tstzrange(fecha_hora, fecha_hora +
  (duracion_minutos || ' minutes')::interval) WITH &&)` parcial sobre estados activos
  (`RESERVADO`, `EN_ESPERA`, `ATENDIDO`). Requiere `btree_gist`.
- **`[NUEVO]`** Análoga por `id_paciente` parcial sobre estados activos.

### 13.6. NOTA_SEGUIMIENTO

Sin cambios.

### 13.7. HORARIO_MEDICO

Sin cambios.

### 13.8. BLOQUEO_AGENDA

Sin cambios.

### 13.9. SOLICITUD_CANCELACION

Sin cambios.

### 13.10. RESTRICCION_USUARIO

Sin cambios. Es la **única** fuente del estado «Usuario rojo».

### 13.11. AUDITORIA

Sin cambios.

### `[NUEVO]` 13.12. VERIFICACION_EMAIL

- `id_verificacion`: PK.
- `id_usuario`: FK hacia USUARIO.
- `token_hash`: `VARCHAR`, único.
- `fecha_creacion`: `TIMESTAMPTZ`.
- `fecha_expiracion`: `TIMESTAMPTZ`.
- `usado`: BOOLEAN, default FALSE.

### `[NUEVO]` 13.13. RECUPERACION_PASSWORD

- `id_recuperacion`: PK.
- `id_usuario`: FK hacia USUARIO.
- `token_hash`: `VARCHAR`, único.
- `fecha_creacion`: `TIMESTAMPTZ`.
- `fecha_expiracion`: `TIMESTAMPTZ`.
- `usado`: BOOLEAN, default FALSE.

### `[NUEVO]` 13.14. NOTIFICACION

- `id_notificacion`: PK.
- `id_usuario_destinatario`: FK hacia USUARIO, NULL (algunas notificaciones podrían ser
  sin destinatario registrado, aunque en el alcance actual siempre hay destinatario).
- `tipo`: `VERIFICACION_EMAIL | RECUPERACION_PASSWORD | CONFIRMACION_TURNO |
  CANCELACION_TURNO | TURNO_AFECTADO_POR_AGENDA | RESTRICCION_USUARIO_ROJO |
  RECORDATORIO_24H`.
- `id_turno`: FK hacia TURNO, NULL.
- `id_solicitud`: FK hacia SOLICITUD_CANCELACION, NULL.
- `subtipo`: `VARCHAR NULL` (para `CANCELACION_TURNO`: `HABITUAL | RAPIDA_APROBADA |
  RAPIDA_RECHAZADA | BLOQUEO`).
- `estado`: `PENDIENTE | ENVIADA | FALLIDA`.
- `intentos`: INTEGER, default 0.
- `ultimo_error`: TEXT NULL.
- `fecha_creacion`: `TIMESTAMPTZ`.
- `fecha_programada_envio`: `TIMESTAMPTZ`.
- `fecha_envio`: `TIMESTAMPTZ`, NULL.

Restricciones (idempotencia, RN-32):

- `UNIQUE (id_turno, tipo)` parcial para `CONFIRMACION_TURNO` y `RECORDATORIO_24H`.
- `UNIQUE (id_turno, tipo, subtipo)` parcial para `CANCELACION_TURNO`.

## 14. RELACIONES Y CARDINALIDADES DEL DER

(Las relaciones originales se mantienen. Se agregan:)

- **USUARIO — VERIFICACION_EMAIL:** un usuario puede tener varias verificaciones
  emitidas a lo largo del tiempo; cada verificación pertenece a un usuario. Solo una
  puede estar vigente (no usada, no expirada) a la vez.
- **USUARIO — RECUPERACION_PASSWORD:** análoga a la anterior.
- **USUARIO — NOTIFICACION:** un usuario puede recibir muchas notificaciones; cada
  notificación tiene un destinatario.
- **TURNO — NOTIFICACION:** un turno puede generar varias notificaciones.
- **SOLICITUD_CANCELACION — NOTIFICACION:** una solicitud puede generar notificaciones
  (resolución aprobada/rechazada).

## 15. DECISIONES DEFINIDAS DEL PROYECTO

1. **Registro de pacientes:** autoregistro web con DNI, contraseña y **correo
   electrónico obligatorio**. Verificación de correo antes de poder reservar.
2. **Registro desde recepción:** recepción crea la cuenta con DNI, correo
   (considerado verificado) y contraseña inicial = DNI. Cambio obligatorio en el primer
   ingreso.
3. **Identificación:** DNI + contraseña. DNI como texto, 7-8 dígitos, único.
4. **Creación de turnos:** pacientes desde la web (con correo verificado y sin
   restricción) y recepción en nombre de los pacientes.
5. **Cancelación habitual:** a ≥ 24 hs del turno.
6. **Cancelación rápida del paciente:** a < 24 hs, con motivo obligatorio, resuelta por
   recepción.
7. **Cancelación desde recepción:** habitual o rápida, en cualquier momento, con motivo
   obligatorio, usuario y fecha/hora.
8. **Anotaciones médicas:** no son historia clínica.
9. **Prevención de duplicados:** exclusion constraint por médico en la base de datos.
10. **Prevención de solapamiento por paciente:** exclusion constraint por paciente.
11. **Prioridad de atención:** llegada dentro de los 10 minutos de tolerancia, ordenada
    por horario programado y luego por hora de llegada; después, quienes llegaron tarde
    por hora de llegada.
12. **Ausencias:** confirmadas individualmente por recepción al final de la jornada.
13. **Usuario rojo:** derivado de `RESTRICCION_USUARIO` vigente. Bloquea **reservar**
    desde la web, no cancelar ni consultar.
14. **Restricción temporal:** 1 mes.
15. **Historia clínica:** fuera del alcance.
16. **Notificaciones:** lista cerrada, asíncronas, idempotentes, con reintentos.
17. **Verificación y recuperación:** tokens de un solo uso, hasheados, con expiración.
18. **Seguridad:** argon2id, JWT en cookie `httpOnly` + CSRF, rate limiting.
19. **Zona horaria:** UTC en base, `America/Argentina/Buenos_Aires` en reglas.
20. **Turnos afectados por agenda:** se cancelan con motivo y notificación, y luego se
    confirma el cambio de agenda.

## 16. METODOLOGÍA DE DESARROLLO

Se utilizará la metodología tradicional o en cascada, organizada en etapas secuenciales.
Cada etapa tendrá entregables que servirán como base para la siguiente.

### 1. Análisis de requisitos

Se identificarán las necesidades del centro médico, los actores, el alcance, los
requerimientos funcionales, los requerimientos no funcionales y las reglas de negocio.

**Entregable:** documento de requisitos aprobado.

### 2. Diseño

Se elaborarán los casos de uso, el modelo entidad-relación, el diseño de la base de
datos, las interfaces y la estructura general del sistema.

**Entregable:** diseño funcional y técnico del sistema.

### 3. Implementación

Se desarrollarán las interfaces, la lógica de negocio, el sistema de autenticación y la
conexión con la base de datos.

**Entregable:** primera versión funcional del sistema.

### 4. Pruebas

Se comprobará el correcto funcionamiento de las funcionalidades, los permisos, la
integridad de los datos y los casos excepcionales.

**Entregable:** resultados de pruebas y corrección de errores detectados.

### 5. Puesta en funcionamiento y mantenimiento

Se preparará el entorno de funcionamiento, se realizarán las configuraciones necesarias
y se establecerán procedimientos de respaldo y mantenimiento.

**Entregable:** sistema implementado y documentación básica de uso.

Aunque la metodología sea secuencial, los errores encontrados durante las pruebas
deberán corregirse y verificarse nuevamente antes de aprobar la entrega.

## 17. PLAN DE PRUEBAS

**P-01. Registro de pacientes:** verificar que un paciente pueda registrarse ingresando
todos los datos obligatorios, incluido el correo electrónico.

**P-02. DNI duplicado:** comprobar que el sistema impida registrar dos pacientes con el
mismo DNI.

**P-03. `[CAMBIO]` Correo electrónico obligatorio y único:** comprobar que el sistema no
permita completar el registro sin correo electrónico y que rechace un correo ya
registrado.

**P-04. Registro desde recepción:** verificar que recepción pueda crear una cuenta, que
la contraseña inicial sea el DNI y que el correo quede marcado como verificado.

**P-05. Inicio de sesión:** comprobar que los usuarios puedan ingresar con sus
credenciales correctas.

**P-06. Contraseña incorrecta:** comprobar que el sistema rechace una contraseña
incorrecta.

**P-07. Cuenta deshabilitada:** comprobar que una cuenta deshabilitada no pueda iniciar
sesión.

**P-08. Reserva disponible:** verificar que un paciente con correo verificado pueda
reservar un horario disponible.

**P-09. Reserva duplicada:** comprobar que el sistema impida reservar un horario ya
ocupado por otro paciente para el mismo médico.

**P-10. Reservas simultáneas:** comprobar que dos solicitudes concurrentes no puedan
confirmar el mismo horario (test con `asyncio.gather` y sesiones separadas).

**P-11. Turno desde recepción:** verificar que la recepcionista pueda crear un turno en
nombre de un paciente.

**P-12. Cancelación habitual:** comprobar que se permita cancelar un turno con al menos
24 horas de anticipación.

**P-13. Cancelación rápida:** verificar que, cuando falten menos de 24 horas, se
deshabilite la cancelación habitual y se habilite la solicitud rápida.

**P-14. Solicitud con motivo:** comprobar que el paciente deba explicar el motivo de la
cancelación rápida.

**P-15. Resolución de solicitud:** comprobar que recepción pueda aprobar o rechazar una
solicitud y que el turno se actualice correctamente y notifique.

**P-16. Cancelación desde recepción:** verificar que recepción pueda cancelar con motivo
y que se registren usuario y fecha/hora.

**P-17. Registro de llegada:** comprobar que recepción pueda registrar la llegada de un
paciente con un turno válido.

**P-18. Llegada duplicada:** verificar que el sistema impida registrar dos veces la
llegada del mismo turno.

**P-19. Orden de atención:** comprobar que se respete el orden definido en RF-12.

**P-20. Tolerancia:** comprobar que un paciente que supere los 10 minutos posteriores
al horario programado pierda la prioridad de su turno.

**P-21. Ausencia:** verificar que recepción pueda confirmar la ausencia y cambiar el
estado a AUSENTE.

**P-22. Anotaciones médicas:** comprobar que el médico autorizado pueda registrar
anotaciones de seguimiento.

**P-23. Acceso a anotaciones:** comprobar que un usuario no autorizado no pueda
registrar ni modificar anotaciones médicas.

**P-24. Usuario rojo:** verificar que recepción pueda clasificar a un paciente como
Usuario rojo y que se envíe la notificación.

**P-25. Restricción web:** comprobar que el Usuario rojo no pueda reservar turnos por
internet durante un mes, pero sí cancelar los existentes.

**P-26. Fin de restricción:** comprobar que el sistema habilite nuevamente las reservas
web una vez cumplido el mes (evaluación por fecha).

**P-27. Gestión de horarios:** verificar que el sistema rechace horarios médicos
superpuestos o inválidos.

**P-28. Cambios de agenda:** comprobar que el sistema detecte los turnos afectados y
exija su cancelación con notificación.

**P-29. Permisos:** comprobar que cada rol tenga acceso únicamente a las funcionalidades
que le corresponden (validado en el servidor).

**P-30. Trazabilidad:** verificar que las operaciones importantes registren el usuario
responsable, la fecha y la hora.

### `[NUEVO]` Pruebas adicionales

**P-31. Correo duplicado:** intentar registrar un paciente con un correo ya existente →
409, sin crear cuenta.

**P-32. Reserva sin correo verificado:** paciente registrado por web pero sin verificar
intenta reservar → 403.

**P-33. Primer login de cuenta de recepción:** verificar que se exige cambiar la
contraseña antes de cualquier otra operación.

**P-34. Recuperación con datos inexistentes:** respuesta genérica 200, sin envío de
correo, sin filtrar información.

**P-35. Token de recuperación expirado:** 400, sin cambio de contraseña.

**P-36. Límite de intentos fallidos de login:** 6º intento → 429 y bloqueo temporal.

**P-37. Reservas concurrentes mismo slot:** una gana, una recibe 409, ninguna queda
parcial.

**P-38. Solapamiento del mismo paciente:** reservar con dos médicos distintos en
horarios solapados → 409 por exclusion constraint del paciente.

**P-39. Idempotencia del recordatorio:** ejecutar dos veces el scheduler para el mismo
turno → una sola notificación `RECORDATORIO_24H`.

**P-40. Turno afectado por bloqueo:** intentar crear un bloqueo que solape turnos
existentes → 409 con lista; tras cancelarlos con motivo `BLOQUEO_AGENDA` → se envían las
notificaciones `TURNO_AFECTADO_POR_AGENDA` y se confirma el bloqueo.

**P-41. Verificación de correo:** registro web → correo de verificación generado y
encolado; clic en enlace → correo verificado; reenvío con token anterior → falla.

**P-42. Idempotencia de confirmación:** ante reintento de la operación de reserva (por
timeout del cliente), no se duplica la notificación `CONFIRMACION_TURNO`.

**P-43. Fallo de SMTP:** el envío falla, la reserva se completa igual y la notificación
queda en estado `FALLIDA` con `intentos` incrementado.

**P-44. Zona horaria:** un turno reservado a las 23:30 hora local se evalúa con la
ventana de 24 hs correcta respecto de UTC.

**P-45. Restore de backup:** restaurar un backup en una base limpia y verificar que los
datos son consistentes.

## 18. RESULTADO ESPERADO

Se espera obtener un sistema web que permita centralizar y organizar la gestión de turnos
de un centro médico, facilitando el trabajo administrativo y mejorando la experiencia de
los pacientes.

El sistema permitirá reducir errores en las reservas, evitar superposiciones de horarios,
organizar la llegada de los pacientes, controlar las cancelaciones e inasistencias y
facilitar el seguimiento de los pacientes mediante anotaciones realizadas por los
médicos.

**`[NUEVO]`** Además, contará con verificación de correo, recuperación de contraseña,
notificaciones automáticas ante eventos del ciclo de vida del turno, control de
solapamientos por paciente y trazabilidad completa de las operaciones críticas.

De esta manera, se busca mejorar la organización general del centro médico, mantener la
información ordenada y brindar una herramienta sencilla, segura y eficiente para la
gestión de consultas programadas.