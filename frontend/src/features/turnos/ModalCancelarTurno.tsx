import { useState } from "react";

import { Alerta } from "@/components/ui/Alerta";
import { Boton } from "@/components/ui/Boton";
import { formatFechaHora } from "@/lib/dates";
import { mensajeDeError } from "@/lib/problem";
import { turnosApi } from "./api";
import type { TurnoResponse } from "./types";

interface Props {
  turno: TurnoResponse;
  onClose: () => void;
  onCancelado: () => void;
}

export function ModalCancelarTurno({ turno, onClose, onCancelado }: Props) {
  const [motivo, setMotivo] = useState("");
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ahora = Date.now();
  const fechaTurnoMs = new Date(turno.fecha_hora).getTime();
  const horasRestantes = (fechaTurnoMs - ahora) / (1000 * 3600);
  const esCancelacionHabitual = horasRestantes >= 24;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!esCancelacionHabitual && (!motivo.trim() || motivo.trim().length < 5)) {
      setError("Por favor detallá el motivo de la cancelación rápida (mínimo 5 caracteres).");
      return;
    }

    setCargando(true);
    try {
      if (esCancelacionHabitual) {
        await turnosApi.cancelarHabitual(turno.id_turno, motivo.trim() || undefined);
      } else {
        await turnosApi.solicitarCancelacionRapida(turno.id_turno, motivo.trim());
      }
      onCancelado();
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setCargando(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-cancelar-titulo"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm animate-fade-in"
    >
      <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl border border-slate-200">
        <div className="flex items-start justify-between">
          <div>
            <h2 id="modal-cancelar-titulo" className="text-xl font-bold text-slate-900">
              {esCancelacionHabitual ? "Cancelar Turno" : "Solicitud de Cancelación Rápida"}
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              {turno.especialidad_nombre} · {turno.medico_nombre} {turno.medico_apellido}
            </p>
            <p className="text-sm font-semibold text-slate-800 mt-0.5">
              Fecha: {formatFechaHora(turno.fecha_hora)}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 text-lg font-bold"
          >
            ✕
          </button>
        </div>

        {error && (
          <div className="mt-4">
            <Alerta tipo="error">{error}</Alerta>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          {esCancelacionHabitual ? (
            <div className="rounded-xl bg-blue-50 p-4 border border-blue-200 text-sm text-blue-900 space-y-1">
              <p className="font-semibold">Cancelación anticipada (+24 hs)</p>
              <p>
                Al cancelar con más de 24 horas de anticipación, tu turno quedará cancelado
                de inmediato y el horario se liberará para otros pacientes.
              </p>
            </div>
          ) : (
            <div className="rounded-xl bg-amber-50 p-4 border border-amber-200 text-sm text-amber-900 space-y-1">
              <p className="font-semibold">Cancelación con menos de 24 hs</p>
              <p>
                Al realizar la cancelación con poca anticipación, se generará una solicitud
                que será evaluada por el equipo de recepción. Es obligatorio indicar el motivo.
              </p>
            </div>
          )}

          <div>
            <label
              htmlFor="motivo-cancelacion"
              className="block text-sm font-medium text-slate-700"
            >
              {esCancelacionHabitual ? "Detalle o motivo (opcional)" : "Motivo de la cancelación (obligatorio)"}
            </label>
            <textarea
              id="motivo-cancelacion"
              rows={3}
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              placeholder={
                esCancelacionHabitual
                  ? "Ej: Cambio de planes o viaje"
                  : "Ej: Imprevisto laboral o problema de salud"
              }
              className="mt-1 block w-full rounded-lg border border-slate-300 p-2.5 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:ring-brand-500"
              required={!esCancelacionHabitual}
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-3">
            <Boton
              type="button"
              variante="secundario"
              className="w-auto"
              onClick={onClose}
              disabled={cargando}
            >
              Volver
            </Boton>
            <Boton
              type="submit"
              variante={esCancelacionHabitual ? "peligro" : "primario"}
              className="w-auto"
              cargando={cargando}
            >
              {esCancelacionHabitual ? "Confirmar Cancelación" : "Enviar Solicitud"}
            </Boton>
          </div>
        </form>
      </div>
    </div>
  );
}
