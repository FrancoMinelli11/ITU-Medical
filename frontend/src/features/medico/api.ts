import { clienteApi } from "@/api/client";
import type { components } from "@/api/schema";
import type { TurnoResponse, TurnosListResponse } from "@/features/turnos/types";

export type NotaSeguimientoOut = components["schemas"]["NotaSeguimientoOut"];
export type HorarioOut = components["schemas"]["HorarioOut"];
export type MedicoOut = components["schemas"]["MedicoOut"];

export interface HorarioItem {
  dia_semana: number;
  hora_inicio: string; // "HH:MM:SS"
  hora_fin: string;
  duracion_minutos: number;
  activo: boolean;
}

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

  /** Obtener el perfil de médico del usuario actual (busca por todos los médicos y filtra por id_usuario). */
  async obtenerMiPerfil(idUsuario: string): Promise<MedicoOut | null> {
    const res = await clienteApi.get<{ items: MedicoOut[]; total: number }>(
      "/medicos?page_size=100"
    );
    return res.items.find((m) => m.id_usuario === idUsuario) ?? null;
  },

  async obtenerHorarios(idMedico: string): Promise<HorarioOut[]> {
    return clienteApi.get<HorarioOut[]>(`/medicos/${idMedico}/horarios`);
  },

  async configurarHorarios(idMedico: string, horarios: HorarioItem[]): Promise<HorarioOut[]> {
    return clienteApi.put<HorarioOut[]>(`/medicos/${idMedico}/horarios`, { horarios });
  },

  /** Admin: listar todos los médicos. */
  async listarMedicos(): Promise<MedicoOut[]> {
    const res = await clienteApi.get<{ items: MedicoOut[]; total: number }>(
      "/medicos?page_size=100"
    );
    return res.items;
  },
};
