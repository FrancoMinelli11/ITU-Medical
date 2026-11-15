import { clienteApi } from "@/api/client";
import type { components } from "@/api/schema";
import type { TurnoResponse, TurnosListResponse } from "@/features/turnos/types";

export type NotaSeguimientoOut = components["schemas"]["NotaSeguimientoOut"];

export const medicoApi = {
  async obtenerTurnos(idMedico?: string, estado?: string): Promise<TurnosListResponse> {
    const params = new URLSearchParams();
    if (idMedico) params.append("id_medico", idMedico);
    if (estado) params.append("estado", estado);
    const query = params.toString() ? `?${params.toString()}` : "";
    return clienteApi.get<TurnosListResponse>(`/turnos${query}`);
  },

  async atenderTurno(idTurno: string): Promise<TurnoResponse> {
    return clienteApi.post<TurnoResponse>(`/turnos/${idTurno}/atender`, {});
  },

  async listarNotasPaciente(idPaciente: string): Promise<NotaSeguimientoOut[]> {
    return clienteApi.get<NotaSeguimientoOut[]>(`/notas/paciente/${idPaciente}`);
  },

  async crearNota(datos: {
    id_paciente: string;
    id_turno?: string;
    contenido: string;
  }): Promise<NotaSeguimientoOut> {
    return clienteApi.post<NotaSeguimientoOut>("/notas", datos);
  },

  async modificarNota(
    idNota: string,
    datos: { contenido: string }
  ): Promise<NotaSeguimientoOut> {
    return clienteApi.put<NotaSeguimientoOut>(`/notas/${idNota}`, datos);
  },
};
