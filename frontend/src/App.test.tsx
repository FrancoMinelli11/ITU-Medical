import { screen } from "@testing-library/react";

import { renderApp } from "@/test/render";

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
