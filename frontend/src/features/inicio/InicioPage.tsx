import { Link } from "react-router-dom";

import { AppNavbar } from "@/components/layout/AppNavbar";
import { Alerta } from "@/components/ui/Alerta";
import { useAuth } from "@/features/auth/useAuth";
import type { Rol } from "@/features/auth/types";

const NOMBRE_ROL: Record<Rol, string> = {
  PACIENTE: "Paciente",
  RECEPCIONISTA: "Recepción",
  MEDICO: "Médico/a",
  ADMINISTRADOR: "Administrador/a",
};

export function InicioPage() {
  const { usuario } = useAuth();

  if (!usuario) return null;

  const esPaciente = usuario.rol === "PACIENTE" || usuario.rol === "ADMINISTRADOR";
  const esStaff = usuario.rol === "RECEPCIONISTA" || usuario.rol === "ADMINISTRADOR";
  const esMedico = usuario.rol === "MEDICO" || usuario.rol === "ADMINISTRADOR";

  return (
    <div className="min-h-screen bg-slate-50">
      <AppNavbar />

      <main className="mx-auto max-w-5xl space-y-8 px-6 py-10">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">
            Hola, {usuario.nombre}
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Panel principal del Sistema de Gestión de Turnos Médicos.
          </p>
        </div>

        {!usuario.email_verificado && (
          <Alerta tipo="info">
            <p className="font-medium">Tu correo todavía no está verificado.</p>
            <p className="mt-1">
              Podés usar tu cuenta, pero la reserva de turnos se habilita cuando confirmás
              el correo.{" "}
              <Link className="font-medium underline" to="/verificar-email">
                Pedir un enlace nuevo
              </Link>
              .
            </p>
          </Alerta>
        )}

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {/* Módulos Paciente */}
          {esPaciente && (
            <>
              <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm hover:shadow-md transition flex flex-col justify-between">
                <div>
                  <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600 font-bold mb-3">
                    📅
                  </div>
                  <h2 className="text-lg font-bold text-slate-900">Mis Turnos</h2>
                  <p className="mt-2 text-sm text-slate-600">
                    Consultá tus turnos activos, historial de visitas y gestioná cancelaciones habituales o solicitudes rápidas.
                  </p>
                </div>
                <div className="mt-5 pt-3 border-t border-slate-100">
                  <Link
                    to="/turnos"
                    className="text-sm font-semibold text-brand-600 hover:text-brand-700"
                  >
                    Ver mis turnos →
                  </Link>
                </div>
              </article>

              <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm hover:shadow-md transition flex flex-col justify-between">
                <div>
                  <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-600 font-bold mb-3">
                    ✨
                  </div>
                  <h2 className="text-lg font-bold text-slate-900">Reservar Turno</h2>
                  <p className="mt-2 text-sm text-slate-600">
                    Elegí especialidad, seleccioná al profesional de tu preferencia y reservá tu horario en línea.
                  </p>
                </div>
                <div className="mt-5 pt-3 border-t border-slate-100">
                  <Link
                    to="/turnos/reservar"
                    className="text-sm font-semibold text-brand-600 hover:text-brand-700"
                  >
                    Iniciar reserva →
                  </Link>
                </div>
              </article>
            </>
          )}

          {/* Módulo Recepción */}
          {esStaff && (
            <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm hover:shadow-md transition flex flex-col justify-between">
              <div>
                <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600 font-bold mb-3">
                  🏥
                </div>
                <h2 className="text-lg font-bold text-slate-900">Módulo de Recepción</h2>
                <p className="mt-2 text-sm text-slate-600">
                  Búsqueda por DNI, registro de llegadas, sala de espera ordenada por prioridad, resolución de cancelaciones y cierre de jornada.
                </p>
              </div>
              <div className="mt-5 pt-3 border-t border-slate-100">
                <Link
                  to="/recepcion"
                  className="text-sm font-semibold text-emerald-600 hover:text-emerald-700"
                >
                  Abrir recepción →
                </Link>
              </div>
            </article>
          )}

          {/* Módulo Médico */}
          {esMedico && (
            <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm hover:shadow-md transition flex flex-col justify-between">
              <div>
                <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-purple-50 text-purple-600 font-bold mb-3">
                  🩺
                </div>
                <h2 className="text-lg font-bold text-slate-900">Consultorio Médico</h2>
                <p className="mt-2 text-sm text-slate-600">
                  Atención de pacientes en espera, visualización de agenda y registro de anotaciones clínicas confidenciales.
                </p>
              </div>
              <div className="mt-5 pt-3 border-t border-slate-100">
                <Link
                  to="/medico"
                  className="text-sm font-semibold text-purple-600 hover:text-purple-700"
                >
                  Ingresar al consultorio →
                </Link>
              </div>
            </article>
          )}

          {/* Ficha Mi Perfil */}
          <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm flex flex-col justify-between">
            <div>
              <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-600 font-bold mb-3">
                👤
              </div>
              <h2 className="text-lg font-bold text-slate-900">Mi Cuenta</h2>
              <dl className="mt-2 space-y-1.5 text-sm text-slate-600">
                <div className="flex justify-between gap-3">
                  <dt>DNI</dt>
                  <dd className="font-semibold text-slate-900">{usuario.dni}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt>Correo</dt>
                  <dd className="font-semibold text-slate-900">{usuario.email}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt>Rol</dt>
                  <dd className="font-semibold text-slate-900">{NOMBRE_ROL[usuario.rol]}</dd>
                </div>
              </dl>
            </div>
            <div className="mt-5 pt-3 border-t border-slate-100">
              <Link
                className="text-sm font-semibold text-brand-600 hover:text-brand-700"
                to="/cambiar-password"
              >
                Cambiar contraseña →
              </Link>
            </div>
          </article>
        </div>
      </main>
    </div>
  );
}
