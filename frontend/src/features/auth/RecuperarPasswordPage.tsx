import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";

import { Alerta } from "@/components/ui/Alerta";
import { Boton } from "@/components/ui/Boton";
import { Campo } from "@/components/ui/Campo";
import { mensajeDeError } from "@/lib/problem";

import { authApi } from "./api";
import { AuthLayout } from "./AuthLayout";
import { recuperarSchema, type RecuperarForm } from "./validacion";

export function RecuperarPasswordPage() {
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RecuperarForm>({ resolver: zodResolver(recuperarSchema) });

  const enviar = handleSubmit(async (valores) => {
    setError(null);
    try {
      // RF-21: la respuesta es siempre genérica, exista o no el par correo + DNI.
      const datos = await authApi.recuperarPassword({
        email: valores.email,
        dni: valores.dni,
      });
      setMensaje(datos.mensaje);
    } catch (fallo) {
      setError(mensajeDeError(fallo));
    }
  });

  return (
    <AuthLayout
      titulo="Recuperar contraseña"
      descripcion="Ingresá tu correo y tu DNI juntos. Te enviamos un enlace para definir una contraseña nueva."
      pie={
        <Link className="font-medium text-brand-600 underline" to="/login">
          Volver al inicio de sesión
        </Link>
      }
    >
      {mensaje ? (
        <div className="space-y-3">
          <Alerta tipo="exito">{mensaje}</Alerta>
          <p className="text-sm text-slate-600">
            Revisá la bandeja de entrada y la carpeta de correo no deseado. El enlace
            vence en 1 hora.
          </p>
        </div>
      ) : (
        <form className="space-y-4" onSubmit={enviar} noValidate>
          {error && <Alerta tipo="error">{error}</Alerta>}
          <Campo
            etiqueta="Correo electrónico"
            type="email"
            autoComplete="email"
            error={errors.email?.message}
            {...register("email")}
          />
          <Campo
            etiqueta="DNI"
            inputMode="numeric"
            autoComplete="off"
            placeholder="Sin puntos"
            error={errors.dni?.message}
            {...register("dni")}
          />
          <Boton type="submit" cargando={isSubmitting}>
            Enviarme el enlace
          </Boton>
        </form>
      )}
    </AuthLayout>
  );
}
