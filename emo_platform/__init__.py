from .api import Client
from .exceptions import (
    BadRequestError,
    EmoPlatformError,
    NoRefreshTokenError,
    NoRoomError,
    NotFoundError,
    RateLimitError,
    UnauthorizedError,
    UnknownError,
)
from .models import Color, Head, WebHook
