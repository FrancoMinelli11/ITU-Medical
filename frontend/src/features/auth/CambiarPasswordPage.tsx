import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";

import { Alerta } from "@/components/ui/Alerta";
import { Boton } from "@/components/ui/Boton";
import { Campo } from "@/components/ui/Campo";
import { mensajeDeError } from "@/lib/problem";

import { AuthLayout } from "./AuthLayout";
import { useAuth } from "./useAuth";
import { cambiarPasswordSchema, type CambiarPasswordForm } from "./validacion";

/**
 * RF-23: cambio de contraseña desde una sesión normal. El servidor revoca todas
 * las familias de refresh, así que después de guardar hay que volver a entrar.
 */
export function CambiarPasswordPage() {
  const { cambiarPassword } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CambiarPasswordForm>({ resolver: zodResolver(cambiarPasswordSchema) });

  const enviar = handleSubmit(async (valores) => {
    setError(null);
    try {
      await cambiarPassword(valores.password_actual, valores.password_nueva);
      navigate("/login", {
        replace: true,
        state: {
          aviso: "Contraseña actualizada. Iniciá sesión con tu contraseña nueva.",
        },
      });
    } catch (fallo) {
      setError(mensajeDeError(fallo));
    }
  });

  return (
    <AuthLayout
      titulo="Cambiar contraseña"
      descripcion="Al guardar se cierran todas las sesiones abiertas, incluida esta."
      pie={
        <Link className="font-medium text-brand-600 underline" to="/">
          Volver al inicio
        </Link>
      }
    >
      <form className="space-y-4" onSubmit={enviar} noValidate>
        {error && <Alerta tipo="error">{error}</Alerta>}
        <Campo
          etiqueta="Contraseña actual"
          type="password"
          autoComplete="current-password"
          error={errors.password_actual?.message}
          {...register("password_actual")}
        />
        <Campo
          etiqueta="Contraseña nueva"
          type="password"
          autoComplete="new-password"
          ayuda="Mínimo 10 caracteres, con letras y números."
          error={errors.password_nueva?.message}
          {...register("password_nueva")}
        />
        <Campo
          etiqueta="Repetir contraseña nueva"
          type="password"
          autoComplete="new-password"
          error={errors.confirmar?.message}
          {...register("confirmar")}
        />
        <Boton type="submit" cargando={isSubmitting}>
          Guardar contraseña
        </Boton>
      </form>
    </AuthLayout>
  );
}
