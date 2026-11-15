import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import { problema } from "@/test/handlers";
import { renderApp } from "@/test/render";
import { server } from "@/test/server";

test("con token válido verifica el correo automáticamente", async () => {
  server.use(
    http.post("*/api/v1/auth/verificar-email", () =>
      HttpResponse.json({
        email_verificado: true,
        mensaje: "Correo verificado. Ya podés reservar turnos.",
      }),
    ),
  );

  renderApp("/verificar-email?token=token-de-prueba-123456");

  expect(
    await screen.findByText(/correo verificado\. ya podés reservar turnos/i),
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Iniciar sesión" })).toBeInTheDocument();
});

test("un token vencido ofrece pedir uno nuevo", async () => {
  server.use(
    http.post("*/api/v1/auth/verificar-email", () =>
      problema(
        400,
        "TOKEN_EXPIRADO",
        "El enlace venció. Pedí uno nuevo desde el inicio de sesión.",
      ),
    ),
  );

  renderApp("/verificar-email?token=token-vencido-123456");

  expect(await screen.findByRole("alert")).toHaveTextContent(/el enlace venció/i);
  expect(
    screen.getByRole("button", { name: /enviarme un enlace nuevo/i }),
  ).toBeInTheDocument();
});

test("sin token se puede pedir el reenvío", async () => {
  server.use(
    http.post("*/api/v1/auth/reenviar-verificacion", () =>
      HttpResponse.json({
        mensaje:
          "Si el correo corresponde a una cuenta sin verificar, te enviamos un nuevo enlace.",
      }),
    ),
  );

  const usuario = userEvent.setup();
  renderApp("/verificar-email");

  await usuario.type(screen.getByLabelText("Correo electrónico"), "ana@example.com");
  await usuario.click(screen.getByRole("button", { name: /enviarme un enlace nuevo/i }));

  expect(await screen.findByText(/te enviamos un nuevo enlace/i)).toBeInTheDocument();
});
