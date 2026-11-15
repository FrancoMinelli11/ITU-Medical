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
import { registroSchema, type RegistroForm } from "./validacion";

export function RegistroPage() {
  const [error, setError] = useState<string | null>(null);
  const [enviado, setEnviado] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegistroForm>({ resolver: zodResolver(registroSchema) });

  const enviar = handleSubmit(async (valores) => {
    setError(null);
    try {
      await authApi.registro({
        dni: valores.dni,
        email: valores.email,
        password: valores.password,
        nombre: valores.nombre,
        apellido: valores.apellido,
        ...(valores.telefono ? { telefono: valores.telefono } : {}),
        ...(valores.fecha_nacimiento
          ? { fecha_nacimiento: valores.fecha_nacimiento }
          : {}),
      });
      setEnviado(valores.email);
    } catch (fallo) {
      setError(mensajeDeError(fallo));
    }
  });

  if (enviado) {
    return (
      <AuthLayout
        titulo="Revisá tu correo"
        descripcion="Ya casi está."
        pie={
          <Link className="font-medium text-brand-600 underline" to="/login">
            Volver al inicio de sesión
          </Link>
        }
      >
        <div className="space-y-3">
          <Alerta tipo="exito">
            Te enviamos un enlace a <strong>{enviado}</strong>. Confirmalo para poder
            reservar turnos.
          </Alerta>
          <p className="text-sm text-slate-600">
            Podés iniciar sesión ahora mismo, pero la reserva de turnos se habilita cuando
            verificás el correo.
          </p>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      titulo="Crear cuenta"
      descripcion="Registrate para reservar turnos."
      pie={
        <p>
          ¿Ya tenés cuenta?{" "}
          <Link className="font-medium text-brand-600 underline" to="/login">
            Iniciá sesión
          </Link>
        </p>
      }
    >
      <form className="space-y-4" onSubmit={enviar} noValidate>
        {error && <Alerta tipo="error">{error}</Alerta>}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Campo
            etiqueta="Nombre"
            autoComplete="given-name"
            error={errors.nombre?.message}
            {...register("nombre")}
          />
          <Campo
            etiqueta="Apellido"
            autoComplete="family-name"
            error={errors.apellido?.message}
            {...register("apellido")}
          />
        </div>
        <Campo
          etiqueta="DNI"
          inputMode="numeric"
          placeholder="Sin puntos"
          error={errors.dni?.message}
          {...register("dni")}
        />
        <Campo
          etiqueta="Correo electrónico"
          type="email"
          autoComplete="email"
          ayuda="Lo usamos para verificar la cuenta y avisarte de tus turnos."
          error={errors.email?.message}
          {...register("email")}
        />
        <Campo
          etiqueta="Contraseña"
          type="password"
          autoComplete="new-password"
          ayuda="Mínimo 10 caracteres, con letras y números."
          error={errors.password?.message}
          {...register("password")}
        />
        <Campo
          etiqueta="Repetir contraseña"
          type="password"
          autoComplete="new-password"
          error={errors.confirmar?.message}
          {...register("confirmar")}
        />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Campo
            etiqueta="Teléfono (opcional)"
            type="tel"
            autoComplete="tel"
            error={errors.telefono?.message}
            {...register("telefono")}
          />
          <Campo
            etiqueta="Fecha de nacimiento (opcional)"
            type="date"
            error={errors.fecha_nacimiento?.message}
            {...register("fecha_nacimiento")}
          />
        </div>
        <Boton type="submit" cargando={isSubmitting}>
          Crear cuenta
        </Boton>
      </form>
    </AuthLayout>
  );
}
