import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import { refreshDemo, usuarioDemo } from "@/test/fixtures";
import { problema } from "@/test/handlers";
import { renderApp } from "@/test/render";
import { server } from "@/test/server";

const PENDIENTE = usuarioDemo({ debe_cambiar_password: true, email_verificado: false });

function sesionCon(usuario = PENDIENTE) {
  server.use(
    http.post("*/api/v1/auth/refresh", () => HttpResponse.json(refreshDemo(usuario))),
  );
}

test("la cuenta con cambio pendiente queda encerrada en el primer ingreso", async () => {
  sesionCon();

  renderApp("/cambiar-password");

  expect(
    await screen.findByRole("heading", { name: /cambiá tu contraseña/i }),
  ).toBeInTheDocument();
});

test("el primer ingreso guarda la contraseña y vuelve al login", async () => {
  sesionCon();
  server.use(
    http.post(
      "*/api/v1/auth/primer-ingreso",
      () => new HttpResponse(null, { status: 204 }),
    ),
  );

  const usuario = userEvent.setup();
  renderApp("/");

  await usuario.type(await screen.findByLabelText("Contraseña nueva"), "NuevaClave456!");
  await usuario.type(screen.getByLabelText("Repetir contraseña nueva"), "NuevaClave456!");
  await usuario.click(screen.getByRole("button", { name: /guardar contraseña/i }));

  expect(await screen.findByText(/contraseña actualizada/i)).toBeInTheDocument();
  expect(
    await screen.findByRole("heading", { name: /iniciar sesión/i }),
  ).toBeInTheDocument();
});

test("un error del servidor se muestra en el formulario", async () => {
  sesionCon();
  server.use(
    http.post("*/api/v1/auth/primer-ingreso", () =>
      problema(400, "PASSWORD_SIN_CAMBIOS", "La nueva contraseña debe ser distinta."),
    ),
  );

  const usuario = userEvent.setup();
  renderApp("/primer-ingreso");

  await usuario.type(await screen.findByLabelText("Contraseña nueva"), "NuevaClave456!");
  await usuario.type(screen.getByLabelText("Repetir contraseña nueva"), "NuevaClave456!");
  await usuario.click(screen.getByRole("button", { name: /guardar contraseña/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent(/distinta/i);
});

test("sin cambio pendiente, el primer ingreso redirige al inicio", async () => {
  sesionCon(usuarioDemo({ nombre: "Bruno" }));

  renderApp("/primer-ingreso");

  expect(
    await screen.findByRole("heading", { name: /hola, bruno/i }),
  ).toBeInTheDocument();
});
