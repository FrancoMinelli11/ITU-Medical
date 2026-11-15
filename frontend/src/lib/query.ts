import { QueryClient } from "@tanstack/react-query";

/** Cliente de consultas: sin reintentos automáticos (los errores se muestran). */
export function crearQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: false },
      mutations: { retry: false },
    },
  });
}
