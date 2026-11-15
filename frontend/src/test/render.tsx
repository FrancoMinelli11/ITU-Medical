import { QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderResult } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import App from "@/App";
import { AuthProvider } from "@/features/auth/AuthProvider";
import { crearQueryClient } from "@/lib/query";

/** Monta la app real (rutas + sesión) en una ruta inicial dada. */
export function renderApp(ruta = "/"): RenderResult {
  const queryClient = crearQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[ruta]}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

/** Crea la cookie de CSRF que el cliente copia al header en mutaciones. */
export function simularCookieCsrf(valor = "csrf-demo"): void {
  document.cookie = `csrf_token=${valor}; path=/`;
}
