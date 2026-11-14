from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración leída exclusivamente desde variables de entorno."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Sistema de Turnos Médicos"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    api_v1_prefix: str = "/api/v1"

    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:5173"
    timezone: str = "America/Argentina/Buenos_Aires"
    log_level: str = "INFO"
    log_json: bool = True
    request_id_header: str = "X-Request-ID"
    trusted_hosts: str = "localhost,127.0.0.1"
    secure_headers: bool = True

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/turnos"
    alembic_database_url: str | None = None
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False

    redis_url: str = "redis://localhost:6379/0"
    rate_limit_storage_url: str = "redis://localhost:6379/1"
    arq_redis_url: str = "redis://localhost:6379/2"
    refresh_redis_url: str = "redis://localhost:6379/3"

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "turnos-api"
    jwt_audience: str = "turnos-web"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    refresh_cookie_name: str = "refresh_token"
    csrf_cookie_name: str = "csrf_token"
    csrf_header_name: str = "X-CSRF-Token"
    # El refresh solo se manda a /api/v1/auth; el CSRF a toda la API para que
    # cualquier mutación pueda leerlo desde `document.cookie`.
    refresh_cookie_path: str = "/api/v1/auth"
    csrf_cookie_path: str = "/api/v1"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    cookie_domain: str | None = None

    argon2_time_cost: int = 3
    argon2_memory_cost: int = 65536
    argon2_parallelism: int = 2
    password_min_length: int = 10

    rate_limit_login_dni: str = "5/15minutes"
    rate_limit_login_ip: str = "20/15minutes"
    rate_limit_password_reset: str = "3/hour"
    rate_limit_verification_resend: str = "3/hour"
    rate_limit_booking: str = "10/hour"

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_starttls: bool = False
    smtp_from: str = "no-reply@turnos.local"
    smtp_from_name: str = "Sistema de Turnos"
    smtp_timeout_seconds: float = 2.0
    mailpit_url: str = "http://localhost:8025"
    email_verification_token_expire_hours: int = 24
    password_reset_token_expire_hours: int = 1
    notification_max_retries: int = 3
    reminder_lead_hours: int = 24
    reminder_min_anticipation_minutes: int = 1410

    appointment_default_duration_minutes: int = 30
    appointment_tolerance_minutes: int = 10
    cancellation_horizon_hours: int = 24
    booking_horizon_days: int = 90
    booking_min_lead_minutes: int = 0
    slot_granularity_minutes: int = 15
    red_user_restriction_days: int = 30

    seed_admin_email: str = "admin@turnos.local"
    seed_admin_dni: str = "10000000"
    seed_admin_password: str = "Admin12345!"

    @property
    def cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def trusted_hosts_list(self) -> list[str]:
        return [item.strip() for item in self.trusted_hosts.split(",") if item.strip()]

    @property
    def sqlalchemy_url(self) -> str:
        return self.alembic_database_url or self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
