export function formatFechaHora(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  return new Intl.DateTimeFormat("es-AR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "America/Argentina/Buenos_Aires",
  }).format(date);
}

export function formatHora(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  return new Intl.DateTimeFormat("es-AR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "America/Argentina/Buenos_Aires",
  }).format(date);
}

export function formatFecha(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  return new Intl.DateTimeFormat("es-AR", {
    dateStyle: "medium",
    timeZone: "America/Argentina/Buenos_Aires",
  }).format(date);
}

export function formatPartesFecha(value: string | Date): {
  diaNumero: string;
  mesAbrev: string;
  diaSemana: string;
  diaMesTexto: string;
  horaTexto: string;
} {
  const date = typeof value === "string" ? new Date(value) : value;
  const timeZone = "America/Argentina/Buenos_Aires";
  const diaNumero = new Intl.DateTimeFormat("es-AR", { day: "2-digit", timeZone }).format(date);
  const mesAbrev = new Intl.DateTimeFormat("es-AR", { month: "short", timeZone })
    .format(date)
    .replace(".", "")
    .toUpperCase();
  const diaSemana = new Intl.DateTimeFormat("es-AR", { weekday: "long", timeZone }).format(date);
  const diaMesTexto = new Intl.DateTimeFormat("es-AR", { day: "numeric", month: "long", timeZone }).format(date);
  const horaTexto = new Intl.DateTimeFormat("es-AR", { hour: "2-digit", minute: "2-digit", timeZone }).format(date);

  return {
    diaNumero,
    mesAbrev,
    diaSemana: diaSemana.charAt(0).toUpperCase() + diaSemana.slice(1),
    diaMesTexto,
    horaTexto,
  };
}
