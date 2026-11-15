import { HttpResponse, http } from "msw";

import { ApiProblem } from "@/lib/problem";
import { problema } from "@/test/handlers";
import { simularCookieCsrf } from "@/test/render";
import { server } from "@/test/server";

import { apiFetch, configurarSesion } from "./client";

afterEach(() => {
  configurarSesion(null);
});

test("adjunta el CSRF y el bearer en mutaciones", async () => {
  simularCookieCsrf("csrf-abc");
  configurarSesion({
    obtenerToken: () => "token-en-memoria",
    refrescar: async () => false,
  });

  let cabeceras: Headers | null = null;
  server.use(
    http.post("*/api/v1/prueba", ({ request }) => {
      cabeceras = request.headers;
      return HttpResponse.json({ ok: true });
    }),
  );

  await expect(
    apiFetch<{ ok: boolean }>("/prueba", { method: "POST", body: JSON.stringify({}) }),
  ).resolves.toEqual({ ok: true });

  expect(cabeceras).not.toBeNull();
  const enviadas = cabeceras as unknown as Headers;
  expect(enviadas.get("X-CSRF-Token")).toBe("csrf-abc");
  expect(enviadas.get("Authorization")).toBe("Bearer token-en-memoria");
  expect(enviadas.get("Content-Type")).toBe("application/json");
});

test("en GET no manda CSRF", async () => {
  simularCookieCsrf("csrf-abc");

  let cabeceras: Headers | null = null;
  server.use(
    http.get("*/api/v1/prueba", ({ request }) => {
      cabeceras = request.headers;
      return HttpResponse.json({ ok: true });
    }),
  );

  await apiFetch("/prueba");

  const enviadas = cabeceras as unknown as Headers;
  expect(enviadas.get("X-CSRF-Token")).toBeNull();
});

test("ante un 401 renueva el token y reintenta una vez", async () => {
  let intentos = 0;
  let renovaciones = 0;

  configurarSesion({
    obtenerToken: () => "nuevo",
    refrescar: async () => {
      renovaciones += 1;
      return true;
    },
  });

  server.use(
    http.get("*/api/v1/turnos", () => {
      intentos += 1;
      if (intentos === 1) {
        return problema(401, "TOKEN_EXPIRADO", "El token de acceso venció.");
      }
      return HttpResponse.json({ items: [] });
    }),
  );

  await expect(apiFetch("/turnos")).resolves.toEqual({ items: [] });
  expect(intentos).toBe(2);
  expect(renovaciones).toBe(1);
});

test("si la renovación falla, el 401 se propaga", async () => {
  configurarSesion({ obtenerToken: () => null, refrescar: async () => false });

  server.use(
    http.get("*/api/v1/turnos", () =>
      problema(401, "NO_AUTENTICADO", "Necesitás iniciar sesión."),
    ),
  );

  await expect(apiFetch("/turnos")).rejects.toBeInstanceOf(ApiProblem);
});

test("no reintenta ni renueva en las rutas /auth", async () => {
  let renovaciones = 0;
  configurarSesion({
    obtenerToken: () => null,
    refrescar: async () => {
      renovaciones += 1;
      return true;
    },
  });

  server.use(
    http.post("*/api/v1/auth/refresh", () =>
      problema(401, "SESION_INVALIDA", "Tu sesión expiró."),
    ),
  );

  const error = await apiFetch("/auth/refresh", { method: "POST" }).catch(
    (fallo: unknown) => fallo,
  );

  expect(error).toBeInstanceOf(ApiProblem);
  expect((error as ApiProblem).code).toBe("SESION_INVALIDA");
  expect(renovaciones).toBe(0);
});

test("un 204 devuelve undefined", async () => {
  server.use(
    http.post("*/api/v1/auth/logout", () => new HttpResponse(null, { status: 204 })),
  );

  await expect(apiFetch("/auth/logout", { method: "POST" })).resolves.toBeUndefined();
});
