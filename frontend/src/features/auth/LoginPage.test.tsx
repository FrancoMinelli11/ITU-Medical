import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import { loginDemo, usuarioDemo } from "@/test/fixtures";
import { problema } from "@/test/handlers";
import { renderApp } from "@/test/render";
import { server } from "@/test/server";

async function ingresar(dni: string, password: string) {
  const usuario = userEvent.setup();
  await usuario.type(await screen.findByLabelText("DNI"), dni);
  await usuario.type(screen.getByLabelText("Contraseña"), password);
  await usuario.click(screen.getByRole("button", { name: /ingresar/i }));
}

test("el login exitoso entra al inicio", async () => {
  server.use(http.post("*/api/v1/auth/login", () => HttpResponse.json(loginDemo())));

  renderApp("/login");
  await ingresar("30111222", "Password123!");

  expect(await screen.findByRole("heading", { name: /hola, ana/i })).toBeInTheDocument();
});

test("las credenciales inválidas muestran el mensaje del servidor", async () => {
  server.use(
    http.post("*/api/v1/auth/login", () =>
      problema(401, "CREDENCIALES_INVALIDAS", "DNI o contraseña incorrectos."),
    ),
  );

  renderApp("/login");
  await ingresar("30111222", "Password123!");

  expect(await screen.findByRole("alert")).toHaveTextContent(
    /dni o contraseña incorrectos/i,
  );
});

test("valida el formato del DNI antes de llamar a la API", async () => {
  const usuario = userEvent.setup();
  renderApp("/login");

  await usuario.type(await screen.findByLabelText("DNI"), "123");
  await usuario.click(screen.getByRole("button", { name: /ingresar/i }));

  expect(await screen.findByText(/ingresá un dni de 7 u 8 dígitos/i)).toBeInTheDocument();
});

test("una cuenta con cambio pendiente va al primer ingreso", async () => {
  const pendiente = usuarioDemo({ debe_cambiar_password: true });
  server.use(
    http.post("*/api/v1/auth/login", () => HttpResponse.json(loginDemo(pendiente))),
  );

  renderApp("/login");
  await ingresar("30111222", "30111222");

  expect(
    await screen.findByRole("heading", { name: /cambiá tu contraseña/i }),
  ).toBeInTheDocument();
});

test("el bloqueo por intentos fallidos (429) se muestra al usuario", async () => {
  server.use(
    http.post("*/api/v1/auth/login", () =>
      problema(429, "RATE_LIMIT_EXCEDIDO", "Demasiados intentos. Probá más tarde."),
    ),
  );

  renderApp("/login");
  await ingresar("30111222", "Password123!");

  expect(await screen.findByRole("alert")).toHaveTextContent(/demasiados intentos/i);
});
