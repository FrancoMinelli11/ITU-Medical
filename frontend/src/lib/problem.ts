export interface ProblemDetail {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance?: string;
  code: string;
  request_id: string;
  errors?: Array<{ field: string; message: string; type?: string }>;
}

export class ApiProblem extends Error {
  readonly status: number;
  readonly code: string;
  readonly title: string;
  readonly detail: string;
  readonly requestId: string;
  readonly errors: ProblemDetail["errors"];

  constructor(problem: ProblemDetail) {
    super(problem.detail);
    this.name = "ApiProblem";
    this.status = problem.status;
    this.code = problem.code;
    this.title = problem.title;
    this.detail = problem.detail;
    this.requestId = problem.request_id;
    this.errors = problem.errors;
  }
}

/** Texto para mostrar en pantalla a partir de cualquier error del cliente. */
export function mensajeDeError(error: unknown): string {
  if (error instanceof ApiProblem) {
    const campos = error.errors?.map((item) => item.message).join(" ");
    return campos ? `${error.detail} ${campos}` : error.detail;
  }
  if (error instanceof Error && error.message) return error.message;
  return "Ocurrió un error inesperado. Intentá de nuevo.";
}
