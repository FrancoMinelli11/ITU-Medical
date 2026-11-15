import { Boton } from "./Boton";

interface ModalConfirmacionProps {
  abierto: boolean;
  titulo: string;
  mensaje: string;
  textoConfirmar?: string;
  textoCancelar?: string;
  variante?: "primario" | "peligro";
  cargando?: boolean;
  onConfirmar: () => void;
  onCancelar: () => void;
}

export function ModalConfirmacion({
  abierto,
  titulo,
  mensaje,
  textoConfirmar = "Confirmar",
  textoCancelar = "Cancelar",
  variante = "peligro",
  cargando = false,
  onConfirmar,
  onCancelar,
}: ModalConfirmacionProps) {
  if (!abierto) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-titulo"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm"
    >
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl border border-slate-200 space-y-4">
        <h3 id="modal-titulo" className="text-lg font-bold text-slate-900">
          {titulo}
        </h3>
        <p className="text-sm text-slate-600">{mensaje}</p>
        <div className="flex justify-end gap-3 pt-2">
          <Boton
            type="button"
            variante="secundario"
            className="w-auto text-xs"
            onClick={onCancelar}
            disabled={cargando}
          >
            {textoCancelar}
          </Boton>
          <Boton
            type="button"
            variante={variante}
            className="w-auto text-xs"
            cargando={cargando}
            onClick={onConfirmar}
          >
            {textoConfirmar}
          </Boton>
        </div>
      </div>
    </div>
  );
}
