import { clienteApi } from "@/api/client";
import type {
  DisponibilidadResponse,
  Especialidad,
  Medico,
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

  async cancelarHabitual(idTurno: string, detalle?: string): Promise<TurnoResponse> {
    return clienteApi.post<TurnoResponse>(`/turnos/${idTurno}/cancelar`, { detalle });
  },

  async solicitarCancelacionRapida(idTurno: string, motivo: string): Promise<unknown> {
    return clienteApi.post(`/turnos/${idTurno}/solicitar-cancelacion`, { motivo });
  },

  async obtenerEspecialidades(): Promise<Especialidad[]> {
    return clienteApi.get<Especialidad[]>("/especialidades");
  },

  async obtenerMedicos(idEspecialidad?: string): Promise<Medico[]> {
    const query = idEspecialidad ? `?id_especialidad=${idEspecialidad}` : "";
    return clienteApi.get<Medico[]>(`/medicos${query}`);
  },

  async obtenerDisponibilidad(
    idMedico: string,
    desde: string,
    hasta: string
  ): Promise<DisponibilidadResponse> {
    return clienteApi.get<DisponibilidadResponse>(
      `/medicos/${idMedico}/disponibilidad?desde=${encodeURIComponent(desde)}&hasta=${encodeURIComponent(hasta)}`
    );
  },

  async obtenerEstadoRestriccion(idPaciente: string): Promise<RestriccionEstadoOut> {
    return clienteApi.get<RestriccionEstadoOut>(`/restricciones/paciente/${idPaciente}`);
  },
};
