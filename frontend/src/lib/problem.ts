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
