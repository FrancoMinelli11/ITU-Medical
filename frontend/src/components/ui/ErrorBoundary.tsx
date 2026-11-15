import { Component, type ErrorInfo, type ReactNode } from "react";

import { Boton } from "./Boton";

export interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, State> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error("Error no controlado capturado por ErrorBoundary:", error, errorInfo);
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          role="alert"
          className="flex min-h-[300px] flex-col items-center justify-center p-6 text-center"
        >
          <div className="w-full max-w-md rounded-lg border border-red-200 bg-red-50 p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-red-800">Algo salió mal</h2>
            <p className="mt-2 text-sm text-red-600">
              Ocurrió un error inesperado al renderizar la vista. Podés intentar reintentar o recargar
              la página.
            </p>
            <div className="mt-4 flex gap-3">
              <Boton
                type="button"
                variante="primario"
                onClick={this.handleReset}
              >
                Reintentar
              </Boton>
              <Boton
                type="button"
                variante="secundario"
                onClick={() => window.location.reload()}
              >
                Recargar página
              </Boton>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
