export type EstadoTurno =
  | "RESERVADO"
  | "EN_ESPERA"
  | "ATENDIDO"
  | "CANCELADO"
  | "AUSENTE";

export interface TurnoResponse {
  id_turno: string;
  id_paciente: string;
  id_medico: string;
  fecha_hora: string;
  duracion_minutos: number;
  estado: EstadoTurno;
  fecha_hora_llegada: string | null;
  fecha_hora_cancelacion: string | null;
  motivo_cancelacion: string | null;
  detalle_cancelacion: string | null;
  medico_nombre: string;
  medico_apellido: string;
  especialidad_nombre: string;
  paciente_nombre: string;
  paciente_apellido: string;
  paciente_dni: string;
  fecha_creacion: string;
}

export interface TurnosListResponse {
  total: number;
  items: TurnoResponse[];
}

export interface Especialidad {
  id_especialidad: string;
  nombre: string;
  activa: boolean;
}

export interface Medico {
  id_medico: string;
  id_usuario: string;
  id_especialidad: string;
  nombre: string;
  apellido: string;
  matricula: string | null;
  especialidad_nombre?: string;
  activo: boolean;
}

export interface SlotDisponibilidad {
  fecha_hora: string;
  duracion_minutos: number;
  disponible: boolean;
}

export interface DisponibilidadResponse {
  id_medico: string;
  desde: string;
  hasta: string;
  slots: SlotDisponibilidad[];
}

export interface RestriccionOut {
  id_restriccion: string;
  id_usuario: string;
  id_paciente: string | null;
  motivo: string;
  fecha_inicio: string;
  fecha_fin: string;
  activa: boolean;
  vigente: boolean;
  id_usuario_creador: string;
  fecha_creacion: string;
  paciente_nombre?: string | null;
  paciente_apellido?: string | null;
  paciente_dni?: string | null;
}

export interface RestriccionEstadoOut {
  id_paciente: string;
  id_usuario: string;
  es_usuario_rojo: boolean;
  restriccion_activa: RestriccionOut | null;
}
