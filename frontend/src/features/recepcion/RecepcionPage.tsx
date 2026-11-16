import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { Alerta } from "@/components/ui/Alerta";
import { Icon } from "@/components/ui/Icon";
import { ModalConfirmacion } from "@/components/ui/ModalConfirmacion";
import { Skeleton } from "@/components/ui/Skeleton";
import { Status } from "@/components/ui/Status";
import type { TurnoResponse } from "@/features/turnos/types";
import { formatPartesFecha } from "@/lib/dates";
import { mensajeDeError } from "@/lib/problem";
import {
  type PacienteItem,
  type SolicitudCancelacionOut,
  type TurnoEnEsperaResponse,
  recepcionApi,
} from "./api";

export function RecepcionPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const tabValida = (tab: string | null): tab is "espera" | "llegada" | "pacientes" | "solicitudes" | "cierre" =>
    tab === "espera" || tab === "pacientes" || tab === "solicitudes" || tab === "cierre";

  const [pestaña, setPestaña] = useState<
    "espera" | "llegada" | "pacientes" | "solicitudes" | "cierre"
  >(tabValida(tabParam) ? tabParam : "espera");

  useEffect(() => {
    if (tabValida(tabParam)) {
      setPestaña(tabParam);
    }
  }, [tabParam]);

  const cambiarPestaña = (nueva: "espera" | "pacientes" | "solicitudes" | "cierre") => {
    setPestaña(nueva);
    setSearchParams({ tab: nueva });
  };

  // Estado Sala de Espera
  const [salaEspera, setSalaEspera] = useState<TurnoEnEsperaResponse[]>([]);
  const [cargandoEspera, setCargandoEspera] = useState(false);

  // Estado Llegada de Pacientes (Typeahead)
  const [dniBusquedaLlegada, setDniBusquedaLlegada] = useState("");
  const [sugerenciasLlegada, setSugerenciasLlegada] = useState<PacienteItem[]>([]);
  const [buscandoSugerenciasLlegada, setBuscandoSugerenciasLlegada] = useState(false);
  const [buscandoPacienteLlegada, setBuscandoPacienteLlegada] = useState(false);
  const [pacienteLlegada, setPacienteLlegada] = useState<PacienteItem | null>(null);
  const [turnosHoyPaciente, setTurnosHoyPaciente] = useState<TurnoResponse[]>([]);
  const [cargandoTurnosHoy, setCargandoTurnosHoy] = useState(false);
  const [registrandoLlegadaId, setRegistrandoLlegadaId] = useState<string | null>(null);

  // Estado Búsqueda de Pacientes (Typeahead)
  const [dniBusqueda, setDniBusqueda] = useState("");
  const [sugerenciasPacientes, setSugerenciasPacientes] = useState<PacienteItem[]>([]);
  const [buscandoSugerenciasPacientes, setBuscandoSugerenciasPacientes] = useState(false);
  const [pacienteSeleccionado, setPacienteSeleccionado] = useState<PacienteItem | null>(null);
  const [buscandoPaciente, setBuscandoPaciente] = useState(false);
  const [esUsuarioRojo, setEsUsuarioRojo] = useState(false);
  const [idRestriccionActiva, setIdRestriccionActiva] = useState<string | null>(null);

  // Alta de Paciente
  const [mostrarAlta, setMostrarAlta] = useState(false);
  const [nuevoDni, setNuevoDni] = useState("");
  const [nuevoNombre, setNuevoNombre] = useState("");
  const [nuevoApellido, setNuevoApellido] = useState("");
  const [nuevoEmail, setNuevoEmail] = useState("");
  const [guardandoPaciente, setGuardandoPaciente] = useState(false);

  // Restricción Usuario Rojo
  const [mostrarModalRojo, setMostrarModalRojo] = useState(false);
  const [motivoRojo, setMotivoRojo] = useState("");
  const [diasRojo, setDiasRojo] = useState(30);
  const [guardandoRojo, setGuardandoRojo] = useState(false);

  // Solicitudes de Cancelación
  const [solicitudes, setSolicitudes] = useState<SolicitudCancelacionOut[]>([]);
  const [cargandoSolicitudes, setCargandoSolicitudes] = useState(false);

  // Cierre de Jornada
  const [ejecutandoCierre, setEjecutandoCierre] = useState(false);
  const [resultadoCierre, setResultadoCierre] = useState<string | null>(null);

  // Estados de confirmación accesibles
  const [idTurnoAusenteConfirmar, setIdTurnoAusenteConfirmar] = useState<string | null>(null);
  const [confirmarLevantarRojo, setConfirmarLevantarRojo] = useState(false);
  const [confirmarCierre, setConfirmarCierre] = useState(false);
  const [solicitudRechazarId, setSolicitudRechazarId] = useState<string | null>(null);
  const [motivoRechazoSolicitud, setMotivoRechazoSolicitud] = useState("");
  const [resolviendoSolicitud, setResolviendoSolicitud] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [mensajeExito, setMensajeExito] = useState<string | null>(null);

  // Cargar sala de espera
  const cargarSalaEspera = async () => {
    setCargandoEspera(true);
    try {
      const items = await recepcionApi.obtenerSalaEspera();
      setSalaEspera(items);
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setCargandoEspera(false);
    }
  };

  // Cargar solicitudes de cancelación
  const cargarSolicitudes = async () => {
    setCargandoSolicitudes(true);
    try {
      const items = await recepcionApi.listarSolicitudesCancelacion("PENDIENTE");
      setSolicitudes(items);
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setCargandoSolicitudes(false);
    }
  };

  useEffect(() => {
    void cargarSalaEspera();
    void cargarSolicitudes();
  }, []);

  // ─── Typeahead: Llegada de Pacientes ─────────────────────────────────────────

  useEffect(() => {
    const q = dniBusquedaLlegada.trim();
    if (!q || pacienteLlegada?.dni === q) {
      setSugerenciasLlegada([]);
      return;
    }

    const timer = setTimeout(async () => {
      setBuscandoSugerenciasLlegada(true);
      try {
        const res = await recepcionApi.buscarPacientes(q);
        setSugerenciasLlegada(res.items);
      } catch {
        setSugerenciasLlegada([]);
      } finally {
        setBuscandoSugerenciasLlegada(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [dniBusquedaLlegada, pacienteLlegada]);

  const seleccionarPacienteLlegada = async (p: PacienteItem) => {
    setDniBusquedaLlegada(p.dni);
    setSugerenciasLlegada([]);
    setPacienteLlegada(p);
    setError(null);
    setCargandoTurnosHoy(true);

    const fechaHoy = new Intl.DateTimeFormat("en-CA", {
      timeZone: "America/Argentina/Buenos_Aires",
    }).format(new Date());

    try {
      const resTurnos = await recepcionApi.listarTurnosDelPaciente(p.id_paciente, fechaHoy);
      const reservadosHoy = resTurnos.items.filter((t) => t.estado === "RESERVADO");
      setTurnosHoyPaciente(reservadosHoy);
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setCargandoTurnosHoy(false);
    }
  };

  const handleBuscarPacienteLlegada = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = dniBusquedaLlegada.trim();
    if (!q) return;

    setBuscandoPacienteLlegada(true);
    setError(null);
    setMensajeExito(null);
    setPacienteLlegada(null);
    setTurnosHoyPaciente([]);
    setSugerenciasLlegada([]);

    try {
      const res = await recepcionApi.buscarPacientes(q);
      const exacto = res.items.find((x: PacienteItem) => x.dni === q);

      if (exacto) {
        await seleccionarPacienteLlegada(exacto);
      } else if (res.items.length === 1) {
        await seleccionarPacienteLlegada(res.items[0]);
      } else if (res.items.length > 1) {
        setSugerenciasLlegada(res.items);
        setError("Hay varias coincidencias: ingresá el DNI completo.");
      } else {
        setError("No se encontró ningún paciente con ese DNI.");
      }
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setBuscandoPacienteLlegada(false);
    }
  };

  const handleRegistrarLlegadaTurno = async (idTurno: string) => {
    setRegistrandoLlegadaId(idTurno);
    setError(null);
    setMensajeExito(null);
    try {
      await recepcionApi.registrarLlegada(idTurno);
      setMensajeExito("Llegada registrada con éxito. El paciente ingresó a la sala de espera.");
      setTurnosHoyPaciente((prev) => prev.filter((t) => t.id_turno !== idTurno));
      void cargarSalaEspera();
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setRegistrandoLlegadaId(null);
    }
  };

  // ─── Typeahead: Ficha de Pacientes ──────────────────────────────────────────

  useEffect(() => {
    const q = dniBusqueda.trim();
    if (!q || pacienteSeleccionado?.dni === q) {
      setSugerenciasPacientes([]);
      return;
    }

    const timer = setTimeout(async () => {
      setBuscandoSugerenciasPacientes(true);
      try {
        const res = await recepcionApi.buscarPacientes(q);
        setSugerenciasPacientes(res.items);
      } catch {
        setSugerenciasPacientes([]);
      } finally {
        setBuscandoSugerenciasPacientes(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [dniBusqueda, pacienteSeleccionado]);

  const seleccionarPacienteFicha = async (p: PacienteItem) => {
    setDniBusqueda(p.dni);
    setSugerenciasPacientes([]);
    setPacienteSeleccionado(p);
    setError(null);
    try {
      const estadoRes = await recepcionApi.obtenerEstadoRestriccion(p.id_paciente);
      setEsUsuarioRojo(estadoRes.es_usuario_rojo);
      setIdRestriccionActiva(estadoRes.restriccion_activa?.id_restriccion || null);
    } catch {
      setEsUsuarioRojo(false);
    }
  };

  const handleBuscarPaciente = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = dniBusqueda.trim();
    if (!q) return;

    setBuscandoPaciente(true);
    setError(null);
    setMensajeExito(null);
    setPacienteSeleccionado(null);
    setSugerenciasPacientes([]);

    try {
      const res = await recepcionApi.buscarPacientes(q);
      const exacto = res.items.find((x: PacienteItem) => x.dni === q);

      if (exacto) {
        await seleccionarPacienteFicha(exacto);
      } else if (res.items.length === 1) {
        await seleccionarPacienteFicha(res.items[0]);
      } else if (res.items.length > 1) {
        setSugerenciasPacientes(res.items);
        setError("Hay varias coincidencias: ingresá el DNI completo.");
      } else {
        setError("No se encontró ningún paciente con ese DNI.");
      }
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setBuscandoPaciente(false);
    }
  };

  // Crear paciente
  const handleCrearPaciente = async (e: React.FormEvent) => {
    e.preventDefault();
    setGuardandoPaciente(true);
    setError(null);
    try {
      const nuevo = await recepcionApi.crearPaciente({
        dni: nuevoDni.trim(),
        nombre: nuevoNombre.trim(),
        apellido: nuevoApellido.trim(),
        email: nuevoEmail.trim().toLowerCase(),
      });
      setMostrarAlta(false);
      setNuevoDni("");
      setNuevoNombre("");
      setNuevoApellido("");
      setNuevoEmail("");
      await seleccionarPacienteFicha(nuevo);
      setMensajeExito(
        `Paciente ${nuevo.nombre} ${nuevo.apellido} dado de alta con éxito. Contraseña inicial: ${nuevo.dni}`,
      );
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setGuardandoPaciente(false);
    }
  };

  // Marcar ausente
  const ejecutarMarcarAusente = async () => {
    if (!idTurnoAusenteConfirmar) return;
    setError(null);
    try {
      await recepcionApi.registrarAusente(idTurnoAusenteConfirmar);
      setMensajeExito("Turno marcado como AUSENTE.");
      setIdTurnoAusenteConfirmar(null);
      void cargarSalaEspera();
    } catch (err) {
      setError(mensajeDeError(err));
    }
  };

  // Aprobar solicitud
  const handleAprobarSolicitud = async (idSolicitud: string) => {
    setError(null);
    try {
      await recepcionApi.resolverSolicitudCancelacion(idSolicitud, { aprobada: true });
      setMensajeExito("Solicitud aprobada: el turno fue cancelado y el horario liberado.");
      void cargarSolicitudes();
    } catch (err) {
      setError(mensajeDeError(err));
    }
  };

  // Rechazar solicitud
  const ejecutarRechazoSolicitud = async () => {
    if (!solicitudRechazarId || !motivoRechazoSolicitud.trim()) return;
    setResolviendoSolicitud(true);
    setError(null);
    try {
      await recepcionApi.resolverSolicitudCancelacion(solicitudRechazarId, {
        aprobada: false,
        detalle: motivoRechazoSolicitud.trim(),
      });
      setMensajeExito("Solicitud rechazada: el turno continúa confirmado.");
      setSolicitudRechazarId(null);
      setMotivoRechazoSolicitud("");
      void cargarSolicitudes();
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setResolviendoSolicitud(false);
    }
  };

  // Sancionar Usuario Rojo
  const handleClasificarRojo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pacienteSeleccionado) return;
    setGuardandoRojo(true);
    setError(null);
    try {
      const res = await recepcionApi.clasificarUsuarioRojo({
        id_paciente: pacienteSeleccionado.id_paciente,
        motivo: motivoRojo.trim(),
        dias_vigencia: diasRojo,
      });
      setEsUsuarioRojo(true);
      setIdRestriccionActiva(res.id_restriccion);
      setMostrarModalRojo(false);
      setMensajeExito("Paciente clasificado como Usuario rojo por 30 días.");
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setGuardandoRojo(false);
    }
  };

  // Levantar Restricción
  const ejecutarLevantarRestriccion = async () => {
    if (!idRestriccionActiva) return;
    setError(null);
    try {
      await recepcionApi.levantarRestriccion(idRestriccionActiva);
      setEsUsuarioRojo(false);
      setIdRestriccionActiva(null);
      setConfirmarLevantarRojo(false);
      setMensajeExito("Restricción levantada exitosamente.");
    } catch (err) {
      setError(mensajeDeError(err));
    }
  };

  // Cierre de jornada
  const ejecutarCierreJornada = async () => {
    setEjecutandoCierre(true);
    setError(null);
    setResultadoCierre(null);
    try {
      const res = await recepcionApi.cerrarJornada();
      setResultadoCierre(`Cierre completado: se marcaron ${res.total_ausentes} turnos como ausentes.`);
      setConfirmarCierre(false);
      void cargarSalaEspera();
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setEjecutandoCierre(false);
    }
  };

  return (
    <>
      <div className="page-title">
        <div>
          <p>ITU MEDICAL</p>
          <h1>Módulo de Recepción</h1>
          <span>Control de sala de espera, búsqueda en vivo por DNI o nombre y gestión de pacientes.</span>
        </div>
      </div>

      {error && <Alerta tipo="error">{error}</Alerta>}
      {mensajeExito && <Alerta tipo="exito">{mensajeExito}</Alerta>}

      {/* Barra de Estadísticas */}
      <section className="stats">
        <div>
          <span className="stat-icon green">
            <Icon name="people" />
          </span>
          <p>
            En espera<b>{salaEspera.length} pacientes</b>
          </p>
          <small>Ahora</small>
        </div>

        <div>
          <span className="stat-icon blue">
            <Icon name="calendar" />
          </span>
          <p>
            Cancelaciones<b>{solicitudes.length} pendientes</b>
          </p>
          <small>&lt; 24 hs</small>
        </div>

        <div>
          <span className="stat-icon amber">
            <Icon name="clock" />
          </span>
          <p>
            Cierre de Jornada<b>Marcado ausente</b>
          </p>
          <small>Final de turno</small>
        </div>
      </section>

      {/* Pestañas de Administración */}
      <div className="admin-tabs">
        <button
          type="button"
          className={pestaña === "espera" ? "active" : ""}
          onClick={() => cambiarPestaña("espera")}
        >
          Sala de espera
        </button>
        <button
          type="button"
          className={pestaña === "pacientes" ? "active" : ""}
          onClick={() => cambiarPestaña("pacientes")}
        >
          Pacientes & DNI
        </button>
        <button
          type="button"
          className={pestaña === "solicitudes" ? "active" : ""}
          onClick={() => cambiarPestaña("solicitudes")}
        >
          Solicitudes {solicitudes.length > 0 && <b>{solicitudes.length}</b>}
        </button>
        <button
          type="button"
          className={pestaña === "cierre" ? "active" : ""}
          onClick={() => cambiarPestaña("cierre")}
        >
          Cierre de jornada
        </button>
      </div>

      {/* PESTAÑA: SALA DE ESPERA (RF-12) & REGISTRO DE LLEGADA */}
      {pestaña === "espera" && (
        <div className="space-y-6">
          {/* Registro rápido de llegada con Autocomplete */}
          <section className="panel">
            <div className="panel-head">
              <div>
                <h2>Registrar Llegada de Paciente</h2>
                <p>Buscá al paciente por DNI o por nombre/apellido mientras escribís para ver sus turnos de hoy.</p>
              </div>
            </div>

            <div className="p-6 space-y-4">
              <div className="relative">
                <form onSubmit={handleBuscarPacienteLlegada} className="flex flex-wrap items-center gap-3">
                  <label className="flex items-center gap-2 border border-slate-300 rounded-xl px-3 py-2 w-full sm:w-96 bg-white focus-within:ring-2 focus-within:ring-brand-500">
                    <Icon name="search" size={17} />
                    <input
                      type="text"
                      placeholder="Ingresá DNI del paciente, nombre o apellido..."
                      value={dniBusquedaLlegada}
                      onChange={(e) => setDniBusquedaLlegada(e.target.value)}
                      className="outline-none text-sm w-full"
                      required
                    />
                    {buscandoSugerenciasLlegada && (
                      <span className="text-xs text-slate-400 animate-spin">⟳</span>
                    )}
                  </label>
                  <button type="submit" className="primary" disabled={buscandoPacienteLlegada}>
                    {buscandoPacienteLlegada ? "Buscando..." : "Buscar turnos de hoy"}
                  </button>
                  {pacienteLlegada && (
                    <button
                      type="button"
                      className="secondary text-xs"
                      onClick={() => {
                        setPacienteLlegada(null);
                        setTurnosHoyPaciente([]);
                        setDniBusquedaLlegada("");
                      }}
                    >
                      Limpiar
                    </button>
                  )}
                </form>

                {/* Dropdown de autocompletado en vivo */}
                {sugerenciasLlegada.length > 0 && (
                  <div className="absolute z-20 top-full left-0 mt-1 w-full sm:w-96 rounded-xl border border-slate-200 bg-white p-1 shadow-lg max-h-60 overflow-y-auto">
                    <div className="px-3 py-1.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                      Resultados ({sugerenciasLlegada.length})
                    </div>
                    {sugerenciasLlegada.map((p) => {
                      const ini = `${p.nombre.charAt(0)}${p.apellido.charAt(0)}`.toUpperCase();
                      return (
                        <button
                          key={p.id_paciente}
                          type="button"
                          className="w-full text-left px-3 py-2 rounded-lg hover:bg-slate-50 flex items-center justify-between gap-2 transition-colors border-b last:border-b-0 border-slate-100"
                          onClick={() => void seleccionarPacienteLlegada(p)}
                        >
                          <div className="flex items-center gap-2">
                            <span className="w-7 h-7 rounded-full bg-slate-100 text-slate-700 text-xs font-bold flex items-center justify-center">
                              {ini}
                            </span>
                            <div>
                              <b className="text-xs font-semibold text-slate-900 block">
                                {p.nombre} {p.apellido}
                              </b>
                              <span className="text-[11px] text-slate-500">
                                DNI {p.dni}
                              </span>
                            </div>
                          </div>
                          <span className="text-xs text-brand-600 font-semibold">Seleccionar</span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              {cargandoTurnosHoy && (
                <div className="py-4 space-y-2">
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                </div>
              )}

              {pacienteLlegada && !cargandoTurnosHoy && (
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-3">
                  <div>
                    <h3 className="font-bold text-slate-900">
                      {pacienteLlegada.nombre} {pacienteLlegada.apellido}
                    </h3>
                    <p className="text-xs text-slate-500">
                      DNI {pacienteLlegada.dni} · {pacienteLlegada.email}
                    </p>
                  </div>

                  {turnosHoyPaciente.length === 0 ? (
                    <p className="text-sm text-slate-600 italic">
                      El paciente no tiene turnos programados para el día de hoy.
                    </p>
                  ) : (
                    <div className="divide-y divide-slate-200">
                      {turnosHoyPaciente.map((turno) => {
                        const hora = formatPartesFecha(turno.fecha_hora).horaTexto;

                        return (
                          <div
                            key={turno.id_turno}
                            className="py-3 flex flex-wrap items-center justify-between gap-3"
                          >
                            <div>
                              <span className="font-semibold text-sm text-slate-900">
                                {hora} hs
                              </span>
                              <span className="text-xs text-slate-600 block">
                                Dr(a). {turno.medico_nombre} {turno.medico_apellido} · {turno.especialidad_nombre}
                              </span>
                            </div>
                            <button
                              type="button"
                              className="primary"
                              disabled={registrandoLlegadaId === turno.id_turno}
                              onClick={() => void handleRegistrarLlegadaTurno(turno.id_turno)}
                            >
                              {registrandoLlegadaId === turno.id_turno ? "Registrando..." : "Registrar Llegada"}
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          </section>

          {/* Tabla de sala de espera */}
          <section className="panel">
            <div className="panel-head">
              <div>
                <h2>Pacientes en Espera (Orden de Prioridad)</h2>
                <p>Ordenados según algoritmo RF-12: puntuales en tolerancia de 10 min por horario de turno.</p>
              </div>
              <div className="panel-tools">
                <button
                  type="button"
                  className="icon-button"
                  onClick={cargarSalaEspera}
                  disabled={cargandoEspera}
                  aria-label="Actualizar sala de espera"
                >
                  <Icon name="refresh" />
                </button>
              </div>
            </div>

            {cargandoEspera ? (
              <div className="space-y-3 p-6">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : salaEspera.length === 0 ? (
              <div className="empty-action">
                <span>
                  <Icon name="people" size={28} />
                </span>
                <h3>No hay pacientes en espera</h3>
                <p>Los pacientes ingresarán aquí al registrar su llegada en recepción.</p>
              </div>
            ) : (
              <div className="patient-table">
                <div className="table-row table-header">
                  <span>PACIENTE</span>
                  <span>TURNO</span>
                  <span>PROFESIONAL</span>
                  <span>LLEGADA</span>
                  <span>CONDICIÓN</span>
                  <span />
                </div>

                {salaEspera.map((t) => {
                  const iniciales = `${t.paciente_nombre.charAt(0)}${t.paciente_apellido.charAt(0)}`.toUpperCase();
                  const partesTurno = formatPartesFecha(t.fecha_hora);
                  const partesLlegada = formatPartesFecha(t.fecha_hora_llegada);

                  return (
                    <div className="table-row" key={t.id_turno}>
                      <span className="patient">
                        <i>{iniciales}</i>
                        <b>
                          {t.paciente_nombre} {t.paciente_apellido}
                          <small>DNI {t.paciente_dni}</small>
                        </b>
                      </span>

                      <span>
                        <b>{partesTurno.horaTexto} hs</b>
                        <small>Prioridad #{t.orden_atencion}</small>
                      </span>

                      <span>
                        <b>Dr(a). {t.medico_nombre} {t.medico_apellido}</b>
                        <small>{t.especialidad_nombre}</small>
                      </span>

                      <span>
                        <b>{partesLlegada.horaTexto} hs</b>
                      </span>

                      <span>
                        <Status tone={t.en_tolerancia ? "green" : "amber"}>
                          {t.en_tolerancia ? "En tolerancia" : "Demorado (+10m)"}
                        </Status>
                      </span>

                      <span>
                        <button
                          type="button"
                          className="row-action"
                          onClick={() => setIdTurnoAusenteConfirmar(t.id_turno)}
                        >
                          Ausente
                        </button>
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      )}

      {/* PESTAÑA: PACIENTES & DNI CON TYPEAHEAD */}
      {pestaña === "pacientes" && (
        <section className="panel">
          <div className="panel-head">
            <div>
              <h2>Búsqueda y Ficha de Pacientes</h2>
              <p>Consultá en vivo por DNI o nombre/apellido, estado de cuenta y restricciones.</p>
            </div>
            <button
              type="button"
              className="primary"
              onClick={() => setMostrarAlta(true)}
            >
              <Icon name="plus" size={16} /> Alta de Paciente
            </button>
          </div>

          <div className="p-6 space-y-6">
            <div className="relative w-full sm:w-96">
              <form onSubmit={handleBuscarPaciente} className="flex items-center gap-3">
                <label className="flex items-center gap-2 border border-slate-300 rounded-xl px-3 py-2 w-full bg-white focus-within:ring-2 focus-within:ring-brand-500">
                  <Icon name="search" size={17} />
                  <input
                    type="text"
                    placeholder="Ingresá DNI del paciente, nombre o apellido..."
                    value={dniBusqueda}
                    onChange={(e) => setDniBusqueda(e.target.value)}
                    className="outline-none text-sm w-full"
                  />
                  {buscandoSugerenciasPacientes && (
                    <span className="text-xs text-slate-400 animate-spin">⟳</span>
                  )}
                </label>
                <button type="submit" className="primary" disabled={buscandoPaciente}>
                  {buscandoPaciente ? "Buscando..." : "Buscar"}
                </button>
              </form>

              {/* Dropdown de autocompletado en vivo */}
              {sugerenciasPacientes.length > 0 && (
                <div className="absolute z-20 top-full left-0 mt-1 w-full rounded-xl border border-slate-200 bg-white p-1 shadow-lg max-h-60 overflow-y-auto">
                  <div className="px-3 py-1.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    Resultados ({sugerenciasPacientes.length})
                  </div>
                  {sugerenciasPacientes.map((p) => {
                    const ini = `${p.nombre.charAt(0)}${p.apellido.charAt(0)}`.toUpperCase();
                    return (
                      <button
                        key={p.id_paciente}
                        type="button"
                        className="w-full text-left px-3 py-2 rounded-lg hover:bg-slate-50 flex items-center justify-between gap-2 transition-colors border-b last:border-b-0 border-slate-100"
                        onClick={() => void seleccionarPacienteFicha(p)}
                      >
                        <div className="flex items-center gap-2">
                          <span className="w-7 h-7 rounded-full bg-slate-100 text-slate-700 text-xs font-bold flex items-center justify-center">
                            {ini}
                          </span>
                          <div>
                            <b className="text-xs font-semibold text-slate-900 block">
                              {p.nombre} {p.apellido}
                            </b>
                            <span className="text-[11px] text-slate-500">
                              DNI {p.dni}
                            </span>
                          </div>
                        </div>
                        <span className="text-xs text-brand-600 font-semibold">Seleccionar</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {pacienteSeleccionado && (
              <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
                  <div>
                    <h3 className="text-lg font-bold text-slate-900">
                      {pacienteSeleccionado.nombre} {pacienteSeleccionado.apellido}
                    </h3>
                    <p className="text-xs text-slate-500">
                      DNI: {pacienteSeleccionado.dni} · Correo: {pacienteSeleccionado.email}
                    </p>
                  </div>

                  <div>
                    {esUsuarioRojo ? (
                      <div className="flex items-center gap-2">
                        <Status tone="amber">Usuario Rojo Activo</Status>
                        <button
                          type="button"
                          className="secondary"
                          onClick={() => setConfirmarLevantarRojo(true)}
                        >
                          Levantar Sanción
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => setMostrarModalRojo(true)}
                      >
                        Sancionar (Usuario Rojo)
                      </button>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs text-slate-600">
                  <div>
                    <span className="font-semibold block text-slate-400">DNI</span>
                    <span className="font-bold text-slate-900">{pacienteSeleccionado.dni}</span>
                  </div>
                  <div>
                    <span className="font-semibold block text-slate-400">Teléfono</span>
                    <span className="font-bold text-slate-900">{pacienteSeleccionado.telefono || "No registrado"}</span>
                  </div>
                  <div>
                    <span className="font-semibold block text-slate-400">Email Verificado</span>
                    <span className="font-bold text-slate-900">{pacienteSeleccionado.email_verificado ? "Sí" : "Pendiente"}</span>
                  </div>
                  <div>
                    <span className="font-semibold block text-slate-400">Estado</span>
                    <span className="font-bold text-slate-900">{pacienteSeleccionado.habilitado ? "Habilitado" : "Deshabilitado"}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* PESTAÑA: SOLICITUDES (<24 hs) */}
      {pestaña === "solicitudes" && (
        <section className="panel">
          <div className="panel-head">
            <div>
              <h2>Solicitudes de Cancelación Rápida (&lt; 24 hs)</h2>
              <p>Revisión y resolución de cancelaciones con poca anticipación.</p>
            </div>
            <button
              type="button"
              className="icon-button"
              onClick={cargarSolicitudes}
              disabled={cargandoSolicitudes}
              aria-label="Actualizar solicitudes"
            >
              <Icon name="refresh" />
            </button>
          </div>

          {cargandoSolicitudes ? (
            <div className="space-y-3 p-6">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : solicitudes.length === 0 ? (
            <div className="empty-action">
              <span>
                <Icon name="check" size={28} />
              </span>
              <h3>No hay solicitudes pendientes</h3>
              <p>Las cancelaciones solicitadas con menos de 24 hs aparecerán en esta sección.</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100 p-6">
              {solicitudes.map((s) => (
                <div key={s.id_solicitud} className="py-4 flex flex-wrap items-center justify-between gap-4">
                  <div className="space-y-1">
                    <p className="font-semibold text-slate-900">
                      {s.paciente_nombre} {s.paciente_apellido} (DNI {s.paciente_dni})
                    </p>
                    <p className="text-xs text-slate-600">
                      {s.especialidad_nombre} · Dr(a). {s.medico_nombre} {s.medico_apellido}
                    </p>
                    <p className="text-xs text-slate-800 bg-slate-50 p-2 rounded border border-slate-200">
                      <b>Motivo:</b> {s.motivo}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      className="primary"
                      onClick={() => void handleAprobarSolicitud(s.id_solicitud)}
                    >
                      Aprobar
                    </button>
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => setSolicitudRechazarId(s.id_solicitud)}
                    >
                      Rechazar
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* PESTAÑA: CIERRE DE JORNADA */}
      {pestaña === "cierre" && (
        <section className="panel p-8 text-center max-w-xl mx-auto space-y-4">
          <h2>Cierre de Jornada de Atención</h2>
          <p className="text-sm text-slate-600">
            Al finalizar el día laboral, esta acción busca todos los turnos del día que quedaron en estado reservado y sin llegada registrada, marcándolos automáticamente como <b>AUSENTE</b>.
          </p>

          {resultadoCierre && <Alerta tipo="exito">{resultadoCierre}</Alerta>}

          <div className="pt-4 flex justify-center">
            <button
              type="button"
              className="primary"
              onClick={() => setConfirmarCierre(true)}
              disabled={ejecutandoCierre}
            >
              {ejecutandoCierre ? "Procesando..." : "Ejecutar Cierre de Jornada"}
            </button>
          </div>
        </section>
      )}

      {/* MODAL ALTA DE PACIENTE */}
      {mostrarAlta && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm"
        >
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl border border-slate-200 space-y-4">
            <h3 className="text-lg font-bold text-slate-900">Dar de Alta Paciente en Recepción</h3>
            <form onSubmit={handleCrearPaciente} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700">DNI</label>
                <input
                  type="text"
                  required
                  value={nuevoDni}
                  onChange={(e) => setNuevoDni(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-300 p-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700">Nombre</label>
                <input
                  type="text"
                  required
                  value={nuevoNombre}
                  onChange={(e) => setNuevoNombre(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-300 p-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700">Apellido</label>
                <input
                  type="text"
                  required
                  value={nuevoApellido}
                  onChange={(e) => setNuevoApellido(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-300 p-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700">Correo Electrónico</label>
                <input
                  type="email"
                  required
                  value={nuevoEmail}
                  onChange={(e) => setNuevoEmail(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-300 p-2 text-sm"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3">
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setMostrarAlta(false)}
                >
                  Cancelar
                </button>
                <button type="submit" className="primary" disabled={guardandoPaciente}>
                  {guardandoPaciente ? "Guardando..." : "Crear Paciente"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL SANCIONAR USUARIO ROJO */}
      {mostrarModalRojo && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm"
        >
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl border border-slate-200 space-y-4">
            <h3 className="text-lg font-bold text-slate-900">Sancionar Paciente (Usuario Rojo)</h3>
            <p className="text-xs text-slate-600">
              La restricción bloquea reservas por la web pero permite reservas presenciales o telefónicas.
            </p>
            <form onSubmit={handleClasificarRojo} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700">Motivo</label>
                <textarea
                  required
                  rows={3}
                  value={motivoRojo}
                  onChange={(e) => setMotivoRojo(e.target.value)}
                  placeholder="Ej: Inasistencias reiteradas sin aviso"
                  className="mt-1 block w-full rounded-lg border border-slate-300 p-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700">Días de vigencia</label>
                <input
                  type="number"
                  min={1}
                  max={365}
                  value={diasRojo}
                  onChange={(e) => setDiasRojo(Number(e.target.value))}
                  className="mt-1 block w-full rounded-lg border border-slate-300 p-2 text-sm"
                />
              </div>
              <div className="flex justify-end gap-2 pt-3">
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setMostrarModalRojo(false)}
                >
                  Cancelar
                </button>
                <button type="submit" className="primary" disabled={guardandoRojo}>
                  {guardandoRojo ? "Aplicando..." : "Aplicar Sanción"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL RECHAZO SOLICITUD */}
      {solicitudRechazarId && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm"
        >
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl border border-slate-200 space-y-4">
            <h3 className="text-lg font-bold text-slate-900">Rechazar Solicitud de Cancelación</h3>
            <p className="text-sm text-slate-600">
              Indicá el motivo del rechazo. El turno permanecerá en estado RESERVADO.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void ejecutarRechazoSolicitud();
              }}
              className="space-y-4"
            >
              <textarea
                required
                rows={3}
                value={motivoRechazoSolicitud}
                onChange={(e) => setMotivoRechazoSolicitud(e.target.value)}
                placeholder="Ej: Solicitud fuera de término"
                className="mt-1 block w-full rounded-lg border border-slate-300 p-2 text-sm"
              />
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  className="secondary"
                  onClick={() => {
                    setSolicitudRechazarId(null);
                    setMotivoRechazoSolicitud("");
                  }}
                  disabled={resolviendoSolicitud}
                >
                  Cancelar
                </button>
                <button type="submit" className="primary" disabled={resolviendoSolicitud}>
                  Rechazar Solicitud
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modales de Confirmación Accesibles */}
      <ModalConfirmacion
        abierto={idTurnoAusenteConfirmar !== null}
        titulo="Confirmar Ausencia"
        mensaje="¿Confirmás que el paciente no se presentó al turno? Esta acción registrará la ausencia en el historial del paciente."
        textoConfirmar="Marcar Ausente"
        variante="peligro"
        onConfirmar={ejecutarMarcarAusente}
        onCancelar={() => setIdTurnoAusenteConfirmar(null)}
      />

      <ModalConfirmacion
        abierto={confirmarLevantarRojo}
        titulo="Levantar Sanción de Usuario Rojo"
        mensaje="¿Confirmás levantar la restricción de usuario rojo para este paciente?"
        textoConfirmar="Levantar Sanción"
        variante="primario"
        onConfirmar={ejecutarLevantarRestriccion}
        onCancelar={() => setConfirmarLevantarRojo(false)}
      />

      <ModalConfirmacion
        abierto={confirmarCierre}
        titulo="Confirmar Cierre de Jornada"
        mensaje="¿Estás seguro de ejecutar el cierre? Todos los turnos de hoy reservados sin llegada se marcarán como AUSENTE."
        textoConfirmar="Ejecutar Cierre"
        variante="peligro"
        cargando={ejecutandoCierre}
        onConfirmar={ejecutarCierreJornada}
        onCancelar={() => setConfirmarCierre(false)}
      />
    </>
  );
}
