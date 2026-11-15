import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { AppNavbar } from "@/components/layout/AppNavbar";
import { Alerta } from "@/components/ui/Alerta";
import { Boton } from "@/components/ui/Boton";
import { Cargando } from "@/components/ui/Cargando";
import { formatFecha, formatHora } from "@/lib/dates";
import { mensajeDeError } from "@/lib/problem";
import { turnosApi } from "./api";
import type { Especialidad, Medico, SlotDisponibilidad } from "./types";

export function ReservarTurnoPage() {
  const navigate = useNavigate();

  const [especialidades, setEspecialidades] = useState<Especialidad[]>([]);
  const [medicos, setMedicos] = useState<Medico[]>([]);
  const [slots, setSlots] = useState<SlotDisponibilidad[]>([]);

  const [idEspecialidad, setIdEspecialidad] = useState<string>("");
  const [idMedico, setIdMedico] = useState<string>("");
  const [fechaSeleccionada, setFechaSeleccionada] = useState<string>("");
  const [slotSeleccionado, setSlotSeleccionado] = useState<SlotDisponibilidad | null>(null);

  const [cargandoInicial, setCargandoInicial] = useState(true);
  const [cargandoMedicos, setCargandoMedicos] = useState(false);
  const [cargandoSlots, setCargandoSlots] = useState(false);
  const [reservando, setReservando] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [exito, setExito] = useState(false);

  // Cargar especialidades iniciales
  useEffect(() => {
    async function inicializar() {
      setCargandoInicial(true);
      setError(null);
      try {
        const esp = await turnosApi.obtenerEspecialidades();
        setEspecialidades(esp);
      } catch (err) {
        setError(mensajeDeError(err));
      } finally {
        setCargandoInicial(false);
      }
    }
    void inicializar();
  }, []);

  // Cargar médicos al cambiar especialidad
  useEffect(() => {
    if (!idEspecialidad) {
      setMedicos([]);
      setIdMedico("");
      return;
    }
    async function cargarMedicos() {
      setCargandoMedicos(true);
      setIdMedico("");
      setSlotSeleccionado(null);
      setSlots([]);
      try {
        const med = await turnosApi.obtenerMedicos(idEspecialidad);
        setMedicos(med.filter((m) => m.activo));
      } catch (err) {
        setError(mensajeDeError(err));
      } finally {
        setCargandoMedicos(false);
      }
    }
    void cargarMedicos();
  }, [idEspecialidad]);

  // Cargar disponibilidad al seleccionar médico y fecha
  useEffect(() => {
    if (!idMedico || !fechaSeleccionada) {
      setSlots([]);
      setSlotSeleccionado(null);
      return;
    }
        async function cargarDisponibilidad() {
      setCargandoSlots(true);
      setSlotSeleccionado(null);
      setError(null);
      try {
        const res = await turnosApi.obtenerDisponibilidad(idMedico, fechaSeleccionada);
        setSlots(res.slots);
      } catch (err) {
        setError(mensajeDeError(err));
      } finally {
        setCargandoSlots(false);
      }
    }
    void cargarDisponibilidad();
  }, [idMedico, fechaSeleccionada]);

  const handleReservar = async () => {
    if (!idMedico || !slotSeleccionado) return;
    setReservando(true);
    setError(null);
    try {
      await turnosApi.reservarWeb({
        id_medico: idMedico,
        fecha_hora: slotSeleccionado.fecha_hora,
      });
      setExito(true);
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setReservando(false);
    }
  };

  const medicoSeleccionado = medicos.find((m) => m.id_medico === idMedico);
  const especialidadSeleccionada = especialidades.find((e) => e.id_especialidad === idEspecialidad);

    // Fechas disponibles: mañana hasta +14 días, en el día local de Buenos Aires.
  const formatoDia = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Argentina/Buenos_Aires",
  });
  const fechasDisponibles = Array.from({ length: 14 }, (_, i) =>
    formatoDia.format(new Date(Date.now() + (i + 1) * 24 * 3600 * 1000)),
  );

  if (cargandoInicial) {
    return (
      <div className="min-h-screen bg-slate-50">
        <AppNavbar />
        <div className="py-20 flex justify-center">
          <Cargando texto="Cargando catálogo médico..." />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <AppNavbar />

      <main className="mx-auto max-w-4xl space-y-6 px-6 py-10">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">
            Reservar Turno Médico
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Elegí la especialidad, el profesional y el horario de tu preferencia.
          </p>
        </div>

        {error && <Alerta tipo="error">{error}</Alerta>}

        {exito ? (
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-8 text-center space-y-4">
            <span className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-emerald-600 text-white text-2xl font-bold">
              ✓
            </span>
            <h2 className="text-2xl font-bold text-emerald-950">
              ¡Turno reservado con éxito!
            </h2>
            <p className="text-sm text-emerald-800 max-w-md mx-auto">
              Te enviamos un correo electrónico con los detalles del turno. Te recordamos presentarte con 10 minutos de anticipación.
            </p>
            <div className="pt-2 flex justify-center gap-4">
              <Link to="/turnos">
                <Boton className="w-auto">Ver mis turnos</Boton>
              </Link>
              <Boton
                variante="secundario"
                className="w-auto"
                onClick={() => {
                  setExito(false);
                  setSlotSeleccionado(null);
                  setIdMedico("");
                  setIdEspecialidad("");
                  setFechaSeleccionada("");
                }}
              >
                Reservar otro turno
              </Boton>
            </div>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-3">
            {/* Formulario de selección */}
            <div className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm md:col-span-2">
              {/* Paso 1: Especialidad */}
              <div>
                <label
                  htmlFor="especialidad"
                  className="block text-sm font-semibold text-slate-900"
                >
                  1. Especialidad Médica
                </label>
                <select
                  id="especialidad"
                  value={idEspecialidad}
                  onChange={(e) => setIdEspecialidad(e.target.value)}
                  className="mt-2 block w-full rounded-xl border border-slate-300 p-3 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:ring-brand-500"
                >
                  <option value="">Seleccioná una especialidad...</option>
                  {especialidades.map((esp) => (
                    <option key={esp.id_especialidad} value={esp.id_especialidad}>
                      {esp.nombre}
                    </option>
                  ))}
                </select>
              </div>

              {/* Paso 2: Profesional */}
              {idEspecialidad && (
                <div>
                  <label
                    htmlFor="medico"
                    className="block text-sm font-semibold text-slate-900"
                  >
                    2. Profesional
                  </label>
                  {cargandoMedicos ? (
                    <p className="text-sm text-slate-500 mt-2">Cargando médicos...</p>
                  ) : medicos.length === 0 ? (
                    <p className="text-sm text-slate-500 mt-2">
                      No hay profesionales disponibles para esta especialidad.
                    </p>
                  ) : (
                    <select
                      id="medico"
                      value={idMedico}
                      onChange={(e) => setIdMedico(e.target.value)}
                      className="mt-2 block w-full rounded-xl border border-slate-300 p-3 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:ring-brand-500"
                    >
                      <option value="">Seleccioná un profesional...</option>
                      {medicos.map((m) => (
                        <option key={m.id_medico} value={m.id_medico}>
                          Dr(a). {m.nombre} {m.apellido} {m.matricula ? `(${m.matricula})` : ""}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              )}

              {/* Paso 3: Fecha */}
              {idMedico && (
                <div>
                  <label
                    htmlFor="fecha"
                    className="block text-sm font-semibold text-slate-900"
                  >
                    3. Fecha de Atención
                  </label>
                  <select
                    id="fecha"
                    value={fechaSeleccionada}
                    onChange={(e) => setFechaSeleccionada(e.target.value)}
                    className="mt-2 block w-full rounded-xl border border-slate-300 p-3 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:ring-brand-500"
                  >
                    <option value="">Seleccioná una fecha...</option>
                    {fechasDisponibles.map((f) => (
                      <option key={f} value={f}>
                        {formatFecha(`${f}T12:00:00-03:00`)}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Paso 4: Horarios */}
              {idMedico && fechaSeleccionada && (
                <div>
                  <label className="block text-sm font-semibold text-slate-900 mb-2">
                    4. Horarios Disponibles
                  </label>
                  {cargandoSlots ? (
                    <Cargando texto="Consultando disponibilidad..." />
                  ) : slots.length === 0 ? (
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600 text-center">
                      No hay horarios libres para esta fecha. Probá seleccionando otro día.
                    </div>
                  ) : (
                    <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                      {slots.map((slot) => {
                        const esSeleccionado =
                          slotSeleccionado?.fecha_hora === slot.fecha_hora;
                        return (
                          <button
                            key={slot.fecha_hora}
                            type="button"
                            onClick={() => setSlotSeleccionado(slot)}
                            className={`py-2 px-3 text-sm font-semibold rounded-lg border transition ${
                              esSeleccionado
                                ? "bg-brand-600 text-white border-brand-600 shadow"
                                : "bg-white text-slate-700 border-slate-200 hover:border-brand-400 hover:bg-brand-50/50"
                            }`}
                          >
                            {formatHora(slot.fecha_hora)}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Resumen de reserva */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm flex flex-col justify-between h-fit space-y-4">
              <div>
                <h3 className="text-base font-bold text-slate-900 border-b border-slate-100 pb-3">
                  Resumen del Turno
                </h3>
                <dl className="mt-3 space-y-3 text-sm text-slate-600">
                  <div>
                    <dt className="font-medium text-slate-500">Especialidad</dt>
                    <dd className="font-semibold text-slate-900">
                      {especialidadSeleccionada?.nombre || "—"}
                    </dd>
                  </div>
                  <div>
                    <dt className="font-medium text-slate-500">Profesional</dt>
                    <dd className="font-semibold text-slate-900">
                      {medicoSeleccionado
                        ? `Dr(a). ${medicoSeleccionado.nombre} ${medicoSeleccionado.apellido}`
                        : "—"}
                    </dd>
                  </div>
                  <div>
                    <dt className="font-medium text-slate-500">Fecha y Hora</dt>
                    <dd className="font-semibold text-slate-900">
                      {slotSeleccionado
                        ? formatFecha(slotSeleccionado.fecha_hora) + " " + formatHora(slotSeleccionado.fecha_hora) + " hs"
                        : "—"}
                    </dd>
                  </div>
                </dl>
              </div>

              <div className="pt-4 border-t border-slate-100 space-y-2">
                <Boton
                  disabled={!slotSeleccionado || reservando}
                  cargando={reservando}
                  onClick={handleReservar}
                >
                  Confirmar Reserva
                </Boton>
                <Boton
                  variante="secundario"
                  onClick={() => navigate("/turnos")}
                  disabled={reservando}
                >
                  Cancelar
                </Boton>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
