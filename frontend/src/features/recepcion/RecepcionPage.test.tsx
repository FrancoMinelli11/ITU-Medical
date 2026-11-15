import { HttpResponse, http } from "msw";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { refreshDemo, usuarioDemo } from "@/test/fixtures";
import { renderApp, simularCookieCsrf } from "@/test/render";
import { server } from "@/test/server";

describe("RecepcionPage", () => {
  it("muestra la sala de espera ordenada con indicadores de prioridad y tolerancia", async () => {
    simularCookieCsrf();
    server.use(
      http.post("*/api/v1/auth/refresh", () =>
        HttpResponse.json(refreshDemo(usuarioDemo({ rol: "RECEPCIONISTA" }))),
      ),
      http.get("*/api/v1/recepcion/sala-espera", () =>
        HttpResponse.json([
          {
            id_turno: "t-1",
            id_paciente: "p-1",
            id_medico: "m-1",
            fecha_hora: "2026-11-15T10:00:00Z",
            duracion_minutos: 30,
            estado: "EN_ESPERA",
            fecha_hora_llegada: "2026-11-15T09:55:00Z",
            orden_prioridad: 1,
            esta_en_tolerancia: true,
            medico_nombre: "María",
            medico_apellido: "López",
            especialidad_nombre: "Pediatría",
            paciente_nombre: "Lucas",
            paciente_apellido: "Martínez",
            paciente_dni: "44111222",
          },
        ]),
      ),
    );

    renderApp("/recepcion");

    expect(await screen.findByRole("heading", { name: /módulo de recepción/i })).toBeInTheDocument();
    expect(await screen.findByText(/lucas martínez/i)).toBeInTheDocument();
    expect(screen.getByText(/pediatría/i)).toBeInTheDocument();
    expect((await screen.findAllByText(/en tolerancia/i)).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /ausente/i })).toBeInTheDocument();
  });

  it("permite navegar a la pestaña de pacientes y buscar por DNI", async () => {
    const user = userEvent.setup();
    simularCookieCsrf();
    server.use(
      http.post("*/api/v1/auth/refresh", () =>
        HttpResponse.json(refreshDemo(usuarioDemo({ rol: "RECEPCIONISTA" }))),
      ),
      http.get("*/api/v1/recepcion/sala-espera", () => HttpResponse.json([])),
      http.get("*/api/v1/pacientes", () =>
        HttpResponse.json({
          total: 1,
          items: [
            {
              id_paciente: "pac-123",
              id_usuario: "u-123",
              dni: "38999111",
              email: "paciente@example.com",
              nombre: "Federico",
              apellido: "Ríos",
              telefono: "1122334455",
              fecha_nacimiento: null,
              habilitado: true,
              email_verificado: true,
            },
          ],
        }),
      ),
      http.get("*/api/v1/restricciones/paciente/pac-123", () =>
        HttpResponse.json({
          id_paciente: "pac-123",
          id_usuario: "u-123",
          es_usuario_rojo: false,
          restriccion_activa: null,
        }),
      ),
    );

    renderApp("/recepcion");

    const tabPacientes = await screen.findByRole("button", { name: /pacientes & dni/i });
    await user.click(tabPacientes);

    const inputBusqueda = screen.getByPlaceholderText(/ingresá dni del paciente/i);
    await user.type(inputBusqueda, "38999111");

    const botonBuscar = screen.getByRole("button", { name: /buscar/i });
    await user.click(botonBuscar);

    expect(await screen.findByText(/federico ríos/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sancionar \(usuario rojo\)/i })).toBeInTheDocument();
  });
});
