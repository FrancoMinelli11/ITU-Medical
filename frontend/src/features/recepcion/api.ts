import { clienteApi } from "@/api/client";
import type {
  RestriccionEstadoOut,
  RestriccionOut,
  TurnoResponse,
  TurnosListResponse,
} from "@/features/turnos/types";

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
  items: PacienteItem[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
}

export interface TurnoEnEsperaResponse {
  id_turno: string;
  id_paciente: string;
  id_medico: string;
  fecha_hora: string;
  fecha_hora_llegada: string;
  duracion_minutos: number;
  orden_atencion: number;
  en_tolerancia: boolean;
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
  motivo: string;
  estado: "PENDIENTE" | "APROBADA" | "RECHAZADA";
  fecha_creacion: string;
  fecha_resolucion: string | null;
  id_usuario_resolucion: string | null;
  detalle_resolucion: string | null;
  paciente_nombre?: string | null;
  paciente_apellido?: string | null;
  paciente_dni?: string | null;
  turno_fecha_hora?: string | null;
  medico_nombre?: string | null;
  medico_apellido?: string | null;
  especialidad_nombre?: string | null;
}

export interface CierreJornadaResponse {
  total_ausentes: number;
  turnos_afectados: string[];
}

export const recepcionApi = {
  /** `q` busca por DNI, nombre, apellido o correo (parcial, sin distinguir mayúsculas). */
  async buscarPacientes(q?: string): Promise<PacientesListResponse> {
    const query = q ? `?q=${encodeURIComponent(q)}` : "";
    return clienteApi.get<PacientesListResponse>(`/pacientes${query}`);
  },

  async crearPaciente(datos: {
    dni: string;
    nombre: string;
    apellido: string;
    email: string;
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

  async listarTurnosDelPaciente(idPaciente: string, fecha?: string): Promise<TurnosListResponse> {
    const params = new URLSearchParams({
      id_paciente: idPaciente,
      estado: "RESERVADO",
      tamano_pagina: "50",
    });
    if (fecha) {
      params.set("fecha_desde", fecha);
      params.set("fecha_hasta", fecha);
    }
    return clienteApi.get<TurnosListResponse>(`/turnos?${params.toString()}`);
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
    datos: { aprobada: boolean; detalle?: string },
  ): Promise<SolicitudCancelacionOut> {
    return clienteApi.post<SolicitudCancelacionOut>(
      `/solicitudes-cancelacion/${idSolicitud}/resolver`,
      datos,
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