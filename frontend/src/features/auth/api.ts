import { apiFetch } from "@/api/client";

import type {
  CambiarPasswordDatos,
  LoginDatos,
  LoginResponse,
  MensajeResponse,
  PacienteOut,
  RecuperarDatos,
  RefreshResponse,
  RegistroDatos,
  RestablecerDatos,
  Usuario,
  VerificacionResponse,
} from "./types";

function cuerpo(datos: unknown): RequestInit {
  return { method: "POST", body: JSON.stringify(datos) };
}

export const authApi = {
  csrf: () => apiFetch<void>("/auth/csrf"),

  login: (datos: LoginDatos) => apiFetch<LoginResponse>("/auth/login", cuerpo(datos)),

  refresh: () => apiFetch<RefreshResponse>("/auth/refresh", { method: "POST" }),

  logout: () => apiFetch<void>("/auth/logout", { method: "POST" }),

  me: () => apiFetch<Usuario>("/auth/me"),

  registro: (datos: RegistroDatos) =>
    apiFetch<PacienteOut>("/auth/registro", cuerpo(datos)),

  verificarEmail: (token: string) =>
    apiFetch<VerificacionResponse>("/auth/verificar-email", cuerpo({ token })),

  reenviarVerificacion: (email: string) =>
    apiFetch<MensajeResponse>("/auth/reenviar-verificacion", cuerpo({ email })),

  recuperarPassword: (datos: RecuperarDatos) =>
    apiFetch<MensajeResponse>("/auth/recuperar-password", cuerpo(datos)),

  restablecerPassword: (datos: RestablecerDatos) =>
    apiFetch<MensajeResponse>("/auth/restablecer-password", cuerpo(datos)),

  cambiarPassword: (datos: CambiarPasswordDatos) =>
    apiFetch<void>("/auth/cambiar-password", cuerpo(datos)),

  primerIngreso: (passwordNueva: string) =>
    apiFetch<void>("/auth/primer-ingreso", cuerpo({ password_nueva: passwordNueva })),
};
