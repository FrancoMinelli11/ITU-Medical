import { z } from "zod";

/** RN-30: el DNI viaja y se valida siempre como texto. */
export const dniSchema = z
  .string()
  .trim()
  .regex(/^\d{7,8}$/, "Ingresá un DNI de 7 u 8 dígitos.");

/** RN-28: mínimo 10 caracteres, al menos una letra y un dígito. */
export const passwordSchema = z
  .string()
  .min(10, "La contraseña debe tener al menos 10 caracteres.")
  .max(128, "La contraseña no puede superar los 128 caracteres.")
  .refine(
    (valor) => /[A-Za-z]/.test(valor) && /\d/.test(valor),
    "La contraseña debe combinar letras y números.",
  );

export const emailSchema = z
  .string()
  .trim()
  .min(1, "Ingresá tu correo electrónico.")
  .email("Ingresá un correo electrónico válido.");

const nombreSchema = z
  .string()
  .trim()
  .min(1, "Este campo es obligatorio.")
  .max(80, "Máximo 80 caracteres.");

function obligatorio(mensaje: string) {
  return z.string().min(1, mensaje);
}

export const loginSchema = z.object({
  dni: dniSchema,
  password: obligatorio("Ingresá tu contraseña."),
});
export type LoginForm = z.infer<typeof loginSchema>;

export const registroSchema = z
  .object({
    nombre: nombreSchema,
    apellido: nombreSchema,
    dni: dniSchema,
    email: emailSchema,
    password: passwordSchema,
    confirmar: obligatorio("Repetí la contraseña."),
    telefono: z
      .string()
      .trim()
      .max(30, "Máximo 30 caracteres.")
      .optional()
      .or(z.literal("")),
    fecha_nacimiento: z.string().optional().or(z.literal("")),
  })
  .refine((datos) => datos.password === datos.confirmar, {
    path: ["confirmar"],
    message: "Las contraseñas no coinciden.",
  });
export type RegistroForm = z.infer<typeof registroSchema>;

export const recuperarSchema = z.object({
  email: emailSchema,
  dni: dniSchema,
});
export type RecuperarForm = z.infer<typeof recuperarSchema>;

export const reenviarSchema = z.object({ email: emailSchema });
export type ReenviarForm = z.infer<typeof reenviarSchema>;

export const restablecerSchema = z
  .object({
    password: passwordSchema,
    confirmar: obligatorio("Repetí la contraseña."),
  })
  .refine((datos) => datos.password === datos.confirmar, {
    path: ["confirmar"],
    message: "Las contraseñas no coinciden.",
  });
export type RestablecerForm = z.infer<typeof restablecerSchema>;

export const cambiarPasswordSchema = z
  .object({
    password_actual: obligatorio("Ingresá tu contraseña actual."),
    password_nueva: passwordSchema,
    confirmar: obligatorio("Repetí la nueva contraseña."),
  })
  .refine((datos) => datos.password_nueva === datos.confirmar, {
    path: ["confirmar"],
    message: "Las contraseñas no coinciden.",
  })
  .refine((datos) => datos.password_actual !== datos.password_nueva, {
    path: ["password_nueva"],
    message: "La nueva contraseña debe ser distinta de la actual.",
  });
export type CambiarPasswordForm = z.infer<typeof cambiarPasswordSchema>;

export const primerIngresoSchema = z
  .object({
    password_nueva: passwordSchema,
    confirmar: obligatorio("Repetí la nueva contraseña."),
  })
  .refine((datos) => datos.password_nueva === datos.confirmar, {
    path: ["confirmar"],
    message: "Las contraseñas no coinciden.",
  });
export type PrimerIngresoForm = z.infer<typeof primerIngresoSchema>;
