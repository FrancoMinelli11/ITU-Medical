import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Boton } from "@/components/ui/Boton";
import { useAuth } from "@/features/auth/useAuth";
import type { Rol } from "@/features/auth/types";

const NOMBRE_ROL: Record<Rol, string> = {
  PACIENTE: "Paciente",
  RECEPCIONISTA: "Recepción",
  MEDICO: "Médico/a",
  ADMINISTRADOR: "Administrador/a",
};

const COLOR_ROL: Record<Rol, string> = {
  PACIENTE: "bg-blue-50 text-blue-700 border-blue-200",
  RECEPCIONISTA: "bg-emerald-50 text-emerald-700 border-emerald-200",
  MEDICO: "bg-purple-50 text-purple-700 border-purple-200",
  ADMINISTRADOR: "bg-amber-50 text-amber-700 border-amber-200",
};

export function AppNavbar() {
  const { usuario, logout } = useAuth();
  const navigate = useNavigate();
  const [saliendo, setSaliendo] = useState(false);

  if (!usuario) return null;

  const cerrarSesion = async () => {
    setSaliendo(true);
    try {
      await logout();
    } finally {
      navigate("/login", { replace: true });
    }
  };

  const esPaciente = usuario.rol === "PACIENTE";
  const esStaff = usuario.rol === "RECEPCIONISTA" || usuario.rol === "ADMINISTRADOR";
  const esMedico = usuario.rol === "MEDICO" || usuario.rol === "ADMINISTRADOR";

  return (
    <header className="border-b border-slate-200 bg-white shadow-sm sticky top-0 z-20">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-3.5">
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white font-bold text-sm">
              IT
            </span>
            <span className="font-bold text-slate-900 tracking-tight text-lg">
              ITU Medical
            </span>
          </Link>

          <nav className="flex items-center gap-1 sm:gap-2">
            <Link
              to="/"
              className="px-3 py-1.5 rounded-lg text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition"
            >
              Inicio
            </Link>

            {esPaciente && (
              <>
                <Link
                  to="/turnos"
                  className="px-3 py-1.5 rounded-lg text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition"
                >
                  Mis Turnos
                </Link>
                <Link
                  to="/turnos/reservar"
                  className="px-3 py-1.5 rounded-lg text-sm font-medium text-brand-600 hover:bg-brand-50 transition"
                >
                  + Reservar Turno
                </Link>
              </>
            )}

            {esStaff && (
              <Link
                to="/recepcion"
                className="px-3 py-1.5 rounded-lg text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition"
              >
                Recepción & Espera
              </Link>
            )}

            {esMedico && (
              <Link
                to="/medico"
                className="px-3 py-1.5 rounded-lg text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition"
              >
                Consultorio Médico
              </Link>
            )}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <span
            className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${COLOR_ROL[usuario.rol]}`}
          >
            {NOMBRE_ROL[usuario.rol]}
          </span>
          <span className="hidden sm:inline text-sm font-medium text-slate-700">
            {usuario.nombre} {usuario.apellido}
          </span>
          <Boton
            variante="secundario"
            className="w-auto text-xs py-1.5 px-3"
            onClick={cerrarSesion}
            cargando={saliendo}
          >
            Cerrar sesión
          </Boton>
        </div>
      </div>
    </header>
  );
}
