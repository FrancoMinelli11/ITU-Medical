import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Alerta } from "@/components/ui/Alerta";
import { Boton } from "@/components/ui/Boton";
import { useAuth } from "@/features/auth/useAuth";
import type { Rol } from "@/features/auth/types";

const NOMBRE_ROL: Record<Rol, string> = {
  PACIENTE: "Paciente",
  RECEPCIONISTA: "Recepción",
  MEDICO: "Médico/a",
  ADMINISTRADOR: "Administrador/a",
};

export function InicioPage() {
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

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-4 px-6 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
              Sistema de Turnos
            </p>
            <p className="text-sm text-slate-600">
              {usuario.nombre} {usuario.apellido} · {NOMBRE_ROL[usuario.rol]}
            </p>
          </div>
          <Boton
            variante="secundario"
            className="w-auto"
            onClick={cerrarSesion}
            cargando={saliendo}
          >
            Cerrar sesión
          </Boton>
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-6 px-6 py-10">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">
          Hola, {usuario.nombre}
        </h1>

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

        <section className="grid gap-4 sm:grid-cols-2">
          <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-base font-semibold text-slate-900">Mi cuenta</h2>
            <dl className="mt-3 space-y-1 text-sm text-slate-600">
              <div className="flex justify-between gap-3">
                <dt>DNI</dt>
                <dd className="font-medium text-slate-900">{usuario.dni}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt>Correo</dt>
                <dd className="font-medium text-slate-900">{usuario.email}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt>Rol</dt>
                <dd className="font-medium text-slate-900">{NOMBRE_ROL[usuario.rol]}</dd>
              </div>
            </dl>
            <Link
              className="mt-4 inline-block text-sm font-medium text-brand-600 underline"
              to="/cambiar-password"
            >
              Cambiar contraseña
            </Link>
          </article>

          <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-base font-semibold text-slate-900">Turnos</h2>
            <p className="mt-3 text-sm text-slate-600">
              La agenda y la gestión de turnos se habilitan en el próximo hito del
              proyecto.
            </p>
          </article>
        </section>
      </main>
    </div>
  );
}
