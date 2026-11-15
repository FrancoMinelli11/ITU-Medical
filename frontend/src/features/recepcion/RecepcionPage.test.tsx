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
            fecha_hora_llegada: "2026-11-15T09:55:00Z",
            orden_atencion: 1,
            en_tolerancia: true,
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
      http.get("*/api/v1/pacientes", ({ request }) => {
        // Regresión: el front debe enviar `q`, no `dni`.
        expect(new URL(request.url).searchParams.get("q")).toBe("38999111");
        const base = {
          id_usuario: "u", email: "x@example.com", telefono: null,
          fecha_nacimiento: null, habilitado: true, email_verificado: true,
        };
        return HttpResponse.json({
          items: [
            { ...base, id_paciente: "pac-000", dni: "20000000", nombre: "Camila", apellido: "Duarte" },
            { ...base, id_paciente: "pac-123", dni: "38999111", nombre: "Federico", apellido: "Ríos" },
          ],
          page: 1, page_size: 20, total: 2, pages: 1,
        });
      }),
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
    expect(screen.queryByText(/camila duarte/i)).not.toBeInTheDocument();
  });

  it("permite buscar turnos de hoy del paciente y registrar llegada con un clic", async () => {
    const user = userEvent.setup();
    simularCookieCsrf();
    let llamadaLlegadaTurnoId: string | null = null;

    server.use(
      http.post("*/api/v1/auth/refresh", () =>
        HttpResponse.json(refreshDemo(usuarioDemo({ rol: "RECEPCIONISTA" }))),
      ),
      http.get("*/api/v1/recepcion/sala-espera", () => HttpResponse.json([])),
      http.get("*/api/v1/pacientes", () =>
        HttpResponse.json({
          items: [
            {
              id_paciente: "pac-123",
              id_usuario: "u-123",
              dni: "38999111",
              email: "federico@example.com",
              nombre: "Federico",
              apellido: "Ríos",
              telefono: null,
              fecha_nacimiento: null,
              habilitado: true,
              email_verificado: true,
            },
          ],
          page: 1,
          page_size: 20,
          total: 1,
          pages: 1,
        }),
      ),
      http.get("*/api/v1/turnos", ({ request }) => {
        const url = new URL(request.url);
        expect(url.searchParams.get("id_paciente")).toBe("pac-123");
        expect(url.searchParams.get("estado")).toBe("RESERVADO");
        return HttpResponse.json({
          total: 1,
          items: [
            {
              id_turno: "turno-hoy-1",
              id_paciente: "pac-123",
              id_medico: "med-1",
              fecha_hora: "2026-11-15T15:00:00Z",
              duracion_minutos: 30,
              estado: "RESERVADO",
              fecha_hora_llegada: null,
              fecha_hora_cancelacion: null,
              motivo_cancelacion: null,
              detalle_cancelacion: null,
              medico_nombre: "María",
              medico_apellido: "López",
              especialidad_nombre: "Pediatría",
              paciente_nombre: "Federico",
              paciente_apellido: "Ríos",
              paciente_dni: "38999111",
              fecha_creacion: "2026-11-14T10:00:00Z",
            },
          ],
        });
      }),
      http.post("*/api/v1/recepcion/turnos/:id/llegada", ({ params }) => {
        llamadaLlegadaTurnoId = params.id as string;
        return HttpResponse.json({
          id_turno: params.id,
          estado: "EN_ESPERA",
          fecha_hora_llegada: new Date().toISOString(),
        });
      }),
    );

    renderApp("/recepcion");

    const inputDni = await screen.findByPlaceholderText(/ingresá dni del paciente/i);
    await user.type(inputDni, "38999111");

    const botonBuscarTurnos = screen.getByRole("button", { name: /buscar turnos de hoy/i });
    await user.click(botonBuscarTurnos);

    expect(await screen.findByText(/dr\(a\)\. maría lópez · pediatría/i)).toBeInTheDocument();
    const botonLlegada = screen.getByRole("button", { name: /registrar llegada/i });
    await user.click(botonLlegada);

    expect(await screen.findByText(/llegada registrada con éxito/i)).toBeInTheDocument();
    expect(llamadaLlegadaTurnoId).toBe("turno-hoy-1");
  });
});
