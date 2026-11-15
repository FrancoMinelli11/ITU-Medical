import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useSearchParams } from "react-router-dom";

import { Alerta } from "@/components/ui/Alerta";
import { Boton } from "@/components/ui/Boton";
import { Campo } from "@/components/ui/Campo";
import { mensajeDeError } from "@/lib/problem";

import { authApi } from "./api";
import { AuthLayout } from "./AuthLayout";
import { restablecerSchema, type RestablecerForm } from "./validacion";

export function RestablecerPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [error, setError] = useState<string | null>(null);
  const [exito, setExito] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RestablecerForm>({ resolver: zodResolver(restablecerSchema) });

  const enviar = handleSubmit(async (valores) => {
    setError(null);
    try {
      const datos = await authApi.restablecerPassword({
        token,
        password: valores.password,
      });
      setExito(datos.mensaje);
    } catch (fallo) {
      setError(mensajeDeError(fallo));
    }
  });

  if (!token) {
    return (
      <AuthLayout titulo="Restablecer contraseña">
        <div className="space-y-4">
          <Alerta tipo="error">
            El enlace no incluye un token válido. Pedí uno nuevo desde la recuperación de
            contraseña.
          </Alerta>
          <Link
            className="inline-block text-sm font-medium text-brand-600 underline"
            to="/recuperar-password"
          >
            Pedir un enlace nuevo
          </Link>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      titulo="Restablecer contraseña"
      descripcion="Definí una contraseña nueva. Al guardarla se cierran todas las sesiones abiertas."
      pie={
        <Link className="font-medium text-brand-600 underline" to="/login">
          Volver al inicio de sesión
        </Link>
      }
    >
      {exito ? (
        <div className="space-y-3">
          <Alerta tipo="exito">{exito}</Alerta>
          <Link
            className="inline-block text-sm font-medium text-brand-600 underline"
            to="/login"
          >
            Iniciar sesión con la contraseña nueva
          </Link>
        </div>
      ) : (
        <form className="space-y-4" onSubmit={enviar} noValidate>
          {error && <Alerta tipo="error">{error}</Alerta>}
          <Campo
            etiqueta="Contraseña nueva"
            type="password"
            autoComplete="new-password"
            ayuda="Mínimo 10 caracteres, con letras y números."
            error={errors.password?.message}
            {...register("password")}
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
      )}
    </AuthLayout>
  );
}
