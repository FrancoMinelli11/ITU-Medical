import { useCallback, useEffect, useRef, useState, type PropsWithChildren } from "react";

import { configurarSesion } from "@/api/client";

import { authApi } from "./api";
import { AuthContext, type EstadoSesion } from "./AuthContext";
import type { LoginResponse, Usuario } from "./types";

/**
 * Sesión del SPA: el access token vive **solo en memoria** (nunca en
 * `localStorage`). Al montar se pide un access nuevo con el refresh httpOnly;
 * si no hay sesión válida la app queda anónima.
 *
 * El promise de refresco se comparte entre llamadas concurrentes: con el doble
 * montaje de StrictMode, dos refresh simultáneos reutilizarían el mismo token
 * rotado y el servidor lo interpretaría como robo (RN-32/S-10).
 */
export function AuthProvider({ children }: PropsWithChildren) {
  const [estado, setEstado] = useState<EstadoSesion>("cargando");
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const tokenRef = useRef<string | null>(null);
  const refrescoRef = useRef<Promise<boolean> | null>(null);

  const guardarSesion = useCallback((access: string, nuevo: Usuario) => {
    tokenRef.current = access;
    setUsuario(nuevo);
    setEstado("autenticado");
  }, []);

  const limpiarSesion = useCallback(() => {
    tokenRef.current = null;
    setUsuario(null);
    setEstado("anonimo");
  }, []);

  const refrescar = useCallback((): Promise<boolean> => {
    if (refrescoRef.current) return refrescoRef.current;

    const promesa = (async () => {
      try {
        // El refresh exige CSRF double-submit: se asegura la cookie primero.
        await authApi.csrf();
      } catch {
        // Si falla /csrf, el refresh de abajo decidirá: la sesión sigue anónima.
      }
      try {
        const datos = await authApi.refresh();
        guardarSesion(datos.access_token, datos.usuario);
        return true;
      } catch {
        limpiarSesion();
        return false;
      }
    })().finally(() => {
      refrescoRef.current = null;
    });

    refrescoRef.current = promesa;
    return promesa;
  }, [guardarSesion, limpiarSesion]);

  useEffect(() => {
    configurarSesion({ obtenerToken: () => tokenRef.current, refrescar });
    void refrescar();
    return () => configurarSesion(null);
  }, [refrescar]);

  const login = useCallback(
    async (dni: string, password: string): Promise<LoginResponse> => {
      const datos = await authApi.login({ dni, password });
      guardarSesion(datos.access_token, datos.usuario);
      return datos;
    },
    [guardarSesion],
  );

  const logout = useCallback(async (): Promise<void> => {
    try {
      await authApi.logout();
    } finally {
      limpiarSesion();
    }
  }, [limpiarSesion]);

  const cambiarPassword = useCallback(
    async (actual: string, nueva: string): Promise<void> => {
      await authApi.cambiarPassword({
        password_actual: actual,
        password_nueva: nueva,
      });
      // El servidor revoca todas las sesiones: hay que volver a entrar.
      limpiarSesion();
    },
    [limpiarSesion],
  );

  const primerIngreso = useCallback(
    async (nueva: string): Promise<void> => {
      await authApi.primerIngreso(nueva);
      limpiarSesion();
    },
    [limpiarSesion],
  );

  const actualizarUsuario = useCallback((nuevo: Usuario) => {
    setUsuario(nuevo);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        estado,
        usuario,
        login,
        logout,
        refrescar,
        cambiarPassword,
        primerIngreso,
        actualizarUsuario,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
