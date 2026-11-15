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
        const items =
          url.searchParams.get("id_especialidad") === "esp-1"
            ? [
                {
                  id_medico: "med-1",
                  id_usuario: "u-1",
                  id_especialidad: "esp-1",
                  nombre: "Laura",
                  apellido: "Vázquez",
                  matricula: "MN-9988",
                  activo: true,
                },
              ]
            : [];
        return HttpResponse.json({
          items,
          page: 1,
          page_size: 100,
          total: items.length,
          pages: items.length ? 1 : 0,
        });
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

  it("pide la disponibilidad con fecha_desde/fecha_hasta y muestra los horarios", async () => {
    const user = userEvent.setup();
    simularCookieCsrf();
    let consulta: URLSearchParams | null = null;
    server.use(
      http.post("*/api/v1/auth/refresh", () =>
        HttpResponse.json(refreshDemo(usuarioDemo({ rol: "PACIENTE" }))),
      ),
      http.get("*/api/v1/especialidades", () =>
        HttpResponse.json([{ id_especialidad: "esp-1", nombre: "Dermatología", activa: true }]),
      ),
      http.get("*/api/v1/medicos", () =>
        HttpResponse.json({
          items: [
            {
              id_medico: "med-1",
              id_usuario: "u-1",
              id_especialidad: "esp-1",
              nombre: "Laura",
              apellido: "Vázquez",
              matricula: null,
              activo: true,
            },
          ],
          page: 1,
          page_size: 100,
          total: 1,
          pages: 1,
        }),
      ),
      http.get("*/api/v1/medicos/med-1/disponibilidad", ({ request }) => {
        consulta = new URL(request.url).searchParams;
        // Forma real del backend: sin campo `disponible`.
        return HttpResponse.json({
          id_medico: "med-1",
          fecha_desde: consulta.get("fecha_desde"),
          fecha_hasta: consulta.get("fecha_hasta"),
          slots: [{ fecha_hora: "2030-01-01T13:00:00Z", duracion_minutos: 30 }],
        });
      }),
    );

    renderApp("/turnos/reservar");

    await user.selectOptions(await screen.findByLabelText(/1\. especialidad médica/i), "esp-1");
    await user.selectOptions(await screen.findByLabelText(/2\. profesional/i), "med-1");
    const selectFecha = await screen.findByLabelText(/3\. fecha/i);
    const primera = (selectFecha as HTMLSelectElement).querySelectorAll("option")[1].value;
    await user.selectOptions(selectFecha, primera);

    expect(await screen.findByRole("button", { name: /10:00/ })).toBeInTheDocument();
    expect(consulta).not.toBeNull();
    const params = consulta as unknown as URLSearchParams;
    expect(params.get("fecha_desde")).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(params.get("fecha_hasta")).toBe(params.get("fecha_desde"));
  });
});
