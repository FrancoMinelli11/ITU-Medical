"""Esquema inicial del sistema de turnos.

Revision ID: 20261113_0001
Revises:
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261113_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


rol_usuario = postgresql.ENUM(
    "PACIENTE",
    "RECEPCIONISTA",
    "MEDICO",
    "ADMINISTRADOR",
    name="rol_usuario",
    create_type=False,
)
estado_turno = postgresql.ENUM(
    "RESERVADO",
    "EN_ESPERA",
    "ATENDIDO",
    "CANCELADO",
    "AUSENTE",
    name="estado_turno",
    create_type=False,
)
motivo_cancelacion = postgresql.ENUM(
    "HABITUAL",
    "RAPIDA",
    "BLOQUEO_AGENDA",
    "CAMBIO_HORARIO",
    "DESHABILITACION_MEDICO",
    "DESHABILITACION_PACIENTE",
    "RETIRO_VOLUNTARIO",
    "OTRO",
    name="motivo_cancelacion",
    create_type=False,
)
estado_solicitud_cancelacion = postgresql.ENUM(
    "PENDIENTE",
    "APROBADA",
    "RECHAZADA",
    name="estado_solicitud_cancelacion",
    create_type=False,
)
tipo_notificacion = postgresql.ENUM(
    "VERIFICACION_EMAIL",
    "RECUPERACION_PASSWORD",
    "CONFIRMACION_TURNO",
    "CANCELACION_TURNO",
    "TURNO_AFECTADO_POR_AGENDA",
    "RESTRICCION_USUARIO_ROJO",
    "RECORDATORIO_24H",
    name="tipo_notificacion",
    create_type=False,
)
estado_notificacion = postgresql.ENUM(
    "PENDIENTE",
    "ENVIADA",
    "FALLIDA",
    name="estado_notificacion",
    create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.execute(
        "CREATE TYPE rol_usuario AS ENUM ('PACIENTE', 'RECEPCIONISTA', 'MEDICO', 'ADMINISTRADOR')"
    )
    op.execute(
        "CREATE TYPE estado_turno AS ENUM "
        "('RESERVADO', 'EN_ESPERA', 'ATENDIDO', 'CANCELADO', 'AUSENTE')"
    )
    op.execute(
        "CREATE TYPE motivo_cancelacion AS ENUM "
        "('HABITUAL', 'RAPIDA', 'BLOQUEO_AGENDA', 'CAMBIO_HORARIO', "
        "'DESHABILITACION_MEDICO', 'DESHABILITACION_PACIENTE', "
        "'RETIRO_VOLUNTARIO', 'OTRO')"
    )
    op.execute(
        "CREATE TYPE estado_solicitud_cancelacion AS ENUM ('PENDIENTE', 'APROBADA', 'RECHAZADA')"
    )
    op.execute(
        "CREATE TYPE tipo_notificacion AS ENUM "
        "('VERIFICACION_EMAIL', 'RECUPERACION_PASSWORD', 'CONFIRMACION_TURNO', "
        "'CANCELACION_TURNO', 'TURNO_AFECTADO_POR_AGENDA', "
        "'RESTRICCION_USUARIO_ROJO', 'RECORDATORIO_24H')"
    )
    op.execute("CREATE TYPE estado_notificacion AS ENUM ('PENDIENTE', 'ENVIADA', 'FALLIDA')")

    # `timestamptz + interval` es STABLE (depende del TimeZone de la sesión), por lo
    # que no puede usarse dentro de un índice. Esta función calcula el fin del turno
    # en UTC explícito y es IMMUTABLE, requisito de las exclusion constraints.
    # Para intervalos de solo minutos, la aritmética en UTC coincide con la absoluta.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION rango_turno(
            timestamptz,
            integer
        ) RETURNS tstzrange
        LANGUAGE sql
        IMMUTABLE
        PARALLEL SAFE
        RETURNS NULL ON NULL INPUT
        AS $$
            SELECT tstzrange(
                $1,
                (($1 AT TIME ZONE 'UTC') + make_interval(mins => $2)) AT TIME ZONE 'UTC'
            )
        $$
        """
    )

    op.create_table(
        "usuario",
        sa.Column(
            "id_usuario",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("dni", sa.String(length=8), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("rol", rol_usuario, nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("apellido", sa.String(length=120), nullable=False),
        sa.Column("habilitado", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "email_verificado", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "debe_cambiar_password",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "fecha_actualizacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ultimo_login", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("dni ~ '^[0-9]{7,8}$'", name="dni_formato"),
        sa.PrimaryKeyConstraint("id_usuario", name="pk_usuario"),
        sa.UniqueConstraint("dni", name="uq_usuario_dni"),
        sa.UniqueConstraint("email", name="uq_usuario_email"),
    )
    op.create_index("ix_usuario_rol", "usuario", ["rol"])

    op.create_table(
        "paciente",
        sa.Column(
            "id_paciente",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("id_usuario", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha_nacimiento", sa.Date(), nullable=True),
        sa.Column("telefono", sa.String(length=30), nullable=True),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "fecha_actualizacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuario.id_usuario"], name="fk_paciente_usuario"),
        sa.PrimaryKeyConstraint("id_paciente", name="pk_paciente"),
        sa.UniqueConstraint("id_usuario", name="uq_paciente_id_usuario"),
    )

    op.create_table(
        "especialidad",
        sa.Column(
            "id_especialidad",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("descripcion", sa.String(length=500), nullable=True),
        sa.Column("activa", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "fecha_actualizacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id_especialidad", name="pk_especialidad"),
        sa.UniqueConstraint("nombre", name="uq_especialidad_nombre"),
    )

    op.create_table(
        "medico",
        sa.Column(
            "id_medico",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("id_usuario", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_especialidad", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("matricula", sa.String(length=50), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "fecha_actualizacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["id_especialidad"],
            ["especialidad.id_especialidad"],
            name="fk_medico_especialidad",
        ),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuario.id_usuario"], name="fk_medico_usuario"),
        sa.PrimaryKeyConstraint("id_medico", name="pk_medico"),
        sa.UniqueConstraint("id_usuario", name="uq_medico_id_usuario"),
        sa.UniqueConstraint("matricula", name="uq_medico_matricula"),
    )

    op.create_table(
        "horario_medico",
        sa.Column(
            "id_horario",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("id_medico", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dia_semana", sa.SmallInteger(), nullable=False),
        sa.Column("hora_inicio", sa.Time(), nullable=False),
        sa.Column("hora_fin", sa.Time(), nullable=False),
        sa.Column("duracion_minutos", sa.Integer(), nullable=False),
        sa.Column("vigente_desde", sa.Date(), nullable=True),
        sa.Column("vigente_hasta", sa.Date(), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "fecha_actualizacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("dia_semana BETWEEN 0 AND 6", name="dia_semana"),
        sa.CheckConstraint("hora_inicio < hora_fin", name="rango_horario"),
        sa.CheckConstraint("duracion_minutos > 0", name="duracion_positiva"),
        sa.ForeignKeyConstraint(["id_medico"], ["medico.id_medico"], name="fk_horario_medico"),
        sa.PrimaryKeyConstraint("id_horario", name="pk_horario_medico"),
    )
    op.create_index("ix_horario_medico_dia", "horario_medico", ["id_medico", "dia_semana"])

    op.create_table(
        "bloqueo_agenda",
        sa.Column(
            "id_bloqueo",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("id_medico", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fin", sa.DateTime(timezone=True), nullable=False),
        sa.Column("motivo", sa.String(length=255), nullable=False),
        sa.Column("id_usuario_creador", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("fin > inicio", name="rango_bloqueo"),
        sa.ForeignKeyConstraint(["id_medico"], ["medico.id_medico"], name="fk_bloqueo_medico"),
        sa.ForeignKeyConstraint(
            ["id_usuario_creador"],
            ["usuario.id_usuario"],
            name="fk_bloqueo_usuario_creador",
        ),
        sa.PrimaryKeyConstraint("id_bloqueo", name="pk_bloqueo_agenda"),
    )
    op.create_index("ix_bloqueo_medico_rango", "bloqueo_agenda", ["id_medico", "inicio", "fin"])

    op.create_table(
        "turno",
        sa.Column(
            "id_turno",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("id_paciente", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_medico", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha_hora", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duracion_minutos", sa.Integer(), nullable=False),
        sa.Column(
            "estado",
            estado_turno,
            server_default=sa.text("'RESERVADO'::estado_turno"),
            nullable=False,
        ),
        sa.Column("fecha_hora_llegada", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_hora_cancelacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id_usuario_creador", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("motivo_cancelacion", motivo_cancelacion, nullable=True),
        sa.Column("detalle_cancelacion", sa.Text(), nullable=True),
        sa.Column("id_usuario_cancelacion", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "fecha_actualizacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("duracion_minutos > 0", name="duracion_positiva"),
        sa.ForeignKeyConstraint(["id_medico"], ["medico.id_medico"], name="fk_turno_medico"),
        sa.ForeignKeyConstraint(
            ["id_paciente"], ["paciente.id_paciente"], name="fk_turno_paciente"
        ),
        sa.ForeignKeyConstraint(
            ["id_usuario_cancelacion"],
            ["usuario.id_usuario"],
            name="fk_turno_usuario_cancelacion",
        ),
        sa.ForeignKeyConstraint(
            ["id_usuario_creador"],
            ["usuario.id_usuario"],
            name="fk_turno_usuario_creador",
        ),
        sa.PrimaryKeyConstraint("id_turno", name="pk_turno"),
    )
    op.create_index("ix_turno_medico_fecha", "turno", ["id_medico", "fecha_hora"])
    op.create_index("ix_turno_paciente_fecha", "turno", ["id_paciente", "fecha_hora"])
    op.create_index("ix_turno_estado_fecha", "turno", ["estado", "fecha_hora"])
    op.create_index("ix_turno_fecha", "turno", ["fecha_hora"])

    op.create_table(
        "nota_seguimiento",
        sa.Column(
            "id_nota",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("id_medico", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_paciente", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_turno", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("contenido", sa.Text(), nullable=False),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "fecha_modificacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["id_medico"], ["medico.id_medico"], name="fk_nota_medico"),
        sa.ForeignKeyConstraint(["id_paciente"], ["paciente.id_paciente"], name="fk_nota_paciente"),
        sa.ForeignKeyConstraint(["id_turno"], ["turno.id_turno"], name="fk_nota_turno"),
        sa.PrimaryKeyConstraint("id_nota", name="pk_nota_seguimiento"),
    )
    op.create_index("ix_nota_medico_paciente", "nota_seguimiento", ["id_medico", "id_paciente"])

    op.create_table(
        "solicitud_cancelacion",
        sa.Column(
            "id_solicitud",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("id_turno", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_paciente", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column(
            "estado",
            estado_solicitud_cancelacion,
            server_default=sa.text("'PENDIENTE'::estado_solicitud_cancelacion"),
            nullable=False,
        ),
        sa.Column("id_usuario_resolucion", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("fecha_resolucion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("detalle_resolucion", sa.Text(), nullable=True),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["id_paciente"], ["paciente.id_paciente"], name="fk_solicitud_paciente"
        ),
        sa.ForeignKeyConstraint(["id_turno"], ["turno.id_turno"], name="fk_solicitud_turno"),
        sa.ForeignKeyConstraint(
            ["id_usuario_resolucion"],
            ["usuario.id_usuario"],
            name="fk_solicitud_usuario_resolucion",
        ),
        sa.PrimaryKeyConstraint("id_solicitud", name="pk_solicitud_cancelacion"),
    )
    op.create_index("ix_solicitud_estado", "solicitud_cancelacion", ["estado"])
    op.create_index("ix_solicitud_turno", "solicitud_cancelacion", ["id_turno"])

    op.create_table(
        "restriccion_usuario",
        sa.Column(
            "id_restriccion",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("id_usuario", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column(
            "fecha_inicio",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("fecha_fin", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activa", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id_usuario_creador", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("fecha_fin > fecha_inicio", name="rango_restriccion"),
        sa.ForeignKeyConstraint(
            ["id_usuario"], ["usuario.id_usuario"], name="fk_restriccion_usuario"
        ),
        sa.ForeignKeyConstraint(
            ["id_usuario_creador"],
            ["usuario.id_usuario"],
            name="fk_restriccion_usuario_creador",
        ),
        sa.PrimaryKeyConstraint("id_restriccion", name="pk_restriccion_usuario"),
    )
    op.create_index(
        "ix_restriccion_usuario_fechas", "restriccion_usuario", ["id_usuario", "fecha_fin"]
    )

    op.create_table(
        "auditoria",
        sa.Column(
            "id_auditoria",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("id_usuario", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("accion", sa.String(length=80), nullable=False),
        sa.Column("entidad", sa.String(length=80), nullable=False),
        sa.Column("entidad_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("datos_antes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("datos_despues", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "fecha_hora",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["id_usuario"], ["usuario.id_usuario"], name="fk_auditoria_usuario"
        ),
        sa.PrimaryKeyConstraint("id_auditoria", name="pk_auditoria"),
    )
    op.create_index("ix_auditoria_fecha", "auditoria", ["fecha_hora"])
    op.create_index("ix_auditoria_entidad", "auditoria", ["entidad", "entidad_id"])

    op.create_table(
        "verificacion_email",
        sa.Column(
            "id_verificacion",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("id_usuario", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("fecha_expiracion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usado", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(
            ["id_usuario"], ["usuario.id_usuario"], name="fk_verificacion_usuario"
        ),
        sa.PrimaryKeyConstraint("id_verificacion", name="pk_verificacion_email"),
        sa.UniqueConstraint("token_hash", name="uq_verificacion_email_token_hash"),
    )
    op.create_index("ix_verificacion_usuario", "verificacion_email", ["id_usuario"])

    op.create_table(
        "recuperacion_password",
        sa.Column(
            "id_recuperacion",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("id_usuario", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("fecha_expiracion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usado", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(
            ["id_usuario"], ["usuario.id_usuario"], name="fk_recuperacion_usuario"
        ),
        sa.PrimaryKeyConstraint("id_recuperacion", name="pk_recuperacion_password"),
        sa.UniqueConstraint("token_hash", name="uq_recuperacion_password_token_hash"),
    )
    op.create_index("ix_recuperacion_usuario", "recuperacion_password", ["id_usuario"])

    op.create_table(
        "notificacion",
        sa.Column(
            "id_notificacion",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("id_usuario_destinatario", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tipo", tipo_notificacion, nullable=False),
        sa.Column("id_turno", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id_solicitud", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subtipo", sa.String(length=32), nullable=True),
        sa.Column(
            "estado",
            estado_notificacion,
            server_default=sa.text("'PENDIENTE'::estado_notificacion"),
            nullable=False,
        ),
        sa.Column("intentos", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("ultimo_error", sa.Text(), nullable=True),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "fecha_programada_envio",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("fecha_envio", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("intentos >= 0", name="intentos_no_negativos"),
        sa.ForeignKeyConstraint(
            ["id_solicitud"],
            ["solicitud_cancelacion.id_solicitud"],
            name="fk_notificacion_solicitud",
        ),
        sa.ForeignKeyConstraint(["id_turno"], ["turno.id_turno"], name="fk_notificacion_turno"),
        sa.ForeignKeyConstraint(
            ["id_usuario_destinatario"],
            ["usuario.id_usuario"],
            name="fk_notificacion_destinatario",
        ),
        sa.PrimaryKeyConstraint("id_notificacion", name="pk_notificacion"),
    )
    op.create_index(
        "ix_notificacion_estado_programada",
        "notificacion",
        ["estado", "fecha_programada_envio"],
    )
    op.create_index("ix_notificacion_destinatario", "notificacion", ["id_usuario_destinatario"])

    # Restricciones de exclusión parciales (Alembic no las autogenera).
    # El rango se calcula con `rango_turno` porque debe ser IMMUTABLE.
    op.execute(
        """
        ALTER TABLE turno
        ADD CONSTRAINT ex_turno_medico
        EXCLUDE USING gist (
            id_medico WITH =,
            rango_turno(fecha_hora, duracion_minutos) WITH &&
        )
        WHERE (estado IN ('RESERVADO', 'EN_ESPERA', 'ATENDIDO'))
        """
    )
    op.execute(
        """
        ALTER TABLE turno
        ADD CONSTRAINT ex_turno_paciente
        EXCLUDE USING gist (
            id_paciente WITH =,
            rango_turno(fecha_hora, duracion_minutos) WITH &&
        )
        WHERE (estado IN ('RESERVADO', 'EN_ESPERA', 'ATENDIDO'))
        """
    )

    # Una sola restricción activa por usuario.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_restriccion_activa_por_usuario
        ON restriccion_usuario (id_usuario)
        WHERE activa
        """
    )

    # Idempotencia de notificaciones (RN-32).
    op.execute(
        """
        CREATE UNIQUE INDEX uq_notificacion_confirmacion_recordatorio
        ON notificacion (id_turno, tipo)
        WHERE tipo IN ('CONFIRMACION_TURNO', 'RECORDATORIO_24H')
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_notificacion_cancelacion
        ON notificacion (id_turno, tipo, subtipo)
        WHERE tipo = 'CANCELACION_TURNO'
        """
    )


def downgrade() -> None:
    op.drop_table("notificacion")
    op.drop_table("recuperacion_password")
    op.drop_table("verificacion_email")
    op.drop_table("auditoria")
    op.drop_table("restriccion_usuario")
    op.drop_table("solicitud_cancelacion")
    op.drop_table("nota_seguimiento")
    op.drop_table("turno")
    op.drop_table("bloqueo_agenda")
    op.drop_table("horario_medico")
    op.drop_table("medico")
    op.drop_table("especialidad")
    op.drop_table("paciente")
    op.drop_table("usuario")

    for enum_name in (
        "estado_notificacion",
        "tipo_notificacion",
        "estado_solicitud_cancelacion",
        "motivo_cancelacion",
        "estado_turno",
        "rol_usuario",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")

    op.execute("DROP FUNCTION IF EXISTS rango_turno(timestamptz, integer)")
