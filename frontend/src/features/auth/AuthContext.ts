import { createContext } from "react";

import type { LoginResponse, Usuario } from "./types";

export type EstadoSesion = "cargando" | "anonimo" | "autenticado";

export interface ContextoAuth {
  estado: EstadoSesion;
  usuario: Usuario | null;
  login: (dni: string, password: string) => Promise<LoginResponse>;
  logout: () => Promise<void>;
  refrescar: () => Promise<boolean>;
  cambiarPassword: (actual: string, nueva: string) => Promise<void>;
  primerIngreso: (nueva: string) => Promise<void>;
  actualizarUsuario: (usuario: Usuario) => void;
}

export const AuthContext = createContext<ContextoAuth | null>(null);
