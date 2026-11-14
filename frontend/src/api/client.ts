import { ApiProblem, type ProblemDetail } from "@/lib/problem";

const API_URL = import.meta.env.VITE_API_URL ?? "/api/v1";
const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);
const CSRF_COOKIE = "csrf_token";
const CSRF_HEADER = "X-CSRF-Token";

function readCookie(name: string): string | null {
  const prefix = `${name}=`;
  const cookie = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : null;
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
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

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    method,
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    let problem: ProblemDetail;
    try {
      problem = (await response.json()) as ProblemDetail;
    } catch {
      problem = {
        type: "about:blank",
        title: "Error de red",
        status: response.status,
        detail: "No se pudo interpretar la respuesta del servidor.",
        code: "ERROR_DE_RED",
        request_id: response.headers.get("X-Request-ID") ?? "",
      };
    }
    throw new ApiProblem(problem);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
