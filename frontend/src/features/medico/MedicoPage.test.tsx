import { HttpResponse, http } from "msw";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { refreshDemo, usuarioDemo } from "@/test/fixtures";
import { renderApp, simularCookieCsrf } from "@/test/render";
import { server } from "@/test/server";

describe("MedicoPage", () => {
  it("muestra los turnos asignados y permite registrar la atención y notas médicas", async () => {
    const user = userEvent.setup();
    simularCookieCsrf();
    server.use(
      http.post("*/api/v1/auth/refresh", () =>
        HttpResponse.json(refreshDemo(usuarioDemo({ rol: "MEDICO", nombre: "Doctor" }))),
      ),
      http.get("*/api/v1/turnos", () =>
        HttpResponse.json({
          total: 1,
          items: [
            {
              id_turno: "turn-1",
              id_paciente: "pac-1",
              id_medico: "med-1",
              fecha_hora: "2026-11-15T11:00:00Z",
              duracion_minutos: 30,
              estado: "EN_ESPERA",
              fecha_hora_llegada: "2026-11-15T10:50:00Z",
              fecha_hora_cancelacion: null,
              motivo_cancelacion: null,
              detalle_cancelacion: null,
              medico_nombre: "Doctor",
              medico_apellido: "Clínico",
              especialidad_nombre: "Clínica Médica",
              paciente_nombre: "Juan",
              paciente_apellido: "Pérez",
              paciente_dni: "20111222",
              fecha_creacion: "2026-11-10T00:00:00Z",
            },
          ],
        }),
      ),
      http.get("*/api/v1/notas/paciente/pac-1", () =>
        HttpResponse.json([
          {
            id_nota: "nota-1",
            id_medico: "med-1",
            id_paciente: "pac-1",
            id_turno: "turn-1",
            contenido: "Paciente con buena respuesta al tratamiento.",
            fecha_creacion: "2026-11-10T11:30:00Z",
            fecha_modificacion: "2026-11-10T11:30:00Z",
            medico_nombre: "Doctor",
            medico_apellido: "Clínico",
            especialidad_nombre: "Clínica Médica",
          },
        ]),
      ),
      http.post("*/api/v1/turnos/turn-1/atender", () =>
        HttpResponse.json({
          id_turno: "turn-1",
          id_paciente: "pac-1",
          id_medico: "med-1",
          fecha_hora: "2026-11-15T11:00:00Z",
          duracion_minutos: 30,
          estado: "ATENDIDO",
          fecha_hora_llegada: "2026-11-15T10:50:00Z",
          fecha_hora_cancelacion: null,
          motivo_cancelacion: null,
          detalle_cancelacion: null,
          medico_nombre: "Doctor",
          medico_apellido: "Clínico",
          especialidad_nombre: "Clínica Médica",
          paciente_nombre: "Juan",
          paciente_apellido: "Pérez",
          paciente_dni: "20111222",
          fecha_creacion: "2026-11-10T00:00:00Z",
        }),
      ),
    );

    renderApp("/medico");

    expect(await screen.findByRole("heading", { name: /consultorio médico/i })).toBeInTheDocument();
    expect((await screen.findAllByText(/juan pérez/i)).length).toBeGreaterThan(0);
    expect(await screen.findByText(/buena respuesta al tratamiento/i)).toBeInTheDocument();

    const botonAtender = screen.getByRole("button", { name: /marcar como atendido/i });
    await user.click(botonAtender);

    expect(await screen.findByText(/atención registrada con éxito/i)).toBeInTheDocument();
  });
});
