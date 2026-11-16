import { useEffect, useState } from "react";

import { Alerta } from "@/components/ui/Alerta";
import { Icon } from "@/components/ui/Icon";
import { Skeleton } from "@/components/ui/Skeleton";
import { Status } from "@/components/ui/Status";
import { mensajeDeError } from "@/lib/problem";
import { type HorarioItem, type HorarioOut, type MedicoOut, medicoApi } from "@/features/medico/api";

const DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

function horaCorta(t: string): string {
  return t.slice(0, 5);
}

// ─── Panel horarios de un médico ─────────────────────────────────────────────

function PanelAgendaMedico({ medico }: { medico: MedicoOut }) {
  const [abierto, setAbierto] = useState(false);
  const [horarios, setHorarios] = useState<HorarioOut[]>([]);
  const [cargando, setCargando] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exito, setExito] = useState<string | null>(null);
  const [cargado, setCargado] = useState(false);

  // Formulario nuevo horario
  const [diaNuevo, setDiaNuevo] = useState("0");
  const [inicioNuevo, setInicioNuevo] = useState("09:00");
  const [finNuevo, setFinNuevo] = useState("13:00");
  const [duracionNueva, setDuracionNueva] = useState("30");

  const cargar = async () => {
    setCargando(true);
    setError(null);
    try {
      const res = await medicoApi.obtenerHorarios(medico.id_medico);
      setHorarios(res);
      setCargado(true);
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setCargando(false);
    }
  };

  const handleToggle = async () => {
    if (!abierto && !cargado) await cargar();
    setAbierto((prev) => !prev);
  };

  const guardar = async (items: HorarioItem[]) => {
    setGuardando(true);
    setError(null);
    setExito(null);
    try {
      const res = await medicoApi.configurarHorarios(medico.id_medico, items);
      setHorarios(res);
      setExito("Horarios actualizados.");
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setGuardando(false);
    }
  };

  const toggleActivo = (h: HorarioOut) => {
    const actualizados: HorarioItem[] = horarios.map((x) => ({
      dia_semana: x.dia_semana,
      hora_inicio: x.hora_inicio,
      hora_fin: x.hora_fin,
      duracion_minutos: x.duracion_minutos,
      activo: x.id_horario === h.id_horario ? !x.activo : x.activo,
    }));
    void guardar(actualizados);
  };

  const eliminar = (h: HorarioOut) => {
    const actualizados: HorarioItem[] = horarios
      .filter((x) => x.id_horario !== h.id_horario)
      .map((x) => ({
        dia_semana: x.dia_semana,
        hora_inicio: x.hora_inicio,
        hora_fin: x.hora_fin,
        duracion_minutos: x.duracion_minutos,
        activo: x.activo,
      }));
    void guardar(actualizados);
  };

  const agregar = (e: React.FormEvent) => {
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
    void guardar(actualizados);
  };

  const iniciales = `${medico.nombre.charAt(0)}${medico.apellido.charAt(0)}`.toUpperCase();

  return (
    <div className="rounded-2xl border border-slate-200 bg-white overflow-hidden">
      {/* Cabecera del acordeón */}
      <button
        type="button"
        className="w-full flex items-center justify-between gap-4 px-5 py-4 text-left hover:bg-slate-50 transition-colors"
        onClick={() => void handleToggle()}
      >
        <div className="flex items-center gap-3">
          <span className="w-10 h-10 rounded-full bg-green-100 text-green-800 font-bold text-sm flex items-center justify-center">
            {iniciales}
          </span>
          <div>
            <p className="font-semibold text-slate-900">
              Dr(a). {medico.nombre} {medico.apellido}
            </p>
            <p className="text-xs text-slate-500">
              {medico.especialidad_nombre} · Mat. {medico.matricula ?? "—"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Status tone={medico.activo ? "green" : "gray"}>
            {medico.activo ? "Activo" : "Inactivo"}
          </Status>
          <Icon name={abierto ? "close" : "arrow"} size={18} />
        </div>
      </button>

      {/* Contenido del acordeón */}
      {abierto && (
        <div className="border-t border-slate-100 p-5 space-y-5">
          {error && <Alerta tipo="error">{error}</Alerta>}
          {exito && <Alerta tipo="exito">{exito}</Alerta>}

          {cargando ? (
            <div className="space-y-2">
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
            </div>
          ) : (
            <>
              {/* Lista horarios */}
              {horarios.length === 0 ? (
                <p className="text-sm text-slate-500 italic">Sin horarios configurados.</p>
              ) : (
                <div className="space-y-3">
                  {DIAS.map((nombre, dia) => {
                    const items = horarios.filter((h) => h.dia_semana === dia);
                    if (items.length === 0) return null;
                    return (
                      <div key={dia}>
                        <h4 className="text-xs font-semibold text-slate-400 uppercase mb-1">{nombre}</h4>
                        {items.map((h) => (
                          <div
                            key={h.id_horario}
                            className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 mb-1"
                          >
                            <div className="flex items-center gap-2 text-sm">
                              <Status tone={h.activo ? "green" : "gray"}>
                                {h.activo ? "Activo" : "Inactivo"}
                              </Status>
                              <span className="font-semibold">
                                {horaCorta(h.hora_inicio)} – {horaCorta(h.hora_fin)}
                              </span>
                              <span className="text-xs text-slate-500">
                                cada {h.duracion_minutos} min
                              </span>
                            </div>
                            <div className="flex gap-2">
                              <button
                                type="button"
                                className="secondary text-xs py-1 px-2"
                                disabled={guardando}
                                onClick={() => toggleActivo(h)}
                              >
                                {h.activo ? "Desactivar" : "Activar"}
                              </button>
                              <button
                                type="button"
                                className="secondary text-xs py-1 px-2"
                                disabled={guardando}
                                onClick={() => eliminar(h)}
                              >
                                Eliminar
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Formulario agregar */}
              <form onSubmit={agregar} className="grid grid-cols-2 sm:grid-cols-4 gap-3 items-end pt-3 border-t border-slate-100">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Día</label>
                  <select
                    value={diaNuevo}
                    onChange={(e) => setDiaNuevo(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm bg-white"
                  >
                    {DIAS.map((n, i) => (
                      <option key={i} value={i}>{n}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Desde</label>
                  <input
                    type="time"
                    value={inicioNuevo}
                    onChange={(e) => setInicioNuevo(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Hasta</label>
                  <input
                    type="time"
                    value={finNuevo}
                    onChange={(e) => setFinNuevo(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Duración</label>
                  <select
                    value={duracionNueva}
                    onChange={(e) => setDuracionNueva(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm bg-white"
                  >
                    {[15, 20, 30, 45, 60].map((d) => (
                      <option key={d} value={d}>{d} min</option>
                    ))}
                  </select>
                </div>
                <div className="col-span-2 sm:col-span-4 flex justify-end">
                  <button type="submit" className="primary text-sm py-1.5 px-4" disabled={guardando}>
                    <Icon name="plus" size={15} />
                    {guardando ? "Guardando..." : "Agregar"}
                  </button>
                </div>
              </form>
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Página de Administración ─────────────────────────────────────────────────

export function AdminPage() {
  const [medicos, setMedicos] = useState<MedicoOut[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function cargar() {
      setCargando(true);
      try {
        const res = await medicoApi.listarMedicos();
        setMedicos(res);
      } catch (err) {
        setError(mensajeDeError(err));
      } finally {
        setCargando(false);
      }
    }
    void cargar();
  }, []);

  return (
    <>
      <div className="page-title">
        <div>
          <p>ITU MEDICAL</p>
          <h1>Administración de Agendas</h1>
          <span>
            Configurá los horarios de atención habitual de cada profesional. Los turnos disponibles
            se generan automáticamente a partir de estas configuraciones.
          </span>
        </div>
      </div>

      {error && <Alerta tipo="error">{error}</Alerta>}

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>Profesionales y sus horarios</h2>
            <p>Expandí cada médico para ver y editar su agenda semanal.</p>
          </div>
        </div>

        <div className="p-6 space-y-3">
          {cargando ? (
            <>
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </>
          ) : medicos.length === 0 ? (
            <p className="text-sm text-slate-500 italic">
              No hay profesionales cargados en el sistema.
            </p>
          ) : (
            medicos.map((m) => <PanelAgendaMedico key={m.id_medico} medico={m} />)
          )}
        </div>
      </section>
    </>
  );
}
