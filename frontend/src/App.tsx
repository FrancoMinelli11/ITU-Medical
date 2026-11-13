import { Link, Route, Routes } from "react-router-dom";

function Inicio() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <p className="text-sm font-semibold uppercase tracking-wide text-brand-600">
        FASE 2 — Andamiaje
      </p>
      <h1 className="mt-3 text-4xl font-bold tracking-tight text-slate-900">
        Sistema de Turnos
      </h1>
      <p className="mt-4 text-lg text-slate-600">
        Gestión administrativa de turnos médicos. La interfaz funcional se implementa
        en la FASE 3.
      </p>
      <div className="mt-8 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Estado del proyecto</h2>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-slate-600">
          <li>API base y health checks disponibles.</li>
          <li>Migración inicial con exclusion constraints.</li>
          <li>Diseño técnico en docs/diseno.md.</li>
        </ul>
      </div>
    </main>
  );
}

function NoEncontrado() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-bold text-slate-900">Página no encontrada</h1>
      <Link className="mt-4 inline-block text-brand-600 underline" to="/">
        Volver al inicio
      </Link>
    </main>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Inicio />} />
      <Route path="*" element={<NoEncontrado />} />
    </Routes>
  );
}
