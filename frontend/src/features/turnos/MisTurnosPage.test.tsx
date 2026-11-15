import { HttpResponse, http } from "msw";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { refreshDemo, usuarioDemo } from "@/test/fixtures";
import { renderApp, simularCookieCsrf } from "@/test/render";
import { server } from "@/test/server";

describe("MisTurnosPage", () => {
  it("muestra la lista de turnos próximos del paciente", async () => {
    simularCookieCsrf();
    server.use(
      http.post("*/api/v1/auth/refresh", () =>
        HttpResponse.json(refreshDemo(usuarioDemo({ rol: "PACIENTE" }))),
      ),
      http.get("*/api/v1/turnos", () =>
        HttpResponse.json({
          total: 1,
          items: [
            {
              id_turno: "t-1111",
              id_paciente: "p-1111",
              id_medico: "m-1111",
              fecha_hora: new Date(Date.now() + 48 * 3600 * 1000).toISOString(),
              duracion_minutos: 30,
              estado: "RESERVADO",
              fecha_hora_llegada: null,
              fecha_hora_cancelacion: null,
              motivo_cancelacion: null,
              detalle_cancelacion: null,
              medico_nombre: "Esteban",
              medico_apellido: "Gómez",
              especialidad_nombre: "Cardiología",
              paciente_nombre: "Ana",
              paciente_apellido: "Pérez",
              paciente_dni: "30111222",
              fecha_creacion: new Date().toISOString(),
            },
          ],
        }),
      ),
    );

    renderApp("/turnos");

    expect(await screen.findByRole("heading", { name: /mis turnos médicos/i })).toBeInTheDocument();
    expect(await screen.findByText(/dr\(a\)\. esteban gómez/i)).toBeInTheDocument();
    expect(screen.getByText(/cardiología/i)).toBeInTheDocument();
    expect(screen.getByText(/confirmado/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /cancelar turno/i })).toBeInTheDocument();
  });

  it("abre el modal de cancelación habitual al hacer clic en cancelar", async () => {
    const user = userEvent.setup();
    simularCookieCsrf();
    server.use(
      http.post("*/api/v1/auth/refresh", () =>
        HttpResponse.json(refreshDemo(usuarioDemo({ rol: "PACIENTE" }))),
      ),
      http.get("*/api/v1/turnos", () =>
        HttpResponse.json({
          total: 1,
          items: [
            {
              id_turno: "t-1111",
              id_paciente: "p-1111",
              id_medico: "m-1111",
              fecha_hora: new Date(Date.now() + 48 * 3600 * 1000).toISOString(),
              duracion_minutos: 30,
              estado: "RESERVADO",
              fecha_hora_llegada: null,
              fecha_hora_cancelacion: null,
              motivo_cancelacion: null,
              detalle_cancelacion: null,
              medico_nombre: "Esteban",
              medico_apellido: "Gómez",
              especialidad_nombre: "Cardiología",
              paciente_nombre: "Ana",
              paciente_apellido: "Pérez",
              paciente_dni: "30111222",
              fecha_creacion: new Date().toISOString(),
            },
          ],
        }),
      ),
      http.post("*/api/v1/turnos/t-1111/cancelar", () =>
        HttpResponse.json({ estado: "CANCELADO" }),
      ),
    );

    renderApp("/turnos");

    const botonCancelar = await screen.findByRole("button", { name: /cancelar turno/i });
    await user.click(botonCancelar);

    expect(await screen.findByRole("heading", { name: /cancelar turno/i })).toBeInTheDocument();
    expect(screen.getByText(/cancelación anticipada \(\+24 hs\)/i)).toBeInTheDocument();

    const botonConfirmar = screen.getByRole("button", { name: /confirmar cancelación/i });
    await user.click(botonConfirmar);

    await waitFor(() => {
      expect(screen.queryByRole("heading", { name: /cancelar turno/i })).not.toBeInTheDocument();
    });
  });
});
