import type { PropsWithChildren, ReactNode } from "react";
import { Link } from "react-router-dom";

interface AuthLayoutProps {
  titulo: string;
  descripcion?: string;
  pie?: ReactNode;
}

export function AuthLayout({
  titulo,
  descripcion,
  pie,
  children,
}: PropsWithChildren<AuthLayoutProps>) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <Link
            to="/"
            className="text-sm font-semibold uppercase tracking-wide text-brand-600"
          >
            Sistema de Turnos
          </Link>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900">
            {titulo}
          </h1>
          {descripcion && <p className="mt-2 text-sm text-slate-600">{descripcion}</p>}
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          {children}
        </div>
        {pie && <div className="mt-4 text-center text-sm text-slate-600">{pie}</div>}
      </div>
    </main>
  );
}
