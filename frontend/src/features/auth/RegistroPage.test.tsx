import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import { problema } from "@/test/handlers";
import { renderApp } from "@/test/render";
import { server } from "@/test/server";

const PACIENTE = {
  id_paciente: "22222222-2222-2222-2222-222222222222",
  id_usuario: "11111111-1111-1111-1111-111111111111",
  dni: "30111222",
  email: "ana@example.com",
  nombre: "Ana",
  apellido: "Perez",
  telefono: null,
  fecha_nacimiento: null,
  email_verificado: false,
  habilitado: true,
  debe_cambiar_password: false,
  fecha_creacion: "2026-11-15T10:00:00Z",
};

async function completar(datos: { password: string; confirmar: string }) {
  const usuario = userEvent.setup();
  await usuario.type(await screen.findByLabelText("Nombre"), "Ana");
  await usuario.type(screen.getByLabelText("Apellido"), "Perez");
  await usuario.type(screen.getByLabelText("DNI"), "30111222");
  await usuario.type(screen.getByLabelText("Correo electrónico"), "ana@example.com");
  await usuario.type(screen.getByLabelText("Contraseña"), datos.password);
  await usuario.type(screen.getByLabelText("Repetir contraseña"), datos.confirmar);
  await usuario.click(screen.getByRole("button", { name: /crear cuenta/i }));
  return usuario;
}

test("el registro exitoso pide verificar el correo", async () => {
  server.use(
    http.post("*/api/v1/auth/registro", () =>
      HttpResponse.json(PACIENTE, { status: 201 }),
    ),
  );

  renderApp("/registro");
  await completar({ password: "Password123!", confirmar: "Password123!" });

  expect(
    await screen.findByRole("heading", { name: /revisá tu correo/i }),
  ).toBeInTheDocument();
  expect(screen.getByText(/ana@example.com/)).toBeInTheDocument();
});

test("la contraseña débil se rechaza en el cliente (RN-28)", async () => {
  renderApp("/registro");
  await completar({ password: "corta", confirmar: "corta" });

  expect(await screen.findByText(/al menos 10 caracteres/i)).toBeInTheDocument();
});

test("las contraseñas distintas no se envían", async () => {
  renderApp("/registro");
  await completar({ password: "Password123!", confirmar: "Password456!" });

  expect(await screen.findByText(/no coinciden/i)).toBeInTheDocument();
});

test("un DNI ya registrado muestra el conflicto del servidor", async () => {
  server.use(
    http.post("*/api/v1/auth/registro", () =>
      problema(409, "DNI_DUPLICADO", "Ya existe una cuenta con ese DNI."),
    ),
  );

  renderApp("/registro");
  await completar({ password: "Password123!", confirmar: "Password123!" });

  expect(await screen.findByRole("alert")).toHaveTextContent(/ya existe una cuenta/i);
});
