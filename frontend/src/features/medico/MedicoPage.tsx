import { useEffect, useState } from "react";

import { Alerta } from "@/components/ui/Alerta";
import { Icon } from "@/components/ui/Icon";
import { Skeleton } from "@/components/ui/Skeleton";
import { Status, type StatusTone } from "@/components/ui/Status";
import type { EstadoTurno, TurnoResponse } from "@/features/turnos/types";
import { formatPartesFecha } from "@/lib/dates";
import { mensajeDeError } from "@/lib/problem";
import { type NotaSeguimientoOut, medicoApi } from "./api";

const ESTADO_TONE: Record<EstadoTurno, StatusTone> = {
  RESERVADO: "blue",
  EN_ESPERA: "amber",
  ATENDIDO: "green",
  CANCELADO: "gray",
  AUSENTE: "gray",
};

export function MedicoPage() {
  const [turnos, setTurnos] = useState<TurnoResponse[]>([]);
  const [turnoSeleccionado, setTurnoSeleccionado] = useState<TurnoResponse | null>(null);
  const [notas, setNotas] = useState<NotaSeguimientoOut[]>([]);

  const [cargandoTurnos, setCargandoTurnos] = useState(true);
  const [cargandoNotas, setCargandoNotas] = useState(false);
  const [atendiendo, setAtendiendo] = useState(false);
  const [guardandoNota, setGuardandoNota] = useState(false);

  const [nuevaNota, setNuevaNota] = useState("");
  const [notaEnEdicion, setNotaEnEdicion] = useState<NotaSeguimientoOut | null>(null);
  const [contenidoEdicion, setContenidoEdicion] = useState("");

  const [error, setError] = useState<string | null>(null);
  const [mensajeExito, setMensajeExito] = useState<string | null>(null);

  // Cargar turnos del médico
  const cargarTurnos = async () => {
    setCargandoTurnos(true);
    setError(null);
    try {
      const res = await medicoApi.obtenerTurnos();
      setTurnos(res.items);
      if (res.items.length > 0 && !turnoSeleccionado) {
        setTurnoSeleccionado(res.items[0]);
      }
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setCargandoTurnos(false);
    }
  };

  useEffect(() => {
    void cargarTurnos();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Cargar notas al seleccionar paciente
  useEffect(() => {
    if (!turnoSeleccionado) {
      setNotas([]);
      return;
    }
    async function cargarNotas() {
      setCargandoNotas(true);
      setError(null);
      try {
        const items = await medicoApi.listarNotasPaciente(turnoSeleccionado!.id_paciente);
        setNotas(items);
      } catch (err) {
        setError(mensajeDeError(err));
      } finally {
        setCargandoNotas(false);
      }
    }
    void cargarNotas();
  }, [turnoSeleccionado]);

  // Atender turno
  const handleAtender = async () => {
    if (!turnoSeleccionado) return;
    setAtendiendo(true);
    setError(null);
    setMensajeExito(null);
    try {
      const actualizado = await medicoApi.atenderTurno(turnoSeleccionado.id_turno);
      setTurnoSeleccionado(actualizado);
      setMensajeExito("Atención registrada con éxito. El turno pasó a estado ATENDIDO.");
      void cargarTurnos();
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setAtendiendo(false);
    }
  };

  // Crear nueva nota
  const handleCrearNota = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!turnoSeleccionado || !nuevaNota.trim()) return;
    setGuardandoNota(true);
    setError(null);
    try {
      const creada = await medicoApi.crearNota({
        id_paciente: turnoSeleccionado.id_paciente,
        id_turno: turnoSeleccionado.id_turno,
        contenido: nuevaNota.trim(),
      });
      setNotas([creada, ...notas]);
      setNuevaNota("");
      setMensajeExito("Anotación médica guardada con éxito.");
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setGuardandoNota(false);
    }
  };

  // Guardar edición de nota
  const handleGuardarEdicion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!notaEnEdicion || !contenidoEdicion.trim()) return;
    setError(null);
    try {
      const mod = await medicoApi.modificarNota(notaEnEdicion.id_nota, {
        contenido: contenidoEdicion.trim(),
      });
      setNotas(notas.map((n) => (n.id_nota === mod.id_nota ? mod : n)));
      setNotaEnEdicion(null);
      setContenidoEdicion("");
      setMensajeExito("Anotación médica actualizada con éxito.");
    } catch (err) {
      setError(mensajeDeError(err));
    }
  };

  const enEspera = turnos.filter((t) => t.estado === "EN_ESPERA");
  const partesTurnoSel = turnoSeleccionado
    ? formatPartesFecha(turnoSeleccionado.fecha_hora)
    : null;
  const nomPac = turnoSeleccionado?.paciente_nombre || "";
  const apePac = turnoSeleccionado?.paciente_apellido || "";
  const inicialesPaciente = turnoSeleccionado && (nomPac || apePac)
    ? `${nomPac.charAt(0)}${apePac.charAt(0)}`.toUpperCase()
    : "P";

  return (
    <>
      <div className="page-title">
        <div>
          <p>ITU MEDICAL</p>
          <h1>Consultorio médico</h1>
          <span>Agenda del día y seguimiento confidencial de pacientes.</span>
        </div>
      </div>

      {error && <Alerta tipo="error">{error}</Alerta>}
      {mensajeExito && <Alerta tipo="exito">{mensajeExito}</Alerta>}

      <div className="consult-layout">
        {/* Panel Izquierdo: Agenda de Hoy */}
        <aside className="agenda-panel">
          <div className="agenda-head">
            <div>
              <h3>Agenda de hoy</h3>
              <p>Turnos del profesional</p>
            </div>
            <button
              type="button"
              className="icon-button"
              onClick={cargarTurnos}
              disabled={cargandoTurnos}
              aria-label="Actualizar agenda"
            >
              <Icon name="refresh" size={17} />
            </button>
          </div>

          <div className="agenda-summary">
            <b>{turnos.length} turnos</b>
            <span>{enEspera.length} en espera</span>
          </div>

          {cargandoTurnos ? (
            <div className="space-y-3 py-2">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : turnos.length === 0 ? (
            <p className="text-xs text-slate-500 py-4 text-center">
              No hay turnos asignados para hoy.
            </p>
          ) : (
            turnos.map((t) => {
              const hora = formatPartesFecha(t.fecha_hora).horaTexto;
              const esSeleccionado = turnoSeleccionado?.id_turno === t.id_turno;

              return (
                <button
                  key={t.id_turno}
                  type="button"
                  className={esSeleccionado ? "selected" : ""}
                  onClick={() => setTurnoSeleccionado(t)}
                >
                  <time>{hora}</time>
                  <span>
                    <b>{t.paciente_nombre} {t.paciente_apellido}</b>
                    <small>{t.especialidad_nombre}</small>
                  </span>
                  {t.estado === "EN_ESPERA" && <i />}
                </button>
              );
            })
          )}
        </aside>

        {/* Panel Derecho: Ficha Clínica y Notas */}
        <section className="clinical-panel">
          {turnoSeleccionado && partesTurnoSel ? (
            <>
              <div className="clinical-head">
                <div className="patient-avatar">{inicialesPaciente}</div>
                <div>
                  <span className="eyebrow">
                    {turnoSeleccionado.estado === "EN_ESPERA"
                      ? "PACIENTE EN SALA DE ESPERA"
                      : "TURNO PROGRAMADO"}
                  </span>
                  <h2>{turnoSeleccionado.paciente_nombre} {turnoSeleccionado.paciente_apellido}</h2>
                  <p>DNI {turnoSeleccionado.paciente_dni}</p>
                </div>
                <Status tone={ESTADO_TONE[turnoSeleccionado.estado]}>
                  {turnoSeleccionado.estado}
                </Status>
              </div>

              <div className="clinical-info">
                <div>
                  <small>TURNO</small>
                  <b>Hoy, {partesTurnoSel.horaTexto} hs</b>
                </div>
                <div>
                  <small>ESPECIALIDAD</small>
                  <b>{turnoSeleccionado.especialidad_nombre}</b>
                </div>
                <div>
                  <small>DURACIÓN</small>
                  <b>{turnoSeleccionado.duracion_minutos} minutos</b>
                </div>
              </div>

              {turnoSeleccionado.estado === "EN_ESPERA" && (
                <div className="clinical-actions">
                  <button
                    type="button"
                    className="primary"
                    disabled={atendiendo}
                    onClick={() => void handleAtender()}
                  >
                    <Icon name="check" size={17} />
                    {atendiendo ? "Registrando..." : "Marcar como atendido"}
                  </button>
                </div>
              )}

              {/* Notas de Seguimiento */}
              <div className="notes-head">
                <div>
                  <h3>Notas de seguimiento</h3>
                  <p>Información confidencial de evolución clínica para este paciente.</p>
                </div>
              </div>

              <form onSubmit={handleCrearNota} className="space-y-3 mb-6">
                <textarea
                  rows={3}
                  required
                  value={nuevaNota}
                  onChange={(e) => setNuevaNota(e.target.value)}
                  placeholder="Registrá observaciones sobre la evolución clínica, indicaciones o controles futuros..."
                  className="block w-full rounded-xl border border-slate-300 p-3 text-xs text-slate-900 shadow-sm"
                />
                <div className="flex justify-end">
                  <button type="submit" className="primary" disabled={guardandoNota}>
                    <Icon name="plus" size={16} />
                    {guardandoNota ? "Guardando..." : "Guardar Nota"}
                  </button>
                </div>
              </form>

              {cargandoNotas ? (
                <div className="space-y-3">
                  <Skeleton className="h-16 w-full" />
                </div>
              ) : notas.length === 0 ? (
                <p className="text-xs text-slate-500 italic py-2">
                  El paciente aún no cuenta con notas previas registradas.
                </p>
              ) : (
                <div className="space-y-3">
                  {notas.map((n) => {
                    const nomMed = n.medico_nombre || "";
                    const apeMed = n.medico_apellido || "";
                    const inicialesMed = nomMed || apeMed
                      ? `${nomMed.charAt(0)}${apeMed.charAt(0)}`.toUpperCase()
                      : "DR";
                    const partesNota = formatPartesFecha(n.fecha_creacion);

                    return (
                      <article key={n.id_nota} className="note">
                        <div className="flex justify-between items-start">
                          <div className="flex items-center gap-2">
                            <span>{inicialesMed}</span>
                            <p>
                              <b>Dr(a). {nomMed} {apeMed}</b>
                              <small>
                                {partesNota.diaMesTexto} · {partesNota.horaTexto} hs
                              </small>
                            </p>
                          </div>
                          <button
                            type="button"
                            className="secondary text-xs py-1 px-2"
                            onClick={() => {
                              setNotaEnEdicion(n);
                              setContenidoEdicion(n.contenido);
                            }}
                          >
                            Editar
                          </button>
                        </div>
                        <p>{n.contenido}</p>
                      </article>
                    );
                  })}
                </div>
              )}
            </>
          ) : (
            <div className="py-12 text-center text-slate-500 text-sm">
              Seleccioná un turno de la agenda izquierda para ver el historial y registrar la atención.
            </div>
          )}
        </section>
      </div>

      {/* Modal Edición de Nota */}
      {notaEnEdicion && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm"
        >
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl border border-slate-200 space-y-4">
            <h3 className="text-lg font-bold text-slate-900">Modificar Anotación Médica</h3>
            <form onSubmit={handleGuardarEdicion} className="space-y-3">
              <textarea
                rows={4}
                required
                value={contenidoEdicion}
                onChange={(e) => setContenidoEdicion(e.target.value)}
                className="block w-full rounded-xl border border-slate-300 p-3 text-sm"
              />
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setNotaEnEdicion(null)}
                >
                  Cancelar
                </button>
                <button type="submit" className="primary">
                  Actualizar Anotación
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
