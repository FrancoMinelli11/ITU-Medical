import { clienteApi } from "@/api/client";
import type { RestriccionEstadoOut, RestriccionOut, TurnoResponse } from "@/features/turnos/types";

export interface PacienteItem {
  id_paciente: string;
  id_usuario: string;
  dni: string;
  email: string;
  nombre: string;
  apellido: string;
  telefono: string | null;
  fecha_nacimiento: string | null;
  habilitado: boolean;
  email_verificado: boolean;
}

export interface PacientesListResponse {
  total: number;
  items: PacienteItem[];
}

export interface TurnoEnEsperaResponse {
  id_turno: string;
  id_paciente: string;
  id_medico: string;
  fecha_hora: string;
  duracion_minutos: number;
  estado: string;
  fecha_hora_llegada: string;
  orden_prioridad: number;
  esta_en_tolerancia: boolean;
  medico_nombre: string;
  medico_apellido: string;
  especialidad_nombre: string;
  paciente_nombre: string;
  paciente_apellido: string;
  paciente_dni: string;
}

export interface SolicitudCancelacionOut {
  id_solicitud: string;
  id_turno: string;
  id_paciente: string;
  motivo_paciente: string;
  estado: "PENDIENTE" | "APROBADA" | "RECHAZADA";
  fecha_solicitud: string;
  fecha_resolucion: string | null;
  id_usuario_resolucion: string | null;
  motivo_resolucion: string | null;
  paciente_nombre?: string;
  paciente_apellido?: string;
  paciente_dni?: string;
  turno_fecha_hora?: string;
  medico_nombre?: string;
  medico_apellido?: string;
  especialidad_nombre?: string;
}

export interface CierreJornadaResponse {
  turnos_marcados_ausentes: number;
  fecha_cierre: string;
}

export const recepcionApi = {
  async buscarPacientes(dni?: string): Promise<PacientesListResponse> {
    const query = dni ? `?dni=${encodeURIComponent(dni)}` : "";
    return clienteApi.get<PacientesListResponse>(`/pacientes${query}`);
  },

  async crearPaciente(datos: {
    dni: string;
    nombre: string;
    apellido: string;
    email?: string;
    telefono?: string;
    fecha_nacimiento?: string;
  }): Promise<PacienteItem> {
    return clienteApi.post<PacienteItem>("/pacientes", datos);
  },

  async reservarRecepcion(datos: {
    dni_paciente: string;
    id_medico: string;
    fecha_hora: string;
  }): Promise<TurnoResponse> {
    return clienteApi.post<TurnoResponse>("/turnos/recepcion", datos);
  },

  async obtenerSalaEspera(idMedico?: string): Promise<TurnoEnEsperaResponse[]> {
    const query = idMedico ? `?id_medico=${idMedico}` : "";
    return clienteApi.get<TurnoEnEsperaResponse[]>(`/recepcion/sala-espera${query}`);
  },

  async registrarLlegada(idTurno: string): Promise<TurnoResponse> {
    return clienteApi.post<TurnoResponse>(`/recepcion/turnos/${idTurno}/llegada`, {});
  },

  async registrarAusente(idTurno: string): Promise<TurnoResponse> {
    return clienteApi.post<TurnoResponse>(`/recepcion/turnos/${idTurno}/ausente`, {});
  },

  async cerrarJornada(): Promise<CierreJornadaResponse> {
    return clienteApi.post<CierreJornadaResponse>("/recepcion/cierre-jornada", {});
  },

  async listarSolicitudesCancelacion(estado?: string): Promise<SolicitudCancelacionOut[]> {
    const query = estado ? `?estado=${estado}` : "";
    return clienteApi.get<SolicitudCancelacionOut[]>(`/solicitudes-cancelacion${query}`);
  },

  async resolverSolicitudCancelacion(
    idSolicitud: string,
    datos: { aprobada: boolean; motivo_resolucion?: string }
  ): Promise<SolicitudCancelacionOut> {
    return clienteApi.post<SolicitudCancelacionOut>(
      `/solicitudes-cancelacion/${idSolicitud}/resolver`,
      datos
    );
  },

  async clasificarUsuarioRojo(datos: {
    id_paciente: string;
    motivo: string;
    dias_vigencia?: number;
  }): Promise<RestriccionOut> {
    return clienteApi.post<RestriccionOut>("/restricciones", datos);
  },

  async levantarRestriccion(idRestriccion: string): Promise<RestriccionOut> {
    return clienteApi.post<RestriccionOut>(`/restricciones/${idRestriccion}/levantar`, {});
  },

  async obtenerEstadoRestriccion(idPaciente: string): Promise<RestriccionEstadoOut> {
    return clienteApi.get<RestriccionEstadoOut>(`/restricciones/paciente/${idPaciente}`);
  },
};
