import { useEffect, useState } from "react";

import { AppNavbar } from "@/components/layout/AppNavbar";
import { Alerta } from "@/components/ui/Alerta";
import { Boton } from "@/components/ui/Boton";
import { Cargando } from "@/components/ui/Cargando";
import { formatFechaHora, formatHora } from "@/lib/dates";
import { mensajeDeError } from "@/lib/problem";
import {
  type PacienteItem,
  type SolicitudCancelacionOut,
  type TurnoEnEsperaResponse,
  recepcionApi,
} from "./api";

export function RecepcionPage() {
  const [pestaña, setPestaña] = useState<"espera" | "pacientes" | "solicitudes" | "cierre">("espera");

  // Estado Sala de Espera
  const [salaEspera, setSalaEspera] = useState<TurnoEnEsperaResponse[]>([]);
  const [cargandoEspera, setCargandoEspera] = useState(false);
  const [idTurnoLlegada, setIdTurnoLlegada] = useState("");
  const [registrandoLlegada, setRegistrandoLlegada] = useState(false);

  // Estado Búsqueda de Pacientes
  const [dniBusqueda, setDniBusqueda] = useState("");
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
    if (pestaña === "espera") void cargarSalaEspera();
    if (pestaña === "solicitudes") void cargarSolicitudes();
  }, [pestaña]);

  // Buscar paciente por DNI
  const handleBuscarPaciente = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dniBusqueda.trim()) return;
    setBuscandoPaciente(true);
    setError(null);
    setMensajeExito(null);
    try {
      const res = await recepcionApi.buscarPacientes(dniBusqueda.trim());
      if (res.items.length > 0) {
        const p = res.items[0];
        setPacienteSeleccionado(p);
        const est = await recepcionApi.obtenerEstadoRestriccion(p.id_paciente);
        setEsUsuarioRojo(est.es_usuario_rojo);
        setIdRestriccionActiva(est.restriccion_activa?.id_restriccion || null);
      } else {
        setPacienteSeleccionado(null);
        setError("No se encontró ningún paciente con el DNI ingresado.");
      }
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setBuscandoPaciente(false);
    }
  };

  // Alta de nuevo paciente
  const handleCrearPaciente = async (e: React.FormEvent) => {
    e.preventDefault();
    setGuardandoPaciente(true);
    setError(null);
    try {
      const creado = await recepcionApi.crearPaciente({
        dni: nuevoDni.trim(),
        nombre: nuevoNombre.trim(),
        apellido: nuevoApellido.trim(),
        email: nuevoEmail.trim() || undefined,
      });
      setPacienteSeleccionado(creado);
      setDniBusqueda(creado.dni);
      setMostrarAlta(false);
      setMensajeExito(`Paciente ${creado.nombre} ${creado.apellido} creado exitosamente.`);
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setGuardandoPaciente(false);
    }
  };

  // Registrar llegada de turno
  const handleRegistrarLlegada = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!idTurnoLlegada.trim()) return;
    setRegistrandoLlegada(true);
    setError(null);
    setMensajeExito(null);
    try {
      await recepcionApi.registrarLlegada(idTurnoLlegada.trim());
      setIdTurnoLlegada("");
      setMensajeExito("Llegada registrada con éxito. El paciente ingresó a la sala de espera.");
      void cargarSalaEspera();
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setRegistrandoLlegada(false);
    }
  };

  // Marcar ausencia individual
  const handleMarcarAusente = async (idTurno: string) => {
    if (!confirm("¿Confirmar ausencia para este turno? Esta acción no se puede deshacer.")) return;
    setError(null);
    try {
      await recepcionApi.registrarAusente(idTurno);
      setMensajeExito("Turno marcado como AUSENTE.");
      void cargarSalaEspera();
    } catch (err) {
      setError(mensajeDeError(err));
    }
  };

  // Resolver solicitud de cancelación
  const handleResolverSolicitud = async (idSolicitud: string, aprobada: boolean) => {
    let motivo: string | undefined = undefined;
    if (!aprobada) {
      const m = prompt("Ingresá el motivo del rechazo:");
      if (!m) return;
      motivo = m;
    }
    setError(null);
    try {
      await recepcionApi.resolverSolicitudCancelacion(idSolicitud, {
        aprobada,
        motivo_resolucion: motivo,
      });
      setMensajeExito(
        aprobada
          ? "Solicitud aprobada: el turno fue cancelado y el horario liberado."
          : "Solicitud rechazada: el turno continúa confirmado."
      );
      void cargarSolicitudes();
    } catch (err) {
      setError(mensajeDeError(err));
    }
  };

  // Clasificar usuario rojo
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

  // Levantar restricción
  const handleLevantarRestriccion = async () => {
    if (!idRestriccionActiva) return;
    if (!confirm("¿Confirmás levantar la restricción de Usuario rojo para este paciente?")) return;
    setError(null);
    try {
      await recepcionApi.levantarRestriccion(idRestriccionActiva);
      setEsUsuarioRojo(false);
      setIdRestriccionActiva(null);
      setMensajeExito("Restricción levantada exitosamente. El paciente puede operar con normalidad.");
    } catch (err) {
      setError(mensajeDeError(err));
    }
  };

  // Cierre de jornada
  const handleCierreJornada = async () => {
    if (!confirm("¿Deseás ejecutar el cierre de jornada? Todos los turnos pasados del día sin llegada serán marcados como AUSENTE.")) return;
    setEjecutandoCierre(true);
    setError(null);
    setResultadoCierre(null);
    try {
      const res = await recepcionApi.cerrarJornada();
      setResultadoCierre(
        `Cierre completado: se marcaron ${res.turnos_marcados_ausentes} turnos como ausentes.`
      );
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setEjecutandoCierre(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <AppNavbar />

      <main className="mx-auto max-w-6xl space-y-6 px-6 py-10">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">
            Módulo de Recepción
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Control de llegadas, sala de espera con prioridad inteligente, gestión de pacientes y cierre de jornada.
          </p>
        </div>

        {error && <Alerta tipo="error">{error}</Alerta>}
        {mensajeExito && <Alerta tipo="exito">{mensajeExito}</Alerta>}

        {/* Pestañas */}
        <div className="flex border-b border-slate-200 space-x-6">
          <button
            type="button"
            onClick={() => setPestaña("espera")}
            className={`pb-3 text-sm font-semibold border-b-2 transition ${
              pestaña === "espera"
                ? "border-brand-600 text-brand-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            Sala de Espera ({salaEspera.length})
          </button>
          <button
            type="button"
            onClick={() => setPestaña("pacientes")}
            className={`pb-3 text-sm font-semibold border-b-2 transition ${
              pestaña === "pacientes"
                ? "border-brand-600 text-brand-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            Pacientes & DNI
          </button>
          <button
            type="button"
            onClick={() => setPestaña("solicitudes")}
            className={`pb-3 text-sm font-semibold border-b-2 transition ${
              pestaña === "solicitudes"
                ? "border-brand-600 text-brand-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            Cancelaciones Rápidas ({solicitudes.length})
          </button>
          <button
            type="button"
            onClick={() => setPestaña("cierre")}
            className={`pb-3 text-sm font-semibold border-b-2 transition ${
              pestaña === "cierre"
                ? "border-brand-600 text-brand-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            Cierre de Jornada
          </button>
        </div>

        {/* PESTAÑA: SALA DE ESPERA (RF-12) */}
        {pestaña === "espera" && (
          <div className="space-y-6">
            {/* Formulario rápido de llegada */}
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-base font-bold text-slate-900 mb-2">
                Registrar Llegada de Paciente
              </h2>
              <form onSubmit={handleRegistrarLlegada} className="flex flex-wrap items-center gap-3">
                <input
                  type="text"
                  placeholder="ID de Turno (UUID)..."
                  value={idTurnoLlegada}
                  onChange={(e) => setIdTurnoLlegada(e.target.value)}
                  className="rounded-xl border border-slate-300 px-3 py-2 text-sm text-slate-900 w-full sm:w-80 focus:border-brand-500 focus:ring-brand-500"
                  required
                />
                <Boton
                  type="submit"
                  className="w-auto"
                  cargando={registrandoLlegada}
                >
                  Registrar Llegada
                </Boton>
              </form>
            </div>

            {/* Tabla con Orden de Atención RF-12 */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-slate-900">
                    Pacientes en Espera (Orden de Prioridad)
                  </h2>
                  <p className="text-xs text-slate-500">
                    Ordenados según el algoritmo de prioridad (RF-12): pacientes puntuales en tolerancia de 10 min por horario de turno; pacientes demorados por hora de llegada.
                  </p>
                </div>
                <Boton
                  variante="secundario"
                  className="w-auto text-xs py-1.5 px-3"
                  onClick={cargarSalaEspera}
                  disabled={cargandoEspera}
                >
                  Actualizar
                </Boton>
              </div>

              {cargandoEspera ? (
                <div className="py-8 flex justify-center">
                  <Cargando texto="Actualizando sala de espera..." />
                </div>
              ) : salaEspera.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
                  No hay pacientes en sala de espera en este momento.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm text-slate-600">
                    <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase font-bold text-slate-700">
                      <tr>
                        <th className="py-3 px-4">Prioridad</th>
                        <th className="py-3 px-4">Paciente</th>
                        <th className="py-3 px-4">Profesional</th>
                        <th className="py-3 px-4">Turno Programado</th>
                        <th className="py-3 px-4">Llegada</th>
                        <th className="py-3 px-4">Condición</th>
                        <th className="py-3 px-4 text-right">Acción</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {salaEspera.map((t) => (
                        <tr key={t.id_turno} className="hover:bg-slate-50/50">
                          <td className="py-3 px-4">
                            <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-brand-100 text-brand-700 font-bold text-xs">
                              {t.orden_prioridad}
                            </span>
                          </td>
                          <td className="py-3 px-4 font-semibold text-slate-900">
                            {t.paciente_nombre} {t.paciente_apellido}
                            <span className="block text-xs font-normal text-slate-500">
                              DNI {t.paciente_dni}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            Dr(a). {t.medico_nombre} {t.medico_apellido}
                            <span className="block text-xs text-slate-500">
                              {t.especialidad_nombre}
                            </span>
                          </td>
                          <td className="py-3 px-4 font-medium text-slate-900">
                            {formatHora(t.fecha_hora)} hs
                          </td>
                          <td className="py-3 px-4 text-slate-600">
                            {formatHora(t.fecha_hora_llegada)} hs
                          </td>
                          <td className="py-3 px-4">
                            {t.esta_en_tolerancia ? (
                              <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                En tolerancia
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                                Demorado (+10m)
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-4 text-right">
                            <Boton
                              variante="peligro"
                              className="w-auto text-xs py-1 px-2.5"
                              onClick={() => handleMarcarAusente(t.id_turno)}
                            >
                              Ausente
                            </Boton>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* PESTAÑA: PACIENTES & DNI */}
        {pestaña === "pacientes" && (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <form onSubmit={handleBuscarPaciente} className="flex items-center gap-3 w-full sm:w-96">
                <input
                  type="text"
                  placeholder="Ingresá DNI del paciente..."
                  value={dniBusqueda}
                  onChange={(e) => setDniBusqueda(e.target.value)}
                  className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm text-slate-900 w-full focus:border-brand-500 focus:ring-brand-500"
                />
                <Boton type="submit" className="w-auto" cargando={buscandoPaciente}>
                  Buscar
                </Boton>
              </form>

              <Boton
                variante="secundario"
                className="w-auto"
                onClick={() => setMostrarAlta(true)}
              >
                + Alta de Paciente
              </Boton>
            </div>

            {/* Ficha de paciente encontrado */}
            {pacienteSeleccionado && (
              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-5">
                <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 pb-4">
                  <div>
                    <h2 className="text-xl font-bold text-slate-900">
                      {pacienteSeleccionado.nombre} {pacienteSeleccionado.apellido}
                    </h2>
                    <p className="text-sm text-slate-500">
                      DNI: {pacienteSeleccionado.dni} · Correo: {pacienteSeleccionado.email}
                    </p>
                  </div>

                  <div className="flex items-center gap-3">
                    {esUsuarioRojo ? (
                      <div className="flex items-center gap-2">
                        <span className="px-3 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300">
                          Usuario Rojo Activo
                        </span>
                        <Boton
                          variante="secundario"
                          className="w-auto text-xs py-1 px-3 border-emerald-300 text-emerald-700 hover:bg-emerald-50"
                          onClick={handleLevantarRestriccion}
                        >
                          Levantar Sanción
                        </Boton>
                      </div>
                    ) : (
                      <Boton
                        variante="peligro"
                        className="w-auto text-xs py-1 px-3"
                        onClick={() => setMostrarModalRojo(true)}
                      >
                        Sancionar (Usuario Rojo)
                      </Boton>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-xs font-semibold text-slate-400 block">DNI</span>
                    <span className="font-medium text-slate-900">{pacienteSeleccionado.dni}</span>
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-slate-400 block">Teléfono</span>
                    <span className="font-medium text-slate-900">{pacienteSeleccionado.telefono || "No registrado"}</span>
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-slate-400 block">Email Verificado</span>
                    <span className="font-medium text-slate-900">
                      {pacienteSeleccionado.email_verificado ? "Sí" : "Pendiente"}
                    </span>
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-slate-400 block">Estado de Cuenta</span>
                    <span className="font-medium text-slate-900">
                      {pacienteSeleccionado.habilitado ? "Habilitado" : "Deshabilitado"}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Modal Alta de Paciente */}
            {mostrarAlta && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
                <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl border border-slate-200 space-y-4">
                  <h3 className="text-lg font-bold text-slate-900">
                    Dar de Alta Paciente en Recepción
                  </h3>
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
                      <label className="block text-xs font-semibold text-slate-700">Correo Electrónico (opcional)</label>
                      <input
                        type="email"
                        value={nuevoEmail}
                        onChange={(e) => setNuevoEmail(e.target.value)}
                        className="mt-1 block w-full rounded-lg border border-slate-300 p-2 text-sm"
                      />
                    </div>

                    <div className="flex justify-end gap-2 pt-3">
                      <Boton
                        type="button"
                        variante="secundario"
                        className="w-auto text-xs"
                        onClick={() => setMostrarAlta(false)}
                      >
                        Cancelar
                      </Boton>
                      <Boton
                        type="submit"
                        className="w-auto text-xs"
                        cargando={guardandoPaciente}
                      >
                        Crear Paciente
                      </Boton>
                    </div>
                  </form>
                </div>
              </div>
            )}

            {/* Modal Usuario Rojo */}
            {mostrarModalRojo && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
                <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl border border-slate-200 space-y-4">
                  <h3 className="text-lg font-bold text-slate-900">
                    Sancionar Paciente (Usuario Rojo)
                  </h3>
                  <p className="text-xs text-slate-600">
                    La restricción bloquea la reserva web por 30 días pero permite reservas presenciales o telefónicas.
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
                      <Boton
                        type="button"
                        variante="secundario"
                        className="w-auto text-xs"
                        onClick={() => setMostrarModalRojo(false)}
                      >
                        Cancelar
                      </Boton>
                      <Boton
                        type="submit"
                        variante="peligro"
                        className="w-auto text-xs"
                        cargando={guardandoRojo}
                      >
                        Aplicar Sanción
                      </Boton>
                    </div>
                  </form>
                </div>
              </div>
            )}
          </div>
        )}

        {/* PESTAÑA: CANCELACIONES RÁPIDAS (RF-09) */}
        {pestaña === "solicitudes" && (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-slate-900">
                  Solicitudes de Cancelación Rápida (&lt;24 hs)
                </h2>
                <p className="text-xs text-slate-500">
                  Revisión y resolución de cancelaciones solicitadas con poca anticipación.
                </p>
              </div>
              <Boton
                variante="secundario"
                className="w-auto text-xs py-1.5 px-3"
                onClick={cargarSolicitudes}
                disabled={cargandoSolicitudes}
              >
                Actualizar
              </Boton>
            </div>

            {cargandoSolicitudes ? (
              <div className="py-8 flex justify-center">
                <Cargando texto="Cargando solicitudes..." />
              </div>
            ) : solicitudes.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
                No hay solicitudes de cancelación rápida pendientes.
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {solicitudes.map((s) => (
                  <div key={s.id_solicitud} className="py-4 flex flex-wrap items-center justify-between gap-4">
                    <div className="space-y-1">
                      <p className="font-semibold text-slate-900">
                        {s.paciente_nombre} {s.paciente_apellido}{" "}
                        <span className="text-xs text-slate-500 font-normal">
                          (DNI {s.paciente_dni})
                        </span>
                      </p>
                      <p className="text-xs text-slate-600">
                        {s.especialidad_nombre} · Dr(a). {s.medico_nombre} {s.medico_apellido} · Fecha: {s.turno_fecha_hora ? formatFechaHora(s.turno_fecha_hora) : "—"}
                      </p>
                      <p className="text-xs text-slate-800 bg-slate-50 p-2 rounded-lg border border-slate-200">
                        <span className="font-semibold">Motivo:</span> {s.motivo_paciente}
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <Boton
                        className="w-auto text-xs py-1.5 px-3 bg-emerald-600 hover:bg-emerald-700"
                        onClick={() => handleResolverSolicitud(s.id_solicitud, true)}
                      >
                        Aprobar
                      </Boton>
                      <Boton
                        variante="peligro"
                        className="w-auto text-xs py-1.5 px-3"
                        onClick={() => handleResolverSolicitud(s.id_solicitud, false)}
                      >
                        Rechazar
                      </Boton>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* PESTAÑA: CIERRE DE JORNADA (RF-15) */}
        {pestaña === "cierre" && (
          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm space-y-5 max-w-xl mx-auto text-center">
            <h2 className="text-xl font-bold text-slate-900">
              Cierre de Jornada de Atención
            </h2>
            <p className="text-sm text-slate-600">
              Al finalizar el día laboral, esta acción busca todos los turnos del día que quedaron en estado reservado y que no registraron su llegada, marcándolos automáticamente como <span className="font-semibold text-rose-600">AUSENTE</span>.
            </p>

            {resultadoCierre && <Alerta tipo="exito">{resultadoCierre}</Alerta>}

            <div className="pt-4 flex justify-center">
              <Boton
                variante="peligro"
                className="w-auto shadow-md"
                onClick={handleCierreJornada}
                cargando={ejecutandoCierre}
              >
                Ejecutar Cierre de Jornada
              </Boton>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
