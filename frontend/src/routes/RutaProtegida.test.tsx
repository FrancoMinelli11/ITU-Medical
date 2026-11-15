import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import type { ContextoAuth } from "@/features/auth/AuthContext";
import { AuthContext } from "@/features/auth/AuthContext";
import type { Usuario } from "@/features/auth/types";

import { RutaProtegida } from "./RutaProtegida";

function contexto(estado: ContextoAuth["estado"], usuario: Usuario | null): ContextoAuth {
  return {
    estado,
    usuario,
    login: async () => {
      throw new Error("no usado");
    },
    logout: async () => undefined,
    refrescar: async () => false,
    cambiarPassword: async () => undefined,
    primerIngreso: async () => undefined,
    actualizarUsuario: () => undefined,
  };
}

const ADMIN: Usuario = {
  id_usuario: "11111111-1111-1111-1111-111111111111",
  dni: "30111222",
  email: "admin@example.com",
  nombre: "Ada",
  apellido: "Admin",
  rol: "ADMINISTRADOR",
  email_verificado: true,
  debe_cambiar_password: false,
  ultimo_login: null,
};

const PACIENTE: Usuario = { ...ADMIN, rol: "PACIENTE" };

function montar(ruta: string, ctx: ContextoAuth) {
  return render(
    <AuthContext.Provider value={ctx}>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route path="/login" element={<p>pantalla de login</p>} />
          <Route path="/primer-ingreso" element={<p>pantalla de primer ingreso</p>} />
          <Route
            path="/admin"
            element={
              <RutaProtegida roles={["ADMINISTRADOR"]}>
                <p>solo administración</p>
              </RutaProtegida>
            }
          />
          <Route
            path="/"
            element={
              <RutaProtegida>
                <p>contenido privado</p>
              </RutaProtegida>
            }
          />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

test("mientras carga la sesión muestra el estado de espera", () => {
  montar("/", contexto("cargando", null));

  expect(screen.getByRole("status")).toHaveTextContent(/cargando/i);
});

test("sin sesión redirige al login", () => {
  montar("/", contexto("anonimo", null));

  expect(screen.getByText("pantalla de login")).toBeInTheDocument();
});

test("con sesión muestra el contenido privado", () => {
  montar("/", contexto("autenticado", PACIENTE));

  expect(screen.getByText("contenido privado")).toBeInTheDocument();
});

test("con cambio de contraseña pendiente encierra en el primer ingreso", () => {
  montar("/", contexto("autenticado", { ...PACIENTE, debe_cambiar_password: true }));

  expect(screen.getByText("pantalla de primer ingreso")).toBeInTheDocument();
});

test("con rol insuficiente vuelve al inicio", () => {
  montar("/admin", contexto("autenticado", PACIENTE));

  expect(screen.getByText("contenido privado")).toBeInTheDocument();
});

test("con rol suficiente entra a la ruta restringida", () => {
  montar("/admin", contexto("autenticado", ADMIN));

  expect(screen.getByText("solo administración")).toBeInTheDocument();
});
