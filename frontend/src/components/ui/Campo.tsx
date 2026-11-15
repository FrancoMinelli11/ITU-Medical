import { forwardRef, type InputHTMLAttributes } from "react";
import { twMerge } from "tailwind-merge";

export interface CampoProps extends InputHTMLAttributes<HTMLInputElement> {
  etiqueta: string;
  error?: string;
  ayuda?: string;
}

export const Campo = forwardRef<HTMLInputElement, CampoProps>(function Campo(
  { etiqueta, error, ayuda, id, className, ...props },
  ref,
) {
  const inputId = id ?? props.name;
  const ayudaId = ayuda ? `${inputId}-ayuda` : undefined;
  const errorId = error ? `${inputId}-error` : undefined;

  return (
    <div className="space-y-1.5">
      <label htmlFor={inputId} className="block text-sm font-medium text-slate-700">
        {etiqueta}
      </label>
      <input
        ref={ref}
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={[ayudaId, errorId].filter(Boolean).join(" ") || undefined}
        className={twMerge(
          "w-full rounded-md border px-3 py-2 text-sm text-slate-900 shadow-sm focus:outline-none focus:ring-1",
          error
            ? "border-red-400 focus:border-red-500 focus:ring-red-500"
            : "border-slate-300 focus:border-brand-500 focus:ring-brand-500",
          className,
        )}
        {...props}
      />
      {ayuda && !error && (
        <p id={ayudaId} className="text-xs text-slate-500">
          {ayuda}
        </p>
      )}
      {error && (
        <p id={errorId} role="alert" className="text-xs font-medium text-red-600">
          {error}
        </p>
      )}
    </div>
  );
});
