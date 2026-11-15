import { clsx } from "clsx";
import type { PropsWithChildren } from "react";

export type TipoAlerta = "error" | "exito" | "info";

const ESTILOS: Record<TipoAlerta, string> = {
  error: "border-red-200 bg-red-50 text-red-700",
  exito: "border-emerald-200 bg-emerald-50 text-emerald-800",
  info: "border-sky-200 bg-sky-50 text-sky-800",
};

export function Alerta({
  tipo = "info",
  children,
}: PropsWithChildren<{ tipo?: TipoAlerta }>) {
  return (
    <div
      role={tipo === "error" ? "alert" : "status"}
      className={clsx("rounded-md border px-3 py-2 text-sm", ESTILOS[tipo])}
    >
      {children}
    </div>
  );
}
