import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { ErrorBoundary } from "./ErrorBoundary";

function ComponenteQueFalla({ debeFallar }: { debeFallar: boolean }) {
  if (debeFallar) {
    throw new Error("Fallo de prueba simulado");
  }
  return <div>Contenido sin fallas</div>;
}

describe("ErrorBoundary", () => {
  const originalError = console.error;

  beforeEach(() => {
    // Silencia el console.error esperado en las pruebas que fallan
    console.error = vi.fn();
  });

  afterEach(() => {
    console.error = originalError;
  });

  test("renderiza los hijos cuando no hay error", () => {
    render(
      <ErrorBoundary>
        <ComponenteQueFalla debeFallar={false} />
      </ErrorBoundary>,
    );

    expect(screen.getByText("Contenido sin fallas")).toBeInTheDocument();
  });

  test("muestra mensaje de alerta y botón de reintentar ante error no controlado", () => {
    render(
      <ErrorBoundary>
        <ComponenteQueFalla debeFallar={true} />
      </ErrorBoundary>,
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /algo salió mal/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reintentar/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /recargar página/i })).toBeInTheDocument();
  });

  test("permite reintentar tras recuperarse del error", async () => {
    const user = userEvent.setup();
    let debeFallar = true;

    const { rerender } = render(
      <ErrorBoundary>
        <ComponenteQueFalla debeFallar={debeFallar} />
      </ErrorBoundary>,
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();

    debeFallar = false;
    rerender(
      <ErrorBoundary>
        <ComponenteQueFalla debeFallar={debeFallar} />
      </ErrorBoundary>,
    );

    await user.click(screen.getByRole("button", { name: /reintentar/i }));

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText("Contenido sin fallas")).toBeInTheDocument();
  });
});
