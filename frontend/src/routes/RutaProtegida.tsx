import type { PropsWithChildren } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { Cargando } from "@/components/ui/Cargando";
import { useAuth } from "@/features/auth/useAuth";
import type { Rol } from "@/features/auth/types";

interface RutaProtegidaProps {
  /** Si se indica, además de estar autenticado se exige uno de estos roles. */
  roles?: Rol[];
}

/**
 * Guard de rutas privadas. Mientras el bootstrap de sesión está en curso se
 * muestra un estado de carga; sin sesión se vuelve al login recordando el
 * destino, y las cuentas con cambio de contraseña pendiente quedan encerradas
 * en `/primer-ingreso` (C3).
 */
export function RutaProtegida({
  roles,
  children,
}: PropsWithChildren<RutaProtegidaProps>) {
  const { estado, usuario } = useAuth();
  const location = useLocation();

  if (estado === "cargando") return <Cargando />;
  if (estado === "anonimo" || !usuario) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ desde: `${location.pathname}${location.search}` }}
      />
    );
  }
  if (usuario.debe_cambiar_password && location.pathname !== "/primer-ingreso") {
    return <Navigate to="/primer-ingreso" replace />;
  }
  if (roles && !roles.includes(usuario.rol)) {
    return <Navigate to="/" replace />;
  }

  return children ? <>{children}</> : <Outlet />;
}
