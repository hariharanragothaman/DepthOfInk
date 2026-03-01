"""Rate limiter singleton, imported by routes and main."""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.rate_limit_default],
    storage_uri="memory://",
    enabled=settings.rate_limit_enabled,
)
