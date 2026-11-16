import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { Alerta } from "@/components/ui/Alerta";
import { Icon } from "@/components/ui/Icon";
import { Skeleton } from "@/components/ui/Skeleton";
import { Status, type StatusTone } from "@/components/ui/Status";
import { useAuth } from "@/features/auth/useAuth";
import type { EstadoTurno, TurnoResponse } from "@/features/turnos/types";
import { formatPartesFecha } from "@/lib/dates";
import { mensajeDeError } from "@/lib/problem";
import { type HorarioItem, type HorarioOut, type MedicoOut, type NotaSeguimientoOut, medicoApi } from "./api";

const ESTADO_TONE: Record<EstadoTurno, StatusTone> = {
  RESERVADO: "blue",
  EN_ESPERA: "amber",
  ATENDIDO: "green",
  CANCELADO: "gray",
  AUSENTE: "gray",
};

const DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

// Convierte "HH:MM:SS" → "HH:MM"
function horaCorta(t: string): string {
  return t.slice(0, 5);
}

// ─── Panel: Gestión de Horarios ───────────────────────────────────────────────

function PanelHorarios({ idMedico }: { idMedico: string }) {
  const [horarios, setHorarios] = useState<HorarioOut[]>([]);
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exito, setExito] = useState<string | null>(null);

  // Formulario nuevo horario
  const [diaNuevo, setDiaNuevo] = useState("0");
  const [inicioNuevo, setInicioNuevo] = useState("09:00");
  const [finNuevo, setFinNuevo] = useState("13:00");
  const [duracionNueva, setDuracionNueva] = useState("30");

  const cargar = async () => {
    setCargando(true);
    setError(null);
    try {
      const res = await medicoApi.obtenerHorarios(idMedico);
      setHorarios(res);
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => { void cargar(); }, [idMedico]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleActivo = async (h: HorarioOut) => {
    const actualizados: HorarioItem[] = horarios.map((x) => ({
      dia_semana: x.dia_semana,
      hora_inicio: x.hora_inicio,
      hora_fin: x.hora_fin,
      duracion_minutos: x.duracion_minutos,
      activo: x.id_horario === h.id_horario ? !x.activo : x.activo,
    }));
    await guardarHorarios(actualizados);
  };

  const eliminarHorario = async (h: HorarioOut) => {
    const actualizados: HorarioItem[] = horarios
      .filter((x) => x.id_horario !== h.id_horario)
      .map((x) => ({
        dia_semana: x.dia_semana,
        hora_inicio: x.hora_inicio,
        hora_fin: x.hora_fin,
        duracion_minutos: x.duracion_minutos,
        activo: x.activo,
      }));
    await guardarHorarios(actualizados);
  };

  const agregarHorario = async (e: React.FormEvent) => {
    e.preventDefault();
    const nuevo: HorarioItem = {
      dia_semana: parseInt(diaNuevo),
      hora_inicio: `${inicioNuevo}:00`,
      hora_fin: `${finNuevo}:00`,
      duracion_minutos: parseInt(duracionNueva),
      activo: true,
    };
    const actualizados: HorarioItem[] = [
      ...horarios.map((x) => ({
        dia_semana: x.dia_semana,
        hora_inicio: x.hora_inicio,
        hora_fin: x.hora_fin,
        duracion_minutos: x.duracion_minutos,
        activo: x.activo,
      })),
      nuevo,
    ];
    await guardarHorarios(actualizados);
  };

  const guardarHorarios = async (items: HorarioItem[]) => {
    setGuardando(true);
    setError(null);
    setExito(null);
    try {
      const res = await medicoApi.configurarHorarios(idMedico, items);
      setHorarios(res);
      setExito("Horarios actualizados correctamente.");
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setGuardando(false);
    }
  };

  if (cargando) {
    return (
      <div className="space-y-3 py-4">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  }

  const horariosPorDia = DIAS.map((_, i) => ({
    dia: i,
    nombre: DIAS[i],
    items: horarios.filter((h) => h.dia_semana === i),
  }));

  return (
    <div className="space-y-6">
      {error && <Alerta tipo="error">{error}</Alerta>}
      {exito && <Alerta tipo="exito">{exito}</Alerta>}

      {/* Tabla actual */}
      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>Horarios de atención configurados</h2>
            <p>Los slots disponibles para reservar se generan a partir de estos horarios.</p>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={() => void cargar()}
            disabled={cargando || guardando}
            aria-label="Actualizar"
          >
            <Icon name="refresh" size={17} />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {horariosPorDia.map(({ dia, nombre, items }) =>
            items.length === 0 ? null : (
              <div key={dia}>
                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                  {nombre}
                </h4>
                <div className="space-y-2">
                  {items.map((h) => (
                    <div
                      key={h.id_horario}
                      className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3"
                    >
                      <div className="flex items-center gap-3">
                        <Status tone={h.activo ? "green" : "gray"}>
                          {h.activo ? "Activo" : "Inactivo"}
                        </Status>
                        <span className="text-sm font-semibold text-slate-900">
                          {horaCorta(h.hora_inicio)} – {horaCorta(h.hora_fin)}
                        </span>
                        <span className="text-xs text-slate-500">
                          Turnos cada {h.duracion_minutos} min
                        </span>
                      </div>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          className="secondary text-xs py-1 px-3"
                          disabled={guardando}
                          onClick={() => void toggleActivo(h)}
                        >
                          {h.activo ? "Desactivar" : "Activar"}
                        </button>
                        <button
                          type="button"
                          className="secondary text-xs py-1 px-3"
                          disabled={guardando}
                          onClick={() => void eliminarHorario(h)}
                        >
                          Eliminar
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          )}
          {horarios.length === 0 && (
            <p className="text-sm text-slate-500 italic">
              No hay horarios configurados. Agregá uno abajo.
            </p>
          )}
        </div>
      </section>

      {/* Formulario agregar */}
      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>Agregar nuevo bloque horario</h2>
            <p>Definí el día, horario y duración de cada turno.</p>
          </div>
        </div>
        <form onSubmit={(e) => void agregarHorario(e)} className="p-6 grid grid-cols-2 sm:grid-cols-4 gap-4 items-end">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Día</label>
            <select
              value={diaNuevo}
              onChange={(e) => setDiaNuevo(e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm bg-white"
            >
              {DIAS.map((nombre, i) => (
                <option key={i} value={i}>{nombre}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Desde</label>
            <input
              type="time"
              value={inicioNuevo}
              onChange={(e) => setInicioNuevo(e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Hasta</label>
            <input
              type="time"
              value={finNuevo}
              onChange={(e) => setFinNuevo(e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Duración (min)</label>
            <select
              value={duracionNueva}
              onChange={(e) => setDuracionNueva(e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm bg-white"
            >
              {[15, 20, 30, 45, 60].map((d) => (
                <option key={d} value={d}>{d} min</option>
              ))}
            </select>
          </div>
          <div className="col-span-2 sm:col-span-4 flex justify-end">
            <button type="submit" className="primary" disabled={guardando}>
              <Icon name="plus" size={16} />
              {guardando ? "Guardando..." : "Agregar Horario"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

// ─── Página principal ─────────────────────────────────────────────────────────

export function MedicoPage() {
  const { usuario } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const [pestaña, setPestaña] = useState<"consultorio" | "horarios">(
    tabParam === "horarios" ? "horarios" : "consultorio",
  );

  useEffect(() => {
    if (tabParam === "horarios" || tabParam === "consultorio") {
      setPestaña(tabParam);
    }
  }, [tabParam]);

  const [miPerfil, setMiPerfil] = useState<MedicoOut | null>(null);
  const [cargandoPerfil, setCargandoPerfil] = useState(true);

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

  // Cargar perfil del médico actual
  useEffect(() => {
    if (!usuario) return;
    async function cargarPerfil() {
      setCargandoPerfil(true);
      try {
        const perfil = await medicoApi.obtenerMiPerfil(usuario!.id_usuario);
        setMiPerfil(perfil);
      } catch {
        // no bloqueamos
      } finally {
        setCargandoPerfil(false);
      }
    }
    void cargarPerfil();
  }, [usuario]);

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
          <span>Agenda del día, seguimiento de pacientes y configuración de horarios.</span>
        </div>
      </div>

      {error && <Alerta tipo="error">{error}</Alerta>}
      {mensajeExito && <Alerta tipo="exito">{mensajeExito}</Alerta>}

      {/* Pestañas */}
      <div className="admin-tabs">
        <button
          type="button"
          className={pestaña === "consultorio" ? "active" : ""}
          onClick={() => {
            setPestaña("consultorio");
            setSearchParams({ tab: "consultorio" });
          }}
        >
          Consultorio del Día
        </button>
        <button
          type="button"
          className={pestaña === "horarios" ? "active" : ""}
          onClick={() => {
            setPestaña("horarios");
            setSearchParams({ tab: "horarios" });
          }}
        >
          Mis Horarios de Atención
        </button>
      </div>

      {/* PESTAÑA: CONSULTORIO */}
      {pestaña === "consultorio" && (
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
      )}

      {/* PESTAÑA: HORARIOS */}
      {pestaña === "horarios" && (
        <>
          {cargandoPerfil ? (
            <div className="space-y-3 py-4">
              <Skeleton className="h-10 w-full" />
            </div>
          ) : miPerfil ? (
            <PanelHorarios idMedico={miPerfil.id_medico} />
          ) : (
            <Alerta tipo="error">
              No se pudo obtener el perfil del médico. Intentá recargar la página.
            </Alerta>
          )}
        </>
      )}

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
