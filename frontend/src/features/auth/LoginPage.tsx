import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { Alerta } from "@/components/ui/Alerta";
import { Boton } from "@/components/ui/Boton";
import { Campo } from "@/components/ui/Campo";
import { mensajeDeError } from "@/lib/problem";

import { AuthLayout } from "./AuthLayout";
import { useAuth } from "./useAuth";
import { loginSchema, type LoginForm } from "./validacion";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState<string | null>(null);
  const [aviso] = useState<string | null>(
    () => (location.state as { aviso?: string } | null)?.aviso ?? null,
  );
  const destino = (location.state as { desde?: string } | null)?.desde ?? "/";

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  const enviar = handleSubmit(async (valores) => {
    setError(null);
    try {
      const datos = await login(valores.dni, valores.password);
      navigate(datos.debe_cambiar_password ? "/primer-ingreso" : destino, {
        replace: true,
      });
    } catch (fallo) {
      setError(mensajeDeError(fallo));
    }
  });

  return (
    <AuthLayout
      titulo="Iniciar sesión"
      descripcion="Ingresá con tu DNI y contraseña."
      pie={
        <div className="space-y-1">
          <p>
            ¿No tenés cuenta?{" "}
            <Link className="font-medium text-brand-600 underline" to="/registro">
              Registrate
            </Link>
          </p>
          <p>
            <Link
              className="font-medium text-brand-600 underline"
              to="/recuperar-password"
            >
              Olvidé mi contraseña
            </Link>
          </p>
        </div>
      }
    >
      <form className="space-y-4" onSubmit={enviar} noValidate>
        {aviso && <Alerta tipo="exito">{aviso}</Alerta>}
        {error && <Alerta tipo="error">{error}</Alerta>}
        <Campo
          etiqueta="DNI"
          inputMode="numeric"
          autoComplete="username"
          placeholder="Sin puntos"
          error={errors.dni?.message}
          {...register("dni")}
        />
        <Campo
          etiqueta="Contraseña"
          type="password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...register("password")}
        />
        <Boton type="submit" cargando={isSubmitting}>
          Ingresar
        </Boton>
      </form>
    </AuthLayout>
  );
}
