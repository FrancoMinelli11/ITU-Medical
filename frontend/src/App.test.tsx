import { screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";

import { refreshDemo, usuarioDemo } from "@/test/fixtures";
import { renderApp } from "@/test/render";
import { server } from "@/test/server";

test("sin sesión, la raíz redirige al login", async () => {
  renderApp("/");

  expect(
    await screen.findByRole("heading", { name: /iniciar sesión/i }),
  ).toBeInTheDocument();
});

test("una ruta inexistente muestra el 404", async () => {
  renderApp("/no-existe");

  expect(
    await screen.findByRole("heading", { name: /página no encontrada/i }),
  ).toBeInTheDocument();
});

test("un paciente navegando a /recepcion es redirigido al inicio", async () => {
  server.use(
    http.post("*/api/v1/auth/refresh", () =>
      HttpResponse.json(refreshDemo(usuarioDemo({ rol: "PACIENTE", nombre: "Ana" }))),
    ),
  );

  renderApp("/recepcion");

  expect(
    await screen.findByRole("heading", { name: /hola, ana/i }),
  ).toBeInTheDocument();
  expect(screen.queryByText(/módulo de recepción/i)).not.toBeInTheDocument();
});
