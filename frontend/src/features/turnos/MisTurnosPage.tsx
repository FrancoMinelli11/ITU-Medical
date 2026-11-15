import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { AppNavbar } from "@/components/layout/AppNavbar";
import { Alerta } from "@/components/ui/Alerta";
import { Boton } from "@/components/ui/Boton";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatFechaHora } from "@/lib/dates";
import { mensajeDeError } from "@/lib/problem";
import { ModalCancelarTurno } from "./ModalCancelarTurno";
import { turnosApi } from "./api";
import type { EstadoTurno, TurnoResponse } from "./types";

const ETIQUETA_ESTADO: Record<EstadoTurno, { texto: string; clases: string }> = {
  RESERVADO: { texto: "Confirmado", clases: "bg-blue-50 text-blue-700 border-blue-200" },
  EN_ESPERA: { texto: "En Sala de Espera", clases: "bg-amber-50 text-amber-700 border-amber-200" },
  ATENDIDO: { texto: "Atendido", clases: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  CANCELADO: { texto: "Cancelado", clases: "bg-slate-100 text-slate-600 border-slate-200" },
  AUSENTE: { texto: "Ausente", clases: "bg-rose-50 text-rose-700 border-rose-200" },
};

export function MisTurnosPage() {
  const [turnos, setTurnos] = useState<TurnoResponse[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pestaña, setPestaña] = useState<"proximos" | "historial">("proximos");
  const [turnoACancelar, setTurnoACancelar] = useState<TurnoResponse | null>(null);

  const cargarTurnos = async () => {
    setCargando(true);
    setError(null);
    try {
      const res = await turnosApi.listarMisTurnos();
      setTurnos(res.items);
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => {
    void cargarTurnos();
  }, []);

  const proximos = turnos.filter(
    (t) => t.estado === "RESERVADO" || t.estado === "EN_ESPERA"
  );
  const historial = turnos.filter(
    (t) => t.estado === "ATENDIDO" || t.estado === "CANCELADO" || t.estado === "AUSENTE"
  );

  const listaActual = pestaña === "proximos" ? proximos : historial;

  return (
    <div className="min-h-screen bg-slate-50">
      <AppNavbar />

      <main className="mx-auto max-w-5xl space-y-6 px-6 py-10">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">
              Mis Turnos Médicos
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              Consultá tus turnos activos y el historial de tus visitas al centro de salud.
            </p>
          </div>

          <Link to="/turnos/reservar">
            <Boton className="w-auto shadow-sm">+ Reservar nuevo turno</Boton>
          </Link>
        </div>

        {error && <Alerta tipo="error">{error}</Alerta>}

        {/* Pestañas */}
        <div className="flex border-b border-slate-200 space-x-6">
          <button
            type="button"
            onClick={() => setPestaña("proximos")}
            className={`pb-3 text-sm font-semibold border-b-2 transition ${
              pestaña === "proximos"
                ? "border-brand-600 text-brand-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            Próximos turnos ({proximos.length})
          </button>
          <button
            type="button"
            onClick={() => setPestaña("historial")}
            className={`pb-3 text-sm font-semibold border-b-2 transition ${
              pestaña === "historial"
                ? "border-brand-600 text-brand-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            Historial ({historial.length})
          </button>
        </div>

        {cargando ? (
          <div className="space-y-4">
            <Skeleton className="h-32 w-full rounded-2xl" />
            <Skeleton className="h-32 w-full rounded-2xl" />
            <Skeleton className="h-32 w-full rounded-2xl" />
          </div>
        ) : listaActual.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center">
            <p className="text-base font-medium text-slate-700">
              {pestaña === "proximos"
                ? "No tenés turnos programados en este momento."
                : "No contás con turnos anteriores registrados."}
            </p>
            {pestaña === "proximos" && (
              <div className="mt-4">
                <Link to="/turnos/reservar">
                  <Boton className="w-auto">Reservar mi primer turno</Boton>
                </Link>
              </div>
            )}
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {listaActual.map((turno) => {
              const badge = ETIQUETA_ESTADO[turno.estado];
              const puedeCancelar = turno.estado === "RESERVADO";

              return (
                <div
                  key={turno.id_turno}
                  className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow-md transition space-y-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <span className="text-xs font-bold uppercase tracking-wider text-brand-600">
                        {turno.especialidad_nombre}
                      </span>
                      <h2 className="text-lg font-bold text-slate-900 mt-0.5">
                        Dr(a). {turno.medico_nombre} {turno.medico_apellido}
                      </h2>
                    </div>
                    <span
                      className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${badge.clases}`}
                    >
                      {badge.texto}
                    </span>
                  </div>

                  <div className="space-y-1 text-sm text-slate-600">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-800">Fecha y hora:</span>
                      <span>{formatFechaHora(turno.fecha_hora)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-800">Duración:</span>
                      <span>{turno.duracion_minutos} minutos</span>
                    </div>

                    {turno.fecha_hora_cancelacion && (
                      <div className="mt-2 rounded-lg bg-slate-50 p-2 text-xs text-slate-500">
                        <span className="font-medium">Cancelado el:</span>{" "}
                        {formatFechaHora(turno.fecha_hora_cancelacion)}
                        {turno.motivo_cancelacion && ` (${turno.motivo_cancelacion})`}
                      </div>
                    )}
                  </div>

                  {puedeCancelar && (
                    <div className="pt-2 border-t border-slate-100 flex justify-end">
                      <Boton
                        variante="secundario"
                        className="w-auto text-xs py-1.5 px-3 border-rose-200 text-rose-600 hover:bg-rose-50"
                        onClick={() => setTurnoACancelar(turno)}
                      >
                        Cancelar turno
                      </Boton>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {turnoACancelar && (
          <ModalCancelarTurno
            turno={turnoACancelar}
            onClose={() => setTurnoACancelar(null)}
            onCancelado={() => {
              setTurnoACancelar(null);
              void cargarTurnos();
            }}
          />
        )}
      </main>
    </div>
  );
}
