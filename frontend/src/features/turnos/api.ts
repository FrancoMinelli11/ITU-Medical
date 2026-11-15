import { clienteApi } from "@/api/client";
import type {
  DisponibilidadResponse,
  Especialidad,
  Medico,
  Pagina,
  RestriccionEstadoOut,
  TurnoResponse,
  TurnosListResponse,
} from "./types";

export const turnosApi = {
  async listarMisTurnos(estado?: string): Promise<TurnosListResponse> {
    const params = new URLSearchParams();
    if (estado) params.append("estado", estado);
    const query = params.toString() ? `?${params.toString()}` : "";
    return clienteApi.get<TurnosListResponse>(`/turnos${query}`);
  },

  async reservarWeb(datos: { id_medico: string; fecha_hora: string }): Promise<TurnoResponse> {
    return clienteApi.post<TurnoResponse>("/turnos", datos);
  },

  async cancelarHabitual(idTurno: string, motivo?: string): Promise<TurnoResponse> {
    return clienteApi.post<TurnoResponse>(`/turnos/${idTurno}/cancelar`, { motivo });
  },

  async solicitarCancelacionRapida(idTurno: string, motivo: string): Promise<unknown> {
    return clienteApi.post(`/turnos/${idTurno}/solicitar-cancelacion`, { motivo });
  },

  async obtenerEspecialidades(): Promise<Especialidad[]> {
    return clienteApi.get<Especialidad[]>("/especialidades");
  },

  /** `GET /medicos` devuelve `{items, page, ...}`, no un array. */
  async obtenerMedicos(idEspecialidad?: string): Promise<Medico[]> {
    const params = new URLSearchParams({ page_size: "100" });
    if (idEspecialidad) params.set("id_especialidad", idEspecialidad);
    const res = await clienteApi.get<Pagina<Medico>>(`/medicos?${params.toString()}`);
    return res.items;
  },

  /** `fecha` es `YYYY-MM-DD` (día local de Buenos Aires). */
  async obtenerDisponibilidad(idMedico: string, fecha: string): Promise<DisponibilidadResponse> {
    const params = new URLSearchParams({ fecha_desde: fecha, fecha_hasta: fecha });
    return clienteApi.get<DisponibilidadResponse>(
      `/medicos/${idMedico}/disponibilidad?${params.toString()}`,
    );
  },

  async obtenerEstadoRestriccion(idPaciente: string): Promise<RestriccionEstadoOut> {
    return clienteApi.get<RestriccionEstadoOut>(`/restricciones/paciente/${idPaciente}`);
  },
};