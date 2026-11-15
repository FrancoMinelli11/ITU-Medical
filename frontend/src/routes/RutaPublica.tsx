import type { PropsWithChildren } from "react";
import { Navigate, Outlet } from "react-router-dom";

import { Cargando } from "@/components/ui/Cargando";
import { useAuth } from "@/features/auth/useAuth";

/**
 * Rutas solo para anónimos (login y registro). Con sesión abierta se redirige
 * al inicio; si falta el cambio de contraseña del primer ingreso, se manda a
 * `/primer-ingreso`.
 */
export function RutaPublica({ children }: PropsWithChildren) {
  const { estado, usuario } = useAuth();

  if (estado === "anonimo") return children ? <>{children}</> : <Outlet />;
  if (estado === "autenticado" && usuario) {
    return (
      <Navigate to={usuario.debe_cambiar_password ? "/primer-ingreso" : "/"} replace />
    );
  }

  return <Cargando />;
}
