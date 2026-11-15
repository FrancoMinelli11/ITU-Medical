import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Alerta } from "@/components/ui/Alerta";
import { Icon } from "@/components/ui/Icon";
import { Skeleton } from "@/components/ui/Skeleton";
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

  // Cargar catálogo de especialidades
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

  // Cargar médicos de la especialidad
  useEffect(() => {
    if (!idEspecialidad) {
      setMedicos([]);
      setIdMedico("");
      setFechaSeleccionada("");
      setSlotSeleccionado(null);
      setSlots([]);
      return;
    }
    async function cargarMedicos() {
      setCargandoMedicos(true);
      setIdMedico("");
      setFechaSeleccionada("");
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

  // Fechas disponibles: mañana hasta +14 días en Buenos Aires
  const formatoDia = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Argentina/Buenos_Aires",
  });
  const fechasDisponibles = Array.from({ length: 14 }, (_, i) =>
    formatoDia.format(new Date(Date.now() + (i + 1) * 24 * 3600 * 1000)),
  );

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
  const especialidadSeleccionada = especialidades.find(
    (e) => e.id_especialidad === idEspecialidad,
  );

  return (
    <>
      <div className="page-title">
        <div>
          <p>ITU MEDICAL</p>
          <h1>Reservar Turno Médico</h1>
          <span>Elegí la especialidad, el profesional y el horario de tu preferencia.</span>
        </div>
      </div>

      {error && <Alerta tipo="error">{error}</Alerta>}

      {cargandoInicial ? (
        <div className="space-y-4 py-4">
          <Skeleton className="h-12 w-full rounded-xl" />
          <Skeleton className="h-48 w-full rounded-2xl" />
        </div>
      ) : exito ? (
        <section className="panel p-8 text-center space-y-4 max-w-xl mx-auto">
          <div className="mx-auto w-12 h-12 rounded-full bg-emerald-100 text-emerald-700 grid place-items-center">
            <Icon name="check" size={24} />
          </div>
          <h2 className="text-xl font-bold text-slate-900">¡Turno reservado con éxito!</h2>
          <p className="text-sm text-slate-600">
            Tu reserva fue confirmada. Podés revisarla y gestionarla en cualquier momento desde tu listado de próximos turnos.
          </p>
          <div className="pt-2 flex justify-center gap-3">
            <Link to="/turnos" className="primary">
              Ver mis turnos
            </Link>
          </div>
        </section>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Formulario de Selección */}
          <div className="lg:col-span-2 space-y-6">
            <section className="panel p-6 space-y-5">
              {/* Paso 1: Especialidad */}
              <div>
                <label
                  htmlFor="especialidad"
                  className="block text-sm font-semibold text-slate-900 mb-2"
                >
                  1. Especialidad médica
                </label>
                <select
                  id="especialidad"
                  value={idEspecialidad}
                  onChange={(e) => setIdEspecialidad(e.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-white p-3 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
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
                    className="block text-sm font-semibold text-slate-900 mb-2"
                  >
                    2. Profesional médico
                  </label>
                  {cargandoMedicos ? (
                    <Skeleton className="h-11 w-full rounded-xl" />
                  ) : medicos.length === 0 ? (
                    <p className="text-sm text-slate-500 italic p-3 rounded-xl bg-slate-50 border border-slate-200">
                      No hay profesionales disponibles para esta especialidad.
                    </p>
                  ) : (
                    <select
                      id="medico"
                      value={idMedico}
                      onChange={(e) => setIdMedico(e.target.value)}
                      className="w-full rounded-xl border border-slate-300 bg-white p-3 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                    >
                      <option value="">Seleccioná un profesional...</option>
                      {medicos.map((m) => (
                        <option key={m.id_medico} value={m.id_medico}>
                          Dr(a). {m.nombre} {m.apellido} {m.matricula ? `· Matrícula: ${m.matricula}` : ""}
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
                    className="block text-sm font-semibold text-slate-900 mb-2"
                  >
                    3. Fecha de atención
                  </label>
                  <select
                    id="fecha"
                    value={fechaSeleccionada}
                    onChange={(e) => setFechaSeleccionada(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 bg-white p-3 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
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
                  <h4 className="time-title block text-sm font-semibold text-slate-900 mb-2">
                    Horarios disponibles
                  </h4>

                  {cargandoSlots ? (
                    <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 py-2">
                      {Array.from({ length: 8 }).map((_, i) => (
                        <Skeleton key={i} className="h-10 rounded-xl" />
                      ))}
                    </div>
                  ) : slots.length === 0 ? (
                    <div className="py-6 text-center text-sm text-slate-500 rounded-xl bg-slate-50 border border-slate-200">
                      No hay horarios libres para esta fecha. Probá seleccionando otro día.
                    </div>
                  ) : (
                    <div className="time-grid">
                      {slots.map((s) => {
                        const esSeleccionado = slotSeleccionado?.fecha_hora === s.fecha_hora;

                        return (
                          <button
                            key={s.fecha_hora}
                            type="button"
                            className={esSeleccionado ? "selected" : ""}
                            onClick={() => setSlotSeleccionado(s)}
                          >
                            {formatHora(s.fecha_hora)} hs
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </section>
          </div>

          {/* Resumen del Turno */}
          <div className="lg:col-span-1">
            <section className="panel p-6 flex flex-col justify-between h-fit space-y-5 sticky top-24">
              <div>
                <h3 className="text-base font-bold text-slate-900 border-b border-slate-100 pb-3 flex items-center gap-2">
                  <Icon name="calendar" size={18} /> Resumen del Turno
                </h3>
                <dl className="mt-4 space-y-3 text-sm text-slate-600">
                  <div>
                    <dt className="text-xs uppercase tracking-wider text-slate-400 font-semibold">
                      Especialidad
                    </dt>
                    <dd className="font-semibold text-slate-900 mt-0.5">
                      {especialidadSeleccionada?.nombre || "—"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wider text-slate-400 font-semibold">
                      Profesional
                    </dt>
                    <dd className="font-semibold text-slate-900 mt-0.5">
                      {medicoSeleccionado
                        ? `Dr(a). ${medicoSeleccionado.nombre} ${medicoSeleccionado.apellido}`
                        : "—"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wider text-slate-400 font-semibold">
                      Fecha y Hora
                    </dt>
                    <dd className="font-semibold text-slate-900 mt-0.5">
                      {slotSeleccionado
                        ? `${formatFecha(slotSeleccionado.fecha_hora)} · ${formatHora(slotSeleccionado.fecha_hora)} hs`
                        : "—"}
                    </dd>
                  </div>
                </dl>
              </div>

              <div className="pt-4 border-t border-slate-100 space-y-2">
                <button
                  type="button"
                  className="primary w-full justify-center py-2.5"
                  disabled={!slotSeleccionado || reservando}
                  onClick={() => void handleReservar()}
                >
                  {reservando ? "Reservando..." : "Confirmar Reserva"}
                </button>
                <button
                  type="button"
                  className="secondary w-full justify-center py-2 text-center text-sm"
                  onClick={() => navigate("/turnos")}
                  disabled={reservando}
                >
                  Cancelar
                </button>
              </div>
            </section>
          </div>
        </div>
      )}
    </>
  );
}
