import type { Usuario } from "@/features/auth/types";

/** Usuario de ejemplo para handlers y tests. */
export function usuarioDemo(cambios: Partial<Usuario> = {}): Usuario {
  return {
    id_usuario: "11111111-1111-1111-1111-111111111111",
    dni: "30111222",
    email: "ana@example.com",
    nombre: "Ana",
    apellido: "Perez",
    rol: "PACIENTE",
    email_verificado: true,
    debe_cambiar_password: false,
    ultimo_login: null,
    ...cambios,
  };
}

/** Cuerpo de `POST /auth/login`. */
export function loginDemo(usuario: Usuario = usuarioDemo()) {
  return {
    access_token: "access-demo",
    token_type: "bearer" as const,
    expires_in: 900,
    usuario,
    debe_cambiar_password: usuario.debe_cambiar_password,
  };
}

/** Cuerpo de `POST /auth/refresh`. */
export function refreshDemo(usuario: Usuario = usuarioDemo()) {
  return {
    access_token: "access-demo",
    token_type: "bearer" as const,
    expires_in: 900,
    usuario,
  };
}
