from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.core.config import get_settings

settings = get_settings()
LOCAL_TZ = ZoneInfo(settings.timezone)


def now_utc() -> datetime:
    return datetime.now(UTC)


def to_local(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(LOCAL_TZ)


def to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=LOCAL_TZ)
    return value.astimezone(UTC)
