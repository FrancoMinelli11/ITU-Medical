"""RF-02, RN-29, C3, CU-02 y P-04: pacientes vistos desde recepción."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.db.models.auditoria import Auditoria
from app.db.models.enums import RolUsuario
from app.db.models.notificacion import Notificacion
from app.db.models.usuario import Usuario
from app.db.session import SessionLocal

PASSWORD = "Password123!"
NUEVO: dict[str, Any] = {
    "dni": "31000111",
    "email": "carla.ruiz@example.com",
    "nombre": "Carla",
    "apellido": "Ruiz",
    "telefono": "1155551234",
    "fecha_nacimiento": "1985-03-15",
}


async def _recepcion(fabrica, sesion, *, password: str = PASSWORD):
    usuario = await fabrica.crear(
        rol=RolUsuario.RECEPCIONISTA,
        password=password,
        nombre="Rita",
        apellido="Recepción",
    )
    await sesion.login(usuario.dni, password)
    return usuario


async def test_alta_desde_recepcion(client, sesion, fabrica) -> None:
    await _recepcion(fabrica, sesion)

    respuesta = await client.post("/api/v1/pacientes", json=NUEVO, headers=sesion.mutacion())

    assert respuesta.status_code == 201, respuesta.text
    datos = respuesta.json()
    assert datos["dni"] == NUEVO["dni"]
    assert datos["email"] == NUEVO["email"]
    # RF-02: el correo se considera verificado y la contraseña debe cambiarse.
    assert datos["email_verificado"] is True
    assert datos["debe_cambiar_password"] is True
    assert datos["habilitado"] is True

    async with SessionLocal() as session:
        usuario = await session.scalar(select(Usuario).where(Usuario.dni == NUEVO["dni"]))
        assert usuario is not None
        assert usuario.rol == RolUsuario.PACIENTE
        # RF-02: no se envía correo de verificación en el alta por recepción.
        notificaciones = (
            await session.scalars(
                select(Notificacion).where(
                    Notificacion.id_usuario_destinatario == usuario.id_usuario
                )
            )
        ).all()
        assert notificaciones == []
        auditorias = (
            await session.scalars(
                select(Auditoria).where(Auditoria.id_usuario == usuario.id_usuario)
            )
        ).all()
        assert [fila.accion for fila in auditorias] == ["ALTA_PACIENTE_RECEPCION"]


async def test_cuenta_de_recepcion_usa_el_dni_y_bloquea_el_resto(
    client, sesion, fabrica, nuevo_client
) -> None:
    """P-04 / RN-29 / C3: ingresa con el DNI y no puede operar hasta cambiarlo."""
    await _recepcion(fabrica, sesion)
    alta = await client.post("/api/v1/pacientes", json=NUEVO, headers=sesion.mutacion())
    assert alta.status_code == 201

    paciente = nuevo_client()
    ingreso = await paciente.post(
        "/api/v1/auth/login", json={"dni": NUEVO["dni"], "password": NUEVO["dni"]}
    )
    assert ingreso.status_code == 200, ingreso.text
    datos = ingreso.json()
    assert datos["debe_cambiar_password"] is True
    assert datos["usuario"]["email_verificado"] is True

    # El 403 de C3 se verifica sobre una cuenta con rol habilitado para el
    # endpoint: un paciente recibiría SIN_PERMISO por rol antes que por el flag.
    staff_con_temporal = await fabrica.crear(
        rol=RolUsuario.RECEPCIONISTA, password=None, debe_cambiar_password=True
    )
    bloqueado = nuevo_client()
    temporal = await bloqueado.post(
        "/api/v1/auth/login",
        json={"dni": staff_con_temporal.dni, "password": staff_con_temporal.dni},
    )
    assert temporal.status_code == 200
    respuesta = await bloqueado.get(
        "/api/v1/pacientes",
        headers={"Authorization": f"Bearer {temporal.json()['access_token']}"},
    )
    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "CAMBIO_PASSWORD_REQUERIDO"


async def test_recepcion_no_requiere_cambio_de_password(client, sesion, fabrica) -> None:
    await _recepcion(fabrica, sesion)

    respuesta = await client.get("/api/v1/pacientes", headers=sesion.bearer)

    assert respuesta.status_code == 200


async def test_paciente_no_puede_listar(client, sesion, fabrica) -> None:
    paciente = await fabrica.crear(password=PASSWORD)
    await sesion.login(paciente.dni, PASSWORD)

    respuesta = await client.get("/api/v1/pacientes", headers=sesion.bearer)

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "SIN_PERMISO"


async def test_medico_no_puede_listar(client, sesion, fabrica) -> None:
    medico = await fabrica.crear(rol=RolUsuario.MEDICO, password=PASSWORD)
    await sesion.login(medico.dni, PASSWORD)

    respuesta = await client.get("/api/v1/pacientes", headers=sesion.bearer)

    assert respuesta.status_code == 403


async def test_sin_autenticacion_es_401(client) -> None:
    respuesta = await client.get("/api/v1/pacientes")

    assert respuesta.status_code == 401
    assert respuesta.headers["content-type"] == "application/problem+json"
    assert respuesta.json()["code"] == "NO_AUTENTICADO"


async def test_alta_exige_csrf(client, sesion, fabrica) -> None:
    await _recepcion(fabrica, sesion)

    respuesta = await client.post("/api/v1/pacientes", json=NUEVO, headers=sesion.bearer)

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "CSRF_INVALIDO"


async def test_alta_con_dni_duplicado(client, sesion, fabrica) -> None:
    await _recepcion(fabrica, sesion)
    await fabrica.crear(dni=NUEVO["dni"])

    respuesta = await client.post("/api/v1/pacientes", json=NUEVO, headers=sesion.mutacion())

    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "DNI_DUPLICADO"


async def test_listar_paginado(client, sesion, fabrica) -> None:
    await _recepcion(fabrica, sesion)
    for apellido in ("Alvarez", "Benitez", "Costa"):
        await fabrica.crear(apellido=apellido)

    primera = await client.get(
        "/api/v1/pacientes", params={"page": 1, "page_size": 2}, headers=sesion.bearer
    )

    assert primera.status_code == 200
    datos = primera.json()
    assert set(datos) == {"items", "page", "page_size", "total", "pages"}
    assert datos["page"] == 1
    assert datos["page_size"] == 2
    assert datos["total"] == 3
    assert datos["pages"] == 2
    assert [item["apellido"] for item in datos["items"]] == ["Alvarez", "Benitez"]

    segunda = await client.get(
        "/api/v1/pacientes", params={"page": 2, "page_size": 2}, headers=sesion.bearer
    )
    assert [item["apellido"] for item in segunda.json()["items"]] == ["Costa"]


async def test_listar_excluye_al_staff(client, sesion, fabrica) -> None:
    await _recepcion(fabrica, sesion)
    await fabrica.crear(rol=RolUsuario.MEDICO)
    await fabrica.crear(apellido="Paciente")

    respuesta = await client.get("/api/v1/pacientes", headers=sesion.bearer)

    assert respuesta.json()["total"] == 1


async def test_busqueda_por_dni_nombre_y_correo(client, sesion, fabrica) -> None:
    await _recepcion(fabrica, sesion)
    objetivo = await fabrica.crear(
        dni="31999888", nombre="Lucía", apellido="Fernández", email="lucia@example.com"
    )
    await fabrica.crear(nombre="Otro", apellido="Distinto")

    for consulta in ("31999888", "Lucía", "fernández", "lucia@example.com"):
        respuesta = await client.get(
            "/api/v1/pacientes", params={"q": consulta}, headers=sesion.bearer
        )
        items = respuesta.json()["items"]
        assert [item["id_usuario"] for item in items] == [str(objetivo.id_usuario)], consulta


async def test_obtener_por_id(client, sesion, fabrica) -> None:
    await _recepcion(fabrica, sesion)
    alta = await client.post("/api/v1/pacientes", json=NUEVO, headers=sesion.mutacion())
    id_paciente = alta.json()["id_paciente"]

    respuesta = await client.get(f"/api/v1/pacientes/{id_paciente}", headers=sesion.bearer)

    assert respuesta.status_code == 200
    assert respuesta.json()["id_paciente"] == id_paciente


async def test_obtener_inexistente(client, sesion, fabrica) -> None:
    await _recepcion(fabrica, sesion)

    respuesta = await client.get(
        "/api/v1/pacientes/00000000-0000-0000-0000-000000000000", headers=sesion.bearer
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "PACIENTE_NO_ENCONTRADO"


async def test_id_invalido_es_400(client, sesion, fabrica) -> None:
    await _recepcion(fabrica, sesion)

    respuesta = await client.get("/api/v1/pacientes/no-es-un-uuid", headers=sesion.bearer)

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "VALIDACION"


async def test_patch_actualiza_y_audita(client, sesion, fabrica) -> None:
    await _recepcion(fabrica, sesion)
    alta = await client.post("/api/v1/pacientes", json=NUEVO, headers=sesion.mutacion())
    id_paciente = alta.json()["id_paciente"]

    respuesta = await client.patch(
        f"/api/v1/pacientes/{id_paciente}",
        json={"telefono": "1166667777", "nombre": "Carolina"},
        headers=sesion.mutacion(),
    )

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["telefono"] == "1166667777"
    assert datos["nombre"] == "Carolina"

    async with SessionLocal() as session:
        auditoria = await session.scalar(
            select(Auditoria).where(Auditoria.accion == "MODIFICACION_PACIENTE")
        )
        assert auditoria is not None
        assert auditoria.datos_antes == {"nombre": "Carla", "telefono": "1155551234"}
        assert auditoria.datos_despues == {"nombre": "Carolina", "telefono": "1166667777"}


async def test_patch_sin_cambios_no_audita(client, sesion, fabrica) -> None:
    await _recepcion(fabrica, sesion)
    alta = await client.post("/api/v1/pacientes", json=NUEVO, headers=sesion.mutacion())
    id_paciente = alta.json()["id_paciente"]

    respuesta = await client.patch(
        f"/api/v1/pacientes/{id_paciente}",
        json={"nombre": NUEVO["nombre"]},
        headers=sesion.mutacion(),
    )

    assert respuesta.status_code == 200
    async with SessionLocal() as session:
        auditoria = await session.scalar(
            select(Auditoria).where(Auditoria.accion == "MODIFICACION_PACIENTE")
        )
        assert auditoria is None


async def test_patch_email_duplicado(client, sesion, fabrica) -> None:
    await _recepcion(fabrica, sesion)
    ocupado = await fabrica.crear(email="ocupado@example.com")
    alta = await client.post("/api/v1/pacientes", json=NUEVO, headers=sesion.mutacion())
    id_paciente = alta.json()["id_paciente"]

    respuesta = await client.patch(
        f"/api/v1/pacientes/{id_paciente}",
        json={"email": ocupado.email},
        headers=sesion.mutacion(),
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "EMAIL_DUPLICADO"


async def test_patch_vacio_es_400(client, sesion, fabrica) -> None:
    await _recepcion(fabrica, sesion)
    alta = await client.post("/api/v1/pacientes", json=NUEVO, headers=sesion.mutacion())
    id_paciente = alta.json()["id_paciente"]

    respuesta = await client.patch(
        f"/api/v1/pacientes/{id_paciente}", json={}, headers=sesion.mutacion()
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "VALIDACION"
