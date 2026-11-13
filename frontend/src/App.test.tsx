import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import App from "./App";

test("muestra la pantalla inicial", () => {
  render(
    <MemoryRouter>
      <App />
    </MemoryRouter>,
  );

  expect(
    screen.getByRole("heading", { name: /sistema de turnos/i }),
  ).toBeInTheDocument();
});
