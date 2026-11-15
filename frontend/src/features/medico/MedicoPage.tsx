import { useEffect, useState } from "react";

import { AppNavbar } from "@/components/layout/AppNavbar";
import { Alerta } from "@/components/ui/Alerta";
import { Boton } from "@/components/ui/Boton";
import { Cargando } from "@/components/ui/Cargando";
import { formatFechaHora, formatHora } from "@/lib/dates";
import { mensajeDeError } from "@/lib/problem";
import type { TurnoResponse } from "@/features/turnos/types";
import { type NotaSeguimientoOut, medicoApi } from "./api";

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

  // Cargar notas al seleccionar un turno/paciente
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

  // Crear nueva nota de seguimiento
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

  // Modificar nota existente
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
  const otrosTurnos = turnos.filter((t) => t.estado !== "EN_ESPERA");

  return (
    <div className="min-h-screen bg-slate-50">
      <AppNavbar />

      <main className="mx-auto max-w-6xl space-y-6 px-6 py-10">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">
            Consultorio Médico
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Gestión de turnos de la jornada, registro de atención médica (RF-13) y notas confidenciales de seguimiento (RF-14).
          </p>
        </div>

        {error && <Alerta tipo="error">{error}</Alerta>}
        {mensajeExito && <Alerta tipo="exito">{mensajeExito}</Alerta>}

        <div className="grid gap-6 md:grid-cols-3">
          {/* Columna Izquierda: Lista de Turnos */}
          <div className="space-y-4 md:col-span-1">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-slate-900">
                Turnos de la Jornada
              </h2>
              <Boton
                variante="secundario"
                className="w-auto text-xs py-1 px-2.5"
                onClick={cargarTurnos}
                disabled={cargandoTurnos}
              >
                Actualizar
              </Boton>
            </div>

            {cargandoTurnos ? (
              <Cargando texto="Cargando agenda..." />
            ) : turnos.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-slate-500">
                No hay turnos asignados en este momento.
              </div>
            ) : (
              <div className="space-y-3">
                {enEspera.length > 0 && (
                  <div className="space-y-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-amber-600">
                      En Sala de Espera ({enEspera.length})
                    </span>
                    {enEspera.map((t) => (
                      <button
                        key={t.id_turno}
                        type="button"
                        onClick={() => setTurnoSeleccionado(t)}
                        className={`w-full text-left p-3.5 rounded-xl border transition shadow-sm ${
                          turnoSeleccionado?.id_turno === t.id_turno
                            ? "bg-amber-50/80 border-amber-400 ring-2 ring-amber-300"
                            : "bg-white border-amber-200 hover:border-amber-300"
                        }`}
                      >
                        <div className="flex justify-between items-start">
                          <span className="font-bold text-slate-900 text-sm">
                            {t.paciente_nombre} {t.paciente_apellido}
                          </span>
                          <span className="text-xs px-2 py-0.5 rounded-full font-semibold bg-amber-100 text-amber-800">
                            {formatHora(t.fecha_hora)} hs
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 mt-1">
                          Llegada: {t.fecha_hora_llegada ? formatHora(t.fecha_hora_llegada) + " hs" : "—"}
                        </p>
                      </button>
                    ))}
                  </div>
                )}

                <div className="space-y-2 pt-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Otros Turnos ({otrosTurnos.length})
                  </span>
                  {otrosTurnos.map((t) => (
                    <button
                      key={t.id_turno}
                      type="button"
                      onClick={() => setTurnoSeleccionado(t)}
                      className={`w-full text-left p-3.5 rounded-xl border transition shadow-sm ${
                        turnoSeleccionado?.id_turno === t.id_turno
                          ? "bg-brand-50 border-brand-400 ring-2 ring-brand-300"
                          : "bg-white border-slate-200 hover:border-slate-300"
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <span className="font-semibold text-slate-800 text-sm">
                          {t.paciente_nombre} {t.paciente_apellido}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-slate-100 text-slate-600">
                          {t.estado}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-1">
                        {formatFechaHora(t.fecha_hora)}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Columna Derecha: Atención y Notas de Seguimiento */}
          <div className="space-y-6 md:col-span-2">
            {turnoSeleccionado ? (
              <>
                {/* Cabecera del Turno Seleccionado */}
                <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
                    <div>
                      <span className="text-xs font-bold uppercase tracking-wider text-brand-600">
                        {turnoSeleccionado.especialidad_nombre}
                      </span>
                      <h2 className="text-xl font-bold text-slate-900 mt-0.5">
                        {turnoSeleccionado.paciente_nombre} {turnoSeleccionado.paciente_apellido}
                      </h2>
                      <p className="text-xs text-slate-500">
                        DNI: {turnoSeleccionado.paciente_dni} · Turno programado: {formatFechaHora(turnoSeleccionado.fecha_hora)}
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="px-3 py-1 rounded-full text-xs font-bold border bg-slate-100 text-slate-800">
                        {turnoSeleccionado.estado}
                      </span>

                      {turnoSeleccionado.estado === "EN_ESPERA" && (
                        <Boton
                          className="w-auto bg-emerald-600 hover:bg-emerald-700 text-xs py-2 px-4 shadow"
                          onClick={handleAtender}
                          cargando={atendiendo}
                        >
                          Marcar como Atendido
                        </Boton>
                      )}
                    </div>
                  </div>

                  {turnoSeleccionado.estado === "RESERVADO" && (
                    <div className="rounded-xl bg-blue-50 p-3 text-xs text-blue-800 border border-blue-200">
                      El paciente aún no anunció su llegada en recepción. El turno pasará a EN_ESPERA al registrarse su llegada.
                    </div>
                  )}

                  {turnoSeleccionado.estado === "ATENDIDO" && (
                    <div className="rounded-xl bg-emerald-50 p-3 text-xs text-emerald-800 border border-emerald-200 font-medium">
                      ✓ Atención médica completada y registrada en auditoría.
                    </div>
                  )}
                </div>

                {/* Notas de Seguimiento (RF-14) */}
                <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-bold text-slate-900">
                        Anotaciones Médicas de Seguimiento
                      </h3>
                      <p className="text-xs text-slate-500">
                        Historial clínico confidencial del paciente. Solo accesible para profesionales médicos.
                      </p>
                    </div>
                  </div>

                  {/* Formulario Nueva Nota */}
                  <form onSubmit={handleCrearNota} className="space-y-3">
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-600">
                      Agregar nueva anotación
                    </label>
                    <textarea
                      rows={3}
                      required
                      value={nuevaNota}
                      onChange={(e) => setNuevaNota(e.target.value)}
                      placeholder="Registrá observaciones sobre la evolución, medicación o indicaciones para controles futuros..."
                      className="block w-full rounded-xl border border-slate-300 p-3 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:ring-brand-500"
                    />
                    <div className="flex justify-end">
                      <Boton
                        type="submit"
                        className="w-auto text-xs py-2 px-4"
                        cargando={guardandoNota}
                      >
                        Guardar Anotación
                      </Boton>
                    </div>
                  </form>

                  {/* Lista de Notas Anteriores */}
                  <div className="border-t border-slate-100 pt-4 space-y-3">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                      Historial de Notas ({notas.length})
                    </h4>

                    {cargandoNotas ? (
                      <Cargando texto="Cargando historial de notas..." />
                    ) : notas.length === 0 ? (
                      <p className="text-xs text-slate-500 italic py-2">
                        El paciente aún no cuenta con anotaciones previas registradas.
                      </p>
                    ) : (
                      <div className="space-y-3">
                        {notas.map((n) => (
                          <div
                            key={n.id_nota}
                            className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 space-y-2 text-sm"
                          >
                            <div className="flex items-center justify-between text-xs text-slate-500">
                              <span>
                                Dr(a). {n.medico_nombre} {n.medico_apellido} · {formatFechaHora(n.fecha_creacion)}
                              </span>
                              <button
                                type="button"
                                onClick={() => {
                                  setNotaEnEdicion(n);
                                  setContenidoEdicion(n.contenido);
                                }}
                                className="font-medium text-brand-600 hover:underline"
                              >
                                Editar
                              </button>
                            </div>
                            <p className="text-slate-800 text-sm whitespace-pre-wrap">
                              {n.contenido}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Modal Edición de Nota */}
                {notaEnEdicion && (
                  <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
                    <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl border border-slate-200 space-y-4">
                      <h3 className="text-lg font-bold text-slate-900">
                        Modificar Anotación Médica
                      </h3>
                      <form onSubmit={handleGuardarEdicion} className="space-y-3">
                        <textarea
                          rows={4}
                          required
                          value={contenidoEdicion}
                          onChange={(e) => setContenidoEdicion(e.target.value)}
                          className="block w-full rounded-xl border border-slate-300 p-3 text-sm"
                        />
                        <div className="flex justify-end gap-2 pt-2">
                          <Boton
                            type="button"
                            variante="secundario"
                            className="w-auto text-xs"
                            onClick={() => setNotaEnEdicion(null)}
                          >
                            Cancelar
                          </Boton>
                          <Boton type="submit" className="w-auto text-xs">
                            Actualizar Anotación
                          </Boton>
                        </div>
                      </form>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center text-slate-500">
                Seleccioná un turno de la lista para visualizar los detalles del paciente y sus notas.
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
