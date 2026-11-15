/** Espera a que el bootstrap de sesión termine de resolver. */
export function Cargando() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50">
      <p role="status" className="text-sm text-slate-600">
        Cargando…
      </p>
    </main>
  );
}
