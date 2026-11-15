import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import { problema } from "@/test/handlers";
import { renderApp } from "@/test/render";
import { server } from "@/test/server";

test("restablece la contraseña y ofrece volver al login", async () => {
  server.use(
    http.post("*/api/v1/auth/restablecer-password", () =>
      HttpResponse.json({
        mensaje: "Contraseña actualizada. Iniciá sesión con la nueva.",
      }),
    ),
  );

  const usuario = userEvent.setup();
  renderApp("/restablecer-password?token=token-de-prueba-123456");

  await usuario.type(screen.getByLabelText("Contraseña nueva"), "NuevaClave456!");
  await usuario.type(screen.getByLabelText("Repetir contraseña nueva"), "NuevaClave456!");
  await usuario.click(screen.getByRole("button", { name: /guardar contraseña/i }));

  expect(await screen.findByRole("status")).toHaveTextContent(/contraseña actualizada/i);
});

test("un token inválido muestra el mensaje del servidor", async () => {
  server.use(
    http.post("*/api/v1/auth/restablecer-password", () =>
      problema(400, "TOKEN_USADO", "Este enlace ya se usó."),
    ),
  );

  const usuario = userEvent.setup();
  renderApp("/restablecer-password?token=token-usado-1234567");

  await usuario.type(screen.getByLabelText("Contraseña nueva"), "NuevaClave456!");
  await usuario.type(screen.getByLabelText("Repetir contraseña nueva"), "NuevaClave456!");
  await usuario.click(screen.getByRole("button", { name: /guardar contraseña/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent(/ya se usó/i);
});

test("sin token en la URL no muestra el formulario", async () => {
  renderApp("/restablecer-password");

  expect(
    await screen.findByText(/el enlace no incluye un token válido/i),
  ).toBeInTheDocument();
  expect(screen.queryByLabelText("Contraseña nueva")).not.toBeInTheDocument();
});
