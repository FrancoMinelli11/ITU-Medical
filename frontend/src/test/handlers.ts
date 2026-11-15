import { HttpResponse, http } from "msw";

import type { ProblemDetail } from "@/lib/problem";

/** Respuesta RFC 7807 con el formato que devuelve la API. */
export function problema(
  status: number,
  code: string,
  detail: string,
  errors?: ProblemDetail["errors"],
) {
  const cuerpo: ProblemDetail = {
    type: "about:blank",
    title: "Error",
    status,
    detail,
    code,
    request_id: "req-test",
    ...(errors ? { errors } : {}),
  };
  return HttpResponse.json(cuerpo, {
    status,
    headers: { "Content-Type": "application/problem+json" },
  });
}

/**
 * Handlers por defecto: sesión inexistente. Cada test sustituye los que necesita
 * con `server.use(...)` y `afterEach` los revierte.
 */
export const handlers = [
  http.get("*/api/v1/auth/csrf", () => new HttpResponse(null, { status: 204 })),
  http.post("*/api/v1/auth/refresh", () =>
    problema(401, "SESION_INVALIDA", "Tu sesión expiró. Iniciá sesión de nuevo."),
  ),
  http.post("*/api/v1/auth/logout", () => new HttpResponse(null, { status: 204 })),
];
