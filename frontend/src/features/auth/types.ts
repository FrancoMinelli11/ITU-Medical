export type Rol = "PACIENTE" | "RECEPCIONISTA" | "MEDICO" | "ADMINISTRADOR";

export interface Usuario {
  id_usuario: string;
  dni: string;
  email: string;
  nombre: string;
  apellido: string;
  rol: Rol;
  email_verificado: boolean;
  debe_cambiar_password: boolean;
  ultimo_login: string | null;
  telefono?: string | null;
  fecha_nacimiento?: string | null;
}

export interface PacienteOut {
  id_paciente: string;
  id_usuario: string;
  dni: string;
  email: string;
  nombre: string;
  apellido: string;
  telefono: string | null;
  fecha_nacimiento: string | null;
  email_verificado: boolean;
  habilitado: boolean;
  debe_cambiar_password: boolean;
  fecha_creacion: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  usuario: Usuario;
  debe_cambiar_password: boolean;
}

export interface RefreshResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  usuario: Usuario;
}

export interface MensajeResponse {
  mensaje: string;
}

export interface VerificacionResponse {
  email_verificado: boolean;
  mensaje: string;
}

export interface LoginDatos {
  dni: string;
  password: string;
}

export interface RegistroDatos {
  dni: string;
  email: string;
  password: string;
  nombre: string;
  apellido: string;
  telefono?: string;
  fecha_nacimiento?: string;
}

export interface RecuperarDatos {
  email: string;
  dni: string;
}

export interface RestablecerDatos {
  token: string;
  password: string;
}

export interface CambiarPasswordDatos {
  password_actual: string;
  password_nueva: string;
}
