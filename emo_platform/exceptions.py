from contextlib import contextmanager

import aiohttp
import requests


class EmoPlatformEror(Exception):
    def __init__(self, message):
        self.message = message


class RateLimitError(EmoPlatformEror):
    pass


class UnauthorizedError(EmoPlatformEror):
    pass


class NotFoundError(EmoPlatformEror):
    pass


class BadRequestError(EmoPlatformEror):
    pass


class UnknownError(EmoPlatformEror):
    pass


class NoRoomError(EmoPlatformEror):
    pass


class NoRefreshTokenError(EmoPlatformEror):
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


@contextmanager
def aiohttp_error_handler():
    try:
        yield None
    except aiohttp.ClientResponseError as e:
        http_exception = http_status_to_exception(e.status)
        raise http_exception(e.message)
