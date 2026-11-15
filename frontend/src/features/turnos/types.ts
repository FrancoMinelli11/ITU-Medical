import type { components } from "@/api/schema";

export type EstadoTurno = components["schemas"]["EstadoTurno"];
export type TurnoResponse = components["schemas"]["TurnoResponse"];
export type TurnosListResponse = components["schemas"]["TurnosListResponse"];
export type Especialidad = components["schemas"]["EspecialidadOut"];
export type Medico = components["schemas"]["MedicoOut"];
export type SlotDisponibilidad = components["schemas"]["SlotDisponibilidad"];
export type DisponibilidadResponse = components["schemas"]["DisponibilidadOut"];
export type RestriccionOut = components["schemas"]["RestriccionOut"];
export type RestriccionEstadoOut = components["schemas"]["RestriccionEstadoOut"];

export interface Pagina<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
}
