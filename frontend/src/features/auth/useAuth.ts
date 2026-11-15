import { useContext } from "react";

import { AuthContext, type ContextoAuth } from "./AuthContext";

export function useAuth(): ContextoAuth {
  const contexto = useContext(AuthContext);
  if (!contexto) {
    throw new Error("useAuth debe usarse dentro de <AuthProvider>.");
  }
  return contexto;
}
