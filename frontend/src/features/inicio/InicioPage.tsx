import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Icon } from "@/components/ui/Icon";
import { Status } from "@/components/ui/Status";
import { useAuth } from "@/features/auth/useAuth";
import { turnosApi } from "@/features/turnos/api";
import type { TurnoResponse } from "@/features/turnos/types";
import { formatPartesFecha } from "@/lib/dates";

export function InicioPage() {
  const { usuario } = useAuth();
  const [proximoTurno, setProximoTurno] = useState<TurnoResponse | null>(null);
  const [cargandoTurnos, setCargandoTurnos] = useState(false);

  const esPaciente = usuario?.rol === "PACIENTE";
  const esRecepcionista = usuario?.rol === "RECEPCIONISTA";
  const esMedico = usuario?.rol === "MEDICO";
  const esAdmin = usuario?.rol === "ADMINISTRADOR";

  useEffect(() => {
    if (!esPaciente) return;

    let cancelado = false;
    async function cargarProximo() {
      setCargandoTurnos(true);
      try {
        const res = await turnosApi.listarMisTurnos("RESERVADO");
        if (!cancelado && res.items.length > 0) {
          const ordenados = [...res.items].sort(
            (a, b) => new Date(a.fecha_hora).getTime() - new Date(b.fecha_hora).getTime(),
          );
          setProximoTurno(ordenados[0]);
        }
      } catch {
        // En caso de fallo silencioso, no bloqueamos el dashboard
      } finally {
        if (!cancelado) setCargandoTurnos(false);
      }
    }

    void cargarProximo();
    return () => {
      cancelado = true;
    };
  }, [esPaciente]);

  if (!usuario) return null;

  const hoyFormato = new Intl.DateTimeFormat("es-AR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: "America/Argentina/Buenos_Aires",
  }).format(new Date());

  const partesTurno = proximoTurno ? formatPartesFecha(proximoTurno.fecha_hora) : null;
  const nombreMed = proximoTurno?.medico_nombre || "";
  const apellidoMed = proximoTurno?.medico_apellido || "";
  const inicialesMedico = proximoTurno && (nombreMed || apellidoMed)
    ? `${nombreMed.charAt(0)}${apellidoMed.charAt(0)}`.toUpperCase()
    : "DR";

  return (
    <>
      <div className="page-title">
        <div>
          <p>{hoyFormato.toUpperCase()}</p>
          <h1>Hola, {usuario.nombre}</h1>
          <span>
            {esPaciente
              ? "Este es el resumen de tu atención médica."
              : esAdmin
              ? "Panel de administración y supervisión del sistema ITU Medical."
              : esMedico
              ? "Panel de consultorio médico y atención de pacientes."
              : "Panel de recepción, llegadas y sala de espera."}
          </span>
        </div>
        <Status tone="green">Sistema operativo</Status>
      </div>

      {/* VISTA PACIENTE */}
      {esPaciente && (
        <>
          {/* Tarjeta de Próxima Visita */}
          {proximoTurno && partesTurno ? (
            <section className="next-card">
              <div className="next-copy">
                <span className="eyebrow">TU PRÓXIMA VISITA</span>
                <h2>{proximoTurno.especialidad_nombre}</h2>
                <p className="doctor">
                  <span>{inicialesMedico}</span>
                  <b>Dr(a). {proximoTurno.medico_nombre} {proximoTurno.medico_apellido}</b>
                </p>
                <div className="next-time">
                  <div>
                    <Icon name="calendar" />
                    <span>
                      <small>{partesTurno.diaSemana}</small>
                      {partesTurno.diaMesTexto}
                    </span>
                  </div>
                  <div>
                    <Icon name="clock" />
                    <span>
                      <small>Horario</small>
                      {partesTurno.horaTexto} hs
                    </span>
                  </div>
                </div>
                <Link to="/turnos" className="text-button">
                  Ver detalle del turno <Icon name="arrow" size={17} />
                </Link>
              </div>
              <div className="next-art">
                <div className="calendar-art">
                  <span>{partesTurno.mesAbrev}</span>
                  <strong>{partesTurno.diaNumero}</strong>
                  <small>{partesTurno.diaSemana.toUpperCase()}</small>
                </div>
              </div>
            </section>
          ) : (
            <section className="next-card">
              <div className="next-copy">
                <span className="eyebrow">AGENDA MÉDICA</span>
                <h2>{cargandoTurnos ? "Cargando tu próxima visita..." : "No tenés turnos próximos"}</h2>
                <p className="doctor">
                  <span>ITU</span>
                  <b>Atención médica programada</b>
                </p>
                <div className="next-time">
                  <div>
                    <Icon name="calendar" />
                    <span>
                      <small>Disponibilidad</small>
                      Turnos inmediatos
                    </span>
                  </div>
                </div>
                <Link to="/turnos/reservar" className="text-button">
                  Reservar un turno ahora <Icon name="arrow" size={17} />
                </Link>
              </div>
            </section>
          )}

          {/* Accesos Rápidos */}
          <div className="section-heading">
            <div>
              <h2>Accesos rápidos</h2>
              <p>Todo lo que necesitás, en un solo lugar.</p>
            </div>
          </div>

          <section className="quick-grid">
            <Link to="/turnos/reservar" className="quick-card mint">
              <span>
                <Icon name="plus" />
              </span>
              <div>
                <h3>Reservar turno</h3>
                <p>Elegí especialidad, profesional y horario disponible.</p>
              </div>
              <Icon name="arrow" />
            </Link>

            <Link to="/turnos?tab=proximos" className="quick-card blue">
              <span>
                <Icon name="calendar" />
              </span>
              <div>
                <h3>Mis turnos próximos</h3>
                <p>Revisá tus turnos programados y confirmados.</p>
              </div>
              <Icon name="arrow" />
            </Link>

            <Link to="/turnos?tab=historial" className="quick-card sand">
              <span>
                <Icon name="file" />
              </span>
              <div>
                <h3>Historial de visitas</h3>
                <p>Consultá tus turnos atendidos y anteriores.</p>
              </div>
              <Icon name="arrow" />
            </Link>
          </section>

          {/* Banner de Estado de Cuenta */}
          {usuario.email_verificado ? (
            <section className="info-banner">
              <span>
                <Icon name="check" />
              </span>
              <div>
                <b>Tu cuenta está verificada</b>
                <p>Podés reservar y gestionar turnos sin restricciones.</p>
              </div>
            </section>
          ) : (
            <section className="info-banner" style={{ borderColor: "#f3c3ba", background: "#fdf3f1" }}>
              <span style={{ color: "#d9534f" }}>
                <Icon name="bell" />
              </span>
              <div>
                <b>Tu correo electrónico todavía no fue verificado</b>
                <p>La reserva de turnos requiere que confirmes tu dirección de correo.</p>
              </div>
              <Link to="/verificar-email" style={{ color: "#c9302c" }}>
                Verificar correo
              </Link>
            </section>
          )}
        </>
      )}

      {/* VISTA RECEPCIONISTA */}
      {esRecepcionista && (
        <>
          <div className="section-heading">
            <div>
              <h2>Gestión de Recepción</h2>
              <p>Control de sala de espera, ingreso de pacientes y turnos de la jornada.</p>
            </div>
          </div>

          <section className="quick-grid">
            <Link to="/recepcion?tab=espera" className="quick-card mint">
              <span>
                <Icon name="people" />
              </span>
              <div>
                <h3>Sala de Espera & Llegadas</h3>
                <p>Búsqueda en vivo por DNI o nombre y registro de arribo con 1 clic.</p>
              </div>
              <Icon name="arrow" />
            </Link>

            <Link to="/recepcion?tab=pacientes" className="quick-card blue">
              <span>
                <Icon name="search" />
              </span>
              <div>
                <h3>Pacientes & Fichas</h3>
                <p>Alta rápida de pacientes, consulta y control de sanciones.</p>
              </div>
              <Icon name="arrow" />
            </Link>

            <Link to="/recepcion?tab=solicitudes" className="quick-card sand">
              <span>
                <Icon name="calendar" />
              </span>
              <div>
                <h3>Solicitudes de Cancelación</h3>
                <p>Aprobación o rechazo de pedidos de cancelación con menos de 24 hs.</p>
              </div>
              <Icon name="arrow" />
            </Link>

            <Link to="/recepcion?tab=cierre" className="quick-card sand">
              <span>
                <Icon name="clock" />
              </span>
              <div>
                <h3>Cierre de Jornada</h3>
                <p>Marcado automático de ausencias al final del día laboral.</p>
              </div>
              <Icon name="arrow" />
            </Link>
          </section>
        </>
      )}

      {/* VISTA ADMINISTRADOR */}
      {esAdmin && (
        <>
          <div className="section-heading">
            <div>
              <h2>Panel de Administración General</h2>
              <p>Supervisión integral de agendas, consultorios y operaciones de recepción.</p>
            </div>
          </div>

          <section className="quick-grid">
            <Link to="/admin" className="quick-card mint">
              <span>
                <Icon name="calendar" />
              </span>
              <div>
                <h3>Gestión de Agendas</h3>
                <p>Configurá días, horarios y duración de turnos de todos los médicos.</p>
              </div>
              <Icon name="arrow" />
            </Link>

            <Link to="/recepcion" className="quick-card blue">
              <span>
                <Icon name="people" />
              </span>
              <div>
                <h3>Recepción & Espera</h3>
                <p>Supervisá la sala de espera, llegadas y altas de pacientes.</p>
              </div>
              <Icon name="arrow" />
            </Link>

            <Link to="/medico" className="quick-card sand">
              <span>
                <Icon name="stethoscope" />
              </span>
              <div>
                <h3>Consultorio Médico</h3>
                <p>Accedé a los consultorios del día y seguimiento de atención.</p>
              </div>
              <Icon name="arrow" />
            </Link>
          </section>
        </>
      )}

      {/* VISTA MÉDICO */}
      {esMedico && (
        <>
          <div className="section-heading">
            <div>
              <h2>Consultorio Médico</h2>
              <p>Atención de pacientes del día y configuración de horarios de disponibilidad.</p>
            </div>
          </div>

          <section className="quick-grid">
            <Link to="/medico?tab=consultorio" className="quick-card mint">
              <span>
                <Icon name="stethoscope" />
              </span>
              <div>
                <h3>Consultorio del Día</h3>
                <p>Visualizá tu agenda de turnos, llamá pacientes y anotá evolución.</p>
              </div>
              <Icon name="arrow" />
            </Link>

            <Link to="/medico?tab=horarios" className="quick-card blue">
              <span>
                <Icon name="clock" />
              </span>
              <div>
                <h3>Mis Horarios de Atención</h3>
                <p>Configurá tus días y franjas de disponibilidad para nuevos turnos.</p>
              </div>
              <Icon name="arrow" />
            </Link>
          </section>
        </>
      )}
    </>
  );
}
