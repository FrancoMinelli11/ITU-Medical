import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useSearchParams } from "react-router-dom";

import { Alerta } from "@/components/ui/Alerta";
import { Boton } from "@/components/ui/Boton";
import { Campo } from "@/components/ui/Campo";
import { mensajeDeError } from "@/lib/problem";

import { authApi } from "./api";
import { AuthLayout } from "./AuthLayout";
import { reenviarSchema, type ReenviarForm } from "./validacion";

type Estado = "verificando" | "verificado" | "error" | "sin-token";

export function VerificarEmailPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [estado, setEstado] = useState<Estado>(token ? "verificando" : "sin-token");
  const [detalle, setDetalle] = useState<string | null>(null);
  const [avisoReenvio, setAvisoReenvio] = useState<string | null>(null);
  const [errorReenvio, setErrorReenvio] = useState<string | null>(null);
  // El token es de un solo uso: en StrictMode el efecto corre dos veces y la
  // segunda llamada marcaría el token como usado. Se verifica una sola vez.
  const yaVerificado = useRef(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ReenviarForm>({ resolver: zodResolver(reenviarSchema) });

  useEffect(() => {
    if (!token || yaVerificado.current) return;
    yaVerificado.current = true;

    void (async () => {
      try {
        const datos = await authApi.verificarEmail(token);
        setEstado("verificado");
        setDetalle(datos.mensaje);
      } catch (fallo) {
        setEstado("error");
        setDetalle(mensajeDeError(fallo));
      }
    })();
  }, [token]);

  const reenviar = handleSubmit(async (valores) => {
    setErrorReenvio(null);
    setAvisoReenvio(null);
    try {
      const datos = await authApi.reenviarVerificacion(valores.email);
      setAvisoReenvio(datos.mensaje);
    } catch (fallo) {
      setErrorReenvio(mensajeDeError(fallo));
    }
  });

  return (
    <AuthLayout
      titulo="Verificación de correo"
      pie={
        <Link className="font-medium text-brand-600 underline" to="/login">
          Volver al inicio de sesión
        </Link>
      }
    >
      <div className="space-y-5">
        {estado === "verificando" && <Alerta tipo="info">Verificando tu correo…</Alerta>}

        {estado === "verificado" && (
          <div className="space-y-3">
            <Alerta tipo="exito">{detalle ?? "Tu correo quedó verificado."}</Alerta>
            <p className="text-sm text-slate-600">
              Ya podés iniciar sesión y reservar tus turnos.
            </p>
            <Link
              className="inline-block text-sm font-medium text-brand-600 underline"
              to="/login"
            >
              Iniciar sesión
            </Link>
          </div>
        )}

        {estado === "error" && (
          <div className="space-y-3">
            <Alerta tipo="error">{detalle ?? "No pudimos verificar el correo."}</Alerta>
            <p className="text-sm text-slate-600">
              Pedí un enlace nuevo con tu correo electrónico.
            </p>
          </div>
        )}

        {estado === "sin-token" && (
          <Alerta tipo="info">
            Abrí el enlace que te enviamos por correo para verificar la cuenta. Si lo
            perdiste, pedí uno nuevo:
          </Alerta>
        )}

        {estado !== "verificado" && (
          <form
            className="space-y-4 border-t border-slate-200 pt-5"
            onSubmit={reenviar}
            noValidate
          >
            <Campo
              etiqueta="Correo electrónico"
              type="email"
              autoComplete="email"
              error={errors.email?.message}
              {...register("email")}
            />
            {errorReenvio && <Alerta tipo="error">{errorReenvio}</Alerta>}
            {avisoReenvio && <Alerta tipo="exito">{avisoReenvio}</Alerta>}
            <Boton type="submit" variante="secundario" cargando={isSubmitting}>
              Enviarme un enlace nuevo
            </Boton>
          </form>
        )}
      </div>
    </AuthLayout>
  );
}
