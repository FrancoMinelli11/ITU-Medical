import { setupServer } from "msw/node";

import { handlers } from "./handlers";

/** Servidor msw de los tests (Vitest, entorno Node). */
export const server = setupServer(...handlers);
