import { clienteApi } from "@/api/client";
import type { components } from "@/api/schema";
import type {
  RestriccionEstadoOut,
  RestriccionOut,
  TurnoResponse,
  TurnosListResponse,
} from "@/features/turnos/types";

export type PacienteItem = components["schemas"]["PacienteOut"];
export type PacientesListResponse = components["schemas"]["Pagina_PacienteOut_"];
export type TurnoEnEsperaResponse = components["schemas"]["TurnoEnEsperaResponse"];
export type SolicitudCancelacionOut = components["schemas"]["SolicitudCancelacionOut"];
export type CierreJornadaResponse = components["schemas"]["CierreJornadaResponse"];

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