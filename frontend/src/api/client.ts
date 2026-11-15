import { ApiProblem, type ProblemDetail } from "@/lib/problem";

const API_URL = import.meta.env.VITE_API_URL ?? "/api/v1";
const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);
const CSRF_COOKIE = "csrf_token";
const CSRF_HEADER = "X-CSRF-Token";

interface HandlersSesion {
  /** Access token vigente (vive en memoria, nunca en `localStorage`). */
  obtenerToken: () => string | null;
  /** Pide un access nuevo; devuelve `false` si la sesión ya no es válida. */
  refrescar: () => Promise<boolean>;
}

let handlers: HandlersSesion | null = null;

/**
 * Conecta el cliente con `AuthProvider`. Se registra al montar la app y se
 * limpia al desmontarla; los tests pueden pasarlo o quitarlo a demanda.
 */
export function configurarSesion(nuevos: HandlersSesion | null): void {
  handlers = nuevos;
}

export function readCookie(name: string): string | null {
  const prefix = `${name}=`;
  const cookie = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : null;
}

function construirInit(init: RequestInit): RequestInit {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");

  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (MUTATING_METHODS.has(method)) {
    const csrf = readCookie(CSRF_COOKIE);
    if (csrf) headers.set(CSRF_HEADER, csrf);
  }

  const token = handlers?.obtenerToken() ?? null;
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  return { ...init, method, headers, credentials: "include" };
}

function errorDeRed(status: number, requestId: string): ProblemDetail {
  return {
    type: "about:blank",
    title: "Error de red",
    status,
    detail: "No se pudo interpretar la respuesta del servidor.",
    code: "ERROR_DE_RED",
    request_id: requestId,
  };
}

/**
 * Cliente único de la API.
 *
 * - Adjunta `X-CSRF-Token` en métodos no idempotentes.
 * - Adjunta el access token en memoria cuando hay sesión.
 * - Ante un `401` en una ruta de negocio, intenta renovar una sola vez y
 *   reintenta; las rutas `/auth/*` quedan afuera para no recursar en el refresh.
 */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const ejecutar = () => fetch(`${API_URL}${path}`, construirInit(init));

  let response = await ejecutar();

  if (response.status === 401 && handlers && !path.startsWith("/auth/")) {
    const renovado = await handlers.refrescar();
    if (renovado) response = await ejecutar();
  }

  if (!response.ok) {
    let problem: ProblemDetail;
    try {
      problem = (await response.json()) as ProblemDetail;
    } catch {
      problem = errorDeRed(response.status, response.headers.get("X-Request-ID") ?? "");
    }
    throw new ApiProblem(problem);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
