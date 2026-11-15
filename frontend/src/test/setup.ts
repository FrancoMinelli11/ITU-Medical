import "@testing-library/jest-dom/vitest";

import { cleanup, configure } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";

import { server } from "./server";

configure({ asyncUtilTimeout: 5000 });

// Sin handlers sin manejar: si un test pega a un endpoint no previsto, falla en
// vez de intentar salir a la red.
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));

afterEach(() => {
  server.resetHandlers();
  cleanup();
  limpiarCookies();
});

afterAll(() => server.close());

function limpiarCookies(): void {
  for (const cookie of document.cookie.split(";")) {
    const nombre = cookie.split("=")[0]?.trim();
    if (nombre) document.cookie = `${nombre}=; Max-Age=0; path=/`;
  }
}
