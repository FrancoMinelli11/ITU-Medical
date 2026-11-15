import { HttpResponse, http } from "msw";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { refreshDemo, usuarioDemo } from "@/test/fixtures";
import { renderApp, simularCookieCsrf } from "@/test/render";
import { server } from "@/test/server";

describe("ReservarTurnoPage", () => {
  it("permite seleccionar especialidad y cargar profesionales médicos", async () => {
    const user = userEvent.setup();
    simularCookieCsrf();
    server.use(
      http.post("*/api/v1/auth/refresh", () =>
        HttpResponse.json(refreshDemo(usuarioDemo({ rol: "PACIENTE" }))),
      ),
      http.get("*/api/v1/especialidades", () =>
        HttpResponse.json([
          { id_especialidad: "esp-1", nombre: "Dermatología", activa: true },
        ]),
      ),
      http.get("*/api/v1/medicos", ({ request }) => {
        const url = new URL(request.url);
        if (url.searchParams.get("id_especialidad") === "esp-1") {
          return HttpResponse.json([
            {
              id_medico: "med-1",
              id_usuario: "u-1",
              id_especialidad: "esp-1",
              nombre: "Laura",
              apellido: "Vázquez",
              matricula: "MN-9988",
              activo: true,
            },
          ]);
        }
        return HttpResponse.json([]);
      }),
    );

    renderApp("/turnos/reservar");

    expect(await screen.findByRole("heading", { name: /reservar turno médico/i })).toBeInTheDocument();
    const selectEspecialidad = await screen.findByLabelText(/1\. especialidad médica/i);
    expect(selectEspecialidad).toBeInTheDocument();

    await user.selectOptions(selectEspecialidad, "esp-1");

    expect(await screen.findByLabelText(/2\. profesional/i)).toBeInTheDocument();
    expect(screen.getByText(/dr\(a\)\. laura vázquez/i)).toBeInTheDocument();
  });
});
