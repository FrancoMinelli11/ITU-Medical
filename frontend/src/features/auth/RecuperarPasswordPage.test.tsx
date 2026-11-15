import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import { problema } from "@/test/handlers";
import { renderApp } from "@/test/render";
import { server } from "@/test/server";

const GENERICO =
  "Si los datos coinciden con una cuenta, te enviamos un correo para restablecer la contraseña.";

test("la solicitud muestra siempre la respuesta genérica", async () => {
  server.use(
    http.post("*/api/v1/auth/recuperar-password", () =>
      HttpResponse.json({ mensaje: GENERICO }),
    ),
  );

  const usuario = userEvent.setup();
  renderApp("/recuperar-password");

  await usuario.type(screen.getByLabelText("Correo electrónico"), "ana@example.com");
  await usuario.type(screen.getByLabelText("DNI"), "30111222");
  await usuario.click(screen.getByRole("button", { name: /enviarme el enlace/i }));

  expect(await screen.findByRole("status")).toHaveTextContent(/si los datos coinciden/i);
});

test("el límite de intentos (429) se informa", async () => {
  server.use(
    http.post("*/api/v1/auth/recuperar-password", () =>
      problema(429, "RATE_LIMIT_EXCEDIDO", "Hiciste demasiadas solicitudes."),
    ),
  );

  const usuario = userEvent.setup();
  renderApp("/recuperar-password");

  await usuario.type(screen.getByLabelText("Correo electrónico"), "ana@example.com");
  await usuario.type(screen.getByLabelText("DNI"), "30111222");
  await usuario.click(screen.getByRole("button", { name: /enviarme el enlace/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent(/demasiadas solicitudes/i);
});

test("exige correo y DNI juntos", async () => {
  renderApp("/recuperar-password");

  expect(
    await screen.findByRole("button", { name: /enviarme el enlace/i }),
  ).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: /revisá/i })).not.toBeInTheDocument();
});
