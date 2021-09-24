from contextlib import contextmanager

import requests


class EmoPlatformError(Exception):
    def __init__(self, message):
        self.message = message


class RateLimitError(EmoPlatformError):
    pass


class UnauthorizedError(EmoPlatformError):
    pass


class NotFoundError(EmoPlatformError):
    pass


class BadRequestError(EmoPlatformError):
    pass


class UnknownError(EmoPlatformError):
    pass


class NoRoomError(EmoPlatformError):
    pass


class NoRefreshTokenError(EmoPlatformError):
    pass


def http_status_to_exception(code):
    if code == 400:
        return BadRequestError
    if code == 401:
        return UnauthorizedError
    elif code == 404:
        return NotFoundError
    elif code == 429:
        return RateLimitError
    else:
        return UnknownError


@contextmanager
def http_error_handler():
    try:
        yield None
    except requests.HTTPError as e:
        http_exception = http_status_to_exception(e.response.status_code)
        raise http_exception(e.response.json())
