import { Link, Route, Routes } from "react-router-dom";

import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { AppShell } from "@/components/layout/AppShell";
import { CambiarPasswordPage } from "@/features/auth/CambiarPasswordPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { PrimerIngresoPage } from "@/features/auth/PrimerIngresoPage";
import { RecuperarPasswordPage } from "@/features/auth/RecuperarPasswordPage";
import { RegistroPage } from "@/features/auth/RegistroPage";
import { RestablecerPasswordPage } from "@/features/auth/RestablecerPasswordPage";
import { VerificarEmailPage } from "@/features/auth/VerificarEmailPage";
import { InicioPage } from "@/features/inicio/InicioPage";
import { MedicoPage } from "@/features/medico/MedicoPage";
import { RecepcionPage } from "@/features/recepcion/RecepcionPage";
import { MisTurnosPage } from "@/features/turnos/MisTurnosPage";
import { ReservarTurnoPage } from "@/features/turnos/ReservarTurnoPage";
import { RutaProtegida } from "@/routes/RutaProtegida";
import { RutaPublica } from "@/routes/RutaPublica";

function NoEncontrado() {
  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col items-center justify-center px-6 text-center">
      <p className="text-sm font-semibold uppercase tracking-wide text-brand-600">404</p>
      <h1 className="mt-2 text-3xl font-bold text-slate-900">Página no encontrada</h1>
      <p className="mt-3 text-slate-600">
        El enlace puede estar mal escrito o la página ya no existe.
      </p>
      <Link className="mt-6 text-sm font-medium text-brand-600 underline" to="/">
        Volver al inicio
      </Link>
    </main>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route element={<RutaPublica />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/registro" element={<RegistroPage />} />
        </Route>

        {/* Abiertas con o sin sesión: se llega desde el enlace del correo y un
            usuario ya autenticado también puede pedir el reenvío. */}
        <Route path="/recuperar-password" element={<RecuperarPasswordPage />} />
        <Route path="/restablecer-password" element={<RestablecerPasswordPage />} />
        <Route path="/verificar-email" element={<VerificarEmailPage />} />

        <Route element={<RutaProtegida />}>
          <Route path="/cambiar-password" element={<CambiarPasswordPage />} />
          <Route path="/primer-ingreso" element={<PrimerIngresoPage />} />

          {/* Rutas principales envueltas en AppShell con Sidebar y Topbar */}
          <Route element={<AppShell />}>
            <Route path="/" element={<InicioPage />} />

            <Route element={<RutaProtegida roles={["PACIENTE"]} />}>
              <Route path="/turnos" element={<MisTurnosPage />} />
              <Route path="/turnos/reservar" element={<ReservarTurnoPage />} />
            </Route>

            <Route element={<RutaProtegida roles={["RECEPCIONISTA", "ADMINISTRADOR"]} />}>
              <Route path="/recepcion" element={<RecepcionPage />} />
            </Route>

            <Route element={<RutaProtegida roles={["MEDICO", "ADMINISTRADOR"]} />}>
              <Route path="/medico" element={<MedicoPage />} />
            </Route>
          </Route>
        </Route>

        <Route path="*" element={<NoEncontrado />} />
      </Routes>
    </ErrorBoundary>
  );
}
