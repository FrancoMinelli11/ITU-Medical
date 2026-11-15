import { forwardRef, type ButtonHTMLAttributes } from "react";
import { twMerge } from "tailwind-merge";

export interface BotonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: "primario" | "secundario" | "peligro";
  cargando?: boolean;
}

export const Boton = forwardRef<HTMLButtonElement, BotonProps>(function Boton(
  { variante = "primario", cargando = false, className, children, disabled, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || cargando}
      className={twMerge(
        "inline-flex w-full items-center justify-center rounded-md px-4 py-2.5 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60",
        variante === "primario"
          ? "bg-brand-600 text-white hover:bg-brand-700"
          : variante === "peligro"
            ? "bg-rose-600 text-white hover:bg-rose-700 focus-visible:ring-rose-500"
            : "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50",
        className,
      )}
      {...props}
    >
      {cargando ? "Procesando…" : children}
    </button>
  );
});
