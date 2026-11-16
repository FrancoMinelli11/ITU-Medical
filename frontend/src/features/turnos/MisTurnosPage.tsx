import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { Alerta } from "@/components/ui/Alerta";
import { Icon } from "@/components/ui/Icon";
import { Skeleton } from "@/components/ui/Skeleton";
import { Status, type StatusTone } from "@/components/ui/Status";
import { formatPartesFecha } from "@/lib/dates";
import { mensajeDeError } from "@/lib/problem";
import { ModalCancelarTurno } from "./ModalCancelarTurno";
import { turnosApi } from "./api";
import type { EstadoTurno, TurnoResponse } from "./types";

const ESTADO_CONFIG: Record<EstadoTurno, { texto: string; tone: StatusTone }> = {
  RESERVADO: { texto: "Confirmado", tone: "green" },
  EN_ESPERA: { texto: "En espera", tone: "amber" },
  ATENDIDO: { texto: "Atendido", tone: "gray" },
  CANCELADO: { texto: "Cancelado", tone: "gray" },
  AUSENTE: { texto: "Ausente", tone: "amber" },
};

export function MisTurnosPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [turnos, setTurnos] = useState<TurnoResponse[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const tabParam = searchParams.get("tab");
  const [pestaña, setPestaña] = useState<"proximos" | "historial">(
    tabParam === "historial" ? "historial" : "proximos",
  );
  const [turnoACancelar, setTurnoACancelar] = useState<TurnoResponse | null>(null);

  useEffect(() => {
    if (tabParam === "historial" || tabParam === "proximos") {
      setPestaña(tabParam);
    }
  }, [tabParam]);

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
    (t) => t.estado === "RESERVADO" || t.estado === "EN_ESPERA",
  );
  const historial = turnos.filter(
    (t) => t.estado === "ATENDIDO" || t.estado === "CANCELADO" || t.estado === "AUSENTE",
  );

  const listaActual = pestaña === "proximos" ? proximos : historial;

  return (
    <>
      <div className="page-title">
        <div>
          <p>ITU MEDICAL</p>
          <h1>Mis turnos médicos</h1>
          <span>Consultá y gestioná tus próximas visitas e historial de atención.</span>
        </div>
      </div>

      {error && <Alerta tipo="error">{error}</Alerta>}

      <div className="toolbar">
        <div className="tabs">
          <button
            type="button"
            className={pestaña === "proximos" ? "active" : ""}
            onClick={() => {
              setPestaña("proximos");
              setSearchParams({ tab: "proximos" });
            }}
          >
            Próximos <b>{proximos.length}</b>
          </button>
          <button
            type="button"
            className={pestaña === "historial" ? "active" : ""}
            onClick={() => {
              setPestaña("historial");
              setSearchParams({ tab: "historial" });
            }}
          >
            Historial <b>{historial.length}</b>
          </button>
        </div>

        <Link to="/turnos/reservar" className="primary">
          <Icon name="plus" size={17} /> Nuevo turno
        </Link>
      </div>

      {cargando ? (
        <div className="space-y-4">
          <Skeleton className="h-28 w-full rounded-2xl" />
          <Skeleton className="h-28 w-full rounded-2xl" />
        </div>
      ) : listaActual.length === 0 ? (
        <section className="list-card py-12 text-center space-y-3">
          <p className="text-sm font-medium text-slate-600">
            {pestaña === "proximos"
              ? "No tenés turnos programados en este momento."
              : "No contás con turnos anteriores registrados."}
          </p>
          {pestaña === "proximos" && (
            <div>
              <Link to="/turnos/reservar" className="primary">
                Reservar turno
              </Link>
            </div>
          )}
        </section>
      ) : (
        <section className="list-card">
          <div className="list-label">
            {pestaña === "proximos" ? "PRÓXIMAS VISITAS" : "VISITAS ANTERIORES"}
          </div>

          {listaActual.map((turno) => {
            const partes = formatPartesFecha(turno.fecha_hora);
            const cfg = ESTADO_CONFIG[turno.estado];
            const puedeCancelar = turno.estado === "RESERVADO";

            return (
              <article key={turno.id_turno} className="appointment-card">
                <div className="date-tile">
                  <strong>{partes.diaNumero}</strong>
                  <span>{partes.mesAbrev}</span>
                </div>

                <div className="appointment-main">
                  <div className="appointment-heading">
                    <div>
                      <p>{turno.especialidad_nombre}</p>
                      <h3>Dr(a). {turno.medico_nombre} {turno.medico_apellido}</h3>
                    </div>
                    <Status tone={cfg.tone}>{cfg.texto}</Status>
                  </div>

                  <div className="appointment-meta">
                    <span>
                      <Icon name="clock" size={16} /> {partes.horaTexto} hs
                    </span>
                    <span>{partes.diaSemana} {partes.diaMesTexto}</span>
                    <span>{turno.duracion_minutos} minutos</span>
                  </div>

                  {turno.fecha_hora_cancelacion && (
                    <p className="text-xs text-slate-500 mt-2">
                      Cancelado: {formatPartesFecha(turno.fecha_hora_cancelacion).diaMesTexto}{" "}
                      {turno.motivo_cancelacion ? `· Motivo: ${turno.motivo_cancelacion}` : ""}
                    </p>
                  )}
                </div>

                {puedeCancelar && (
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => setTurnoACancelar(turno)}
                  >
                    Cancelar turno
                  </button>
                )}
              </article>
            );
          })}
        </section>
      )}

      <section className="care-note">
        <span>
          <Icon name="clock" />
        </span>
        <div>
          <b>¿Necesitás cancelar?</b>
          <p>Podés hacerlo sin cargo hasta 24 horas antes del turno desde el portal web.</p>
        </div>
      </section>

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
    </>
  );
}
