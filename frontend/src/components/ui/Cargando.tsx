/** Indicador de estado de carga. */
export function Cargando({ texto = "Cargando…" }: { texto?: string } = {}) {
  return (
    <div className="flex items-center justify-center p-4">
      <p role="status" className="text-sm text-slate-600">
        {texto}
      </p>
    </div>
  );
}
