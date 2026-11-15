import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { Alerta } from "@/components/ui/Alerta";
import { Boton } from "@/components/ui/Boton";
import { Campo } from "@/components/ui/Campo";
import { mensajeDeError } from "@/lib/problem";

import { AuthLayout } from "./AuthLayout";
import { useAuth } from "./useAuth";
import { primerIngresoSchema, type PrimerIngresoForm } from "./validacion";

/**
 * CU-13: la cuenta se creó en recepción con el DNI como contraseña temporal.
 * La sesión ya está abierta, así que solo se pide la contraseña nueva.
 */
export function PrimerIngresoPage() {
  const { usuario, primerIngreso } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<PrimerIngresoForm>({ resolver: zodResolver(primerIngresoSchema) });

  if (!usuario) return <Navigate to="/login" replace />;
  if (!usuario.debe_cambiar_password) return <Navigate to="/" replace />;

  const enviar = handleSubmit(async (valores) => {
    setError(null);
    try {
      await primerIngreso(valores.password_nueva);
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
      titulo="Cambiá tu contraseña"
      descripcion="Es el primer ingreso a tu cuenta. Por seguridad, definí una contraseña propia antes de continuar."
      pie={
        <Link className="font-medium text-brand-600 underline" to="/login">
          Volver al inicio de sesión
        </Link>
      }
    >
      <form className="space-y-4" onSubmit={enviar} noValidate>
        <Alerta tipo="info">
          Tu contraseña actual es el DNI con el que ingresaste. Al guardar la nueva se
          cierran las sesiones abiertas y vas a tener que volver a entrar.
        </Alerta>
        {error && <Alerta tipo="error">{error}</Alerta>}
        <Campo
          etiqueta="Contraseña nueva"
          type="password"
          autoComplete="new-password"
          ayuda="Mínimo 10 caracteres, con letras y números. No puede ser tu DNI."
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
